"""
Módulo de Inteligencia Artificial - Sistema OSINT EMI
Sprint 3: Identificación de Patrones con IA

Este módulo contiene los componentes de Machine Learning e IA para:
- Análisis de sentimientos con BETO (BERT en español)
- Detección de tendencias temporales con Prophet
- Clustering de opiniones con K-Means
- Detección de anomalías con Isolation Forest
- Análisis de correlaciones estadísticas

Autor: Sistema OSINT EMI
Fecha: Enero 2025
Versión: 1.0.0
"""

from .sentiment_analyzer import SentimentAnalyzer
from .clustering_engine import ClusteringEngine
from .trend_detector import TrendDetector
from .anomaly_detector import AnomalyDetector
from .correlation_analyzer import CorrelationAnalyzer

__version__ = "1.0.0"
__all__ = [
    "SentimentAnalyzer",
    "ClusteringEngine", 
    "TrendDetector",
    "AnomalyDetector",
    "CorrelationAnalyzer"
]

# Configuración por defecto del módulo AI
AI_CONFIG = {
    "sentiment": {
        "model_name": "dccuchile/bert-base-spanish-wwm-uncased",
        "max_length": 512,
        "batch_size": 16,
        "labels": ["Negativo", "Neutral", "Positivo"],
        "confidence_threshold": 0.6
    },
    "clustering": {
        "max_clusters": 10,
        "min_clusters": 2,
        "default_clusters": 5,
        "min_silhouette": 0.3,
        "target_silhouette": 0.5
    },
    "trends": {
        "seasonality_mode": "multiplicative",
        "forecast_periods": 30,
        "changepoint_threshold": 0.05
    },
    "anomalies": {
        "contamination": 0.1,
        "severity_thresholds": {
            "low": -0.3,
            "medium": -0.5,
            "high": -0.7,
            "critical": -0.9
        }
    },
    "correlations": {
        "significance_level": 0.05,
        "min_correlation": 0.5
    }
}
