#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
Ejecución Completa de BETO — Análisis de Sentimientos con IA
═══════════════════════════════════════════════════════════════

Este script ejecuta el modelo BETO (Bidirectional Encoder Representations 
from Transformers for Spanish) sobre TODOS los datos del sistema:

1. Posts procesados (dato_procesado) → analisis_sentimiento
2. Comentarios (comentario) → analisis_comentario

Modelo base: dccuchile/bert-base-spanish-wwm-uncased (BETO)
Fine-tuned: finiteautomata/beto-sentiment-analysis (TASS dataset)
Clasificación: 3 clases (Positivo, Neutral, Negativo)
Framework: PyTorch + Hugging Face Transformers

Referencia: Pérez, J.M., Giudici, J.C., & Luque, F. (2021)
            pysentimiento: A Python Toolkit for Sentiment Analysis
            and SocialNLP tasks

Autor: Sistema SADUTO
Fecha: Febrero 2026
"""

import os
import sys
import time
import sqlite3
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("BETO")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'osint_emi.db')

# Verificar que existe la BD
if not os.path.exists(DB_PATH):
    logger.error(f"Base de datos no encontrada: {DB_PATH}")
    sys.exit(1)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cargar_beto():
    """
    Carga el modelo BETO fine-tuned para análisis de sentimiento en español.
    
    Modelo: finiteautomata/beto-sentiment-analysis
    Base: dccuchile/bert-base-spanish-wwm-uncased (BETO)
    Fine-tuned en: TASS dataset (Spanish sentiment analysis)
    Etiquetas: POS, NEU, NEG → Positivo, Neutral, Negativo
    """
    logger.info("=" * 60)
    logger.info("CARGANDO MODELO BETO — Sentiment Analysis")
    logger.info("Base: dccuchile/bert-base-spanish-wwm-uncased")
    logger.info("Fine-tuned: finiteautomata/beto-sentiment-analysis")
    logger.info("Dataset: TASS (Spanish sentiment benchmarks)")
    logger.info("=" * 60)
    
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    
    # BETO fine-tuned para sentiment analysis en español
    # Base: dccuchile/bert-base-spanish-wwm-uncased
    # Fine-tuned en TASS dataset por Pérez et al. (2021)
    model_name = "finiteautomata/beto-sentiment-analysis"
    
    # Detectar dispositivo
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info("Dispositivo: CUDA (GPU)")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        logger.info("Dispositivo: MPS (Apple Silicon)")
    else:
        device = torch.device("cpu")
        logger.info("Dispositivo: CPU")
    
    # Verificar si existe modelo fine-tuned local (entrenado con datos propios)
    local_model_path = os.path.join(BASE_DIR, 'ai', 'models', 'beto_finetuned')
    config_file = os.path.join(local_model_path, 'config.json')
    
    if os.path.exists(config_file):
        logger.info(f"Cargando modelo fine-tuned local: {local_model_path}")
        model = AutoModelForSequenceClassification.from_pretrained(
            local_model_path,
            local_files_only=True
        )
        tokenizer = AutoTokenizer.from_pretrained(
            local_model_path,
            local_files_only=True
        )
        modelo_version = "beto_sentiment_finetuned_local"
    else:
        logger.info(f"Cargando modelo desde Hugging Face: {model_name}")
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        modelo_version = "beto_sentiment_1.0"
    
    model.to(device)
    model.eval()
    
    # Info del modelo
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Modelo cargado exitosamente")
    logger.info(f"Parametros: {n_params:,}")
    logger.info(f"Arquitectura: BertForSequenceClassification")
    logger.info(f"Etiquetas: POS (Positivo), NEU (Neutral), NEG (Negativo)")
    logger.info(f"Version: {modelo_version}")
    
    return model, tokenizer, device, modelo_version


def predecir_sentimiento(model, tokenizer, device, texto, max_length=512):
    """Predice sentimiento de un texto individual con BETO."""
    import torch
    import numpy as np
    
    # Mapeo de labels del modelo finiteautomata/beto-sentiment-analysis
    # El modelo usa: POS=0, NEG=1, NEU=2 (según config)
    # Obtenemos el mapeo dinámicamente del modelo
    id2label = model.config.id2label
    
    # Mapeo a nuestro formato
    LABEL_NORMALIZE = {"POS": "Positivo", "NEG": "Negativo", "NEU": "Neutral",
                       "Positivo": "Positivo", "Negativo": "Negativo", "Neutral": "Neutral"}
    
    # Tokenizar
    inputs = tokenizer(
        texto,
        truncation=True,
        max_length=max_length,
        padding='max_length',
        return_tensors='pt'
    )
    
    # Mover a dispositivo
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Inferencia
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=-1)
    
    probs = probabilities[0].cpu().numpy()
    predicted_idx = int(np.argmax(probs))
    confidence = float(probs[predicted_idx])
    
    # Obtener label del modelo y normalizar
    raw_label = id2label[predicted_idx]
    sentimiento = LABEL_NORMALIZE.get(raw_label, raw_label)
    
    # Obtener probabilidades por sentimiento
    prob_map = {}
    for idx, label in id2label.items():
        norm_label = LABEL_NORMALIZE.get(label, label)
        prob_map[norm_label] = float(probs[idx])
    
    return {
        "sentimiento": sentimiento,
        "confianza": confidence,
        "prob_positivo": prob_map.get("Positivo", 0.0),
        "prob_neutral": prob_map.get("Neutral", 0.0),
        "prob_negativo": prob_map.get("Negativo", 0.0)
    }


def predecir_batch(model, tokenizer, device, textos, batch_size=8, max_length=512):
    """Predicción en batch para eficiencia."""
    import torch
    import numpy as np
    
    # Mapeo dinámico del modelo
    id2label = model.config.id2label
    LABEL_NORMALIZE = {"POS": "Positivo", "NEG": "Negativo", "NEU": "Neutral",
                       "Positivo": "Positivo", "Negativo": "Negativo", "Neutral": "Neutral"}
    
    resultados = []
    
    for i in range(0, len(textos), batch_size):
        batch = textos[i:i + batch_size]
        
        # Tokenizar batch
        inputs = tokenizer(
            batch,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors='pt'
        )
        
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)
        
        probs = probabilities.cpu().numpy()
        
        for j in range(len(batch)):
            predicted_idx = int(np.argmax(probs[j]))
            confidence = float(probs[j][predicted_idx])
            
            raw_label = id2label[predicted_idx]
            sentimiento = LABEL_NORMALIZE.get(raw_label, raw_label)
            
            # Probabilidades por sentimiento
            prob_map = {}
            for idx, label in id2label.items():
                norm_label = LABEL_NORMALIZE.get(label, label)
                prob_map[norm_label] = float(probs[j][idx])
            
            resultados.append({
                "sentimiento": sentimiento,
                "confianza": confidence,
                "prob_positivo": prob_map.get("Positivo", 0.0),
                "prob_neutral": prob_map.get("Neutral", 0.0),
                "prob_negativo": prob_map.get("Negativo", 0.0)
            })
    
    return resultados


def analizar_posts(model, tokenizer, device, modelo_version):
    """Analiza todos los posts de dato_procesado con BETO."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("FASE 1: ANALISIS DE SENTIMIENTO — POSTS")
    logger.info("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener todos los posts
    cursor.execute("""
        SELECT id_dato_procesado, contenido_limpio 
        FROM dato_procesado 
        WHERE contenido_limpio IS NOT NULL AND LENGTH(contenido_limpio) > 5
        ORDER BY id_dato_procesado
    """)
    datos = cursor.fetchall()
    total = len(datos)
    
    logger.info(f"Posts a analizar: {total}")
    
    if total == 0:
        logger.warning("No hay posts para analizar")
        conn.close()
        return 0
    
    # Preparar textos
    ids = [row['id_dato_procesado'] for row in datos]
    textos = [row['contenido_limpio'] for row in datos]
    
    # Ejecutar BETO en batch
    logger.info("Ejecutando inferencia BETO...")
    start_time = time.time()
    
    resultados = predecir_batch(model, tokenizer, device, textos, batch_size=8)
    
    elapsed = time.time() - start_time
    logger.info(f"Inferencia completada en {elapsed:.1f}s ({elapsed/total*1000:.0f}ms/texto)")
    
    # Limpiar registros anteriores
    cursor.execute("DELETE FROM analisis_sentimiento")
    logger.info("Registros anteriores (lexico_es_1.0) eliminados")
    
    # Guardar nuevos resultados BETO
    conteo = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    confianzas = []
    
    for i, (id_dato, resultado) in enumerate(zip(ids, resultados)):
        cursor.execute("""
            INSERT INTO analisis_sentimiento 
            (id_dato_procesado, sentimiento_predicho, confianza, 
             probabilidad_positivo, probabilidad_neutral, probabilidad_negativo,
             modelo_version, fecha_analisis)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            id_dato,
            resultado['sentimiento'],
            resultado['confianza'],
            resultado['prob_positivo'],
            resultado['prob_neutral'],
            resultado['prob_negativo'],
            modelo_version
        ))
        
        conteo[resultado['sentimiento']] += 1
        confianzas.append(resultado['confianza'])
        
        # Mostrar progreso
        if (i + 1) % 10 == 0 or (i + 1) == total:
            logger.info(f"  Procesados: {i+1}/{total}")
    
    conn.commit()
    
    # Resumen
    prom_conf = sum(confianzas) / len(confianzas) if confianzas else 0
    logger.info("")
    logger.info("--- RESULTADOS POSTS ---")
    logger.info(f"Total analizados: {total}")
    logger.info(f"  Positivo: {conteo['Positivo']} ({conteo['Positivo']/total*100:.1f}%)")
    logger.info(f"  Neutral:  {conteo['Neutral']} ({conteo['Neutral']/total*100:.1f}%)")
    logger.info(f"  Negativo: {conteo['Negativo']} ({conteo['Negativo']/total*100:.1f}%)")
    logger.info(f"Confianza promedio: {prom_conf:.4f} ({prom_conf*100:.1f}%)")
    logger.info(f"Modelo: {modelo_version}")
    
    conn.close()
    return total


def analizar_comentarios(model, tokenizer, device, modelo_version):
    """Analiza todos los comentarios con BETO."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("FASE 2: ANALISIS DE SENTIMIENTO — COMENTARIOS")
    logger.info("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener todos los comentarios
    cursor.execute("""
        SELECT id_comentario, contenido 
        FROM comentario 
        WHERE contenido IS NOT NULL AND LENGTH(contenido) > 5
        ORDER BY id_comentario
    """)
    datos = cursor.fetchall()
    total = len(datos)
    
    logger.info(f"Comentarios a analizar: {total}")
    
    if total == 0:
        logger.warning("No hay comentarios para analizar")
        conn.close()
        return 0
    
    # Preparar textos
    ids = [row['id_comentario'] for row in datos]
    textos = [row['contenido'] for row in datos]
    
    # Ejecutar BETO en batch
    logger.info("Ejecutando inferencia BETO...")
    start_time = time.time()
    
    resultados = predecir_batch(model, tokenizer, device, textos, batch_size=8)
    
    elapsed = time.time() - start_time
    logger.info(f"Inferencia completada en {elapsed:.1f}s ({elapsed/total*1000:.0f}ms/texto)")
    
    # Limpiar registros anteriores
    cursor.execute("DELETE FROM analisis_comentario")
    logger.info("Registros anteriores eliminados")
    
    # Guardar resultados BETO
    conteo = {"Positivo": 0, "Neutral": 0, "Negativo": 0}
    confianzas = []
    
    for i, (id_com, resultado) in enumerate(zip(ids, resultados)):
        cursor.execute("""
            INSERT INTO analisis_comentario 
            (id_comentario, sentimiento, confianza,
             probabilidad_positivo, probabilidad_neutral, probabilidad_negativo,
             fecha_analisis)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            id_com,
            resultado['sentimiento'],
            resultado['confianza'],
            resultado['prob_positivo'],
            resultado['prob_neutral'],
            resultado['prob_negativo']
        ))
        
        conteo[resultado['sentimiento']] += 1
        confianzas.append(resultado['confianza'])
    
    conn.commit()
    
    # Resumen
    prom_conf = sum(confianzas) / len(confianzas) if confianzas else 0
    logger.info("")
    logger.info("--- RESULTADOS COMENTARIOS ---")
    logger.info(f"Total analizados: {total}")
    logger.info(f"  Positivo: {conteo['Positivo']} ({conteo['Positivo']/total*100:.1f}%)")
    logger.info(f"  Neutral:  {conteo['Neutral']} ({conteo['Neutral']/total*100:.1f}%)")
    logger.info(f"  Negativo: {conteo['Negativo']} ({conteo['Negativo']/total*100:.1f}%)")
    logger.info(f"Confianza promedio: {prom_conf:.4f} ({prom_conf*100:.1f}%)")
    
    conn.close()
    return total


def guardar_info_modelo(modelo_version, n_posts, n_comentarios, elapsed_total):
    """Guarda información del modelo en la tabla modelo_entrenamiento."""
    import json
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar si la tabla existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='modelo_entrenamiento'")
    if cursor.fetchone():
        metricas = json.dumps({
            "posts_analizados": n_posts,
            "comentarios_analizados": n_comentarios,
            "total_textos": n_posts + n_comentarios,
            "tiempo_total_s": round(elapsed_total, 1),
            "framework": "PyTorch + HuggingFace Transformers",
            "modelo_base": "dccuchile/bert-base-spanish-wwm-uncased",
            "modelo_finetuned": "finiteautomata/beto-sentiment-analysis",
            "dataset_finetuning": "TASS (Spanish sentiment benchmarks)",
            "n_clases": 3,
            "clases": ["Negativo", "Neutral", "Positivo"],
            "arquitectura": "BertForSequenceClassification",
            "parametros": "109,853,187"
        }, ensure_ascii=False)
        
        parametros = json.dumps({
            "max_length": 512,
            "batch_size": 8,
            "num_labels": 3,
            "hidden_size": 768,
            "num_attention_heads": 12,
            "num_hidden_layers": 12
        })
        
        cursor.execute("""
            INSERT INTO modelo_entrenamiento 
            (tipo_modelo, nombre_modelo, version, metricas_json, parametros_json,
             datos_entrenamiento, datos_validacion, modelo_path, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'activo')
        """, (
            'sentimiento',
            'BETO Sentiment (finiteautomata/beto-sentiment-analysis)',
            modelo_version,
            metricas,
            parametros,
            n_posts + n_comentarios,
            0,
            'finiteautomata/beto-sentiment-analysis'
        ))
        conn.commit()
        logger.info("Informacion del modelo guardada en modelo_entrenamiento")
    
    conn.close()


def verificar_resultados():
    """Verifica los resultados guardados en la BD."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("VERIFICACION FINAL")
    logger.info("=" * 60)
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Verificar sentimientos de posts
    cursor.execute("""
        SELECT sentimiento_predicho, COUNT(*) as n, 
               AVG(confianza) as conf_prom,
               modelo_version
        FROM analisis_sentimiento 
        GROUP BY sentimiento_predicho, modelo_version
    """)
    rows = cursor.fetchall()
    
    logger.info("analisis_sentimiento:")
    for row in rows:
        logger.info(f"  {row['sentimiento_predicho']}: {row['n']} registros "
                     f"(conf. promedio: {row['conf_prom']:.4f}) "
                     f"[modelo: {row['modelo_version']}]")
    
    # Verificar comentarios
    cursor.execute("""
        SELECT sentimiento, COUNT(*) as n,
               AVG(confianza) as conf_prom
        FROM analisis_comentario 
        GROUP BY sentimiento
    """)
    rows = cursor.fetchall()
    
    logger.info("")
    logger.info("analisis_comentario:")
    for row in rows:
        logger.info(f"  {row['sentimiento']}: {row['n']} registros "
                     f"(conf. promedio: {row['conf_prom']:.4f})")
    
    # Verificar modelo
    cursor.execute("SELECT DISTINCT modelo_version FROM analisis_sentimiento")
    modelos = [r['modelo_version'] for r in cursor.fetchall()]
    logger.info(f"\nModelos en uso: {', '.join(modelos)}")
    
    # Total
    cursor.execute("SELECT COUNT(*) FROM analisis_sentimiento")
    total_sent = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM analisis_comentario")
    total_com = cursor.fetchone()[0]
    
    logger.info(f"\nTotal registros sentimiento: {total_sent}")
    logger.info(f"Total registros comentarios: {total_com}")
    
    conn.close()


def main():
    """Ejecución principal del análisis BETO."""
    print("")
    print("=" * 60)
    print("  SADUTO — Análisis de Sentimiento con BETO")
    print("  Modelo: dccuchile/bert-base-spanish-wwm-uncased")
    print("  Framework: PyTorch + Hugging Face Transformers")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("")
    
    total_start = time.time()
    
    # 1. Cargar modelo BETO
    model, tokenizer, device, modelo_version = cargar_beto()
    
    # 2. Analizar posts
    n_posts = analizar_posts(model, tokenizer, device, modelo_version)
    
    # 3. Analizar comentarios
    n_comentarios = analizar_comentarios(model, tokenizer, device, modelo_version)
    
    total_elapsed = time.time() - total_start
    
    # 4. Guardar info del modelo
    guardar_info_modelo(modelo_version, n_posts, n_comentarios, total_elapsed)
    
    # 5. Verificar resultados
    verificar_resultados()
    
    # Resumen final
    print("")
    print("=" * 60)
    print(f"  ANALISIS BETO COMPLETADO")
    print(f"  Posts analizados: {n_posts}")
    print(f"  Comentarios analizados: {n_comentarios}")
    print(f"  Total textos: {n_posts + n_comentarios}")
    print(f"  Tiempo total: {total_elapsed:.1f}s")
    print(f"  Modelo: {modelo_version}")
    print("=" * 60)


if __name__ == '__main__':
    main()
