"""
Academic benchmarking routes — Sistema OSINT EMI

Fuente de datos: tabla `analisis_deepseek` (clasificación dinámica generada por
DeepSeek tras el análisis BERT). NO se usa coincidencia de palabras clave.
Si DeepSeek aún no ha analizado contenido, los endpoints devuelven vacío.
"""
import json
import sqlite3
from collections import defaultdict
from flask import Blueprint, jsonify, request

from api.common.database import get_db
from emi_careers import EMI_CAREERS

bp = Blueprint('benchmarking', __name__)

# ============== BENCHMARKING ACADÉMICO (DeepSeek) ==============


def _load_career_items(conn):
    """Devuelve filas de analisis_deepseek con carreras + métricas asociadas.

    Cada fila: { careers:[ids], sentiment_score, sentimiento, severidad,
                 engagement, fecha }.
    `engagement` solo aplica a posts (likes+shares+comments del post original);
    los comentarios aportan menciones pero engagement 0.

    IMPORTANTE: solo se consideran ítems INSTITUCIONALES (es_institucional=1).
    El sistema es netamente académico de la EMI: el contenido personal
    (confesiones, chismes, declaraciones románticas) se excluye del análisis
    aunque mencione una carrera.
    """
    cur = conn.cursor()
    items = []

    # Posts: unir con el post original para engagement y fecha
    cur.execute('''
        SELECT ds.carreras_json, ds.sentimiento, ds.sentimiento_score, ds.severidad,
               DATE(dr.fecha_recoleccion) AS fecha,
               COALESCE(dr.engagement_likes,0)+COALESCE(dr.engagement_shares,0)
                 +COALESCE(dr.engagement_comments,0) AS engagement
        FROM analisis_deepseek ds
        JOIN dato_procesado dp ON ds.id_contenido = dp.id_dato_procesado
        JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
        WHERE ds.tipo_contenido='post' AND ds.es_institucional=1
    ''')
    for r in cur.fetchall():
        items.append(dict(r))

    # Comentarios: engagement de comentario = likes; fecha de recolección
    cur.execute('''
        SELECT ds.carreras_json, ds.sentimiento, ds.sentimiento_score, ds.severidad,
               DATE(c.fecha_recoleccion) AS fecha,
               COALESCE(c.likes,0) AS engagement
        FROM analisis_deepseek ds
        JOIN comentario c ON ds.id_contenido = c.id_comentario
        WHERE ds.tipo_contenido='comentario' AND ds.es_institucional=1
    ''')
    for r in cur.fetchall():
        items.append(dict(r))

    # Parsear carreras_json una vez
    for it in items:
        try:
            it['careers'] = json.loads(it.get('carreras_json') or '[]')
        except (json.JSONDecodeError, TypeError):
            it['careers'] = []
    return items


@bp.route('/api/ai/benchmarking/careers')
def get_career_rankings():
    """Ranking de carreras basado en la clasificación de DeepSeek."""
    conn = get_db()
    items = _load_career_items(conn)
    conn.close()

    # Inicializar solo las 14 carreras oficiales (aparecen aunque tengan 0)
    data = {cid: {'name': name, 'mentions': 0, 'score_sum': 0.0, 'engagement': 0}
            for cid, name in EMI_CAREERS.items()}

    for it in items:
        for cid in it['careers']:
            if cid not in data:
                continue
            data[cid]['mentions'] += 1
            data[cid]['score_sum'] += (it.get('sentiment_score') or 0.0)
            data[cid]['engagement'] += (it.get('engagement') or 0)

    rankings = []
    ordered = sorted(data.items(), key=lambda x: x[1]['mentions'], reverse=True)
    for rank, (cid, d) in enumerate(ordered, 1):
        avg_score = d['score_sum'] / max(d['mentions'], 1)   # -1..1
        mapped = round((avg_score + 1.0) / 2.0, 2)            # 0..1
        rankings.append({
            'careerId': cid,
            'careerName': d['name'],
            'mentions': d['mentions'],
            'sentiment': mapped,
            'engagement': d['engagement'],
            'rank': rank,
        })
    return jsonify(rankings)


