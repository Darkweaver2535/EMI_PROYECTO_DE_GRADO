"""
Academic benchmarking routes
Auto-extracted from api_real.py during modularization.
"""
import os
import json
import hashlib
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, jsonify, request

from api.common.database import get_db
from api.common.filters import EXTERNAL_POSTS_FILTER, EXTERNAL_PROCESADOS_SUBQUERY
from api.common.auth import hash_password, get_active_tokens, get_current_user

bp = Blueprint('benchmarking', __name__)

# ============== BENCHMARKING ACADÉMICO ==============

import re as _re

# -------------------------------------------------------------------
# Las 14 carreras oficiales de la EMI, con keywords inteligentes.
#
# Cada carrera tiene:
#   - exact  : frases que se buscan con substring (alta confianza)
#   - regex  : patrones regex compilados (para evitar falsos positivos,
#              p.ej. "civil" suelto podría coincidir con "civilización",
#              así que usamos \bcivil\b).
#
# El matcher prueba primero exact, luego regex. Una coincidencia basta.
# -------------------------------------------------------------------

EMI_CAREERS = {
    '1': {
        'name': 'Ingeniería Civil',
        'exact': [
            'ingeniería civil', 'ingenieria civil', 'ing. civil', 'ing civil',
        ],
        'regex': [r'\bcivil\b'],
    },
    '2': {
        'name': 'Ingeniería Geográfica',
        'exact': [
            'ingeniería geográfica', 'ingenieria geografica', 'ing. geográfica',
            'ing. geografica', 'ing geográfica', 'ing geografica',
            'geodesia', 'topografía', 'topografia', 'cartografía', 'cartografia',
            'geomática', 'geomatica',
        ],
        'regex': [r'\bgeográfica\b', r'\bgeografica\b'],
    },
    '3': {
        'name': 'Ingeniería Ambiental',
        'exact': [
            'ingeniería ambiental', 'ingenieria ambiental', 'ing. ambiental',
            'ing ambiental', 'medio ambiente', 'gestión ambiental',
            'gestion ambiental',
        ],
        'regex': [r'\bambiental\b'],
    },
    '4': {
        'name': 'Ingeniería de Sistemas',
        'exact': [
            'ingeniería de sistemas', 'ingenieria de sistemas',
            'ing. de sistemas', 'ing de sistemas', 'ing. sistemas',
            'ing sistemas', 'carrera de sistemas',
        ],
        'regex': [r'\bsistemas\b'],
    },
    '5': {
        'name': 'Ingeniería en Telecomunicaciones',
        'exact': [
            'ingeniería en telecomunicaciones', 'ingenieria en telecomunicaciones',
            'ing. telecomunicaciones', 'ing telecomunicaciones',
            'ing. en telecomunicaciones', 'ing en telecomunicaciones',
        ],
        'regex': [r'\btelecomunicaciones\b', r'\btelecom\b'],
    },
    '6': {
        'name': 'Ingeniería en Sistemas Electrónicos',
        'exact': [
            'sistemas electrónicos', 'sistemas electronicos',
            'ingeniería en sistemas electrónicos', 'ingenieria en sistemas electronicos',
            'ing. sistemas electrónicos', 'ing sistemas electronicos',
        ],
        'regex': [r'\belectrónic[ao]s?\b', r'\belectronic[ao]s?\b'],
    },
    '7': {
        'name': 'Ingeniería Industrial',
        'exact': [
            'ingeniería industrial', 'ingenieria industrial',
            'ing. industrial', 'ing industrial',
        ],
        'regex': [r'\bindustrial\b', r'\bindus\b'],
    },
    '8': {
        'name': 'Ingeniería Petrolera',
        'exact': [
            'ingeniería petrolera', 'ingenieria petrolera',
            'ing. petrolera', 'ing petrolera',
            'petróleo', 'petroleo', 'hidrocarburos',
        ],
        'regex': [r'\bpetrolera\b'],
    },
    '9': {
        'name': 'Ingeniería Mecatrónica',
        'exact': [
            'ingeniería mecatrónica', 'ingenieria mecatronica',
            'ing. mecatrónica', 'ing. mecatronica', 'ing mecatronica',
            'ing mecatrónica',
            'electromecánica', 'electromecanica', 'automotriz',
            'robótica', 'robotica',
        ],
        'regex': [r'\bmecatrónica\b', r'\bmecatronica\b'],
    },
    '10': {
        'name': 'Ingeniería Comercial',
        'exact': [
            'ingeniería comercial', 'ingenieria comercial',
            'ing. comercial', 'ing comercial',
        ],
        'regex': [r'\bcomercial\b'],
    },
    '11': {
        'name': 'Ingeniería Financiera',
        'exact': [
            'ingeniería financiera', 'ingenieria financiera',
            'ing. financiera', 'ing financiera',
            'finanzas',
        ],
        'regex': [r'\bfinanciera\b'],
    },
    '12': {
        'name': 'Derecho',
        'exact': [
            'carrera de derecho', 'estudia derecho', 'estudiar derecho',
            'lic. en derecho', 'licenciatura en derecho',
        ],
        'regex': [r'\bderecho\b'],
    },
    '13': {
        'name': 'Ingeniería Agronómica',
        'exact': [
            'ingeniería agronómica', 'ingenieria agronomica',
            'ing. agronómica', 'ing. agronomica', 'ing agronomica',
            'agronomía', 'agronomia',
        ],
        'regex': [r'\bagronómica\b', r'\bagronomica\b', r'\bagronomía\b', r'\bagronomia\b'],
    },
    '14': {
        'name': 'Ingeniería Agroindustrial',
        'exact': [
            'ingeniería agroindustrial', 'ingenieria agroindustrial',
            'ing. agroindustrial', 'ing agroindustrial',
            'agroindustria',
        ],
        'regex': [r'\bagroindustrial\b'],
    },
}

