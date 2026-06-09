#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  Analizador de Sentimientos — Sistema OSINT EMI
  Motor: Robertuito (pysentimiento) + BETO (fallback)
═══════════════════════════════════════════════════════════════

  Usa modelos de Deep Learning pre-entrenados en español para
  clasificar sentimientos con alta precisión. 

  Pipeline:
  1. ETL: dato_recolectado → dato_procesado
  2. Análisis de sentimiento (posts)  → analisis_sentimiento
  3. Análisis de sentimiento (comentarios) → analisis_comentario
═══════════════════════════════════════════════════════════════
"""

import sqlite3
import re
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'data' / 'osint_emi.db'

# ─── Singleton para el modelo (evita recargas en memoria) ───

_classifier = None
_model_name_used = None

LABEL_MAP = {
    'POS': 'Positivo',
    'NEU': 'Neutral',
    'NEG': 'Negativo',
    'POSITIVE': 'Positivo',
    'NEUTRAL': 'Neutral',
    'NEGATIVE': 'Negativo',
    'LABEL_0': 'Negativo',
    'LABEL_1': 'Neutral',
    'LABEL_2': 'Positivo',
}

def _get_optimal_batch_size() -> int:
    """Detecta el dispositivo disponible y retorna el batch_size óptimo."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return 32
        elif torch.cuda.is_available():
            return 64
    except ImportError:
        pass
    return 8

def _get_classifier():
    """Carga el clasificador de sentimientos una sola vez (singleton)."""
    global _classifier, _model_name_used
    if _classifier is not None:
        return _classifier
    
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
    
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = 0
    else:
        device = -1
        
    # Intentar modelos en orden de preferencia
    models_to_try = [
        ('pysentimiento/robertuito-sentiment-analysis', 'Robertuito'),
        ('finiteautomata/beto-sentiment-analysis', 'BETO'),
    ]
    
    for model_id, name in models_to_try:
        try:
            logger.info(f"Cargando modelo {name} en {device}...")
            tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(model_id, local_files_only=True)
            _classifier = pipeline(
                'sentiment-analysis',
                model=model,
                tokenizer=tokenizer,
                device=device,
                top_k=None,  # Obtener probabilidades de todas las clases
                truncation=True,
                max_length=512,
            )
            _model_name_used = name
            logger.info(f"✅ Modelo {name} cargado correctamente")
            return _classifier
        except (OSError, RuntimeError) as e:
            logger.warning(f"No se pudo cargar {name}: {e}")
            continue
    
    raise RuntimeError("No se pudo cargar ningún modelo de sentimientos")


def limpiar_texto(texto: str) -> str:
    """Limpia y normaliza texto para análisis."""
    if not texto:
        return ''
    # Remover URLs
    texto = re.sub(r'https?://\S+', '', texto)
    # Remover menciones de redes sociales
    texto = re.sub(r'@\w+', '', texto)
    # Remover hashtags pero mantener el texto
    texto = re.sub(r'#(\w+)', r'\1', texto)
    # Remover emojis unicode (mantener texto)
    texto = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF'
        r'\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF'
        r'\U00002702-\U000027B0\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
        r'\U00002600-\U000026FF]+', ' ', texto
    )
    # Normalizar espacios
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


