"""
Statistics and data routes
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
    INSTITUTIONAL_COMMENTS_SUBQUERY,
)
from api.common.auth import hash_password, get_active_tokens, get_current_user

bp = Blueprint('stats', __name__)

# ============== ESTADÍSTICAS GENERALES ==============
@bp.route('/api/stats')
def stats():
    """Estadísticas generales REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
    total_recolectados = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    total_procesados = cursor.fetchone()[0]
    
    # Contar también comentarios (son contenido externo valioso)
    try:
        cursor.execute('SELECT COUNT(*) FROM comentario')
        total_comentarios = cursor.fetchone()[0]
    except Exception:
        total_comentarios = 0
    
    # Sentimientos: solo de contenido externo (no posts oficiales EMI)
    cursor.execute(f'''
        SELECT COUNT(*) FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    total_analizados = cursor.fetchone()[0]
    
    cursor.execute(f'SELECT SUM(engagement_total) FROM dato_procesado dp WHERE {EXTERNAL_PROCESADOS_SUBQUERY}')
    total_engagement = cursor.fetchone()[0] or 0
    
    cursor.execute(f'''
        SELECT a.sentimiento_predicho, COUNT(*) as c 
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
        GROUP BY a.sentimiento_predicho
    ''')
    sentiments = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return jsonify({
        'totalPosts': total_recolectados,
        'totalComments': total_comentarios,
        'processedPosts': total_procesados,
        'analyzedPosts': total_analizados,
        'totalEngagement': total_engagement,
        'sentiments': sentiments,
        'satisfactionIndex': round(
            sentiments.get('Positivo', 0) / max(total_analizados, 1) * 100, 1
        )
    })

# ============== DATOS POR FUENTE ==============
@bp.route('/api/data/by-source')
def data_by_source():
    """Datos agrupados por fuente REAL"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            f.nombre_fuente as fuente,
            COUNT(dr.id_dato) as cantidad,
            SUM(dr.engagement_likes) as likes,
            SUM(dr.engagement_comments) as comments
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        GROUP BY f.nombre_fuente
    ''')
    
    sources = []
    for row in cursor.fetchall():
        sources.append({
            'name': row['fuente'],
            'count': row['cantidad'],
            'likes': row['likes'] or 0,
            'comments': row['comments'] or 0
        })
    
    conn.close()
    return jsonify({'sources': sources})

# ============== DATOS COMPLETOS ==============
@bp.route('/api/data/all')
def all_data():
    """Todos los datos procesados REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    cursor.execute('''
        SELECT 
            dp.id_dato_procesado as id,
            dp.contenido_limpio as content,
            dp.fecha_publicacion_iso as date,
            dp.engagement_total as engagement,
            dp.semestre,
            a.sentimiento_predicho as sentiment,
            a.confianza as confidence
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        ORDER BY dp.fecha_publicacion_iso DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    data = []
    for row in cursor.fetchall():
        data.append({
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'engagement': row['engagement'] or 0,
            'semester': row['semestre'],
            'sentiment': row['sentiment'] or 'Neutral',
            'confidence': row['confidence'] or 0.5
        })
    
    cursor.execute('SELECT COUNT(*) FROM dato_procesado')
    total = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'data': data,
        'total': total,
        'limit': limit,
        'offset': offset
    })

# ============== HEALTH CHECK ==============
@bp.route('/api/health')
def health():
    """Estado del sistema"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'records': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/')
def index():
    """Información de la API"""
    return jsonify({
        'name': 'OSINT EMI API - Datos Reales',
        'version': '1.0.0',
        'database': 'SQLite3',
        'endpoints': [
            'POST /api/auth/login',
            'GET /api/stats',
            'GET /api/ai/sentiments/distribution',
            'GET /api/ai/sentiments/trend',
            'GET /api/ai/sentiments/posts',
            'GET /api/ai/alerts',
            'GET /api/ai/alerts/stats',
            'GET /api/ai/alerts/active',
            'GET /api/data/by-source',
            'GET /api/data/all',
            'GET /api/health'
        ]
    })

