"""
DeepSeek routes — Sistema OSINT EMI

Expone el análisis de DeepSeek (capa post-BERT):
  - GET  /api/ai/deepseek/insights  → último resumen ejecutivo agregado
  - GET  /api/ai/deepseek/status    → conteo de analizados vs pendientes
  - POST /api/ai/deepseek/ejecutar  → dispara el análisis en segundo plano
"""
import json
import threading
import logging

from flask import Blueprint, jsonify, request

from api.common.database import get_db
from emi_careers import EMI_CAREERS

logger = logging.getLogger("OSINT.API.DeepSeek")

bp = Blueprint('deepseek', __name__)

# Estado simple del job en memoria (un análisis a la vez)
_job_state = {'running': False, 'last_result': None}


def _table_exists(cursor, name) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone() is not None


@bp.route('/api/ai/deepseek/insights')
def deepseek_insights():
    """Devuelve el último resumen ejecutivo generado por DeepSeek."""
    conn = get_db()
    cursor = conn.cursor()
    if not _table_exists(cursor, 'deepseek_resumen_global'):
        conn.close()
        return jsonify({'disponible': False, 'mensaje': 'Aún no se ha ejecutado el análisis DeepSeek.'})

    cursor.execute('''
        SELECT resumen_ejecutivo, sentimiento_general, temas_criticos_json,
               recomendaciones_json, carreras_destacadas_json, total_analizados, fecha
        FROM deepseek_resumen_global
        ORDER BY id DESC LIMIT 1
    ''')
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({'disponible': False, 'mensaje': 'Aún no se ha ejecutado el análisis DeepSeek.'})

    def _parse(s):
        try:
            return json.loads(s or '[]')
        except (json.JSONDecodeError, TypeError):
            return []

    return jsonify({
        'disponible': True,
        'resumenEjecutivo': row['resumen_ejecutivo'],
        'sentimientoGeneral': row['sentimiento_general'],
        'temasCriticos': _parse(row['temas_criticos_json']),
        'recomendaciones': _parse(row['recomendaciones_json']),
        'carrerasDestacadas': _parse(row['carreras_destacadas_json']),
        'totalAnalizados': row['total_analizados'],
        'fecha': row['fecha'],
    })


@bp.route('/api/ai/deepseek/status')
def deepseek_status():
    """Conteo de ítems analizados por DeepSeek vs pendientes (ya pasaron por BERT)."""
    conn = get_db()
    cursor = conn.cursor()

    analizados = 0
    if _table_exists(cursor, 'analisis_deepseek'):
        cursor.execute("SELECT COUNT(*) c FROM analisis_deepseek")
        analizados = cursor.fetchone()['c']

    # Total elegible = posts con sentimiento BERT + comentarios con sentimiento BERT
    cursor.execute('''
        SELECT COUNT(*) c FROM dato_procesado dp
        JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
    ''')
    posts = cursor.fetchone()['c']
    cursor.execute('''
        SELECT COUNT(*) c FROM comentario c
        JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
    ''')
    coments = cursor.fetchone()['c']
    conn.close()

    total = posts + coments
    return jsonify({
        'analizados': analizados,
        'total': total,
        'pendientes': max(0, total - analizados),
        'ejecutando': _job_state['running'],
        'ultimoResultado': _job_state['last_result'],
    })


@bp.route('/api/ai/deepseek/analytics')
def deepseek_analytics():
    """Métricas agregadas de la clasificación IA (DeepSeek) para el dashboard NLP.

    Distingue contenido institucional vs personal y, sobre el institucional,
    entrega distribución de sentimiento, severidad, temas y carreras.
    """
    conn = get_db()
    cursor = conn.cursor()
    if not _table_exists(cursor, 'analisis_deepseek'):
        conn.close()
        return jsonify({'disponible': False})

    cursor.execute("SELECT COUNT(*) c FROM analisis_deepseek")
    total = cursor.fetchone()['c']
    cursor.execute("SELECT es_institucional, COUNT(*) c FROM analisis_deepseek GROUP BY es_institucional")
    inst_map = {row['es_institucional']: row['c'] for row in cursor.fetchall()}
    institucional = inst_map.get(1, 0)
    personal = inst_map.get(0, 0)

    # Distribuciones SOLO sobre contenido institucional
    cursor.execute("SELECT sentimiento, COUNT(*) c FROM analisis_deepseek WHERE es_institucional=1 GROUP BY sentimiento")
    sentimiento = {row['sentimiento']: row['c'] for row in cursor.fetchall()}

    cursor.execute("SELECT severidad, COUNT(*) c FROM analisis_deepseek WHERE es_institucional=1 GROUP BY severidad")
    severidad = {row['severidad']: row['c'] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) c FROM analisis_deepseek WHERE es_institucional=1 AND es_queja=1")
    quejas = cursor.fetchone()['c']

    cursor.execute('''SELECT tema_principal, COUNT(*) c FROM analisis_deepseek
                      WHERE es_institucional=1 AND tema_principal IS NOT NULL
                      GROUP BY tema_principal ORDER BY c DESC LIMIT 10''')
    temas = [{'tema': r['tema_principal'], 'menciones': r['c']} for r in cursor.fetchall()]

    # Carreras (desde carreras_json, solo institucional)
    career_counts = {}
    cursor.execute("SELECT carreras_json FROM analisis_deepseek WHERE es_institucional=1 AND carreras_json IS NOT NULL")
    for r in cursor.fetchall():
        try:
            for cid in json.loads(r['carreras_json']):
                career_counts[cid] = career_counts.get(cid, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    carreras = sorted(
        ({'careerId': cid, 'careerName': EMI_CAREERS.get(cid, cid), 'menciones': n}
         for cid, n in career_counts.items()),
        key=lambda x: x['menciones'], reverse=True)[:10]

    conn.close()
    pct = round(institucional / total * 100, 1) if total else 0
    return jsonify({
        'disponible': total > 0,
        'total': total,
        'institucional': institucional,
        'personal': personal,
        'porcentajeInstitucional': pct,
        'quejas': quejas,
        'sentimiento': sentimiento,
        'severidad': severidad,
        'temas': temas,
        'carreras': carreras,
    })


@bp.route('/api/ai/deepseek/ejecutar', methods=['POST'])
def deepseek_ejecutar():
    """Dispara el análisis DeepSeek en segundo plano."""
    if _job_state['running']:
        return jsonify({'status': 'en_progreso',
                        'mensaje': 'Ya hay un análisis DeepSeek en ejecución.'}), 409

    force = bool(request.json.get('force')) if request.is_json else False

    def run_job():
        _job_state['running'] = True
        try:
            from deepseek_analyzer import analizar_con_deepseek
            _job_state['last_result'] = analizar_con_deepseek(force=force)
        except Exception as e:
            logger.exception("Error en análisis DeepSeek")
            _job_state['last_result'] = {'error': str(e)}
        finally:
            _job_state['running'] = False

    threading.Thread(target=run_job, daemon=True).start()
    return jsonify({'status': 'iniciado',
                    'mensaje': 'Análisis DeepSeek iniciado en segundo plano.'})