def analizar_sentimiento(texto: str) -> dict:
    """
    Analiza el sentimiento de un texto usando Deep Learning.
    
    Returns:
        dict con sentimiento, confianza y probabilidades
    """
    if not texto or len(texto.strip()) < 3:
        return {
            'sentimiento': 'Neutral',
            'confianza': 0.5,
            'prob_positivo': 0.33,
            'prob_neutral': 0.34,
            'prob_negativo': 0.33,
        }
    
    classifier = _get_classifier()
    
    # Truncar a 512 tokens (el modelo no acepta más)
    texto_truncado = texto[:512]
    
    try:
        results = classifier(texto_truncado)[0]  # lista de {label, score}
        
        # Mapear resultados a nuestro formato
        probs = {'Positivo': 0.0, 'Neutral': 0.0, 'Negativo': 0.0}
        for item in results:
            label = LABEL_MAP.get(item['label'], item['label'])
            if label in probs:
                probs[label] = item['score']
        
        # Determinar sentimiento predominante
        sentimiento = max(probs, key=probs.get)
        confianza = probs[sentimiento]
        
        return {
            'sentimiento': sentimiento,
            'confianza': round(confianza, 4),
            'prob_positivo': round(probs['Positivo'], 4),
            'prob_neutral': round(probs['Neutral'], 4),
            'prob_negativo': round(probs['Negativo'], 4),
        }
    except (RuntimeError, ValueError) as e:
        logger.error(f"Error en clasificación individual: {e}")
        return {
            'sentimiento': 'Neutral',
            'confianza': 0.5,
            'prob_positivo': 0.33,
            'prob_neutral': 0.34,
            'prob_negativo': 0.33,
        }


def _batch_analyze(texts: list, batch_size: int = None) -> list:
    """Analiza un lote de textos eficientemente con fallback individual."""
    if batch_size is None:
        batch_size = _get_optimal_batch_size()
        
    classifier = _get_classifier()
    results = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        # Preparar batch: limpiar y truncar
        clean_batch = [t[:512] if t else '' for t in batch]
        # Filtrar vacíos, analizando sólo los que tienen contenido
        valid_indices = [j for j, t in enumerate(clean_batch) if len(t.strip()) > 3]
        valid_texts = [clean_batch[j] for j in valid_indices]
        
        batch_results = [None] * len(batch)
        
        if valid_texts:
            try:
                raw_results = classifier(valid_texts)
                for idx, raw in zip(valid_indices, raw_results):
                    probs = {'Positivo': 0.0, 'Neutral': 0.0, 'Negativo': 0.0}
                    for item in raw:
                        label = LABEL_MAP.get(item['label'], item['label'])
                        if label in probs:
                            probs[label] = item['score']
                    
                    sentimiento = max(probs, key=probs.get)
                    batch_results[idx] = {
                        'sentimiento': sentimiento,
                        'confianza': round(probs[sentimiento], 4),
                        'prob_positivo': round(probs['Positivo'], 4),
                        'prob_neutral': round(probs['Neutral'], 4),
                        'prob_negativo': round(probs['Negativo'], 4),
                    }
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Error en batch {i}, analizando individualmente: {e}")
                # Fallback: analizar uno por uno
                for idx in valid_indices:
                    try:
                        raw = classifier(clean_batch[idx][:256])[0]
                        probs = {'Positivo': 0.0, 'Neutral': 0.0, 'Negativo': 0.0}
                        for item in raw:
                            label = LABEL_MAP.get(item['label'], item['label'])
                            if label in probs:
                                probs[label] = item['score']
                        sentimiento = max(probs, key=probs.get)
                        batch_results[idx] = {
                            'sentimiento': sentimiento,
                            'confianza': round(probs[sentimiento], 4),
                            'prob_positivo': round(probs['Positivo'], 4),
                            'prob_neutral': round(probs['Neutral'], 4),
                            'prob_negativo': round(probs['Negativo'], 4),
                        }
                    except (RuntimeError, ValueError) as e:
                        logger.warning(f"Fallo fallback individual para item {idx}: {e}")
                        pass  # Will be filled with neutral default below
        
        # Rellenar nulos con neutral
        for j in range(len(batch)):
            if batch_results[j] is None:
                batch_results[j] = {
                    'sentimiento': 'Neutral',
                    'confianza': 0.5,
                    'prob_positivo': 0.33,
                    'prob_neutral': 0.34,
                    'prob_negativo': 0.33,
                }
        
        results.extend(batch_results)
        
        if i > 0 and i % 100 == 0:
            logger.info(f"  Procesados {i}/{len(texts)} textos...")
    
    return results