# ============== LOG DE ACTIVIDAD ==============
@bp.route('/api/logs')
def get_logs():
    """Obtener log de actividad"""
    conn = get_db()
    cursor = conn.cursor()
    limit = request.args.get('limit', 50, type=int)
    cursor.execute("""
        SELECT l.*, u.username, u.nombre_completo 
        FROM log_actividad l
        LEFT JOIN usuario u ON l.id_usuario = u.id_usuario
        ORDER BY l.fecha DESC LIMIT ?
    """, (limit,))
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'id': row['id_log'], 'usuario': row['username'] or 'sistema',
            'nombre_usuario': row['nombre_completo'] or 'Sistema',
            'accion': row['accion'], 'detalle': row['detalle'],
            'ip': row['ip_address'], 'fecha': row['fecha']
        })
    conn.close()
    return jsonify({'logs': logs, 'total': len(logs)})

# ============== REPUTACIÓN (DATOS REALES) ==============
import re
from collections import Counter

def extract_words_from_texts(texts):
    """Extrae palabras de textos reales eliminando stopwords"""
    stopwords = {
        'el', 'la', 'de', 'en', 'y', 'a', 'que', 'es', 'un', 'una', 'los', 'las',
        'del', 'al', 'por', 'con', 'para', 'se', 'su', 'como', 'más', 'pero', 'muy',
        'sin', 'sobre', 'este', 'esta', 'son', 'han', 'ha', 'hay', 'ser', 'si', 'no',
        'ya', 'está', 'están', 'fue', 'era', 'puede', 'esto', 'eso', 'todo', 'toda',
        'todos', 'todas', 'tiene', 'tienen', 'hacer', 'hace', 'ver', 'más', 'tan',
        'les', 'nos', 'me', 'te', 'lo', 'le', 'mi', 'tu', 'sus', 'qué', 'quién',
        'cómo', 'cuándo', 'dónde', 'porque', 'aunque', 'también', 'así', 'solo',
        'cada', 'entre', 'desde', 'hasta', 'durante', 'antes', 'después', 'aquí',
        'ahí', 'allí', 'bien', 'mal', 'mucho', 'poco', 'otro', 'otra', 'otros'
    }
    
    word_counts = Counter()
    for text in texts:
        if not text:
            continue
        # Limpiar y tokenizar
        words = re.findall(r'\b[a-záéíóúüñ]+\b', text.lower())
        words = [w for w in words if len(w) > 3 and w not in stopwords]
        word_counts.update(words)
    
    return word_counts

@bp.route('/api/ai/reputation/wordcloud')
def reputation_wordcloud():
    """Nube de palabras REAL extraída de los contenidos de la BD"""
    conn = get_db()
    cursor = conn.cursor()
    
    min_freq = request.args.get('min_frequency', 2, type=int)
    
    # Solo contenido institucional (clasificado por DeepSeek). Se excluye el
    # contenido personal aunque mencione la EMI.
    cursor.execute(f'''
        SELECT dp.contenido_limpio FROM dato_procesado dp
        WHERE dp.contenido_limpio IS NOT NULL
        AND {INSTITUTIONAL_POSTS_SUBQUERY}
    ''')
    texts = [row['contenido_limpio'] for row in cursor.fetchall()]

    # Comentarios institucionales
    try:
        cursor.execute(f'''
            SELECT c.contenido FROM comentario c
            WHERE c.contenido IS NOT NULL AND {INSTITUTIONAL_COMMENTS_SUBQUERY}
        ''')
        texts.extend([row['contenido'] for row in cursor.fetchall()])
    except Exception:
        pass
    
    conn.close()
    
    # Extraer palabras reales
    word_counts = extract_words_from_texts(texts)
    
    # Filtrar por frecuencia mínima y convertir a formato esperado
    wordcloud = [
        {'text': word, 'value': count}
        for word, count in word_counts.most_common(100)
        if count >= min_freq
    ]
    
    return jsonify(wordcloud)

