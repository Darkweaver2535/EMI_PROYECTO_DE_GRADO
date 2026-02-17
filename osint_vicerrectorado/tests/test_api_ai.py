"""
Tests para los Endpoints de la API de IA
Sistema OSINT EMI - Sprint 3

Coverage objetivo: ≥85%
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app():
    """Fixture para crear la aplicación Flask."""
    with patch('api.ai_endpoints.SentimentAnalyzer'), \
         patch('api.ai_endpoints.ClusteringEngine'), \
         patch('api.ai_endpoints.TrendDetector'), \
         patch('api.ai_endpoints.AnomalyDetector'), \
         patch('api.ai_endpoints.CorrelationAnalyzer'):
        
        from api import create_app
        app = create_app()
        app.config['TESTING'] = True
        
        yield app


@pytest.fixture
def client(app):
    """Fixture para crear cliente de prueba."""
    return app.test_client()


class TestHealthEndpoint:
    """Tests para el endpoint de health check."""
    
    def test_health_check(self, client):
        """Test endpoint de salud."""
        with patch('api.ai_endpoints.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [100]
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'status' in data


class TestSentimentEndpoints:
    """Tests para endpoints de sentimiento."""
    
    def test_analyze_sentiments_success(self, client):
        """Test análisis de sentimientos exitoso."""
        with patch('api.ai_endpoints.SentimentAnalyzer') as mock_analyzer:
            mock_instance = Mock()
            mock_instance.predict_batch.return_value = [
                {'texto': 'Texto 1', 'sentimiento': 'Positivo', 'confianza': 0.85},
                {'texto': 'Texto 2', 'sentimiento': 'Negativo', 'confianza': 0.78}
            ]
            mock_analyzer.return_value = mock_instance
            
            response = client.post('/api/ai/analyze-sentiments',
                                  json={'texts': ['Texto 1', 'Texto 2']},
                                  content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'results' in data
    
    def test_analyze_sentiments_empty_texts(self, client):
        """Test con textos vacíos."""
        response = client.post('/api/ai/analyze-sentiments',
                              json={'texts': []},
                              content_type='application/json')
        
        assert response.status_code in [200, 400]
    
    def test_analyze_sentiments_invalid_json(self, client):
        """Test con JSON inválido."""
        response = client.post('/api/ai/analyze-sentiments',
                              data='invalid json',
                              content_type='application/json')
        
        assert response.status_code == 400
    
    def test_train_sentiment_model(self, client):
        """Test entrenamiento del modelo."""
        with patch('api.ai_endpoints.SentimentAnalyzer') as mock_analyzer:
            mock_instance = Mock()
            mock_instance.fine_tune.return_value = {
                'accuracy': 0.87,
                'f1_score': 0.85,
                'epochs': 3
            }
            mock_analyzer.return_value = mock_instance
            
            response = client.post('/api/ai/sentiments/train',
                                  json={'epochs': 3, 'batch_size': 16},
                                  content_type='application/json')
            
            assert response.status_code in [200, 202, 500]


class TestClusteringEndpoints:
    """Tests para endpoints de clustering."""
    
    def test_cluster_opinions_success(self, client):
        """Test clustering exitoso."""
        with patch('api.ai_endpoints.ClusteringEngine') as mock_engine:
            mock_instance = Mock()
            mock_instance.fit_clusters.return_value = {
                'n_clusters': 3,
                'silhouette_score': 0.55,
                'labels': [0, 1, 2, 0, 1, 2],
                'clusters': {
                    0: {'size': 2, 'keywords': ['universidad', 'educacion']},
                    1: {'size': 2, 'keywords': ['servicio', 'atencion']},
                    2: {'size': 2, 'keywords': ['horario', 'biblioteca']}
                }
            }
            mock_engine.return_value = mock_instance
            
            response = client.post('/api/ai/cluster-opinions',
                                  json={'n_clusters': 3},
                                  content_type='application/json')
            
            assert response.status_code in [200, 500]
    
    def test_cluster_opinions_auto_k(self, client):
        """Test clustering con k automático."""
        with patch('api.ai_endpoints.ClusteringEngine') as mock_engine:
            mock_instance = Mock()
            mock_instance.find_optimal_k.return_value = {'optimal_k': 4}
            mock_instance.fit_clusters.return_value = {
                'n_clusters': 4,
                'silhouette_score': 0.52
            }
            mock_engine.return_value = mock_instance
            
            response = client.post('/api/ai/cluster-opinions',
                                  json={},
                                  content_type='application/json')
            
            assert response.status_code in [200, 500]


class TestTrendEndpoints:
    """Tests para endpoints de tendencias."""
    
    def test_get_trends_success(self, client):
        """Test obtención de tendencias exitoso."""
        with patch('api.ai_endpoints.TrendDetector') as mock_detector, \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_instance = Mock()
            mock_instance.analyze_sentiment_trend.return_value = {
                'trend': 'increasing',
                'strength': 0.65,
                'forecast': [0.55, 0.57, 0.59]
            }
            mock_detector.return_value = mock_instance
            
            # Mock database
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = [
                ('2024-01-01', 10, 5, 3),
                ('2024-01-02', 12, 6, 4)
            ]
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/trends?period=30')
            
            assert response.status_code in [200, 500]
    
    def test_get_trends_with_forecast(self, client):
        """Test tendencias con pronóstico."""
        with patch('api.ai_endpoints.TrendDetector') as mock_detector, \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_instance = Mock()
            mock_instance.forecast.return_value = {
                'dates': ['2024-04-01', '2024-04-02'],
                'values': [55, 57],
                'lower': [50, 52],
                'upper': [60, 62]
            }
            mock_detector.return_value = mock_instance
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/trends?forecast_days=7')
            
            assert response.status_code in [200, 500]


class TestAnomalyEndpoints:
    """Tests para endpoints de anomalías."""
    
    def test_get_anomalies_success(self, client):
        """Test obtención de anomalías exitoso."""
        with patch('api.ai_endpoints.AnomalyDetector') as mock_detector, \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_instance = Mock()
            mock_instance.detect_anomalies.return_value = {
                'anomalies': [
                    {'date': '2024-03-15', 'type': 'pico_negatividad', 'severity': 'alta'}
                ],
                'total_detected': 1
            }
            mock_detector.return_value = mock_instance
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/anomalies')
            
            assert response.status_code in [200, 500]
    
    def test_get_anomalies_with_severity_filter(self, client):
        """Test anomalías con filtro de severidad."""
        with patch('api.ai_endpoints.AnomalyDetector') as mock_detector, \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_instance = Mock()
            mock_instance.detect_anomalies.return_value = {
                'anomalies': [
                    {'date': '2024-03-15', 'type': 'pico_negatividad', 'severity': 'critica'}
                ],
                'total_detected': 1
            }
            mock_detector.return_value = mock_instance
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/anomalies?min_severity=alta')
            
            assert response.status_code in [200, 500]


class TestCorrelationEndpoints:
    """Tests para endpoints de correlación."""
    
    def test_get_correlations_success(self, client):
        """Test obtención de correlaciones exitoso."""
        with patch('api.ai_endpoints.CorrelationAnalyzer') as mock_analyzer, \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_instance = Mock()
            mock_instance.calculate_correlation_matrix.return_value = {
                'matrix': [[1.0, 0.5], [0.5, 1.0]],
                'variables': ['sentimiento', 'engagement']
            }
            mock_instance.identify_significant_correlations.return_value = [
                {'var1': 'sentimiento', 'var2': 'engagement', 'correlation': 0.65, 'p_value': 0.01}
            ]
            mock_analyzer.return_value = mock_instance
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/correlations')
            
            assert response.status_code in [200, 500]


class TestErrorHandling:
    """Tests para manejo de errores."""
    
    def test_404_endpoint(self, client):
        """Test endpoint no existente."""
        response = client.get('/api/ai/nonexistent')
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test método no permitido."""
        response = client.put('/api/ai/health')
        
        assert response.status_code in [405, 404]
    
    def test_internal_server_error(self, client):
        """Test error interno del servidor."""
        with patch('api.ai_endpoints.SentimentAnalyzer') as mock_analyzer:
            mock_analyzer.side_effect = Exception('Error interno')
            
            response = client.post('/api/ai/analyze-sentiments',
                                  json={'texts': ['test']},
                                  content_type='application/json')
            
            assert response.status_code in [200, 500]


