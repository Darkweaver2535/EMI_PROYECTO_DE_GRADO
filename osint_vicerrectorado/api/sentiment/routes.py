"""
Sentiment analysis routes
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
from api.common.filters import (
    EXTERNAL_POSTS_FILTER,
    EXTERNAL_PROCESADOS_SUBQUERY,
    INSTITUTIONAL_POSTS_SUBQUERY,
)
from api.common.auth import hash_password, get_active_tokens, get_current_user

bp = Blueprint('sentiment', __name__)

# ============== SENTIMIENTOS ==============
@bp.route('/api/ai/sentiments/distribution')
def sentiment_distribution():
    """Distribución de sentimientos REAL - solo contenido externo (no posts oficiales EMI)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT 
            a.sentimiento_predicho,
            COUNT(*) as cantidad,
            AVG(a.confianza) as confianza_promedio
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        GROUP BY a.sentimiento_predicho
    ''')
    
    result = {'Positivo': 0, 'Negativo': 0, 'Neutral': 0}
    for row in cursor.fetchall():
        result[row['sentimiento_predicho']] = row['cantidad']
    
    total = sum(result.values())
    conn.close()
    
    return jsonify({
        'positive': result.get('Positivo', 0),
        'negative': result.get('Negativo', 0),
        'neutral': result.get('Neutral', 0),
        'total': total,
        'positivePercent': round(result.get('Positivo', 0) / total * 100, 1) if total > 0 else 0,
        'negativePercent': round(result.get('Negativo', 0) / total * 100, 1) if total > 0 else 0,
        'neutralPercent': round(result.get('Neutral', 0) / total * 100, 1) if total > 0 else 0
    })

@bp.route('/api/ai/sentiments/trend')
def sentiment_trend():
    """Tendencia de sentimientos por fecha REAL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT 
            DATE(dp.fecha_publicacion_iso) as fecha,
            a.sentimiento_predicho,
            COUNT(*) as cantidad
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        GROUP BY DATE(dp.fecha_publicacion_iso), a.sentimiento_predicho
        ORDER BY fecha
    ''')
    
    # Mapeo español -> inglés
    sentiment_map = {'positivo': 'positive', 'negativo': 'negative', 'neutral': 'neutral'}
    
    data_by_date = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0})
    for row in cursor.fetchall():
        fecha = row['fecha']
        sent_es = row['sentimiento_predicho'].lower()
        sent_en = sentiment_map.get(sent_es, 'neutral')
        data_by_date[fecha][sent_en] = row['cantidad']
    
    conn.close()
    
    return jsonify({
        'data': [
            {
                'date': fecha,
                'positive': vals['positive'],
                'negative': vals['negative'],
                'neutral': vals['neutral']
            }
            for fecha, vals in sorted(data_by_date.items())
        ]
    })

@bp.route('/api/ai/sentiments/posts')
def top_posts():
    """Posts con mayor engagement - solo contenido externo (no posts oficiales EMI)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as text,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence,
            'facebook' as source,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        ORDER BY dp.engagement_total DESC
        LIMIT 20
    ''')
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id'],
            'text': row['text'],
            'sentiment': row['sentiment'] or 'Neutral',
            'confidence': row['confidence'] or 0.5,
            'source': row['source'],
            'date': row['date'],
            'engagement': row['engagement'] or 0
        })
    
    conn.close()
    return jsonify({'posts': posts})

@bp.route('/api/ai/sentiments/top-posts')
def sentiment_top_posts():
    """Top posts positivos o negativos"""
    post_type = request.args.get('type', 'positive')
    limit = int(request.args.get('limit', 10))
    
    sentiment_filter = 'Positivo' if post_type == 'positive' else 'Negativo'
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(f'''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as text,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence,
            'facebook' as source,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement
        FROM dato_procesado dp
        JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE a.sentimiento_predicho = ?
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        ORDER BY a.confianza DESC, dp.engagement_total DESC
        LIMIT ?
    ''', (sentiment_filter, limit))
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id'],
            'text': row['text'][:200] + '...' if len(row['text'] or '') > 200 else row['text'],
            'sentiment': row['sentiment'],
            'confidence': row['confidence'] or 0.5,
            'source': row['source'],
            'date': row['date'],
            'engagement': row['engagement'] or 0
        })
    
    conn.close()
    return jsonify(posts)

@bp.route('/api/ai/sentiments/kpis')
def sentiment_kpis():
    """KPIs de sentimientos"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Totales - solo contenido externo
    cursor.execute(f'''
        SELECT 
            a.sentimiento_predicho,
            COUNT(*) as cantidad,
            AVG(a.confianza) as confianza_promedio
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        GROUP BY a.sentimiento_predicho
    ''')
    
    result = {'Positivo': 0, 'Negativo': 0, 'Neutral': 0}
    confidences = {}
    for row in cursor.fetchall():
        result[row['sentimiento_predicho']] = row['cantidad']
        confidences[row['sentimiento_predicho']] = row['confianza_promedio'] or 0.5
    
    total = sum(result.values())
    
    # Tendencia (comparar última semana con anterior) - solo contenido externo
    cursor.execute(f'''
        SELECT 
            CASE WHEN DATE(dp.fecha_publicacion_iso) >= DATE('now', '-7 days') THEN 'current' ELSE 'previous' END as period,
            a.sentimiento_predicho,
            COUNT(*) as cantidad
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-14 days')
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
          AND {INSTITUTIONAL_POSTS_SUBQUERY}
        GROUP BY period, a.sentimiento_predicho
    ''')
    
    periods = {'current': {'Positivo': 0, 'Negativo': 0}, 'previous': {'Positivo': 0, 'Negativo': 0}}
    for row in cursor.fetchall():
        period = row['period']
        sent = row['sentimiento_predicho']
        if period in periods and sent in periods[period]:
            periods[period][sent] = row['cantidad']
    
    # Calcular cambio
    pos_change = periods['current']['Positivo'] - periods['previous']['Positivo']
    neg_change = periods['current']['Negativo'] - periods['previous']['Negativo']
    
    conn.close()
    
    pos_pct = round(result.get('Positivo', 0) / total * 100, 1) if total > 0 else 0
    neg_pct = round(result.get('Negativo', 0) / total * 100, 1) if total > 0 else 0
    
    return jsonify({
        'positivePercent': pos_pct,
        'negativePercent': neg_pct,
        'neutralPercent': round(result.get('Neutral', 0) / total * 100, 1) if total > 0 else 0,
        'totalAnalyzed': total,
        'avgConfidence': round(sum(confidences.values()) / len(confidences) if confidences else 0.5, 2),
        'positiveChange': pos_change,
        'negativeChange': neg_change,
        'satisfactionIndex': round(pos_pct - neg_pct, 1)
    })