@bp.route('/api/ai/reputation/topics')
def reputation_topics():
    """Clusters temáticos dinámicos según la clasificación de DeepSeek.

    Agrupa `analisis_deepseek` por `tema_principal`. Si DeepSeek aún no ha
    analizado contenido, devuelve [] (el frontend muestra estado vacío).
    """
    conn = get_db()
    cursor = conn.cursor()

    # Solo temas institucionales (sistema académico EMI); se excluye contenido
    # personal/no institucional aunque mencione la universidad.
    cursor.execute('''
        SELECT tema_principal, sentimiento, keywords_json, resumen
        FROM analisis_deepseek
        WHERE tema_principal IS NOT NULL AND es_institucional=1
    ''')
    rows = cursor.fetchall()
    conn.close()

    grupos = {}
    for row in rows:
        tema = (row['tema_principal'] or 'general').strip().lower()
        g = grupos.setdefault(tema, {
            'name': row['tema_principal'] or 'General',
            'mentions': 0, 'positive': 0, 'negative': 0,
            'keywords': Counter(), 'samples': []
        })
        g['mentions'] += 1
        sent = row['sentimiento']
        if sent == 'Positivo':
            g['positive'] += 1
        elif sent == 'Negativo':
            g['negative'] += 1
        try:
            for kw in json.loads(row['keywords_json'] or '[]'):
                if kw:
                    g['keywords'][str(kw).lower()] += 1
        except (json.JSONDecodeError, TypeError):
            pass
        if row['resumen'] and len(g['samples']) < 3:
            g['samples'].append(row['resumen'][:120])

    topics = []
    for tema, g in grupos.items():
        topics.append({
            'id': tema.replace(' ', '_'),
            'name': g['name'].capitalize(),
            'keywords': [w for w, _ in g['keywords'].most_common(5)],
            'documentCount': g['mentions'],
            'sentiment': {
                'positive': g['positive'],
                'negative': g['negative'],
                'neutral': g['mentions'] - g['positive'] - g['negative'],
            },
            'sampleTexts': g['samples'],
        })

    # Limitar a los temas más relevantes para evitar una cola larga de
    # singletons (DeepSeek genera muchos temas únicos). Se mantiene dinámico.
    topics.sort(key=lambda x: x['documentCount'], reverse=True)
    return jsonify(topics[:20])

