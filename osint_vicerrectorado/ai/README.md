# 🤖 Módulo de IA - Sistema OSINT EMI

## Sprint 3: Identificación de Patrones con Inteligencia Artificial

Este módulo implementa capacidades avanzadas de análisis mediante IA para el Sistema de Analítica OSINT de la EMI Bolivia.

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Componentes](#componentes)
4. [Instalación](#instalación)
5. [Uso](#uso)
6. [API REST](#api-rest)
7. [Métricas de Rendimiento](#métricas-de-rendimiento)
8. [Entrenamiento](#entrenamiento)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Visión General

El módulo de IA proporciona cinco capacidades principales:

| Componente | Tecnología | Objetivo |
|------------|------------|----------|
| **Análisis de Sentimientos** | BETO (Spanish BERT) | Clasificar opiniones como Positivo/Negativo/Neutral |
| **Clustering** | K-Means + TF-IDF | Agrupar temáticamente las opiniones |
| **Detección de Tendencias** | Prophet/ARIMA | Identificar patrones temporales |
| **Detección de Anomalías** | Isolation Forest | Alertar sobre comportamientos inusuales |
| **Análisis de Correlaciones** | Pearson/Spearman | Encontrar relaciones entre variables |

---

## 🏗️ Arquitectura

```
ai/
├── __init__.py              # Exports y configuración
├── sentiment_analyzer.py    # Análisis de sentimientos con BETO
├── clustering_engine.py     # Clustering K-Means
├── trend_detector.py        # Detección de tendencias
├── anomaly_detector.py      # Detección de anomalías
├── correlation_analyzer.py  # Análisis de correlaciones
├── models/                  # Modelos entrenados
│   ├── sentiment/           # Modelo BETO fine-tuned
│   ├── clustering/          # Modelos de clustering
│   └── anomaly/             # Modelos de anomalías
└── utils/
    ├── __init__.py
    ├── vectorizer.py        # Utilidades de vectorización
    └── metrics.py           # Cálculo de métricas

api/
├── __init__.py
└── ai_endpoints.py          # Endpoints REST
```

---

## 🔧 Componentes

### 1. SentimentAnalyzer

Analiza el sentimiento de textos en español usando el modelo BETO.

```python
from ai import SentimentAnalyzer

# Inicializar
analyzer = SentimentAnalyzer()

# Predecir sentimiento
result = analyzer.predict("Excelente servicio de la universidad")
# {
#     'texto': 'Excelente servicio de la universidad',
#     'sentimiento': 'Positivo',
#     'confianza': 0.92,
#     'probabilidades': {'Negativo': 0.03, 'Neutral': 0.05, 'Positivo': 0.92}
# }

# Predicción en batch
results = analyzer.predict_batch([
    "Muy buena atención",
    "Pésimo servicio",
    "Información sobre inscripciones"
])
```

**Características:**
- Modelo: `dccuchile/bert-base-spanish-wwm-uncased`
- Labels: Positivo, Negativo, Neutral
- Fine-tuning soportado con datos anotados
- Accuracy objetivo: ≥85%

### 2. ClusteringEngine

Agrupa textos similares usando K-Means con vectorización TF-IDF.

```python
from ai import ClusteringEngine

# Inicializar
engine = ClusteringEngine(n_clusters=5, max_features=1000)

# Encontrar número óptimo de clusters
optimal = engine.find_optimal_k(texts, k_range=(2, 10))
print(f"K óptimo: {optimal['optimal_k']}")

# Ajustar clusters
result = engine.fit_clusters(texts)
# {
#     'n_clusters': 5,
#     'silhouette_score': 0.55,
#     'labels': [0, 1, 2, 0, 3, ...],
#     'cluster_sizes': {0: 150, 1: 120, 2: 80, 3: 75, 4: 45}
# }

# Obtener keywords por cluster
keywords = engine.get_cluster_keywords(top_n=5)
# {0: ['universidad', 'educación', 'carrera', 'estudiante', 'profesional'], ...}
```

**Características:**
- Vectorización TF-IDF con stopwords en español
- Detección automática de K óptimo (método del codo + silhouette)
- Silhouette score objetivo: ≥0.5

### 3. TrendDetector

Detecta tendencias temporales usando Prophet o ARIMA.

```python
from ai import TrendDetector

# Inicializar
detector = TrendDetector(freq='D', periods=30)

# Ajustar con datos históricos
detector.fit(dates, values)

# Analizar tendencia de sentimientos
trend = detector.analyze_sentiment_trend(df)
# {
#     'direction': 'increasing',
#     'strength': 0.65,
#     'change_points': ['2024-03-01', '2024-03-15']
# }

# Detectar estacionalidad
seasonality = detector.detect_seasonality()
# {
#     'has_weekly': True,
#     'has_academic': True,
#     'academic_periods': ['inicio_semestre', 'examenes', 'vacaciones']
# }

# Pronóstico
forecast = detector.forecast(periods=14)
# {
#     'dates': [...],
#     'values': [...],
#     'lower_bound': [...],
#     'upper_bound': [...]
# }
```

**Características:**
- Prophet para series complejas
- ARIMA como fallback
- Detección de estacionalidad académica

### 4. AnomalyDetector

Detecta anomalías usando Isolation Forest.

```python
from ai import AnomalyDetector

# Inicializar
detector = AnomalyDetector(contamination=0.05)

# Ajustar con datos históricos
detector.fit(historical_data)

# Detectar anomalías
anomalies = detector.detect_anomalies(new_data)
# [
#     {
#         'fecha': '2024-03-15',
#         'tipo': 'pico_negatividad',
#         'severidad': 'alta',
#         'descripcion': 'Incremento inusual de comentarios negativos',
#         'valor_observado': 85,
#         'valor_esperado': 20
#     }
# ]

# Generar alerta
alert = detector.generate_alert(anomaly)
```

**Características:**
- Severidad: baja, media, alta, crítica
- Tipos: pico_volumen, pico_negatividad, caida_engagement, patron_inusual
- Precisión objetivo: ≥70%

### 5. CorrelationAnalyzer

Analiza correlaciones entre variables.

```python
from ai import CorrelationAnalyzer

# Inicializar
analyzer = CorrelationAnalyzer(method='pearson', min_significance=0.05)

# Calcular matriz de correlación
matrix = analyzer.calculate_correlation_matrix(df)

# Identificar correlaciones significativas
significant = analyzer.identify_significant_correlations()
# [
#     {
#         'variable_1': 'sentimiento_positivo',
#         'variable_2': 'engagement',
#         'correlacion': 0.72,
#         'p_valor': 0.001,
#         'interpretacion': 'fuerte_positiva'
#     }
# ]
```

---

## 📦 Instalación

### 1. Instalar dependencias

```bash
cd osint_vicerrectorado
pip install -r requirements.txt
```

### 2. Descargar modelo BETO (primera ejecución)

```python
from ai import SentimentAnalyzer

# Descarga automática del modelo
analyzer = SentimentAnalyzer()
```

### 3. Crear tablas de IA en la base de datos

```bash
sqlite3 data/osint_emi.db < database/schema_ai.sql
```

---

## 🚀 Uso

### Línea de Comandos

```bash
# Analizar sentimientos de datos existentes
python -m ai.sentiment_analyzer --analyze-all

# Ejecutar clustering
python -m ai.clustering_engine --fit --k auto

# Detectar anomalías
python -m ai.anomaly_detector --detect

# Iniciar servidor API
python -m api.ai_endpoints
```

### Script de Anotación

```bash
# Anotar textos para entrenamiento
python annotate_sentiments.py --limit 100
```

---

## 🌐 API REST

### Iniciar servidor

```bash
python -m api.ai_endpoints
# Servidor en http://localhost:5000
```

### Endpoints

#### Análisis de Sentimientos

```bash
# POST /api/ai/analyze-sentiments
curl -X POST http://localhost:5000/api/ai/analyze-sentiments \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Excelente servicio", "Mala atención"]}'

# Respuesta
{
  "status": "success",
  "results": [
    {"texto": "Excelente servicio", "sentimiento": "Positivo", "confianza": 0.92},
    {"texto": "Mala atención", "sentimiento": "Negativo", "confianza": 0.88}
  ],
  "processing_time_ms": 245
}
```

#### Clustering

```bash
# POST /api/ai/cluster-opinions
curl -X POST http://localhost:5000/api/ai/cluster-opinions \
  -H "Content-Type: application/json" \
  -d '{"n_clusters": 5}'

# Respuesta
{
  "status": "success",
  "n_clusters": 5,
  "silhouette_score": 0.55,
  "clusters": {
    "0": {"size": 150, "keywords": ["universidad", "carrera"]},
    "1": {"size": 120, "keywords": ["servicio", "atención"]}
  }
}
```

#### Tendencias

```bash
# GET /api/ai/trends
curl "http://localhost:5000/api/ai/trends?period=30&forecast_days=7"

# Respuesta
{
  "status": "success",
  "trend": {
    "direction": "increasing",
    "strength": 0.65
  },
  "forecast": {
    "dates": ["2024-04-01", "2024-04-02"],
    "values": [55, 57]
  }
}
```

#### Anomalías

```bash
# GET /api/ai/anomalies
curl "http://localhost:5000/api/ai/anomalies?min_severity=media"

# Respuesta
{
  "status": "success",
  "anomalies": [
    {
      "fecha": "2024-03-15",
      "tipo": "pico_negatividad",
      "severidad": "alta",
      "descripcion": "Incremento inusual de comentarios negativos"
    }
  ],
  "total_detected": 1
}
```

#### Correlaciones

```bash
# GET /api/ai/correlations
curl "http://localhost:5000/api/ai/correlations?min_correlation=0.5"

# Respuesta
{
  "status": "success",
  "significant_correlations": [
    {
      "var1": "sentimiento_positivo",
      "var2": "engagement",
      "correlation": 0.72,
      "p_value": 0.001
    }
  ]
}
```

#### Health Check

```bash
# GET /api/ai/health
curl http://localhost:5000/api/ai/health

# Respuesta
{
  "status": "healthy",
  "components": {
    "sentiment_model": "loaded",
    "clustering_model": "not_fitted",
    "database": "connected"
  }
}
```

---

## 📊 Métricas de Rendimiento

### Objetivos Sprint 3

| Métrica | Objetivo | Actual |
|---------|----------|--------|
| Accuracy Sentimientos | ≥85% | - |
| Silhouette Clustering | ≥0.5 | - |
| Precisión Anomalías | ≥70% | - |
| Test Coverage | ≥85% | - |

### Evaluación

```python
from ai import SentimentAnalyzer
from ai.utils.metrics import AIMetrics

# Evaluar modelo de sentimientos
analyzer = SentimentAnalyzer()
metrics = analyzer.evaluate(test_texts, test_labels)
print(f"Accuracy: {metrics['accuracy']:.2%}")
print(f"F1 Macro: {metrics['f1_macro']:.2%}")
```

---

## 🎓 Entrenamiento

### Fine-tuning del modelo de sentimientos

#### 1. Generar datos de entrenamiento

```bash
# Anotar manualmente 500+ textos
python annotate_sentiments.py --limit 500
```

#### 2. Entrenar modelo

```python
from ai import SentimentAnalyzer

analyzer = SentimentAnalyzer()

# Cargar datos anotados
texts, labels = load_annotations('data/annotations.json')

# Fine-tune
metrics = analyzer.fine_tune(
    texts=texts,
    labels=labels,
    epochs=3,
    batch_size=16,
    learning_rate=2e-5
)

print(f"Accuracy final: {metrics['accuracy']:.2%}")

# Guardar modelo
analyzer.save_model('ai/models/sentiment/fine_tuned')
```

#### 3. Usar modelo entrenado

```python
# Cargar modelo fine-tuned
analyzer = SentimentAnalyzer(model_name='ai/models/sentiment/fine_tuned')
```

---

## 🐛 Troubleshooting

### Error: CUDA out of memory

```python
# Usar CPU en lugar de GPU
analyzer = SentimentAnalyzer(device='cpu')
```

### Error: Prophet no instalado

```bash
# Instalar Prophet
pip install prophet

# O usar ARIMA como fallback (automático)
```

### Error: Modelo no encontrado

```bash
# Descargar modelo BETO manualmente
python -c "from transformers import AutoModelForSequenceClassification; AutoModelForSequenceClassification.from_pretrained('dccuchile/bert-base-spanish-wwm-uncased')"
```

### Bajo rendimiento en clustering

```python
# Ajustar parámetros
engine = ClusteringEngine(
    n_clusters=None,  # Auto-detect
    max_features=2000,  # Más features
    min_df=2,  # Eliminar palabras raras
    max_df=0.95  # Eliminar palabras muy comunes
)
```

---

## 📚 Referencias

- [BETO - Spanish BERT](https://github.com/dccuchile/beto)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [scikit-learn](https://scikit-learn.org/)
- [Prophet](https://facebook.github.io/prophet/)
- [Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)

---

## 👥 Equipo

- **Proyecto:** Sistema de Analítica OSINT - EMI Bolivia
- **Sprint:** 3 - Módulo de IA
- **Fecha:** Enero 2025

---

*Documentación generada automáticamente. Para más información, contactar al equipo de desarrollo.*
