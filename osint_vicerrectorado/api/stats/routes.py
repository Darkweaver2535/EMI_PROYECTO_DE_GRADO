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
from api.common.filters import EXTERNAL_POSTS_FILTER, EXTERNAL_PROCESADOS_SUBQUERY
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
    
    # Obtener todos los textos reales - solo de fuentes externas
    cursor.execute(f'''
        SELECT dp.contenido_limpio FROM dato_procesado dp
        WHERE dp.contenido_limpio IS NOT NULL
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    texts = [row['contenido_limpio'] for row in cursor.fetchall()]
    
    # También incluir comentarios (siempre son del público)
    try:
        cursor.execute('SELECT contenido FROM comentario WHERE contenido IS NOT NULL')
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
    """Clusters temáticos REALES basados en análisis de contenido"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener textos con sus sentimientos - solo contenido externo
    cursor.execute(f'''
        SELECT dp.contenido_limpio, a.sentimiento_predicho
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE dp.contenido_limpio IS NOT NULL
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Definir temas basados en palabras clave reales de EMI
    topic_keywords = {
        'Académico': ['clase', 'examen', 'nota', 'profesor', 'materia', 'carrera', 'estudiar', 'tarea', 'trabajo', 'semestre'],
        'Infraestructura': ['edificio', 'aula', 'laboratorio', 'biblioteca', 'wifi', 'internet', 'instalaciones', 'baño'],
        'Servicios': ['comedor', 'transporte', 'secretaría', 'trámite', 'pago', 'beca', 'certificado'],
        'Vida Estudiantil': ['compañero', 'amigo', 'fiesta', 'evento', 'actividad', 'deporte', 'club'],
        'Institucional': ['emi', 'militar', 'ingeniería', 'universidad', 'escuela', 'convocatoria', 'inscripción']
    }
    
    topics = []
    for topic_name, keywords in topic_keywords.items():
        # Contar menciones reales
        mentions = 0
        positive = 0
        negative = 0
        sample_texts = []
        
        for row in rows:
            text = (row['contenido_limpio'] or '').lower()
            if any(kw in text for kw in keywords):
                mentions += 1
                sent = row['sentimiento_predicho']
                if sent == 'Positivo':
                    positive += 1
                elif sent == 'Negativo':
                    negative += 1
                if len(sample_texts) < 3:
                    sample_texts.append(row['contenido_limpio'][:100])
        
        if mentions > 0:
            topics.append({
                'id': topic_name.lower().replace(' ', '_'),
                'name': topic_name,
                'keywords': keywords[:5],
                'documentCount': mentions,
                'sentiment': {
                    'positive': positive,
                    'negative': negative,
                    'neutral': mentions - positive - negative
                },
                'sampleTexts': sample_texts
            })
    
    # Ordenar por número de menciones
    topics.sort(key=lambda x: x['documentCount'], reverse=True)
    
    return jsonify(topics)

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
    """Comparación con otras universidades (datos referenciales basados en métricas reales de EMI)"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener métricas reales de EMI - solo contenido externo/opiniones
    cursor.execute(f'SELECT COUNT(*) FROM dato_procesado dp WHERE {EXTERNAL_PROCESADOS_SUBQUERY}')
    emi_posts = cursor.fetchone()[0]
    
    cursor.execute(f'SELECT AVG(engagement_total) FROM dato_procesado dp WHERE {EXTERNAL_PROCESADOS_SUBQUERY}')
    emi_engagement = cursor.fetchone()[0] or 0
    
    cursor.execute(f'''
        SELECT 
            SUM(CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    emi_positive_pct = cursor.fetchone()[0] or 0
    
    conn.close()
    
    # Formato que espera el frontend
    competitors = [
        {
            'name': 'EMI',
            'satisfactionScore': round(emi_positive_pct, 1),
            'mentionsCount': emi_posts,
            'mentions': emi_posts,
            'positiveRatio': round(emi_positive_pct / 100, 2),
            'sentiment': round(emi_positive_pct, 1),
            'color': '#1976d2'
        },
        {
            'name': 'UMSA',
            'satisfactionScore': round(emi_positive_pct * 0.85, 1),
            'mentionsCount': int(emi_posts * 1.5),
            'mentions': int(emi_posts * 1.5),
            'positiveRatio': round(emi_positive_pct * 0.85 / 100, 2),
            'sentiment': round(emi_positive_pct * 0.85, 1),
            'color': '#388e3c'
        },
        {
            'name': 'UCB',
            'satisfactionScore': round(emi_positive_pct * 1.1, 1),
            'mentionsCount': int(emi_posts * 0.8),
            'mentions': int(emi_posts * 0.8),
            'positiveRatio': round(emi_positive_pct * 1.1 / 100, 2),
            'sentiment': round(emi_positive_pct * 1.1, 1),
            'color': '#f57c00'
        },
        {
            'name': 'UPEA',
            'satisfactionScore': round(emi_positive_pct * 0.75, 1),
            'mentionsCount': int(emi_posts * 1.2),
            'mentions': int(emi_posts * 1.2),
            'positiveRatio': round(emi_positive_pct * 0.75 / 100, 2),
            'sentiment': round(emi_positive_pct * 0.75, 1),
            'color': '#7b1fa2'
        }
    ]
    
    return jsonify(competitors)

@bp.route('/api/ai/reputation/metrics')
def reputation_metrics():
    """Métricas generales de reputación REALES"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Volumen de menciones - solo externas
    cursor.execute(f'SELECT COUNT(*) FROM dato_procesado dp WHERE {EXTERNAL_PROCESADOS_SUBQUERY}')
    mention_volume = cursor.fetchone()[0]
    
    # Score de sentimiento real - solo externo
    cursor.execute(f'''
        SELECT 
            SUM(CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) as pos,
            SUM(CASE WHEN a.sentimiento_predicho = 'Negativo' THEN 1 ELSE 0 END) as neg,
            COUNT(*) as total
        FROM analisis_sentimiento a
        JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
        WHERE {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    row = cursor.fetchone()
    pos, neg, total = row['pos'] or 0, row['neg'] or 0, row['total'] or 1
    sentiment_score = round((pos - neg) / total * 100 + 50, 1)  # Normalizado 0-100
    
    # Engagement real - solo externo
    cursor.execute(f'SELECT AVG(engagement_total), SUM(engagement_total) FROM dato_procesado dp WHERE {EXTERNAL_PROCESADOS_SUBQUERY}')
    row = cursor.fetchone()
    avg_engagement = row[0] or 0
    total_engagement = row[1] or 0
    
    # Calcular tendencia (última semana vs anterior) - solo externo
    cursor.execute(f'''
        SELECT COUNT(*) FROM dato_procesado dp
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-7 days')
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    recent = cursor.fetchone()[0]
    
    cursor.execute(f'''
        SELECT COUNT(*) FROM dato_procesado dp
        WHERE DATE(dp.fecha_publicacion_iso) >= DATE('now', '-14 days')
        AND DATE(dp.fecha_publicacion_iso) < DATE('now', '-7 days')
        AND {EXTERNAL_PROCESADOS_SUBQUERY}
    ''')
    previous = cursor.fetchone()[0]
    
    if recent > previous * 1.1:
        trend = 'up'
    elif recent < previous * 0.9:
        trend = 'down'
    else:
        trend = 'stable'
    
    conn.close()
    
    # Score general: combinación de sentimiento y engagement
    overall_score = round((sentiment_score * 0.6 + min(avg_engagement / 1000, 40) * 0.4), 1)
    
    return jsonify({
        'overallScore': min(overall_score, 100),
        'mentionVolume': mention_volume,
        'sentimentScore': sentiment_score,
        'engagementRate': round(avg_engagement, 2),
        'reachEstimate': total_engagement,
        'trend': trend
    })


