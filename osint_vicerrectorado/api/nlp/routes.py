"""
NLP pipeline routes
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

bp = Blueprint('nlp', __name__)

# ============== NLP PIPELINE (OE3) ==============

@bp.route('/api/nlp/ejecutar', methods=['POST'])
def nlp_ejecutar():
    """Ejecuta el pipeline NLP completo."""
    import threading
    def run_nlp():
        try:
            from nlp_pipeline import NLPPipeline
            pipeline = NLPPipeline()
            pipeline.ejecutar_pipeline_completo()
        except Exception as e:
            print(f"Error NLP: {e}")
    
    t = threading.Thread(target=run_nlp, daemon=True)
    t.start()
    return jsonify({'status': 'Pipeline NLP iniciado', 'mensaje': 'Ejecutando TF-IDF, LDA, K-Means, NER...'})

@bp.route('/api/nlp/resumen')
def nlp_resumen():
    """Resumen general del análisis NLP."""
    conn = get_db()
    cursor = conn.cursor()
    
    resultado = {
        'keywords': 0, 'topicos': 0, 'clusters': 0, 'entidades': 0,
        'tecnicas_aplicadas': [], 'resumen_ejecutivo': None
    }
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_keywords")
        resultado['keywords'] = cursor.fetchone()[0]
        if resultado['keywords'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'TF-IDF Keyword Extraction',
                'tipo': 'NLP',
                'resultados': resultado['keywords']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_topicos")
        resultado['topicos'] = cursor.fetchone()[0]
        if resultado['topicos'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Topic Modeling (LDA)',
                'tipo': 'ML',
                'resultados': resultado['topicos']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_clusters")
        resultado['clusters'] = cursor.fetchone()[0]
        if resultado['clusters'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'K-Means Clustering',
                'tipo': 'ML',
                'resultados': resultado['clusters']
            })
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_entidades")
        resultado['entidades'] = cursor.fetchone()[0]
        if resultado['entidades'] > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Named Entity Recognition',
                'tipo': 'NLP',
                'resultados': resultado['entidades']
            })
    except: pass
    
    # Agregar BETO que ya está implementado
    try:
        cursor.execute("SELECT COUNT(*) FROM analisis_sentimiento")
        n_sent = cursor.fetchone()[0]
        if n_sent > 0:
            resultado['tecnicas_aplicadas'].append({
                'nombre': 'Análisis de Sentimiento (BETO)',
                'tipo': 'Deep Learning',
                'resultados': n_sent
            })
    except: pass
    
    try:
        cursor.execute("SELECT contenido FROM nlp_resumen_ejecutivo ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            resultado['resumen_ejecutivo'] = json.loads(row['contenido'])
    except: pass
    
    conn.close()
    return jsonify(resultado)

@bp.route('/api/nlp/keywords')
def nlp_keywords():
    """Retorna keywords extraídas con TF-IDF."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_keywords ORDER BY tfidf_score DESC LIMIT 50")
        keywords = [dict(row) for row in cursor.fetchall()]
    except:
        keywords = []
    conn.close()
    return jsonify(keywords)

@bp.route('/api/nlp/topicos')
def nlp_topicos():
    """Retorna tópicos descubiertos por LDA."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_topicos ORDER BY num_documentos DESC")
        topicos = []
        for row in cursor.fetchall():
            t = dict(row)
            try:
                t['palabras_clave'] = json.loads(t['palabras_clave'])
            except:
                pass
            topicos.append(t)
    except:
        topicos = []
    conn.close()
    return jsonify(topicos)

@bp.route('/api/nlp/clusters')
def nlp_clusters():
    """Retorna clusters de opiniones (K-Means)."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nlp_clusters ORDER BY num_documentos DESC")
        clusters = []
        for row in cursor.fetchall():
            c = dict(row)
            try:
                c['palabras_clave'] = json.loads(c['palabras_clave'])
            except: pass
            try:
                c['textos_representativos'] = json.loads(c['textos_representativos'])
            except: pass
            clusters.append(c)
    except:
        clusters = []
    conn.close()
    return jsonify(clusters)

@bp.route('/api/nlp/entidades')
def nlp_entidades():
    """Retorna entidades extraídas por NER."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT tipo_entidad, entidad, frecuencia 
            FROM nlp_entidades 
            ORDER BY tipo_entidad, frecuencia DESC
        """)
        rows = cursor.fetchall()
        entidades = {}
        for row in rows:
            tipo = row['tipo_entidad']
            if tipo not in entidades:
                entidades[tipo] = []
            entidades[tipo].append({
                'entidad': row['entidad'],
                'frecuencia': row['frecuencia']
            })
    except:
        entidades = {}
    conn.close()
    return jsonify(entidades)

@bp.route('/api/nlp/sentimiento-aspecto')
def nlp_sentimiento_aspecto():
    """Retorna sentimiento por aspecto/tema - siempre calcula en vivo."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Solo contenido externo (confesiones, etc.) + TODOS los comentarios (siempre del público)
        cursor.execute(f"""
            SELECT dp.contenido_limpio as texto, COALESCE(a.sentimiento_predicho, 'Neutral') as sent
            FROM dato_procesado dp
            LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
            WHERE dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 5
            AND {EXTERNAL_PROCESADOS_SUBQUERY}
            UNION ALL
            SELECT c.contenido as texto, COALESCE(ac.sentimiento, 'Neutral') as sent
            FROM comentario c
            LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
            WHERE c.contenido IS NOT NULL AND LENGTH(c.contenido) > 5
        """)
        rows = cursor.fetchall()
        
        aspectos = {
            'Calidad Académica': ['clase', 'profesor', 'docente', 'materia', 'nota', 'examen', 'académic', 'enseñanza', 'educaci', 'carrera', 'ingeniería', 'universidad'],
            'Infraestructura': ['edificio', 'aula', 'laboratorio', 'wifi', 'instalacion', 'campus', 'sede'],
            'Servicios': ['comedor', 'transporte', 'beca', 'tramite', 'secretaria', 'biblioteca', 'servicio', 'pagar', 'formulario', 'costo'],
            'Vida Estudiantil': ['compañero', 'amigo', 'evento', 'deporte', 'actividad', 'confesión', 'semestre', 'estudiante', 'cadete'],
            'Formación Militar': ['militar', 'disciplina', 'formacion', 'valores', 'escuela', 'ejército', 'cuartel', 'uniforme'],
            'Empleo y Futuro': ['trabajo', 'empleo', 'egresado', 'empresa', 'practica', 'profesional', 'futuro', 'oportunidad'],
            'Procesos Administrativos': ['inscripción', 'convocatoria', 'requisito', 'documento', 'trámite', 'admisión', 'proceso'],
        }
        
        resultado = {}
        for asp, kws in aspectos.items():
            pos = neg = neu = 0
            for row in rows:
                txt = (row['texto'] or '').lower()
                if any(kw in txt for kw in kws):
                    sent = (row['sent'] or 'Neutral').lower()
                    if sent == 'positivo' or sent == 'positive': pos += 1
                    elif sent == 'negativo' or sent == 'negative': neg += 1
                    else: neu += 1
            total = pos + neg + neu
            if total > 0:
                resultado[asp] = {
                    'total_menciones': total,
                    'positivos': pos, 'negativos': neg, 'neutrales': neu,
                    'score': round((pos - neg) / total * 100, 1)
                }
        
        conn.close()
        return jsonify(resultado)
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500


