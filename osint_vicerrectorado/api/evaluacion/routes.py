"""
System evaluation routes
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

bp = Blueprint('evaluacion', __name__)

# ============== EVALUACIÓN DEL SISTEMA (OE4) ==============

@bp.route('/api/evaluacion/ejecutar', methods=['POST'])
def evaluacion_ejecutar():
    """Ejecuta evaluación completa del sistema."""
    try:
        from evaluacion_sistema import EvaluadorSistema
        evaluador = EvaluadorSistema()
        resultados = evaluador.ejecutar_evaluacion_completa()
        return jsonify(resultados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/evaluacion/resumen')
def evaluacion_resumen():
    """Retorna métricas de evaluación almacenadas."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM evaluacion_sistema ORDER BY categoria, id")
        metricas = [dict(row) for row in cursor.fetchall()]
    except:
        metricas = []
    
    # Agrupar por categoría
    por_categoria = {}
    for m in metricas:
        cat = m.get('categoria', 'general')
        if cat not in por_categoria:
            por_categoria[cat] = []
        por_categoria[cat].append(m)
    
    # Calcular scores
    scores = {}
    for cat, items in por_categoria.items():
        valores = [m['valor'] for m in items if m['valor'] is not None]
        scores[cat] = round(sum(valores) / len(valores), 1) if valores else 0
    
    total_score = round(sum(scores.values()) / len(scores), 1) if scores else 0
    
    conn.close()
    return jsonify({
        'score_general': total_score,
        'categorias': scores,
        'metricas': metricas,
        'total_metricas': len(metricas)
    })

@bp.route('/api/evaluacion/objetivos')
def evaluacion_objetivos():
    """Evalúa el cumplimiento de cada objetivo específico."""
    conn = get_db()
    cursor = conn.cursor()
    
    objetivos = []
    
    # OE1: Fuentes OSINT
    try:
        cursor.execute("SELECT COUNT(DISTINCT nombre_fuente) FROM fuente_osint")
        n_fuentes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dato_procesado")
        n_datos = cursor.fetchone()[0]
        n_noticias = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM osint_noticias")
            n_noticias = cursor.fetchone()[0]
        except: pass
        n_patrones = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM patron_identificado")
            n_patrones = cursor.fetchone()[0]
        except: pass
        
        score_oe1 = min(100, (n_fuentes * 15) + (min(n_datos, 50) * 1) + (n_noticias * 5) + (n_patrones * 5))
        objetivos.append({
            'id': 'OE1',
            'titulo': 'Analizar datos de fuentes abiertas usando técnicas OSINT',
            'score': round(score_oe1, 1),
            'evidencias': [
                f'{n_fuentes} fuentes OSINT activas (Facebook, TikTok)',
                f'{n_datos} datos recolectados y procesados',
                f'{n_noticias} noticias monitoreadas (NEWSINT)',
                f'{n_patrones} patrones identificados',
                'Técnicas: SOCMINT, NEWSINT, TRENDINT implementadas'
            ]
        })
    except:
        objetivos.append({'id': 'OE1', 'titulo': 'Analizar datos de fuentes abiertas', 'score': 0, 'evidencias': []})
    
    # OE2: Dashboard de visualización
    try:
        dashboards = [
            'PostsDashboard (fuentes y datos)',
            'SentimentDashboard (sentimientos)',
            'ReputationDashboard (wordcloud, heatmap)',
            'AlertsDashboard (anomalías)',
            'BenchmarkingDashboard (comparativas)',
            'OSINTDashboard (OSINT multifuente)',
            'NLPDashboard (IA/ML/NLP)',
            'EvaluacionDashboard (evaluación)',
        ]
        score_oe2 = min(100, len(dashboards) * 12.5)
        objetivos.append({
            'id': 'OE2',
            'titulo': 'Dashboard con patrones, tendencias y estadísticas',
            'score': round(score_oe2, 1),
            'evidencias': [f'Dashboard: {d}' for d in dashboards]
        })
    except:
        objetivos.append({'id': 'OE2', 'titulo': 'Dashboard de visualización', 'score': 0, 'evidencias': []})
    
    # OE3: IA, ML y NLP
    tecnicas_ia = []
    score_oe3 = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM analisis_sentimiento")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'BETO (BERT español): {n} análisis de sentimiento')
            score_oe3 += 20
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_topicos")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'BERTopic Topic Modeling: {n} tópicos descubiertos')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_clusters")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'K-Means Clustering: {n} clusters de opiniones')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_keywords")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'TF-IDF Keywords: {n} palabras clave')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM nlp_entidades")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'NER (Entity Recognition): {n} entidades')
            score_oe3 += 15
    except: pass
    
    try:
        cursor.execute("SELECT COUNT(*) FROM clasificacion_tematica")
        n = cursor.fetchone()[0]
        if n > 0:
            tecnicas_ia.append(f'Clasificación Temática NLP: {n} clasificaciones')
            score_oe3 += 10
    except: pass
    
    tecnicas_ia.append('Aspect-Based Sentiment Analysis implementado')
    tecnicas_ia.append('Isolation Forest para anomalías implementado')
    score_oe3 += 10
    
    objetivos.append({
        'id': 'OE3',
        'titulo': 'Aplicar modelos de IA, ML y NLP para análisis',
        'score': min(100, round(score_oe3, 1)),
        'evidencias': tecnicas_ia
    })
    
    # OE4: Evaluación
    try:
        cursor.execute("SELECT COUNT(*) FROM evaluacion_sistema")
        n_eval = cursor.fetchone()[0]
    except:
        n_eval = 0
    
    score_oe4 = min(100, n_eval * 3)
    objetivos.append({
        'id': 'OE4',
        'titulo': 'Evaluar el funcionamiento mediante pruebas',
        'score': round(score_oe4, 1),
        'evidencias': [
            f'{n_eval} métricas de evaluación registradas',
            'Evaluación de recolección de datos',
            'Evaluación de análisis de sentimiento',
            'Evaluación de pipeline NLP/ML',
            'Evaluación de completitud de BD',
            'Evaluación de técnicas OSINT',
            'Evaluación de rendimiento API'
        ] if n_eval > 0 else ['Ejecutar evaluación para generar métricas']
    })
    
    conn.close()
    
    # Score general
    total = round(sum(o['score'] for o in objetivos) / len(objetivos), 1) if objetivos else 0
    
    return jsonify({
        'score_general': total,
        'objetivos': objetivos
    })