def ejecutar_analisis_completo(force_reanalysis: bool = False):
    """
    Ejecuta el pipeline completo:
    1. Procesa posts → dato_procesado (ETL)
    2. Analiza sentimiento de posts → analisis_sentimiento (Deep Learning)
    3. Analiza sentimiento de comentarios → analisis_comentario (Deep Learning)
    
    Args:
        force_reanalysis: Si True, re-analiza TODO incluso lo ya analizado
    """
    logger.info("🔬 Iniciando análisis de sentimientos (Deep Learning)")
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    stats = {
        'posts_procesados': 0,
        'posts_analizados': 0,
        'posts_re_analizados': 0,
        'comentarios_analizados': 0,
        'comentarios_re_analizados': 0,
        'modelo': _model_name_used or 'pendiente',
        'sentimientos': {'Positivo': 0, 'Negativo': 0, 'Neutral': 0}
    }
    
    # ─── FASE 1: ETL → dato_procesado ───────────────────────────
    logger.info("📦 Fase 1: Procesando posts en dato_procesado...")
    
    cursor.execute('''
        SELECT dr.id_dato, dr.contenido_original, dr.fecha_publicacion,
               dr.engagement_likes, dr.engagement_comments, dr.engagement_shares,
               dr.engagement_views, f.tipo_fuente
        FROM dato_recolectado dr
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        WHERE dr.id_dato NOT IN (SELECT id_dato_original FROM dato_procesado)
    ''')
    
    posts_nuevos = cursor.fetchall()
    
    for post in posts_nuevos:
        texto = post['contenido_original'] or ''
        texto_limpio = limpiar_texto(texto)
        
        if len(texto_limpio) < 3:
            continue
        
        # Extraer componentes de fecha
        fecha_pub = post['fecha_publicacion'] or ''
        try:
            dt = datetime.fromisoformat(fecha_pub.replace('Z', '+00:00'))
            anio = dt.year
            mes = dt.month
            dia_semana = dt.strftime('%A')
            hora = dt.hour
            semestre = 1 if mes <= 6 else 2
            es_horario_laboral = 8 <= hora <= 18
            fecha_iso = dt.isoformat()
        except ValueError as e:
            logger.warning(f"Error parseando fecha '{fecha_pub}': {e}")
            anio = mes = hora = semestre = 0
            dia_semana = ''
            es_horario_laboral = False
            fecha_iso = fecha_pub
        
        # Engagement
        likes = post['engagement_likes'] or 0
        comments = post['engagement_comments'] or 0
        shares = post['engagement_shares'] or 0
        views = post['engagement_views'] or 0
        engagement_total = likes + comments + shares
        engagement_normalizado = engagement_total / max(views, 1) if views > 0 else 0
        
        # Sentimiento básico — usaremos 'pendiente' y luego lo actualizaremos
        contiene_emi = any(kw in texto_limpio.lower() for kw in 
                          ['emi', 'escuela militar', 'ingeniería', 'ingenieria'])
        
        cursor.execute('''
            INSERT INTO dato_procesado
            (id_dato_original, contenido_limpio, longitud_texto, cantidad_palabras,
             fecha_publicacion_iso, anio, mes, dia_semana, hora, semestre,
             es_horario_laboral, engagement_total, engagement_normalizado,
             ratio_engagement, categoria_preliminar, idioma_detectado,
             contiene_mencion_emi, sentimiento_basico, fecha_procesamiento, version_etl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), '3.0-DL')
        ''', (
            post['id_dato'],
            texto_limpio,
            len(texto_limpio),
            len(texto_limpio.split()),
            fecha_iso,
            anio, mes, dia_semana, hora, semestre,
            es_horario_laboral,
            engagement_total,
            round(engagement_normalizado, 6),
            round(engagement_total / max(likes + 1, 1), 4),
            post['tipo_fuente'],
            'es',
            contiene_emi,
            'pendiente',  # Se actualizará en Fase 2
        ))
        stats['posts_procesados'] += 1
    
    conn.commit()
    logger.info(f"📦 {stats['posts_procesados']} posts nuevos procesados en ETL")
    
    # ─── FASE 2: Análisis de sentimiento (posts) — Deep Learning ─
    logger.info("🧠 Fase 2: Analizando sentimiento de posts con IA...")
    
    if force_reanalysis:
        # Re-analizar todo
        cursor.execute('''
            SELECT dp.id_dato_procesado, dp.contenido_limpio
            FROM dato_procesado dp
            WHERE dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 3
        ''')
    else:
        # Solo los nuevos (no analizados)
        cursor.execute('''
            SELECT dp.id_dato_procesado, dp.contenido_limpio
            FROM dato_procesado dp
            WHERE dp.id_dato_procesado NOT IN (
                SELECT id_dato_procesado FROM analisis_sentimiento
            )
            AND dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 3
        ''')
    
    posts_sin_analizar = cursor.fetchall()
    
    if posts_sin_analizar:
        ids = [p['id_dato_procesado'] for p in posts_sin_analizar]
        texts = [p['contenido_limpio'] for p in posts_sin_analizar]
        
        logger.info(f"  Analizando {len(texts)} posts...")
        results = _batch_analyze(texts)
        
        for post_id, result in zip(ids, results):
            if force_reanalysis:
                # Borrar análisis previo
                cursor.execute('DELETE FROM analisis_sentimiento WHERE id_dato_procesado = ?', (post_id,))
                stats['posts_re_analizados'] += 1
            
            cursor.execute('''
                INSERT OR REPLACE INTO analisis_sentimiento
                (id_dato_procesado, sentimiento_predicho, confianza,
                 probabilidad_positivo, probabilidad_neutral, probabilidad_negativo,
                 modelo_version, fecha_analisis)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                post_id,
                result['sentimiento'],
                result['confianza'],
                result['prob_positivo'],
                result['prob_neutral'],
                result['prob_negativo'],
                f'{_model_name_used or "DL"}_v3',
            ))
            
            # Actualizar sentimiento_basico en dato_procesado
            cursor.execute('''
                UPDATE dato_procesado SET sentimiento_basico = ?
                WHERE id_dato_procesado = ?
            ''', (result['sentimiento'].lower(), post_id))
            
            stats['posts_analizados'] += 1
            stats['sentimientos'][result['sentimiento']] += 1
        
        conn.commit()
    
    logger.info(f"🧠 {stats['posts_analizados']} posts analizados")
    
    # ─── FASE 3: Análisis de comentarios — Deep Learning ────────
    logger.info("💬 Fase 3: Analizando sentimiento de comentarios con IA...")
    
    # Crear tabla si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analisis_comentario (
            id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
            id_comentario INTEGER NOT NULL,
            sentimiento VARCHAR(20),
            confianza DECIMAL(5,4),
            probabilidad_positivo DECIMAL(5,4),
            probabilidad_neutral DECIMAL(5,4),
            probabilidad_negativo DECIMAL(5,4),
            fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    if force_reanalysis:
        cursor.execute('''
            SELECT c.id_comentario, c.contenido
            FROM comentario c
            WHERE c.contenido IS NOT NULL AND LENGTH(c.contenido) > 3
        ''')
    else:
        cursor.execute('''
            SELECT c.id_comentario, c.contenido
            FROM comentario c
            WHERE c.id_comentario NOT IN (
                SELECT id_comentario FROM analisis_comentario
            )
            AND c.contenido IS NOT NULL AND LENGTH(c.contenido) > 3
        ''')
    
    comentarios = cursor.fetchall()
    
    if comentarios:
        com_ids = [c['id_comentario'] for c in comentarios]
        com_texts = [limpiar_texto(c['contenido']) for c in comentarios]
        
        logger.info(f"  Analizando {len(com_texts)} comentarios...")
        com_results = _batch_analyze(com_texts)
        
        for com_id, result in zip(com_ids, com_results):
            if force_reanalysis:
                cursor.execute('DELETE FROM analisis_comentario WHERE id_comentario = ?', (com_id,))
                stats['comentarios_re_analizados'] += 1
            
            cursor.execute('''
                INSERT OR REPLACE INTO analisis_comentario
                (id_comentario, sentimiento, confianza,
                 probabilidad_positivo, probabilidad_neutral, probabilidad_negativo,
                 fecha_analisis)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                com_id,
                result['sentimiento'],
                result['confianza'],
                result['prob_positivo'],
                result['prob_neutral'],
                result['prob_negativo'],
            ))
            
            stats['comentarios_analizados'] += 1
            stats['sentimientos'][result['sentimiento']] += 1
        
        conn.commit()
    
    stats['modelo'] = _model_name_used or 'N/A'
    
    # ─── FASE 4: Alertas objetivas (picos de engagement) ─────────────────────
    # NOTA: La detección de quejas institucionales/académicas ya NO se hace por
    # listas de palabras clave. Esa clasificación la realiza DeepSeek (FASE 5),
    # que decide `es_institucional` y `severidad` y genera las alertas
    # correspondientes en `deepseek_analyzer._generar_alertas()`.
    logger.info("🚨 Fase 4: Generando alertas objetivas (picos de engagement)...")

    alertas_generadas = 0

    # Evaluar picos de engagement (Posts Virales)
    cursor.execute('''
        SELECT dp.id_dato_procesado as id, dp.contenido_limpio as texto, dp.engagement_total, f.tipo_fuente as fuente
        FROM dato_procesado dp
        JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        WHERE dp.engagement_total > 100000
          AND dp.id_dato_procesado NOT IN (SELECT id_dato_procesado FROM alerta WHERE tipo = 'engagement_spike')
    ''')
    picos_engagement = cursor.fetchall()
    
    for pico in picos_engagement:
        titulo = f"Pico de engagement detectado ({pico['engagement_total']} interacciones)"
        descripcion = pico['texto'][:500]
        cursor.execute('''
            INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado, id_dato_procesado, engagement, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', ('engagement_spike', 'media', titulo, descripcion, pico['fuente'], 'nueva', pico['id'], pico['engagement_total']))
        alertas_generadas += 1

    conn.commit()
    stats['alertas_generadas'] = alertas_generadas
    logger.info(f"  {alertas_generadas} alertas de engagement generadas.")

    conn.close()

    # ─── FASE 5: Análisis con DeepSeek (clasificación dinámica post-BERT) ──────
    # Toma los posts/comentarios ya analizados por BERT y los clasifica con
    # DeepSeek (carrera, tema, severidad, institucionalidad, insights). Es la
    # única fuente de los dashboards de carreras/reputación/insights.
    # Envuelto en try/except: si DeepSeek no está disponible, NO rompe el
    # pipeline BERT.
    logger.info("🤖 Fase 5: Análisis con DeepSeek...")
    try:
        from deepseek_analyzer import analizar_con_deepseek
        ds_stats = analizar_con_deepseek()
        stats['deepseek'] = ds_stats
        if ds_stats.get('error'):
            logger.warning(f"  DeepSeek no completó: {ds_stats['error']}")
        else:
            logger.info(f"  DeepSeek: {ds_stats.get('analizados', 0)} ítems, "
                        f"{ds_stats.get('alertas', 0)} alertas")
    except Exception as e:
        logger.warning(f"  DeepSeek omitido (no fatal): {e}")
        stats['deepseek'] = {'error': str(e)}

    logger.info(f"✅ Análisis completo ({stats['modelo']}): "
                f"{stats['posts_procesados']} ETL, "
                f"{stats['posts_analizados']} posts, "
                f"{stats['comentarios_analizados']} comentarios, "
                f"{stats['alertas_generadas']} alertas generadas")
    logger.info(f"   Sentimientos: {stats['sentimientos']}")
    
    return stats


# ═══════════════════════════════════════════════════════════════
#   CAPACIDADES AVANZADAS (Fine-Tuning y Evaluación)
#   Migradas desde ai/sentiment_analyzer.py
# ═══════════════════════════════════════════════════════════════

import numpy as np
import torch
from torch.utils.data import Dataset
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report
)

class SentimentDataset(Dataset):
    """Dataset personalizado para entrenamiento de sentimientos."""
    def __init__(self, texts, labels, tokenizer, max_length=512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text, truncation=True, max_length=self.max_length,
            padding='max_length', return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

def fine_tune_model(
    training_data: list,
    model_name: str = "pysentimiento/robertuito-sentiment-analysis",
    models_dir: str = "models/custom_sentiment",
    validation_split: float = 0.2,
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    save_model: bool = True
) -> dict:
    """Fine-tuning del modelo con datos anotados (Migrado)."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, TrainingArguments, Trainer, EarlyStoppingCallback
    
    logger.info(f"Iniciando fine-tuning de {model_name} con {len(training_data)} ejemplos")
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=3, ignore_mismatched_sizes=True)
    
    # Preparamos datos
    texts = [item['text'] for item in training_data]
    label_to_id = {"Negativo": 0, "Neutral": 1, "Positivo": 2}
    labels = [label_to_id.get(item['label'], 1) for item in training_data]
    
    n_samples = len(texts)
    n_val = int(n_samples * validation_split)
    indices = np.random.permutation(n_samples)
    
    train_dataset = SentimentDataset(
        [texts[i] for i in indices[n_val:]],
        [labels[i] for i in indices[n_val:]],
        tokenizer
    )
    val_dataset = SentimentDataset(
        [texts[i] for i in indices[:n_val]],
        [labels[i] for i in indices[:n_val]],
        tokenizer
    )
    
    training_args = TrainingArguments(
        output_dir=f"{models_dir}/checkpoints",
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        report_to=[]
    )
    
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        acc = accuracy_score(labels, predictions)
        prec, rec, f1, _ = precision_recall_fscore_support(labels, predictions, average='weighted')
        return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1}
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
    )
    
    train_result = trainer.train()
    eval_result = trainer.evaluate()
    
    if save_model:
        os.makedirs(models_dir, exist_ok=True)
        model.save_pretrained(models_dir)
        tokenizer.save_pretrained(models_dir)
        logger.info(f"Modelo guardado en {models_dir}")
        
        # Actualizar global para usar este modelo
        global _classifier
        from transformers import pipeline
        _classifier = pipeline('sentiment-analysis', model=model, tokenizer=tokenizer, device=-1, top_k=None, truncation=True, max_length=512)
        
    return {
        "eval_accuracy": eval_result.get("eval_accuracy", 0),
        "eval_f1": eval_result.get("eval_f1", 0),
        "train_loss": train_result.training_loss
    }

def evaluate_model(test_data: list) -> dict:
    """Evalúa el clasificador global actual con datos de prueba (Migrado)."""
    classifier = _get_classifier()
    texts = [item['text'] for item in test_data]
    label_to_id = {"Negativo": 0, "Neutral": 1, "Positivo": 2}
    true_labels = [label_to_id.get(item['label'], 1) for item in test_data]
    
    predictions = []
    # Usar batch_analyze para evaluar
    results = _batch_analyze(texts)
    for res in results:
        predictions.append(label_to_id.get(res['sentimiento'], 1))
        
    acc = accuracy_score(true_labels, predictions)
    report = classification_report(true_labels, predictions, target_names=["Negativo", "Neutral", "Positivo"], output_dict=True)
    
    return {
        "accuracy": float(acc),
        "classification_report": report
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Analizador de Sentimientos OSINT EMI')
    parser.add_argument('--force', action='store_true', 
                        help='Re-analizar TODO (incluso lo ya procesado)')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    result = ejecutar_analisis_completo(force_reanalysis=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