@bp.route('/api/ai/reputation/heatmap')
def reputation_heatmap():
    """Heatmap de actividad REAL por día y hora"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            strftime('%w', fecha_publicacion_iso) as day_of_week,
            strftime('%H', fecha_publicacion_iso) as hour,
            COUNT(*) as count
        FROM dato_procesado
        WHERE fecha_publicacion_iso IS NOT NULL
        GROUP BY day_of_week, hour
    ''')
    
    # Inicializar matriz 7x24
    heatmap_data = []
    days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
    
    data_dict = {}
    for row in cursor.fetchall():
        key = (int(row['day_of_week']), int(row['hour']))
        data_dict[key] = row['count']
    
    conn.close()
    
    for day_idx, day_name in enumerate(days):
        for hour in range(24):
            count = data_dict.get((day_idx, hour), 0)
            heatmap_data.append({
                'day': day_name,
                'dayIndex': day_idx,
                'hour': hour,
                'value': count
            })
    
    return jsonify(heatmap_data)

@bp.route('/api/ai/reputation/competitors')
def reputation_competitors():
    """Comparación con otras universidades (datos REALES extraídos de los textos)"""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Comparación entre universidades: se usa TODO el discurso público (los
    # nombres de otras universidades no son contenido personal y suelen
    # aparecer en posts comparativos). No se filtra a institucional aquí para
    # no perder menciones de la competencia.
    cursor.execute(f'''
        SELECT dp.contenido_limpio, a.sentimiento_predicho
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    posts = [dict(row) for row in cursor.fetchall()]

    # Textos de comentarios
    try:
        cursor.execute('''
            SELECT c.contenido as contenido_limpio, ac.sentimiento as sentimiento_predicho
            FROM comentario c
            LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        ''')
        comments = [dict(row) for row in cursor.fetchall()]
    except:
        comments = []
        
    all_texts = posts + comments
    
    target_universities = {
        'EMI': ['emi', 'escuela militar', 'ingeniería', 'ingenieria'],
        'UMSA': ['umsa', 'san andrés', 'san andres'],
        'UCB': ['ucb', 'católica', 'catolica'],
        'UPEA': ['upea', 'pública de el alto', 'publica de el alto'],
        'UNIFRANZ': ['unifranz', 'franz tamayo']
    }
    
    competitors_data = []
    colors = ['#1976d2', '#388e3c', '#f57c00', '#7b1fa2', '#d32f2f']
    
    for idx, (name, keywords) in enumerate(target_universities.items()):
        mentions = 0
        positive = 0
        total_with_sentiment = 0
        
        for item in all_texts:
            text = (item['contenido_limpio'] or '').lower()
            if any(kw in text for kw in keywords):
                mentions += 1
                sent = item['sentimiento_predicho']
                if sent:
                    total_with_sentiment += 1
                    if sent == 'Positivo':
                        positive += 1
        
        if mentions > 0:
            sentiment_score = (positive / total_with_sentiment * 100) if total_with_sentiment > 0 else 50
            
            competitors_data.append({
                'name': name,
                'satisfactionScore': round(sentiment_score, 1),
                'mentionsCount': mentions,
                'mentions': mentions,
                'positiveRatio': round(sentiment_score / 100, 2),
                'sentiment': round(sentiment_score, 1),
                'color': colors[idx % len(colors)]
            })
            
    conn.close()
    
    # Ordenar por menciones
    competitors_data.sort(key=lambda x: x['mentions'], reverse=True)
    
    return jsonify(competitors_data)

@bp.route('/api/ai/reputation/metrics')
def reputation_metrics():
    """Métricas generales de reputación REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Volumen de menciones institucionales (posts + comentarios)
    cursor.execute(f'SELECT COUNT(*) FROM dato_procesado dp WHERE {INSTITUTIONAL_POSTS_SUBQUERY}')
    post_volume = cursor.fetchone()[0]

    try:
        cursor.execute(f'SELECT COUNT(*) FROM comentario c WHERE {INSTITUTIONAL_COMMENTS_SUBQUERY}')
        comment_volume = cursor.fetchone()[0]
    except:
        comment_volume = 0

    mention_volume = post_volume + comment_volume

    # Score de sentimiento real (solo institucional)
    cursor.execute(f'''
        SELECT
            SUM(CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) as pos,
            SUM(CASE WHEN a.sentimiento_predicho = 'Negativo' THEN 1 ELSE 0 END) as neg,
            COUNT(*) as total
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {INSTITUTIONAL_POSTS_SUBQUERY}
    ''')
    row = cursor.fetchone()
    pos, neg, total = row['pos'] or 0, row['neg'] or 0, row['total'] or 1
    sentiment_score = round((pos - neg) / total * 100 + 50, 1)  # Normalizado 0-100
    
    # Engagement: promedio de likes+comments+shares por post
    cursor.execute(f'''
        SELECT
            AVG(dp.engagement_total) as avg_engagement,
            SUM(dp.engagement_total) as total_engagement
        FROM dato_procesado dp
        WHERE {INSTITUTIONAL_POSTS_SUBQUERY}
    ''')
    row = cursor.fetchone()
    avg_engagement = row['avg_engagement'] or 0
    total_engagement = row['total_engagement'] or 0
    
    # Alcance estimado basado en views reales
    cursor.execute('''
        SELECT SUM(engagement_views) FROM dato_recolectado
        WHERE engagement_views IS NOT NULL
    ''')
    total_views = cursor.fetchone()[0] or total_engagement
    
    # Calcular tendencia (última semana vs anterior)
    cursor.execute(f'''
        SELECT COUNT(*) FROM dato_procesado dp
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-7 days')
        AND {INSTITUTIONAL_POSTS_SUBQUERY}
    ''')
    recent = cursor.fetchone()[0]
    
    cursor.execute(f'''
        SELECT COUNT(*) FROM dato_procesado dp
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-14 days')
        AND DATE(dp.fecha_publicacion_iso) < DATE('now', '-7 days')
        AND {INSTITUTIONAL_POSTS_SUBQUERY}
    ''')
    previous = cursor.fetchone()[0]
    
    if recent > previous * 1.1:
        trend = 'up'
    elif recent < previous * 0.9:
        trend = 'down'
    else:
        trend = 'stable'
    
    conn.close()
    
    # Score general: sentimiento pesa 60%, ratio pos/total 40%
    positive_ratio = pos / max(total, 1) * 100
    overall_score = round(sentiment_score * 0.6 + positive_ratio * 0.4, 1)
    overall_score = min(max(overall_score, 0), 100)
    
    return jsonify({
        'overallScore': overall_score,
        'mentionVolume': mention_volume,
        'sentimentScore': sentiment_score,
        'engagementRate': round(avg_engagement, 0),
        'reachEstimate': total_views,
        'trend': trend
    })


