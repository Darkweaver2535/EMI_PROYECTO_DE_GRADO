"""
API Flask para Módulo de IA - Sistema OSINT EMI
Sprint 3: Endpoints de Análisis de Patrones

Este módulo implementa los endpoints REST para los servicios de IA:
- Análisis de sentimientos
- Detección de tendencias
- Clustering de opiniones
- Detección de anomalías
- Análisis de correlaciones

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

from flask import Flask, Blueprint, request, jsonify
from functools import wraps
import logging
from datetime import datetime
from typing import Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
)
logger = logging.getLogger("OSINT.API")

# Blueprint para endpoints de IA
ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')


def handle_errors(f):
    """Decorador para manejo de errores en endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Error de validación: {str(e)}")
            return jsonify({
                "error": "Validation Error",
                "message": str(e),
                "status": 400
            }), 400
        except RuntimeError as e:
            logger.error(f"Error de ejecución: {str(e)}")
            return jsonify({
                "error": "Runtime Error",
                "message": str(e),
                "status": 500
            }), 500
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            return jsonify({
                "error": "Internal Server Error",
                "message": str(e),
                "status": 500
            }), 500
    return decorated_function


def validate_request_json(*required_fields):
    """Decorador para validar campos requeridos en JSON."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    "error": "Invalid Content-Type",
                    "message": "Content-Type must be application/json",
                    "status": 400
                }), 400
            
            data = request.get_json()
            missing = [field for field in required_fields if field not in data]
            
            if missing:
                return jsonify({
                    "error": "Missing Fields",
                    "message": f"Required fields missing: {', '.join(missing)}",
                    "status": 400
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# Endpoints de Análisis de Sentimientos
# ============================================================

@ai_bp.route('/analyze-sentiments', methods=['POST'])
@handle_errors
@validate_request_json('texts')
def analyze_sentiments():
    """
    Analiza el sentimiento de uno o más textos.
    
    Request Body:
        {
            "texts": ["texto1", "texto2", ...],
            "return_probabilities": false  // opcional
        }
    
    Response:
        [
            {
                "text": "texto1",
                "sentiment": "Positivo",
                "confidence": 0.89,
                "probabilities": {...}  // si se solicitó
            },
            ...
        ]
    """
    from ai.sentiment_analyzer import SentimentAnalyzer
    
    data = request.get_json()
    texts = data.get('texts', [])
    return_probs = data.get('return_probabilities', False)
    
    if not texts:
        return jsonify({
            "error": "Empty texts list",
            "message": "At least one text is required",
            "status": 400
        }), 400
    
    logger.info(f"Analizando sentimientos de {len(texts)} textos")
    
    # Inicializar analizador
    analyzer = SentimentAnalyzer()
    analyzer.load_model()
    
    # Analizar
    if len(texts) == 1:
        result = analyzer.predict(texts[0])
        if not return_probs and 'probabilities' in result:
            del result['probabilities']
        results = [result]
    else:
        results = analyzer.predict_batch(texts, return_probabilities=return_probs)
    
    return jsonify({
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/sentiments/train', methods=['POST'])
@handle_errors
@validate_request_json('training_data')
def train_sentiment_model():
    """
    Entrena/fine-tune el modelo de sentimientos con datos anotados.
    
    Request Body:
        {
            "training_data": [
                {"text": "texto", "label": "Positivo"},
                ...
            ],
            "epochs": 3,  // opcional
            "validation_split": 0.2  // opcional
        }
    
    Response:
        {
            "status": "success",
            "metrics": {...}
        }
    """
    from ai.sentiment_analyzer import SentimentAnalyzer
    
    data = request.get_json()
    training_data = data.get('training_data', [])
    epochs = data.get('epochs', 3)
    validation_split = data.get('validation_split', 0.2)
    
    if len(training_data) < 50:
        return jsonify({
            "error": "Insufficient data",
            "message": "At least 50 training examples are required",
            "status": 400
        }), 400
    
    logger.info(f"Entrenando modelo con {len(training_data)} ejemplos")
    
    analyzer = SentimentAnalyzer()
    analyzer.load_model()
    
    metrics = analyzer.fine_tune(
        training_data,
        epochs=epochs,
        validation_split=validation_split
    )
    
    return jsonify({
        "status": "success",
        "message": "Model trained successfully",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/sentiments/evaluate', methods=['POST'])
@handle_errors
@validate_request_json('test_data')
def evaluate_sentiment_model():
    """
    Evalúa el modelo de sentimientos con datos de prueba.
    
    Request Body:
        {
            "test_data": [
                {"text": "texto", "label": "Positivo"},
                ...
            ]
        }
    
    Response:
        {
            "accuracy": 0.85,
            "f1_weighted": 0.84,
            ...
        }
    """
    from ai.sentiment_analyzer import SentimentAnalyzer
    
    data = request.get_json()
    test_data = data.get('test_data', [])
    
    if len(test_data) < 10:
        return jsonify({
            "error": "Insufficient data",
            "message": "At least 10 test examples are required",
            "status": 400
        }), 400
    
    logger.info(f"Evaluando modelo con {len(test_data)} ejemplos")
    
    analyzer = SentimentAnalyzer()
    analyzer.load_model()
    
    metrics = analyzer.evaluate(test_data)
    
    return jsonify({
        "status": "success",
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Endpoints de Detección de Tendencias
# ============================================================

@ai_bp.route('/trends', methods=['GET'])
@handle_errors
def get_trends():
    """
    Analiza tendencias temporales de sentimiento.
    
    Query Parameters:
        start_date: YYYY-MM-DD (opcional)
        end_date: YYYY-MM-DD (opcional)
        metric: string (default: 'sentiment')
    
    Response:
        {
            "trend": "creciente",
            "confidence": 0.85,
            "change_points": [...],
            "forecast": [...],
            ...
        }
    """
    from ai.trend_detector import TrendDetector
    import pandas as pd
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    metric = request.args.get('metric', 'sentiment')
    
    logger.info(f"Analizando tendencias: {start_date} a {end_date}")
    
    # TODO: Obtener datos de la BD
    # Por ahora, generar datos de ejemplo
    import numpy as np
    dates = pd.date_range(
        start=start_date or '2024-01-01',
        end=end_date or datetime.now().strftime('%Y-%m-%d'),
        freq='D'
    )
    
    # Simular datos (reemplazar con query a BD)
    np.random.seed(42)
    values = np.random.normal(0.6, 0.1, len(dates))
    
    data = pd.DataFrame({
        'fecha': dates,
        'valor': values
    })
    
    # Analizar
    detector = TrendDetector()
    detector.fit(data, date_col='fecha', value_col='valor')
    
    trend_analysis = detector.analyze_sentiment_trend(start_date, end_date)
    seasonality = detector.detect_seasonality()
    change_points = detector.identify_change_points()
    
    # Forecast
    forecast = detector.forecast(periods=30)
    
    return jsonify({
        "trend": trend_analysis,
        "seasonality": seasonality,
        "change_points": change_points,
        "forecast": forecast,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/trends/forecast', methods=['GET'])
@handle_errors
def get_forecast():
    """
    Genera proyección futura.
    
    Query Parameters:
        periods: int (default: 30)
        metric: string (default: 'sentiment')
    
    Response:
        {
            "predictions": [...],
            "method": "Prophet",
            ...
        }
    """
    from ai.trend_detector import TrendDetector
    import pandas as pd
    import numpy as np
    
    periods = int(request.args.get('periods', 30))
    metric = request.args.get('metric', 'sentiment')
    
    logger.info(f"Generando forecast de {periods} períodos")
    
    # TODO: Obtener datos reales de BD
    dates = pd.date_range(start='2024-01-01', end=datetime.now(), freq='D')
    np.random.seed(42)
    values = np.random.normal(0.6, 0.1, len(dates))
    
    data = pd.DataFrame({'fecha': dates, 'valor': values})
    
    detector = TrendDetector()
    detector.fit(data, date_col='fecha', value_col='valor')
    
    forecast = detector.forecast(periods=periods)
    
    return jsonify({
        "forecast": forecast,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Endpoints de Clustering
# ============================================================

@ai_bp.route('/cluster-opinions', methods=['POST'])
@handle_errors
def cluster_opinions():
    """
    Agrupa opiniones en clusters temáticos.
    
    Request Body:
        {
            "texts": ["texto1", "texto2", ...],
            "k": 5,  // opcional, None para auto
            "max_k": 10  // opcional
        }
    
    Response:
        {
            "clusters": [...],
            "silhouette_score": 0.67,
            "cluster_summaries": [...]
        }
    """
    from ai.clustering_engine import ClusteringEngine
    
    data = request.get_json()
    texts = data.get('texts', [])
    k = data.get('k')
    max_k = data.get('max_k', 10)
    
    if not texts:
        return jsonify({
            "error": "Empty texts list",
            "message": "At least one text is required",
            "status": 400
        }), 400
    
    if len(texts) < 10:
        return jsonify({
            "error": "Insufficient texts",
            "message": "At least 10 texts are required for clustering",
            "status": 400
        }), 400
    
    logger.info(f"Clustering {len(texts)} textos")
    
    engine = ClusteringEngine()
    engine.vectorize_texts(texts)
    
    # Encontrar k óptimo si no se especificó
    if k is None:
        optimal_result = engine.find_optimal_k(max_k=max_k)
        k = optimal_result['optimal_k']
    
    # Entrenar
    metrics = engine.fit_clusters(k)
    
    # Obtener resumen
    summaries = engine.get_cluster_summary()
    
    # Asignar cada texto a su cluster
    assignments = []
    for i, text in enumerate(texts):
        prediction = engine.predict_cluster(text)
        assignments.append({
            "text": text[:200] + "..." if len(text) > 200 else text,
            "cluster_id": prediction['cluster_id'],
            "distance": prediction['distance_to_centroid']
        })
    
    return jsonify({
        "n_clusters": k,
        "silhouette_score": metrics['silhouette_score'],
        "cluster_summaries": summaries,
        "assignments": assignments,
        "metrics": metrics,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/clusters/optimal-k', methods=['POST'])
@handle_errors
@validate_request_json('texts')
def find_optimal_clusters():
    """
    Encuentra el número óptimo de clusters.
    
    Request Body:
        {
            "texts": ["texto1", "texto2", ...],
            "max_k": 10
        }
    
    Response:
        {
            "optimal_k": 5,
            "silhouette_score": 0.67,
            "all_scores": {...}
        }
    """
    from ai.clustering_engine import ClusteringEngine
    
    data = request.get_json()
    texts = data.get('texts', [])
    max_k = data.get('max_k', 10)
    
    if len(texts) < 10:
        return jsonify({
            "error": "Insufficient texts",
            "message": "At least 10 texts required",
            "status": 400
        }), 400
    
    logger.info(f"Buscando k óptimo para {len(texts)} textos")
    
    engine = ClusteringEngine()
    engine.vectorize_texts(texts)
    
    result = engine.find_optimal_k(max_k=max_k)
    
    return jsonify({
        "optimal_k": result['optimal_k'],
        "silhouette_score": result['silhouette_score'],
        "recommendation": result['recommendation'],
        "all_k_scores": result['all_k_scores'],
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Endpoints de Detección de Anomalías
# ============================================================

@ai_bp.route('/anomalies', methods=['GET'])
@handle_errors
def get_anomalies():
    """
    Detecta anomalías en las métricas recientes.
    
    Query Parameters:
        days: int (default: 30)
        severity: string (opcional, 'baja', 'media', 'alta', 'critica')
    
    Response:
        [
            {
                "type": "pico_quejas",
                "severity": "alta",
                "date": "...",
                ...
            },
            ...
        ]
    """
    from ai.anomaly_detector import AnomalyDetector
    import pandas as pd
    import numpy as np
    
    days = int(request.args.get('days', 30))
    severity_filter = request.args.get('severity')
    
    logger.info(f"Detectando anomalías de los últimos {days} días")
    
    # TODO: Obtener datos reales de BD
    # Por ahora, datos de ejemplo
    np.random.seed(42)
    n_samples = days
    
    normal_data = pd.DataFrame({
        'engagement': np.random.normal(100, 20, n_samples - 3),
        'sentiment_score': np.random.normal(0.6, 0.1, n_samples - 3),
        'post_count': np.random.normal(10, 3, n_samples - 3)
    })
    
    # Añadir algunas anomalías
    anomaly_data = pd.DataFrame({
        'engagement': [250, 20, 300],
        'sentiment_score': [0.2, 0.9, 0.1],
        'post_count': [30, 2, 50]
    })
    
    all_data = pd.concat([normal_data, anomaly_data], ignore_index=True)
    
    # Detectar
    detector = AnomalyDetector(contamination=0.1)
    detector.fit(normal_data)
    anomalies = detector.detect_anomalies(all_data)
    
    # Filtrar por severidad si se especificó
    if severity_filter:
        anomalies = [a for a in anomalies if a['severity'] == severity_filter]
    
    # Generar alertas
    alerts = []
    for anomaly in anomalies[:5]:  # Limitar a 5
        alert = detector.generate_alert(anomaly)
        alerts.append(alert)
    
    summary = detector.get_anomaly_summary()
    
    return jsonify({
        "anomalies": anomalies,
        "alerts": alerts,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/anomalies/detect', methods=['POST'])
@handle_errors
@validate_request_json('data')
def detect_anomalies():
    """
    Detecta anomalías en datos proporcionados.
    
    Request Body:
        {
            "data": [
                {"engagement": 100, "sentiment": 0.5, ...},
                ...
            ],
            "baseline_data": [...]  // opcional, para entrenar
        }
    
    Response:
        {
            "anomalies": [...],
            "total_anomalies": 3
        }
    """
    from ai.anomaly_detector import AnomalyDetector
    import pandas as pd
    
    request_data = request.get_json()
    data = pd.DataFrame(request_data.get('data', []))
    baseline_data = request_data.get('baseline_data')
    
    if len(data) < 5:
        return jsonify({
            "error": "Insufficient data",
            "message": "At least 5 data points required",
            "status": 400
        }), 400
    
    logger.info(f"Detectando anomalías en {len(data)} registros")
    
    detector = AnomalyDetector()
    
    if baseline_data:
        detector.fit(pd.DataFrame(baseline_data))
    else:
        # Usar los primeros 80% como baseline
        n_baseline = int(len(data) * 0.8)
        detector.fit(data.iloc[:n_baseline])
    
    anomalies = detector.detect_anomalies(data)
    
    return jsonify({
        "anomalies": anomalies,
        "total_anomalies": len(anomalies),
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Endpoints de Análisis de Correlaciones
# ============================================================

@ai_bp.route('/correlations', methods=['GET'])
@handle_errors
def get_correlations():
    """
    Obtiene análisis de correlaciones entre métricas.
    
    Query Parameters:
        min_correlation: float (default: 0.3)
        significance_level: float (default: 0.05)
    
    Response:
        {
            "matrix": [[...]],
            "significant": [...],
            "summary": {...}
        }
    """
    from ai.correlation_analyzer import CorrelationAnalyzer
    import pandas as pd
    import numpy as np
    
    min_corr = float(request.args.get('min_correlation', 0.3))
    sig_level = float(request.args.get('significance_level', 0.05))
    
    logger.info("Calculando correlaciones")
    
    # TODO: Obtener datos reales de BD
    # Datos de ejemplo
    np.random.seed(42)
    n = 100
    
    engagement = np.random.normal(100, 20, n)
    likes = engagement * 5 + np.random.normal(0, 30, n)
    sentiment = engagement * 0.01 + np.random.normal(0.6, 0.1, n)
    comments = np.random.normal(20, 10, n)
    shares = likes * 0.1 + np.random.normal(0, 10, n)
    
    data = pd.DataFrame({
        'engagement': engagement,
        'likes': likes,
        'sentiment': sentiment,
        'comments': comments,
        'shares': shares
    })
    
    analyzer = CorrelationAnalyzer(
        significance_level=sig_level,
        min_correlation=min_corr
    )
    
    analyzer.calculate_correlation_matrix(data)
    significant = analyzer.identify_significant_correlations()
    summary = analyzer.get_correlation_summary()
    
    return jsonify({
        "correlation_matrix": analyzer.correlation_matrix.to_dict(),
        "significant_correlations": significant,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/correlations/analyze', methods=['POST'])
@handle_errors
@validate_request_json('data')
def analyze_correlations():
    """
    Analiza correlaciones en datos proporcionados.
    
    Request Body:
        {
            "data": [
                {"var1": 1.0, "var2": 2.0, ...},
                ...
            ],
            "columns": ["var1", "var2"]  // opcional
        }
    
    Response:
        {
            "correlation_matrix": {...},
            "significant_correlations": [...],
            "summary": {...}
        }
    """
    from ai.correlation_analyzer import CorrelationAnalyzer
    import pandas as pd
    
    request_data = request.get_json()
    data = pd.DataFrame(request_data.get('data', []))
    columns = request_data.get('columns')
    
    if len(data) < 10:
        return jsonify({
            "error": "Insufficient data",
            "message": "At least 10 data points required",
            "status": 400
        }), 400
    
    logger.info(f"Analizando correlaciones en {len(data)} registros")
    
    analyzer = CorrelationAnalyzer()
    analyzer.calculate_correlation_matrix(data, columns=columns)
    significant = analyzer.identify_significant_correlations()
    summary = analyzer.get_correlation_summary()
    
    return jsonify({
        "correlation_matrix": analyzer.correlation_matrix.to_dict(),
        "significant_correlations": significant,
        "summary": summary,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Endpoints de Estado y Salud
# ============================================================

@ai_bp.route('/health', methods=['GET'])
def health_check():
    """
    Verifica el estado de los módulos de IA.
    
    Response:
        {
            "status": "healthy",
            "modules": {...}
        }
    """
    modules_status = {
        "sentiment_analyzer": {"status": "available"},
        "clustering_engine": {"status": "available"},
        "trend_detector": {"status": "available"},
        "anomaly_detector": {"status": "available"},
        "correlation_analyzer": {"status": "available"}
    }
    
    # Verificar disponibilidad de dependencias opcionales
    try:
        from prophet import Prophet
        modules_status["trend_detector"]["prophet"] = "available"
    except ImportError:
        modules_status["trend_detector"]["prophet"] = "not installed"
    
    try:
        import torch
        modules_status["sentiment_analyzer"]["torch"] = f"available (version {torch.__version__})"
        modules_status["sentiment_analyzer"]["cuda"] = "available" if torch.cuda.is_available() else "not available"
    except ImportError:
        modules_status["sentiment_analyzer"]["torch"] = "not installed"
    
    return jsonify({
        "status": "healthy",
        "modules": modules_status,
        "timestamp": datetime.now().isoformat()
    })


@ai_bp.route('/models/info', methods=['GET'])
def get_models_info():
    """
    Obtiene información de los modelos cargados.
    
    Response:
        {
            "sentiment_model": {...},
            "clustering_model": {...},
            ...
        }
    """
    info = {}
    
    try:
        from ai.sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        info["sentiment_analyzer"] = analyzer.get_model_info()
    except Exception as e:
        info["sentiment_analyzer"] = {"error": str(e)}
    
    try:
        from ai.clustering_engine import ClusteringEngine
        engine = ClusteringEngine()
        info["clustering_engine"] = engine.get_model_info()
    except Exception as e:
        info["clustering_engine"] = {"error": str(e)}
    
    try:
        from ai.trend_detector import TrendDetector
        detector = TrendDetector()
        info["trend_detector"] = detector.get_model_info()
    except Exception as e:
        info["trend_detector"] = {"error": str(e)}
    
    try:
        from ai.anomaly_detector import AnomalyDetector
        detector = AnomalyDetector()
        info["anomaly_detector"] = detector.get_model_info()
    except Exception as e:
        info["anomaly_detector"] = {"error": str(e)}
    
    return jsonify({
        "models": info,
        "timestamp": datetime.now().isoformat()
    })


# ============================================================
# Crear aplicación Flask
# ============================================================

def create_app() -> Flask:
    """
    Crea y configura la aplicación Flask.
    
    Returns:
        Instancia de Flask configurada
    """
    app = Flask(__name__)
    
    # Configuración
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSON_AS_ASCII'] = False
    
    # Registrar blueprint
    app.register_blueprint(ai_bp)
    
    # Endpoint raíz
    @app.route('/')
    def index():
        return jsonify({
            "name": "OSINT EMI - AI Module API",
            "version": "1.0.0",
            "endpoints": {
                "sentiments": "/api/ai/analyze-sentiments",
                "trends": "/api/ai/trends",
                "clustering": "/api/ai/cluster-opinions",
                "anomalies": "/api/ai/anomalies",
                "correlations": "/api/ai/correlations",
                "health": "/api/ai/health"
            }
        })
    
    return app


# ============================================================
# Punto de entrada
# ============================================================

if __name__ == '__main__':
    app = create_app()
    
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         OSINT EMI - AI Module API Server                 ║
    ║                                                          ║
    ║  Endpoints disponibles:                                  ║
    ║  POST /api/ai/analyze-sentiments - Análisis sentimientos ║
    ║  GET  /api/ai/trends            - Tendencias temporales  ║
    ║  POST /api/ai/cluster-opinions  - Clustering opiniones   ║
    ║  GET  /api/ai/anomalies         - Detectar anomalías     ║
    ║  GET  /api/ai/correlations      - Correlaciones          ║
    ║  GET  /api/ai/health            - Estado del sistema     ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