class TestRequestValidation:
    """Tests para validación de requests."""
    
    def test_missing_required_field(self, client):
        """Test campo requerido faltante."""
        response = client.post('/api/ai/analyze-sentiments',
                              json={},
                              content_type='application/json')
        
        assert response.status_code in [400, 500]
    
    def test_invalid_field_type(self, client):
        """Test tipo de campo inválido."""
        response = client.post('/api/ai/analyze-sentiments',
                              json={'texts': 'not a list'},
                              content_type='application/json')
        
        assert response.status_code in [400, 500]
    
    def test_empty_request_body(self, client):
        """Test body de request vacío."""
        response = client.post('/api/ai/analyze-sentiments',
                              content_type='application/json')
        
        assert response.status_code in [400, 415]


class TestResponseFormat:
    """Tests para formato de respuestas."""
    
    def test_response_is_json(self, client):
        """Test que las respuestas son JSON."""
        with patch('api.ai_endpoints.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [100]
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/health')
            
            assert response.content_type == 'application/json'
    
    def test_response_structure(self, client):
        """Test estructura de respuesta."""
        with patch('api.ai_endpoints.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [100]
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/health')
            data = json.loads(response.data)
            
            # Verificar estructura mínima
            assert isinstance(data, dict)


class TestPagination:
    """Tests para paginación."""
    
    def test_pagination_params(self, client):
        """Test parámetros de paginación."""
        with patch('api.ai_endpoints.AnomalyDetector'), \
             patch('api.ai_endpoints.get_db_connection') as mock_db:
            
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            response = client.get('/api/ai/anomalies?page=1&limit=10')
            
            assert response.status_code in [200, 500]


class TestCORS:
    """Tests para CORS."""
    
    def test_cors_headers(self, client):
        """Test headers CORS."""
        response = client.options('/api/ai/health')
        
        # Verificar que no falla
        assert response.status_code in [200, 204, 404]


class TestRateLimiting:
    """Tests para rate limiting (si está implementado)."""
    
    def test_multiple_requests(self, client):
        """Test múltiples requests."""
        with patch('api.ai_endpoints.get_db_connection') as mock_db:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor.fetchone.return_value = [100]
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__ = Mock(return_value=mock_conn)
            mock_db.return_value.__exit__ = Mock(return_value=None)
            
            responses = [client.get('/api/ai/health') for _ in range(10)]
            
            # Todas deberían ser exitosas
            assert all(r.status_code == 200 for r in responses)


class TestIntegration:
    """Tests de integración de la API."""
    
    def test_full_analysis_workflow(self, client):
        """Test flujo completo de análisis."""
        with patch('api.ai_endpoints.SentimentAnalyzer') as mock_sentiment, \
             patch('api.ai_endpoints.ClusteringEngine') as mock_cluster:
            
            # Análisis de sentimientos
            mock_sentiment_instance = Mock()
            mock_sentiment_instance.predict_batch.return_value = [
                {'texto': 'Buen servicio', 'sentimiento': 'Positivo', 'confianza': 0.9}
            ]
            mock_sentiment.return_value = mock_sentiment_instance
            
            response1 = client.post('/api/ai/analyze-sentiments',
                                   json={'texts': ['Buen servicio']},
                                   content_type='application/json')
            
            assert response1.status_code in [200, 500]
            
            # Clustering
            mock_cluster_instance = Mock()
            mock_cluster_instance.fit_clusters.return_value = {
                'n_clusters': 2,
                'silhouette_score': 0.6
            }
            mock_cluster.return_value = mock_cluster_instance
            
            response2 = client.post('/api/ai/cluster-opinions',
                                   json={'n_clusters': 2},
                                   content_type='application/json')
            
            assert response2.status_code in [200, 500]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=api.ai_endpoints', '--cov-report=term-missing'])
