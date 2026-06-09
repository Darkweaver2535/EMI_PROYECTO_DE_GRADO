"""
Alerts and anomalies routes
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
from emi_careers import EMI_CAREERS

bp = Blueprint('alerts', __name__)


@bp.route('/api/ai/alerts/estadisticas-problemas')
def estadisticas_problemas():
    """Estadísticas reales para la DETECCIÓN DE PROBLEMAS (OE).

    Un "problema" = contenido institucional clasificado por la IA como
    Negativo o como queja. Devuelve agregados listos para graficar:
    por tema, por severidad, por carrera, evolución temporal y tasa global.
    """
    conn = get_db()
    cur = conn.cursor()

    def _existe(t):
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,))
        return cur.fetchone() is not None

    if not _existe('analisis_deepseek'):
        conn.close()
        return jsonify({'disponible': False})

    # Total institucional analizado (denominador para la tasa)
    cur.execute("SELECT COUNT(*) c FROM analisis_deepseek WHERE es_institucional=1")
    total_inst = cur.fetchone()['c']

    # Problemas (posts) con su fecha real de publicación/recolección
    cur.execute('''
        SELECT ds.tema_principal AS tema, ds.severidad AS sev, ds.sentimiento AS sent,
               ds.es_queja AS queja, ds.carreras_json AS carreras, ds.resumen AS resumen,
               DATE(COALESCE(dr.fecha_publicacion, dr.fecha_recoleccion)) AS fecha
        FROM analisis_deepseek ds
        JOIN dato_procesado dp ON ds.id_contenido = dp.id_dato_procesado
        JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
        WHERE ds.tipo_contenido='post' AND ds.es_institucional=1
          AND (ds.sentimiento='Negativo' OR ds.es_queja=1)
    ''')
    rows = [dict(r) for r in cur.fetchall()]

    # Problemas (comentarios)
    cur.execute('''
        SELECT ds.tema_principal AS tema, ds.severidad AS sev, ds.sentimiento AS sent,
               ds.es_queja AS queja, ds.carreras_json AS carreras, ds.resumen AS resumen,
               DATE(COALESCE(c.fecha_publicacion, c.fecha_recoleccion)) AS fecha
        FROM analisis_deepseek ds
        JOIN comentario c ON ds.id_contenido = c.id_comentario
        WHERE ds.tipo_contenido='comentario' AND ds.es_institucional=1
          AND (ds.sentimiento='Negativo' OR ds.es_queja=1)
    ''')
    rows += [dict(r) for r in cur.fetchall()]
    conn.close()

    from collections import defaultdict
    por_tema = defaultdict(lambda: {'problemas': 0, 'negativos': 0, 'quejas': 0})
    por_sev = defaultdict(int)
    por_carrera = defaultdict(int)
    por_fecha = defaultdict(int)
    sev_rank = {'critica': 4, 'alta': 3, 'media': 2, 'baja': 1}
    top = []

    for r in rows:
        tema = (r['tema'] or 'general').strip().lower()
        por_tema[tema]['problemas'] += 1
        if r['sent'] == 'Negativo':
            por_tema[tema]['negativos'] += 1
        if r['queja']:
            por_tema[tema]['quejas'] += 1
        por_sev[(r['sev'] or 'baja')] += 1
        if r['fecha']:
            por_fecha[r['fecha']] += 1
        try:
            for cid in json.loads(r['carreras'] or '[]'):
                por_carrera[cid] += 1
        except (json.JSONDecodeError, TypeError):
            pass
        top.append({
            'tema': r['tema'] or 'general',
            'severidad': r['sev'] or 'baja',
            'resumen': r['resumen'] or '',
            '_rank': sev_rank.get(r['sev'], 0),
        })

    problemas_tema = sorted(
        ({'tema': t.capitalize(), **v} for t, v in por_tema.items()),
        key=lambda x: x['problemas'], reverse=True)[:10]

    severidad = [{'severidad': s, 'cantidad': por_sev[s]}
                 for s in ['critica', 'alta', 'media', 'baja'] if por_sev.get(s)]

    carrera = sorted(
        ({'careerId': cid, 'careerName': EMI_CAREERS.get(cid, cid), 'problemas': n}
         for cid, n in por_carrera.items()),
        key=lambda x: x['problemas'], reverse=True)[:10]

    tendencia = [{'fecha': f, 'problemas': por_fecha[f]} for f in sorted(por_fecha.keys())]

    top.sort(key=lambda x: x['_rank'], reverse=True)
    top_problemas = [{k: v for k, v in t.items() if k != '_rank'} for t in top[:8]]

    total_problemas = len(rows)
    criticos = por_sev.get('critica', 0) + por_sev.get('alta', 0)

    return jsonify({
        'disponible': True,
        'resumen': {
            'totalAnalizado': total_inst,
            'totalProblemas': total_problemas,
            'tasaProblemas': round(total_problemas / total_inst * 100, 1) if total_inst else 0,
            'criticos': criticos,
            'temasAfectados': len(por_tema),
        },
        'porTema': problemas_tema,
        'porSeveridad': severidad,
        'porCarrera': carrera,
        'tendencia': tendencia,
        'topProblemas': top_problemas,
    })

# ============== ALERTAS (Persistentes en tabla alerta) ==============
def _severity_map(sev):
    """Map Spanish severity to English for frontend"""
    m = {'critica': 'critical', 'alta': 'high', 'media': 'medium', 'baja': 'low'}
    return m.get(sev, sev)

def _status_map(est):
    m = {'nueva': 'new', 'en_proceso': 'pending', 'resuelta': 'resolved', 'descartada': 'resolved'}
    return m.get(est, est)

def _alert_row_to_dict(row):
    return {
        'id': str(row['id_alerta']),
        'type': row['tipo'],
        'severity': _severity_map(row['severidad']),
        'severidad': row['severidad'],
        'title': row['titulo'],
        'titulo': row['titulo'],
        'message': row['descripcion'] or '',
        'descripcion': row['descripcion'] or '',
        'source': row['fuente'] or 'facebook',
        'status': _status_map(row['estado']),
        'estado': row['estado'],
        'createdAt': row['fecha_creacion'],
        'confidence': row['confianza'],
        'engagement': row['engagement'] or 0,
        'asignado_a': row['asignado_a'],
        'resolucion': row['resolucion'],
        'fecha_resolucion': row['fecha_resolucion'],
    }

@bp.route('/api/ai/alerts')
def get_alerts():
    """Lista de alertas persistentes con filtros"""
    conn = get_db()
    cursor = conn.cursor()
    severity = request.args.get('severity')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)

    where = []
    params = []
    if severity:
        sev_rev = {'critical': 'critica', 'high': 'alta', 'medium': 'media', 'low': 'baja'}
        where.append('severidad = ?')
        params.append(sev_rev.get(severity, severity))
    if status:
        st_rev = {'new': 'nueva', 'pending': 'en_proceso', 'resolved': 'resuelta'}
        where.append('estado = ?')
        params.append(st_rev.get(status, status))

    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''

    cursor.execute(f'SELECT COUNT(*) as cnt FROM alerta{where_sql}', params)
    total = cursor.fetchone()['cnt']

    offset = (page - 1) * limit
    cursor.execute(f'SELECT * FROM alerta{where_sql} ORDER BY fecha_creacion DESC LIMIT ? OFFSET ?',
                   params + [limit, offset])
    alerts = [_alert_row_to_dict(r) for r in cursor.fetchall()]
    conn.close()

    return jsonify({
        'alerts': alerts,
        'total': total,
        'page': page,
        'pages': max(1, (total + limit - 1) // limit)
    })

@bp.route('/api/ai/alerts/stats')
def get_alert_stats():
    """Estadísticas de alertas persistentes"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as cnt FROM alerta')
    total = cursor.fetchone()['cnt']
    cursor.execute('SELECT severidad, COUNT(*) as cnt FROM alerta GROUP BY severidad')
    by_sev = {r['severidad']: r['cnt'] for r in cursor.fetchall()}
    cursor.execute('SELECT estado, COUNT(*) as cnt FROM alerta GROUP BY estado')
    by_est = {r['estado']: r['cnt'] for r in cursor.fetchall()}
    cursor.execute('SELECT tipo, COUNT(*) as cnt FROM alerta GROUP BY tipo')
    by_type = {r['tipo']: r['cnt'] for r in cursor.fetchall()}

    nuevas = by_est.get('nueva', 0) + by_est.get('en_proceso', 0)
    resueltas = by_est.get('resuelta', 0) + by_est.get('descartada', 0)

    # Last hour / 24h
    now = datetime.now()
    cursor.execute("SELECT COUNT(*) as cnt FROM alerta WHERE fecha_creacion >= ?",
                   ((now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),))
    last_hour = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM alerta WHERE fecha_creacion >= ?",
                   ((now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S'),))
    last_24h = cursor.fetchone()['cnt']

    conn.close()

    return jsonify({
        'totalAlertas': total,
        'totalAlerts': total,
        'total': total,
        'bySeverity': {_severity_map(k): v for k, v in by_sev.items()},
        'byStatus': {'new': by_est.get('nueva', 0), 'pending': by_est.get('en_proceso', 0), 'resolved': resueltas},
        'byType': by_type,
        'critical': by_sev.get('critica', 0),
        'high': by_sev.get('alta', 0),
        'medium': by_sev.get('media', 0),
        'low': by_sev.get('baja', 0),
        'pending': nuevas,
        'resolved': resueltas,
        'lastHour': last_hour,
        'last24Hours': last_24h,
    })

@bp.route('/api/ai/alerts/active')
def get_active_alerts():
    """Alertas activas (no resueltas)"""
    conn = get_db()
    cursor = conn.cursor()
    limit = request.args.get('limit', 10, type=int)
    cursor.execute("SELECT * FROM alerta WHERE estado IN ('nueva','en_proceso') ORDER BY fecha_creacion DESC LIMIT ?", (limit,))
    alerts = [_alert_row_to_dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(alerts)

@bp.route('/api/ai/alerts/<alert_id>')
def get_alert_by_id(alert_id):
    """Obtener alerta por ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    return jsonify(_alert_row_to_dict(row))

@bp.route('/api/ai/alerts/<alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    """Resolver una alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Alerta no encontrada'}), 404
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        UPDATE alerta SET estado = 'resuelta', resolucion = ?, fecha_resolucion = ?
        WHERE id_alerta = ?
    """, (data.get('resolution', 'Resuelta'), now_str, alert_id))
    conn.commit()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    updated = cursor.fetchone()
    conn.close()
    return jsonify(_alert_row_to_dict(updated))

@bp.route('/api/ai/alerts/<alert_id>/read', methods=['PUT'])
def mark_alert_read(alert_id):
    """Marcar alerta como en proceso (leída)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerta SET estado = 'en_proceso' WHERE id_alerta = ? AND estado = 'nueva'", (alert_id,))
    conn.commit()
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (alert_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Alerta no encontrada'}), 404
    return jsonify(_alert_row_to_dict(row))

@bp.route('/api/ai/alerts', methods=['POST'])
def create_alert():
    """Crear alerta manual"""
    data = request.json or {}
    sev_rev = {'critical': 'critica', 'high': 'alta', 'medium': 'media', 'low': 'baja'}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado)
        VALUES (?, ?, ?, ?, ?, 'nueva')
    """, (
        data.get('type', 'manual'),
        sev_rev.get(data.get('severity', 'medium'), data.get('severity', 'media')),
        data.get('title', 'Alerta manual'),
        data.get('message', ''),
        data.get('source', 'manual'),
    ))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.execute('SELECT * FROM alerta WHERE id_alerta = ?', (new_id,))
    row = cursor.fetchone()
    conn.close()
    return jsonify(_alert_row_to_dict(row)), 201

@bp.route('/api/ai/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Eliminar alerta"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM alerta WHERE id_alerta = ?', (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Alerta eliminada'})

# ---------- Anomalías detectadas por Isolation Forest ----------
@bp.route('/api/ai/alerts/anomalies')
def get_anomalies():
    """Historial de anomalías detectadas por IA (Isolation Forest)"""
    conn = get_db()
    cursor = conn.cursor()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    where_parts = []
    params = []
    if start_date:
        where_parts.append('fecha_deteccion >= ?')
        params.append(start_date)
    if end_date:
        where_parts.append('fecha_deteccion <= ?')
        params.append(end_date + ' 23:59:59')
    where_sql = (' WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

    cursor.execute(f'''
        SELECT id_anomalia, tipo_anomalia, descripcion, severidad,
               metrica_afectada, valor_esperado, valor_observado, anomaly_score,
               fecha_deteccion, fecha_ocurrencia, estado, notas, metadata_json
        FROM anomalia_detectada{where_sql}
        ORDER BY fecha_deteccion DESC
    ''', params)

    anomalies = []
    for r in cursor.fetchall():
        anomalies.append({
            'id': r['id_anomalia'],
            'date': r['fecha_deteccion'],
            'metric': r['metrica_afectada'] or r['tipo_anomalia'],
            'type': r['tipo_anomalia'],
            'description': r['descripcion'],
            'severity': r['severidad'],
            'expected': r['valor_esperado'],
            'actual': r['valor_observado'],
            'deviation': r['anomaly_score'],
            'status': r['estado'],
        })
    conn.close()
    return jsonify({'anomalies': anomalies, 'total': len(anomalies)})

# ============== MÓDULOS IA: TENDENCIAS Y CORRELACIONES ==============

@bp.route('/api/ai/analysis/trends')
def get_ai_trends():
    """Tendencias detectadas por análisis estadístico (scipy linregress)"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id_tendencia, periodo, metrica, tipo_tendencia,
               valor_slope, valor_r_squared, confianza,
               fecha_inicio, fecha_fin, datos_puntos,
               estacionalidad_detectada, forecast_json, metadata_json, fecha_analisis
        FROM analisis_tendencia
        ORDER BY fecha_analisis DESC
    ''')
    trends = []
    for r in cursor.fetchall():
        import json as _json
        meta = {}
        if r['metadata_json']:
            try:
                meta = _json.loads(r['metadata_json'])
            except Exception:
                pass
        trends.append({
            'id': r['id_tendencia'],
            'period': r['periodo'],
            'metric': r['metrica'],
            'type': r['tipo_tendencia'],
            'slope': r['valor_slope'],
            'rSquared': r['valor_r_squared'],
            'confidence': r['confianza'],
            'startDate': r['fecha_inicio'],
            'endDate': r['fecha_fin'],
            'dataPoints': r['datos_puntos'],
            'seasonality': bool(r['estacionalidad_detectada']),
            'metadata': meta,
        })
    conn.close()
    return jsonify({'trends': trends, 'total': len(trends)})

@bp.route('/api/ai/analysis/correlations')
def get_ai_correlations():
    """Correlaciones Pearson entre variables del dataset"""
    conn = get_db()
    cursor = conn.cursor()
    only_significant = request.args.get('significant', 'false').lower() == 'true'

    where_sql = ' WHERE es_significativa = 1' if only_significant else ''
    cursor.execute(f'''
        SELECT id_correlacion, variable_1, variable_2,
               coeficiente_correlacion, p_value, es_significativa,
               fuerza, direccion, n_muestras, metodo, fecha_analisis
        FROM correlacion_resultado{where_sql}
        ORDER BY ABS(coeficiente_correlacion) DESC
    ''')
    correlations = []
    for r in cursor.fetchall():
        correlations.append({
            'id': r['id_correlacion'],
            'variable1': r['variable_1'],
            'variable2': r['variable_2'],
            'correlation': r['coeficiente_correlacion'],
            'pValue': r['p_value'],
            'significant': bool(r['es_significativa']),
            'strength': r['fuerza'],
            'direction': r['direccion'],
            'samples': r['n_muestras'],
            'method': r['metodo'],
        })
    conn.close()
    return jsonify({'correlations': correlations, 'total': len(correlations)})

@bp.route('/api/ai/analysis/anomalies')
def get_ai_analysis_anomalies():
    """Alias: anomalías vía ruta de análisis"""
    return get_anomalies()

# ============== CONFIGURACIÓN DE ALERTAS ==============
@bp.route('/api/configuracion-alertas')
def get_config_alertas():
    """Lista configuraciones de alertas"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM configuracion_alerta ORDER BY id_config')
    configs = []
    for row in cursor.fetchall():
        configs.append({
            'id': row['id_config'], 'nombre': row['nombre'],
            'tipo_alerta': row['tipo_alerta'], 'umbral_valor': row['umbral_valor'],
            'umbral_confianza': row['umbral_confianza'], 'severidad_minima': row['severidad_minima'],
            'activa': bool(row['activa']), 'notificar_email': bool(row['notificar_email']),
            'creado_por': row['creado_por'], 'fecha_creacion': row['fecha_creacion'],
        })
    conn.close()
    return jsonify({'configuraciones': configs, 'total': len(configs)})

@bp.route('/api/configuracion-alertas/<int:cid>', methods=['PUT'])
def update_config_alerta(cid):
    """Actualizar configuración de alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    for f in ['nombre', 'tipo_alerta', 'umbral_valor', 'umbral_confianza', 'severidad_minima']:
        if f in data:
            fields.append(f'{f} = ?')
            values.append(data[f])
    if 'activa' in data:
        fields.append('activa = ?')
        values.append(1 if data['activa'] else 0)
    if 'notificar_email' in data:
        fields.append('notificar_email = ?')
        values.append(1 if data['notificar_email'] else 0)
    if fields:
        values.append(cid)
        cursor.execute(f'UPDATE configuracion_alerta SET {", ".join(fields)} WHERE id_config = ?', values)
        conn.commit()
    conn.close()
    return jsonify({'message': 'Configuración actualizada'})

@bp.route('/api/configuracion-alertas', methods=['POST'])
def create_config_alerta():
    """Crear configuración de alerta"""
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracion_alerta (nombre, tipo_alerta, umbral_valor, umbral_confianza, severidad_minima, activa, notificar_email)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('nombre', 'Nueva regla'),
        data.get('tipo_alerta', 'custom'),
        data.get('umbral_valor', 0.7),
        data.get('umbral_confianza', 0.5),
        data.get('severidad_minima', 'media'),
        1 if data.get('activa', True) else 0,
        1 if data.get('notificar_email', False) else 0,
    ))
    conn.commit()
    conn.close()
    return jsonify({'id': cursor.lastrowid, 'message': 'Configuración creada'}), 201

@bp.route('/api/configuracion-alertas/<int:cid>', methods=['DELETE'])
def delete_config_alerta(cid):
    """Eliminar configuración de alerta"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM configuracion_alerta WHERE id_config = ?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Configuración eliminada'})