# Pre-compilar regex una sola vez al importar
for _cid, _info in EMI_CAREERS.items():
    _info['_compiled'] = [_re.compile(p, _re.IGNORECASE) for p in _info.get('regex', [])]


def _match_careers_in_text(text):
    """Retorna set de career IDs mencionados en un texto.

    Usa primero coincidencias exactas (substring) por velocidad,
    luego regex con word-boundaries para evitar falsos positivos.
    """
    if not text:
        return set()
    text_lower = text.lower()
    matched = set()
    for cid, info in EMI_CAREERS.items():
        # Fase 1: exact substring (rápido)
        found = False
        for kw in info.get('exact', []):
            if kw in text_lower:
                matched.add(cid)
                found = True
                break
        if found:
            continue
        # Fase 2: regex con word boundaries (preciso)
        for pat in info.get('_compiled', []):
            if pat.search(text_lower):
                matched.add(cid)
                break
    return matched


@bp.route('/api/ai/benchmarking/careers')
def get_career_rankings():
    """Ranking de carreras reales de la EMI basado en menciones en posts externos y comentarios"""
    conn = get_db()
    cursor = conn.cursor()

    career_data = {}
    sent_map = {'Positivo': 1, 'Neutral': 0, 'Negativo': -1}

    # 1) Buscar menciones de carreras en POSTS EXTERNOS (no oficiales EMI)
    cursor.execute('''
        SELECT dr.id_dato, dr.contenido_original, a.sentimiento_predicho, a.confianza,
               dr.engagement_likes, dr.engagement_shares, dr.engagement_comments
        FROM dato_recolectado dr
        JOIN fuente_osint fo ON dr.id_fuente = fo.id_fuente
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE fo.es_oficial = 0 OR fo.es_oficial IS NULL
    ''')
    for r in cursor.fetchall():
        matched = _match_careers_in_text(r['contenido_original'])
        for cid in matched:
            if cid not in career_data:
                career_data[cid] = {'name': EMI_CAREERS[cid]['name'], 'mentions': 0,
                                    'sentiment_sum': 0, 'engagement': 0}
            career_data[cid]['mentions'] += 1
            career_data[cid]['sentiment_sum'] += sent_map.get(r['sentimiento_predicho'], 0)
            career_data[cid]['engagement'] += (
                (r['engagement_likes'] or 0) +
                (r['engagement_shares'] or 0) +
                (r['engagement_comments'] or 0)
            )

    # 2) Buscar menciones de carreras en TODOS los COMENTARIOS (siempre son del público)
    try:
        cursor.execute('''
            SELECT c.contenido
            FROM comentario c
        ''')
        for r in cursor.fetchall():
            matched = _match_careers_in_text(r['contenido'])
            for cid in matched:
                if cid not in career_data:
                    career_data[cid] = {'name': EMI_CAREERS[cid]['name'], 'mentions': 0,
                                        'sentiment_sum': 0, 'engagement': 0}
                career_data[cid]['mentions'] += 1
    except Exception:
        pass

    # Construir ranking solo con carreras reales
    rankings = []
    sorted_careers = sorted(career_data.items(),
                            key=lambda x: x[1]['mentions'], reverse=True)
    for rank, (cid, data) in enumerate(sorted_careers, 1):
        avg_sent = data['sentiment_sum'] / max(data['mentions'], 1)
        rankings.append({
            'careerId': cid,
            'careerName': data['name'],
            'mentions': data['mentions'],
            'sentiment': round(avg_sent, 2),
            'engagement': data['engagement'],
            'rank': rank,
        })

    conn.close()
    return jsonify(rankings)

@bp.route('/api/ai/benchmarking/correlations')
def get_benchmarking_correlations():
    """Matriz de correlaciones para benchmarking (datos reales de correlacion_resultado)"""
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

    # Construir la matriz
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

    return jsonify({
        'variables': var_set,
        'values': matrix,
        'cells': cells,
    })

