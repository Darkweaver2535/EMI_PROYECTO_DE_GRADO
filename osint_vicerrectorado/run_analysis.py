#!/usr/bin/env python3
"""
Script para analizar sentimientos usando un método simple basado en léxico español
"""
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_writer import DatabaseWriter

# Diccionario de palabras positivas/negativas en español para EMI
PALABRAS_POSITIVAS = [
    'bueno', 'buena', 'excelente', 'genial', 'gracias', 'feliz', 'mejor', 'bien',
    'recomiendo', 'calidad', 'profesional', 'apoyo', 'ayuda', 'importante',
    'éxito', 'logro', 'orgullo', 'amor', 'cariño', 'respeto', 'dedicación',
    'esfuerzo', 'compromiso', 'responsable', 'amable', 'atento', 'servicio',
    'aprendizaje', 'crecimiento', 'oportunidad', 'beneficio', 'ventaja',
    'agradezco', 'encanta', 'increíble', 'maravilloso', 'fantástico', 'perfecto',
    'positivo', 'satisfecho', 'contento', 'alegre', 'motivado', 'inspirador'
]

PALABRAS_NEGATIVAS = [
    'malo', 'mala', 'pésimo', 'horrible', 'terrible', 'problema', 'queja',
    'estafa', 'engaño', 'mentira', 'fraude', 'robo', 'corrupción', 'abuso',
    'pena', 'triste', 'decepción', 'frustración', 'enojo', 'molestia',
    'falta', 'deficiente', 'pobre', 'inadecuado', 'insuficiente', 'lento',
    'caro', 'costoso', 'excesivo', 'injusto', 'desorganizado', 'caos',
    'negligencia', 'irresponsable', 'incompetente', 'prepotente', 'grosero',
    'discriminación', 'favoritismo', 'nepotismo', 'burocracia', 'demora',
    'nunca', 'jamás', 'odio', 'peor', 'desastre', 'vergüenza', 'asco',
    'rotada', 'alardea', 'pena'
]

def analyze_sentiment_simple(text):
    """Análisis de sentimiento simple basado en léxico"""
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    pos_count = sum(1 for word in words if word in PALABRAS_POSITIVAS)
    neg_count = sum(1 for word in words if word in PALABRAS_NEGATIVAS)
    
    total = pos_count + neg_count
    if total == 0:
        return 'neutral', 0.5
    
    pos_ratio = pos_count / total
    neg_ratio = neg_count / total
    
    if pos_ratio > 0.6:
        return 'positivo', min(0.5 + pos_ratio * 0.5, 0.95)
    elif neg_ratio > 0.6:
        return 'negativo', min(0.5 + neg_ratio * 0.5, 0.95)
    else:
        return 'neutral', 0.5 + abs(pos_ratio - neg_ratio) * 0.3

def main():
    db = DatabaseWriter()
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id_dato_procesado, contenido_limpio FROM dato_procesado')
    datos = cursor.fetchall()
    
    print(f'📊 Analizando {len(datos)} textos reales de la BD...\n')
    
    resultados = {'positivo': 0, 'negativo': 0, 'neutral': 0}
    
    for id_dato, texto in datos:
        sentiment, confidence = analyze_sentiment_simple(texto)
        resultados[sentiment] += 1
        
        # Guardar en BD
        cursor.execute('''
            INSERT OR REPLACE INTO analisis_sentimiento 
            (id_dato_procesado, sentimiento_predicho, confianza, modelo_version, fecha_analisis)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (id_dato, sentiment.capitalize(), confidence, 'lexico_es_1.0'))
        
        # Mostrar primeros ejemplos
        if id_dato <= 5:
            print(f'  ID {id_dato}: {sentiment} ({confidence:.2f})')
            print(f'     "{texto[:80]}..."')
    
    conn.commit()
    
    # Verificar
    cursor.execute('SELECT COUNT(*) FROM analisis_sentimiento')
    total = cursor.fetchone()[0]
    
    print(f'\n✅ Análisis completado: {total} registros guardados')
    print(f'\n📈 Distribución de sentimientos:')
    print(f'   Positivo: {resultados["positivo"]} ({resultados["positivo"]/len(datos)*100:.1f}%)')
    print(f'   Negativo: {resultados["negativo"]} ({resultados["negativo"]/len(datos)*100:.1f}%)')
    print(f'   Neutral:  {resultados["neutral"]} ({resultados["neutral"]/len(datos)*100:.1f}%)')

if __name__ == '__main__':
    main()