@bp.route('/api/ai/benchmarking/correlations')
def get_benchmarking_correlations():
    """Matriz de correlaciones (datos reales de correlacion_resultado)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT variable_1, variable_2, coeficiente_correlacion, p_value, es_significativa, fuerza
        FROM correlacion_resultado
        ORDER BY id_correlacion
    ''')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({'variables': [], 'values': [], 'cells': []})

    var_set = []
    for r in rows:
        if r['variable_1'] not in var_set:
            var_set.append(r['variable_1'])
        if r['variable_2'] not in var_set:
            var_set.append(r['variable_2'])

    n = len(var_set)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        matrix[i][i] = 1.0

    cells = []
    for r in rows:
        i = var_set.index(r['variable_1'])
        j = var_set.index(r['variable_2'])
        val = r['coeficiente_correlacion']
        matrix[i][j] = val
        matrix[j][i] = val

        sig = 'none'
        if r['es_significativa']:
            strength = r['fuerza'] or ''
            if 'muy_fuerte' in strength or 'fuerte' in strength:
                sig = 'high'
            elif 'moderada' in strength:
                sig = 'medium'
            else:
                sig = 'low'
        cells.append({
            'variable1': r['variable_1'],
            'variable2': r['variable_2'],
            'correlation': val,
            'pValue': r['p_value'],
            'significance': sig,
        })

    return jsonify({'variables': var_set, 'values': matrix, 'cells': cells})


@bp.route('/api/ai/benchmarking/careers/<career_id>/profile')
def get_career_profile(career_id):
    """Perfil radar de una carrera (clasificación DeepSeek)."""
    career_name = EMI_CAREERS.get(career_id, f'Carrera #{career_id}')

    conn = get_db()
    items = _load_career_items(conn)
    conn.close()

    total = 0
    score_sum = 0.0
    eng_sum = 0
    for it in items:
        if career_id in it['careers']:
            total += 1
            score_sum += (it.get('sentiment_score') or 0.0)
            eng_sum += (it.get('engagement') or 0)

    avg_score = score_sum / max(total, 1)                 # -1..1
    sent_score = max(0, min(100, int((avg_score + 1) * 50)))
    mention_score = min(100, total * 10)
    eng_score = min(100, int(eng_sum / max(total, 1)))
    visibility = (mention_score + eng_score) // 2

    return jsonify({
        'careerId': career_id,
        'careerName': career_name,
        'metrics': {
            'sentiment': sent_score,
            'mentions': mention_score,
            'engagement': eng_score,
            'visibility': visibility,
            'reputation': (sent_score + visibility) // 2,
        },
    })


@bp.route('/api/ai/benchmarking/careers/<career_id>/trends')
def get_career_trends(career_id):
    """Tendencias históricas de una carrera (clasificación DeepSeek)."""
    conn = get_db()
    items = _load_career_items(conn)
    conn.close()

    date_data = defaultdict(lambda: {'mentions': 0, 'score_sum': 0.0, 'eng': 0})
    for it in items:
        if career_id in it['careers']:
            fecha = it.get('fecha') or 'sin-fecha'
            date_data[fecha]['mentions'] += 1
            date_data[fecha]['score_sum'] += (it.get('sentiment_score') or 0.0)
            date_data[fecha]['eng'] += (it.get('engagement') or 0)

    trends = []
    for fecha in sorted(date_data.keys()):
        d = date_data[fecha]
        trends.append({
            'date': fecha,
            'mentions': d['mentions'],
            'sentiment': round(d['score_sum'] / max(d['mentions'], 1), 2),
            'engagement': d['eng'],
        })
    return jsonify(trends)


@bp.route('/api/ai/benchmarking/compare')
def compare_careers():
    """Comparar múltiples carreras."""
    career_ids = request.args.get('career_ids', '').split(',')
    results = []
    for cid in career_ids:
        cid = cid.strip()
        if cid:
            resp = get_career_profile(cid)
            results.append(resp.get_json())
    return jsonify(results)


@bp.route('/api/careers')
def get_careers_list():
    """Lista de las carreras oficiales de la EMI."""
    careers = [{'id': cid, 'name': name, 'faculty': 'Ingeniería'}
               for cid, name in EMI_CAREERS.items()]
    return jsonify(sorted(careers, key=lambda x: x['name']))
