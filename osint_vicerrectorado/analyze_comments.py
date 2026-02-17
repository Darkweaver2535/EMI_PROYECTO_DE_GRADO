#!/usr/bin/env python3
"""
Script para analizar sentimientos de los comentarios usando modelo básico.
"""
import sqlite3
import re
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'osint_emi.db')

# Palabras clave para análisis básico de sentimiento
POSITIVE_WORDS = [
    'felicidades', 'excelente', 'bueno', 'genial', 'increíble', 'bendiciones',
    'gracias', 'éxitos', 'bien', 'mejor', 'amor', 'alegría', 'feliz', 'suerte',
    'bravo', 'exito', 'exitoso', 'orgullo', 'orgulloso', 'admiro', 'apoyo',
    'brillar', 'brillas', 'adelante', 'felicitar', '💪', '👏', '❤️', '🎉', '💙', '💛',
    'hermoso', 'lindo', 'maravilloso', 'perfecto', 'logro', 'logrado'
]

NEGATIVE_WORDS = [
    'malo', 'terrible', 'horror', 'miedo', 'terror', 'problema', 'pésimo',
    'triste', 'decepción', 'decepciona', 'desilusión', 'estafa', 'fraude',
    'engaño', 'peor', 'odio', 'asco', 'horrible', 'desastre', 'fracaso',
    'injusto', 'abuso', 'robo', 'corrupción', '😭', '😖', '☠', '💀', '😫',
    'parcial', 'examen', 'reprobar', 'jalé', 'perdí'
]

def analyze_sentiment(text):
    """Analiza sentimiento de un texto de forma básica"""
    text_lower = text.lower()
    
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)
    
    # Calcular probabilidades
    total = positive_count + negative_count + 1  # +1 para evitar división por cero
    
    prob_positive = (positive_count + 0.33) / (total + 1)
    prob_negative = (negative_count + 0.33) / (total + 1)
    prob_neutral = 1 - prob_positive - prob_negative
    
    # Normalizar
    total_prob = prob_positive + prob_negative + prob_neutral
    prob_positive /= total_prob
    prob_negative /= total_prob
    prob_neutral /= total_prob
    
    # Determinar sentimiento
    if positive_count > negative_count and positive_count > 0:
        sentiment = 'Positivo'
        confidence = prob_positive
    elif negative_count > positive_count and negative_count > 0:
        sentiment = 'Negativo'
        confidence = prob_negative
    else:
        sentiment = 'Neutral'
        confidence = prob_neutral
    
    return {
        'sentimiento': sentiment,
        'confianza': round(confidence, 4),
        'prob_positivo': round(prob_positive, 4),
        'prob_neutral': round(prob_neutral, 4),
        'prob_negativo': round(prob_negative, 4)
    }

def analyze_all_comments():
    """Analiza todos los comentarios sin análisis"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔍 Analizando sentimientos de comentarios...")
    
    # Obtener comentarios sin análisis
    cursor.execute('''
        SELECT c.id_comentario, c.contenido 
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        WHERE ac.id_analisis IS NULL
    ''')
    
    comentarios = cursor.fetchall()
    print(f"   Comentarios a analizar: {len(comentarios)}")
    
    analyzed = 0
    results = {'Positivo': 0, 'Neutral': 0, 'Negativo': 0}
    
    for row in comentarios:
        result = analyze_sentiment(row['contenido'])
        
        cursor.execute('''
            INSERT INTO analisis_comentario 
            (id_comentario, sentimiento, confianza, 
             probabilidad_positivo, probabilidad_neutral, probabilidad_negativo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            row['id_comentario'],
            result['sentimiento'],
            result['confianza'],
            result['prob_positivo'],
            result['prob_neutral'],
            result['prob_negativo']
        ))
        
        results[result['sentimiento']] += 1
        analyzed += 1
    
    conn.commit()
    
    print(f"\n✅ Análisis completado:")
    print(f"   - Comentarios analizados: {analyzed}")
    print(f"   - Positivos: {results['Positivo']}")
    print(f"   - Neutrales: {results['Neutral']}")
    print(f"   - Negativos: {results['Negativo']}")
    
    conn.close()
    return results

if __name__ == '__main__':
    analyze_all_comments()
