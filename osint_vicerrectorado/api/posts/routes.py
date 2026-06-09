"""
Posts and comments routes
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

bp = Blueprint('posts', __name__)

# ============== POSTS ==============
@bp.route('/api/posts')
def get_posts():
    """Lista todos los posts con resumen de comentarios - JERÁRQUICO"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Parámetros de filtrado
    source_id = request.args.get('source_id', type=int)
    platform = request.args.get('platform')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Base query
    query = '''
        SELECT 
            dr.id_dato as id_post,
            f.id_fuente,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as content,
            dr.fecha_publicacion,
            dr.engagement_likes as likes,
            dr.engagement_comments as comments_count,
            dr.engagement_shares as shares,
            dr.engagement_views as views,
            dr.tipo_contenido as content_type,
            dr.url_publicacion as url,
            (SELECT COUNT(*) FROM comentario c WHERE c.id_post = dr.id_dato) as collected_comments,
            dp.sentimiento_basico as sentiment,
            COALESCE(ds.sentimiento, asent.sentimiento_predicho) as ai_sentiment,
            COALESCE(ds.confianza_pseudo, asent.confianza) as ai_confidence
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        LEFT JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento asent ON dp.id_dato_procesado = asent.id_dato_procesado
        LEFT JOIN (
            SELECT id_contenido, sentimiento, ABS(sentimiento_score) AS confianza_pseudo
            FROM analisis_deepseek WHERE tipo_contenido = 'post'
        ) ds ON ds.id_contenido = dp.id_dato_procesado
        WHERE 1=1
    '''
    params = []
    
    if source_id:
        query += ' AND f.id_fuente = ?'
        params.append(source_id)
    
    if platform:
        query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        params.append(platform)
    
    query += ' ORDER BY dr.fecha_publicacion DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
    posts = []
    for row in cursor.fetchall():
        posts.append({
            'id': row['id_post'],
            'sourceId': row['id_fuente'],
            'sourceName': row['source_name'],
            'platform': row['platform'],
            'content': row['content'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'commentsCount': row['comments_count'] or 0,
            'collectedComments': row['collected_comments'] or 0,
            'shares': row['shares'] or 0,
            'views': row['views'] or 0,
            'contentType': row['content_type'],
            'url': row['url'],
            'sentiment': row['ai_sentiment'] or row['sentiment'],
            'aiConfidence': row['ai_confidence']
        })
    
    # Obtener total
    count_query = '''
        SELECT COUNT(*) FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        WHERE 1=1
    '''
    count_params = []
    if source_id:
        count_query += ' AND f.id_fuente = ?'
        count_params.append(source_id)
    if platform:
        count_query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        count_params.append(platform)
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    conn.close()
    return jsonify({
        'posts': posts,
        'total': total,
        'limit': limit,
        'offset': offset
    })

@bp.route('/api/posts/<int:post_id>')
def get_post_detail(post_id):
    """Detalle de un post específico con análisis"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            dr.id_dato as id_post,
            f.id_fuente,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as content,
            dr.fecha_publicacion,
            dr.engagement_likes as likes,
            dr.engagement_comments as comments_count,
            dr.engagement_shares as shares,
            dr.engagement_views as views,
            dr.tipo_contenido as content_type,
            dr.url_publicacion as url,
            dp.contenido_limpio,
            dp.cantidad_palabras,
            dp.engagement_normalizado,
            dp.categoria_preliminar,
            COALESCE(ds.sentimiento, asent.sentimiento_predicho) as ai_sentiment,
            asent.confianza as ai_confidence,
            asent.probabilidad_positivo,
            asent.probabilidad_neutral,
            asent.probabilidad_negativo
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        LEFT JOIN dato_procesado dp ON dr.id_dato = dp.id_dato_original
        LEFT JOIN analisis_sentimiento asent ON dp.id_dato_procesado = asent.id_dato_procesado
        LEFT JOIN analisis_deepseek ds ON ds.tipo_contenido='post' AND ds.id_contenido = dp.id_dato_procesado
        WHERE dr.id_dato = ?
    ''', (post_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Post no encontrado'}), 404
    
    # Resumen de sentimientos de comentarios (prefiere DeepSeek sobre BERT)
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN COALESCE(ds.sentimiento, ac.sentimiento) = 'Positivo' THEN 1 ELSE 0 END) as positivos,
            SUM(CASE WHEN COALESCE(ds.sentimiento, ac.sentimiento) = 'Neutral' THEN 1 ELSE 0 END) as neutrales,
            SUM(CASE WHEN COALESCE(ds.sentimiento, ac.sentimiento) = 'Negativo' THEN 1 ELSE 0 END) as negativos
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        LEFT JOIN analisis_deepseek ds ON ds.tipo_contenido='comentario' AND ds.id_contenido = c.id_comentario
        WHERE c.id_post = ?
    ''', (post_id,))
    comments_sentiment = cursor.fetchone()
    
    conn.close()
    
    return jsonify({
        'id': row['id_post'],
        'sourceId': row['id_fuente'],
        'sourceName': row['source_name'],
        'platform': row['platform'],
        'content': row['content'],
        'cleanContent': row['contenido_limpio'],
        'date': row['fecha_publicacion'],
        'likes': row['likes'] or 0,
        'commentsCount': row['comments_count'] or 0,
        'shares': row['shares'] or 0,
        'views': row['views'] or 0,
        'contentType': row['content_type'],
        'url': row['url'],
        'wordCount': row['cantidad_palabras'],
        'engagementNormalized': row['engagement_normalizado'],
        'category': row['categoria_preliminar'],
        'sentiment': {
            'prediction': row['ai_sentiment'],
            'confidence': row['ai_confidence'],
            'probabilities': {
                'positive': row['probabilidad_positivo'],
                'neutral': row['probabilidad_neutral'],
                'negative': row['probabilidad_negativo']
            }
        },
        'commentsSentiment': {
            'total': comments_sentiment['total'] or 0,
            'positive': comments_sentiment['positivos'] or 0,
            'neutral': comments_sentiment['neutrales'] or 0,
            'negative': comments_sentiment['negativos'] or 0
        }
    })

# ============== COMENTARIOS ==============
@bp.route('/api/posts/<int:post_id>/comments')
def get_post_comments(post_id):
    """Lista todos los comentarios de un post específico"""
    conn = get_db()
    cursor = conn.cursor()
    
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    cursor.execute('''
        SELECT 
            c.id_comentario,
            c.autor,
            c.contenido,
            c.fecha_publicacion,
            c.likes,
            c.respuestas,
            c.es_respuesta,
            c.id_comentario_padre,
            COALESCE(ds.sentimiento, ac.sentimiento) as sentimiento,
            ac.confianza,
            ac.probabilidad_positivo,
            ac.probabilidad_neutral,
            ac.probabilidad_negativo
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        LEFT JOIN analisis_deepseek ds ON ds.tipo_contenido='comentario' AND ds.id_contenido = c.id_comentario
        WHERE c.id_post = ?
        ORDER BY c.fecha_publicacion DESC
        LIMIT ? OFFSET ?
    ''', (post_id, limit, offset))
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'id': row['id_comentario'],
            'postId': post_id,
            'author': row['autor'],
            'content': row['contenido'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'repliesCount': row['respuestas'] or 0,
            'isReply': bool(row['es_respuesta']),
            'parentCommentId': row['id_comentario_padre'],
            'sentiment': {
                'prediction': row['sentimiento'],
                'confidence': row['confianza'],
                'probabilities': {
                    'positive': row['probabilidad_positivo'],
                    'neutral': row['probabilidad_neutral'],
                    'negative': row['probabilidad_negativo']
                }
            } if row['sentimiento'] else None
        })
    
    # Total de comentarios
    cursor.execute('SELECT COUNT(*) FROM comentario WHERE id_post = ?', (post_id,))
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'comments': comments,
        'total': total,
        'limit': limit,
        'offset': offset,
        'postId': post_id
    })

@bp.route('/api/comments')
def get_all_comments():
    """Lista todos los comentarios con filtros"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Filtros
    sentiment = request.args.get('sentiment')
    source_id = request.args.get('source_id', type=int)
    platform = request.args.get('platform')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    query = '''
        SELECT 
            c.id_comentario,
            c.id_post,
            c.autor,
            c.contenido,
            c.fecha_publicacion,
            c.likes,
            f.nombre_fuente as source_name,
            f.tipo_fuente as platform,
            dr.contenido_original as post_content,
            COALESCE(ds.sentimiento, ac.sentimiento) as sentimiento,
            ac.confianza
        FROM comentario c
        JOIN dato_recolectado dr ON c.id_post = dr.id_dato
        JOIN fuente_osint f ON c.id_fuente = f.id_fuente
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        LEFT JOIN analisis_deepseek ds ON ds.tipo_contenido='comentario' AND ds.id_contenido = c.id_comentario
        WHERE 1=1
    '''
    params = []

    if sentiment:
        query += ' AND COALESCE(ds.sentimiento, ac.sentimiento) = ?'
        params.append(sentiment)
    
    if source_id:
        query += ' AND c.id_fuente = ?'
        params.append(source_id)
    
    if platform:
        query += ' AND LOWER(f.tipo_fuente) = LOWER(?)'
        params.append(platform)
    
    query += ' ORDER BY c.fecha_publicacion DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
    comments = []
    for row in cursor.fetchall():
        comments.append({
            'id': row['id_comentario'],
            'postId': row['id_post'],
            'author': row['autor'],
            'content': row['contenido'],
            'date': row['fecha_publicacion'],
            'likes': row['likes'] or 0,
            'sourceName': row['source_name'],
            'platform': row['platform'],
            'postPreview': row['post_content'][:100] + '...' if row['post_content'] and len(row['post_content']) > 100 else row['post_content'],
            'sentiment': row['sentimiento'],
            'confidence': row['confianza']
        })
    
    conn.close()
    
    return jsonify({
        'comments': comments,
        'total': len(comments),
        'limit': limit,
        'offset': offset
    })

# ============== ESTADÍSTICAS JERÁRQUICAS ==============
@bp.route('/api/hierarchy/stats')
def hierarchy_stats():
    """Estadísticas de la estructura jerárquica Fuentes→Posts→Comentarios"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total por nivel
    cursor.execute('SELECT COUNT(*) FROM fuente_osint WHERE activa = 1')
    total_sources = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM dato_recolectado')
    total_posts = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM comentario')
    total_comments = cursor.fetchone()[0]
    
    # Por plataforma
    cursor.execute('''
        SELECT 
            f.tipo_fuente as platform,
            COUNT(DISTINCT f.id_fuente) as sources,
            COUNT(DISTINCT dr.id_dato) as posts,
            COUNT(DISTINCT c.id_comentario) as comments
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        LEFT JOIN comentario c ON dr.id_dato = c.id_post
        GROUP BY f.tipo_fuente
    ''')
    
    by_platform = []
    for row in cursor.fetchall():
        by_platform.append({
            'platform': row['platform'],
            'sources': row['sources'],
            'posts': row['posts'],
            'comments': row['comments']
        })
    
    # Sentimientos de comentarios (prefiere DeepSeek; incluye comentarios de
    # solo emojis que tienen DeepSeek pero no BERT → LEFT JOIN en ambos)
    cursor.execute('''
        SELECT
            COALESCE(ds.sentimiento, ac.sentimiento) as sentimiento,
            COUNT(*) as count
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        LEFT JOIN analisis_deepseek ds ON ds.tipo_contenido='comentario' AND ds.id_contenido = c.id_comentario
        WHERE COALESCE(ds.sentimiento, ac.sentimiento) IS NOT NULL
        GROUP BY COALESCE(ds.sentimiento, ac.sentimiento)
    ''')

    comments_sentiment = {'Positivo': 0, 'Neutral': 0, 'Negativo': 0}
    for row in cursor.fetchall():
        if row['sentimiento'] in comments_sentiment:
            comments_sentiment[row['sentimiento']] = row['count']
    
    conn.close()
    
    return jsonify({
        'totals': {
            'sources': total_sources,
            'posts': total_posts,
            'comments': total_comments
        },
        'byPlatform': by_platform,
        'commentsSentiment': {
            'positive': comments_sentiment['Positivo'],
            'neutral': comments_sentiment['Neutral'],
            'negative': comments_sentiment['Negativo']
        }
    })

@bp.route('/api/hierarchy/tree')
def hierarchy_tree():
    """Árbol jerárquico completo para visualización"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener estructura completa
    cursor.execute('''
        SELECT 
            f.id_fuente,
            f.nombre_fuente,
            f.tipo_fuente,
            dr.id_dato as post_id,
            SUBSTR(dr.contenido_original, 1, 80) as post_preview,
            dr.fecha_publicacion,
            dr.engagement_comments,
            (SELECT COUNT(*) FROM comentario c WHERE c.id_post = dr.id_dato) as collected_comments
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        ORDER BY f.tipo_fuente, f.nombre_fuente, dr.fecha_publicacion DESC
    ''')
    
    # Construir árbol
    tree = {}
    for row in cursor.fetchall():
        source_id = row['id_fuente']
        if source_id not in tree:
            tree[source_id] = {
                'id': source_id,
                'name': row['nombre_fuente'],
                'platform': row['tipo_fuente'],
                'posts': []
            }
        
        if row['post_id']:
            tree[source_id]['posts'].append({
                'id': row['post_id'],
                'preview': row['post_preview'] + '...' if row['post_preview'] else '',
                'date': row['fecha_publicacion'],
                'totalComments': row['engagement_comments'] or 0,
                'collectedComments': row['collected_comments'] or 0
            })
    
    conn.close()
    
    return jsonify(list(tree.values()))