@bp.route('/api/ai/benchmarking/careers/<career_id>/profile')
def get_career_profile(career_id):
    """Perfil radar de una carrera real de la EMI"""
    career_info = EMI_CAREERS.get(career_id)
    career_name = career_info['name'] if career_info else f'Carrera #{career_id}'

    conn = get_db()
    cursor = conn.cursor()

    # Buscar posts EXTERNOS que mencionan esta carrera
    cursor.execute('''
        SELECT dr.contenido_original, a.sentimiento_predicho, a.confianza,
               dr.engagement_likes, dr.engagement_shares, dr.engagement_comments
        FROM dato_recolectado dr
        JOIN fuente_osint fo ON dr.id_fuente = fo.id_fuente
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE fo.es_oficial = 0 OR fo.es_oficial IS NULL
    ''')

    total = 0
    sent_sum = 0
    eng_sum = 0
    conf_sum = 0
    sent_map = {'Positivo': 1, 'Neutral': 0, 'Negativo': -1}

    for r in cursor.fetchall():
        if career_id in _match_careers_in_text(r['contenido_original']):
            total += 1
            sent_sum += sent_map.get(r['sentimiento_predicho'], 0)
            eng_sum += (r['engagement_likes'] or 0) + (r['engagement_shares'] or 0) + (r['engagement_comments'] or 0)
            conf_sum += (r['confianza'] or 0)

    # También buscar en comentarios
    try:
        cursor.execute('SELECT contenido FROM comentario')
        for r in cursor.fetchall():
            if career_id in _match_careers_in_text(r['contenido']):
                total += 1
    except Exception:
        pass

    conn.close()

    avg_sent = sent_sum / max(total, 1)
    avg_conf = conf_sum / max(total, 1)

    sent_score = max(0, min(100, int((avg_sent + 1) * 50)))
    mention_score = min(100, total * 10)  # escala para pocas menciones
    eng_score = min(100, int(eng_sum / max(total, 1)))
    conf_score = int(avg_conf * 100)
    visibility = (mention_score + eng_score) // 2

    return jsonify({
        'careerId': career_id,
        'careerName': career_name,
        'metrics': {
            'sentiment': sent_score,
            'mentions': mention_score,
            'engagement': eng_score,
            'visibility': visibility,
            'reputation': (sent_score + conf_score) // 2,
        },
    })

@bp.route('/api/ai/benchmarking/careers/<career_id>/trends')
def get_career_trends(career_id):
    """Tendencias históricas de una carrera real de la EMI"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DATE(dr.fecha_recoleccion) as fecha, dr.contenido_original,
               a.sentimiento_predicho,
               COALESCE(dr.engagement_likes,0)+COALESCE(dr.engagement_shares,0)+COALESCE(dr.engagement_comments,0) as eng
        FROM dato_recolectado dr
        JOIN fuente_osint fo ON dr.id_fuente = fo.id_fuente
        JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE fo.es_oficial = 0 OR fo.es_oficial IS NULL
        ORDER BY fecha
    ''')

    # Agrupar por fecha solo posts que mencionan esta carrera
    date_data = {}
    sent_map = {'Positivo': 1, 'Neutral': 0, 'Negativo': -1}
    for r in cursor.fetchall():
        if career_id in _match_careers_in_text(r['contenido_original']):
            fecha = r['fecha']
            if fecha not in date_data:
                date_data[fecha] = {'mentions': 0, 'sent_sum': 0, 'eng': 0}
            date_data[fecha]['mentions'] += 1
            date_data[fecha]['sent_sum'] += sent_map.get(r['sentimiento_predicho'], 0)
            date_data[fecha]['eng'] += r['eng'] or 0

    conn.close()

    trends = []
    for fecha in sorted(date_data.keys()):
        d = date_data[fecha]
        trends.append({
            'date': fecha,
            'mentions': d['mentions'],
            'sentiment': round(d['sent_sum'] / max(d['mentions'], 1), 2),
            'engagement': d['eng'],
        })
    return jsonify(trends)

@bp.route('/api/ai/benchmarking/compare')
def compare_careers():
    """Comparar múltiples carreras/fuentes"""
    career_ids = request.args.get('career_ids', '').split(',')
    results = []
    for cid in career_ids:
        if cid.strip():
            # Reutilizar la lógica del perfil
            with app.test_request_context():
                resp = get_career_profile(cid.strip())
                data = resp.get_json()
                results.append(data)
    return jsonify(results)

@bp.route('/api/careers')
def get_careers_list():
    """Lista de carreras reales de la EMI"""
    careers = []
    for cid, info in EMI_CAREERS.items():
        careers.append({
            'id': cid,
            'name': info['name'],
            'faculty': 'Ingeniería',
        })
    return jsonify(sorted(careers, key=lambda x: x['name']))


