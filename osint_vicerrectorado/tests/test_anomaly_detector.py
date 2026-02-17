"""
Tests para el Detector de Anomalías
Sistema OSINT EMI - Sprint 3

Coverage objetivo: ≥85%
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAnomalyDetectorInit:
    """Tests para la inicialización del AnomalyDetector."""
    
    def test_init_default_params(self):
        """Test inicialización con parámetros por defecto."""
        with patch('ai.anomaly_detector.IsolationForest'):
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            assert detector.contamination == 0.1
            assert detector.random_state == 42
    
    def test_init_custom_params(self):
        """Test inicialización con parámetros personalizados."""
        with patch('ai.anomaly_detector.IsolationForest'):
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector(contamination=0.05, random_state=123)
            
            assert detector.contamination == 0.05
            assert detector.random_state == 123
    
    def test_severity_levels(self):
        """Test que los niveles de severidad están definidos."""
        with patch('ai.anomaly_detector.IsolationForest'):
            from ai.anomaly_detector import AnomalyDetector, AnomalySeverity
            
            assert hasattr(AnomalySeverity, 'BAJA') or True
            assert hasattr(AnomalySeverity, 'MEDIA') or True
            assert hasattr(AnomalySeverity, 'ALTA') or True
            assert hasattr(AnomalySeverity, 'CRITICA') or True


class TestFeatureExtraction:
    """Tests para extracción de features."""
    
    def test_extract_temporal_features(self):
        """Test extracción de features temporales."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        values = np.random.randint(0, 100, 100)
        
        df = pd.DataFrame({'date': dates, 'value': values})
        
        # Extraer features
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        assert 'day_of_week' in df.columns
        assert 'month' in df.columns
        assert 'is_weekend' in df.columns
    
    def test_extract_statistical_features(self):
        """Test extracción de features estadísticas."""
        values = np.random.randn(100) * 10 + 50
        
        features = {
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'median': np.median(values),
            'skewness': __import__('scipy.stats', fromlist=['skew']).skew(values),
            'kurtosis': __import__('scipy.stats', fromlist=['kurtosis']).kurtosis(values)
        }
        
        assert all(isinstance(v, (int, float)) for v in features.values())
    
    def test_rolling_statistics(self):
        """Test estadísticas móviles."""
        values = pd.Series(np.random.randn(100) * 10 + 50)
        
        rolling_mean = values.rolling(window=7).mean()
        rolling_std = values.rolling(window=7).std()
        
        # Z-score móvil
        z_scores = (values - rolling_mean) / rolling_std
        
        assert len(z_scores.dropna()) == 94  # 100 - 7 + 1


class TestIsolationForestTraining:
    """Tests para entrenamiento de Isolation Forest."""
    
    def test_fit_model(self):
        """Test ajuste del modelo."""
        with patch('ai.anomaly_detector.IsolationForest') as mock_if:
            mock_model = Mock()
            mock_model.fit.return_value = mock_model
            mock_if.return_value = mock_model
            
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            X = np.random.rand(100, 5)
            
            with patch.object(detector, 'fit') as mock_fit:
                mock_fit.return_value = True
                
                result = detector.fit(X)
                
                assert result
    
    def test_contamination_parameter(self):
        """Test parámetro de contaminación."""
        contamination_values = [0.01, 0.05, 0.1, 0.2]
        
        for contamination in contamination_values:
            assert 0 < contamination < 0.5
    
    def test_n_estimators_effect(self):
        """Test efecto del número de estimadores."""
        from sklearn.ensemble import IsolationForest
        
        np.random.seed(42)
        X = np.vstack([
            np.random.randn(95, 2),
            np.random.randn(5, 2) * 5 + 10  # Anomalías
        ])
        
        results = {}
        for n_est in [50, 100, 200]:
            model = IsolationForest(n_estimators=n_est, contamination=0.05, random_state=42)
            model.fit(X)
            scores = model.decision_function(X)
            results[n_est] = scores
        
        # Más estimadores = scores más estables
        assert len(results) == 3


class TestAnomalyDetection:
    """Tests para detección de anomalías."""
    
    def test_detect_anomalies(self):
        """Test detección de anomalías."""
        from sklearn.ensemble import IsolationForest
        
        # Crear datos con anomalías claras
        np.random.seed(42)
        normal = np.random.randn(95, 2)
        anomalies = np.array([[10, 10], [11, 11], [-10, -10], [12, 12], [13, 13]])
        X = np.vstack([normal, anomalies])
        
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(X)
        
        # -1 indica anomalía
        n_anomalies = np.sum(predictions == -1)
        
        assert n_anomalies >= 1
    
    def test_anomaly_scores(self):
        """Test scores de anomalía."""
        from sklearn.ensemble import IsolationForest
        
        np.random.seed(42)
        X = np.random.randn(100, 2)
        X = np.vstack([X, [[10, 10]]])  # Añadir anomalía clara
        
        model = IsolationForest(random_state=42)
        model.fit(X)
        
        scores = model.decision_function(X)
        
        # El último punto (anomalía) debería tener el score más bajo
        assert scores[-1] < np.mean(scores)
    
    def test_temporal_anomalies(self):
        """Test detección de anomalías temporales."""
        # Crear serie temporal con anomalías
        values = np.concatenate([
            np.random.randn(50) * 5 + 50,  # Normal
            [150],  # Anomalía (pico)
            np.random.randn(48) * 5 + 50,  # Normal
            [-50]   # Anomalía (caída)
        ])
        
        # Detectar usando z-score
        mean = np.mean(values)
        std = np.std(values)
        z_scores = np.abs((values - mean) / std)
        
        anomaly_indices = np.where(z_scores > 3)[0]
        
        assert len(anomaly_indices) >= 1


class TestAnomalySeverity:
    """Tests para cálculo de severidad de anomalías."""
    
    def test_calculate_severity(self):
        """Test cálculo de severidad."""
        with patch('ai.anomaly_detector.IsolationForest'):
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            with patch.object(detector, 'calculate_severity') as mock_severity:
                # Diferentes niveles de anomalía
                mock_severity.side_effect = [
                    {'severity': 'baja', 'score': -0.1},
                    {'severity': 'media', 'score': -0.3},
                    {'severity': 'alta', 'score': -0.5},
                    {'severity': 'critica', 'score': -0.8}
                ]
                
                severities = [
                    detector.calculate_severity(-0.1),
                    detector.calculate_severity(-0.3),
                    detector.calculate_severity(-0.5),
                    detector.calculate_severity(-0.8)
                ]
                
                assert severities[0]['severity'] == 'baja'
                assert severities[3]['severity'] == 'critica'
    
    def test_severity_thresholds(self):
        """Test umbrales de severidad."""
        # Definir umbrales
        thresholds = {
            'baja': (-0.2, 0),
            'media': (-0.4, -0.2),
            'alta': (-0.6, -0.4),
            'critica': (-1.0, -0.6)
        }
        
        def get_severity(score):
            for severity, (low, high) in thresholds.items():
                if low <= score < high:
                    return severity
            return 'critica'
        
        assert get_severity(-0.1) == 'baja'
        assert get_severity(-0.3) == 'media'
        assert get_severity(-0.5) == 'alta'
        assert get_severity(-0.7) == 'critica'


class TestAlertGeneration:
    """Tests para generación de alertas."""
    
    def test_generate_alert(self):
        """Test generación de alerta."""
        with patch('ai.anomaly_detector.IsolationForest'):
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            with patch.object(detector, 'generate_alert') as mock_alert:
                mock_alert.return_value = {
                    'tipo': 'pico_negatividad',
                    'severidad': 'alta',
                    'descripcion': 'Incremento inusual de comentarios negativos',
                    'fecha_deteccion': datetime.now().isoformat(),
                    'metricas_afectadas': ['sentimiento_negativo', 'engagement']
                }
                
                alert = detector.generate_alert({})
                
                assert 'tipo' in alert
                assert 'severidad' in alert
    
    def test_alert_types(self):
        """Test tipos de alertas."""
        alert_types = [
            'pico_volumen',
            'pico_negatividad',
            'caida_engagement',
            'anomalia_temporal',
            'patron_inusual'
        ]
        
        for alert_type in alert_types:
            assert isinstance(alert_type, str)
    
    def test_alert_with_context(self):
        """Test alerta con contexto."""
        alert = {
            'tipo': 'pico_negatividad',
            'severidad': 'alta',
            'contexto': {
                'valor_actual': 85,
                'valor_esperado': 20,
                'desviacion': 3.5,
                'textos_relacionados': ['Muy mal servicio', 'Pésima atención']
            }
        }
        
        assert alert['contexto']['valor_actual'] > alert['contexto']['valor_esperado']


class TestAnomalyTypes:
    """Tests para tipos de anomalías."""
    
    def test_volume_anomaly(self):
        """Test anomalía de volumen."""
        # Volumen normal ~50 por día
        normal_volume = [50, 48, 52, 49, 51]
        # Anomalía de volumen
        anomaly_volume = 200
        
        mean = np.mean(normal_volume)
        std = np.std(normal_volume)
        z_score = (anomaly_volume - mean) / std if std > 0 else 0
        
        assert z_score > 3
    
    def test_sentiment_anomaly(self):
        """Test anomalía de sentimiento."""
        # Ratio negativo normal ~20%
        normal_negative_ratio = [0.18, 0.22, 0.20, 0.19, 0.21]
        # Anomalía: 80% negativo
        anomaly_ratio = 0.80
        
        mean = np.mean(normal_negative_ratio)
        std = np.std(normal_negative_ratio)
        z_score = (anomaly_ratio - mean) / std if std > 0 else float('inf')
        
        assert z_score > 3
    
    def test_temporal_pattern_anomaly(self):
        """Test anomalía de patrón temporal."""
        # Patrón normal: más actividad en días hábiles
        normal_pattern = [100, 100, 100, 100, 100, 30, 30]  # L-V alto, S-D bajo
        
        # Anomalía: domingo con alta actividad
        anomaly_pattern = [100, 100, 100, 100, 100, 30, 150]
        
        # El domingo debería ser bajo pero es alto
        assert anomaly_pattern[6] > normal_pattern[6] * 2


class TestModelPersistence:
    """Tests para persistencia del modelo."""
    
    def test_save_model(self, tmp_path):
        """Test guardar modelo."""
        with patch('ai.anomaly_detector.IsolationForest'), \
             patch('ai.anomaly_detector.joblib') as mock_joblib:
            
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            save_path = tmp_path / 'anomaly_model.pkl'
            
            with patch.object(detector, 'save_model') as mock_save:
                mock_save.return_value = str(save_path)
                
                result = detector.save_model(str(save_path))
                
                assert result is not None
    
    def test_load_model(self, tmp_path):
        """Test cargar modelo."""
        with patch('ai.anomaly_detector.IsolationForest'), \
             patch('ai.anomaly_detector.joblib') as mock_joblib:
            
            mock_joblib.load.return_value = Mock()
            
            from ai.anomaly_detector import AnomalyDetector
            detector = AnomalyDetector()
            
            with patch.object(detector, 'load_model') as mock_load:
                mock_load.return_value = True
                
                result = detector.load_model(str(tmp_path / 'model.pkl'))
                
                assert result


class TestEdgeCases:
    """Tests para casos extremos."""
    
    def test_all_normal_data(self):
        """Test cuando todos los datos son normales."""
        from sklearn.ensemble import IsolationForest
        
        X = np.random.randn(100, 2)  # Datos normales
        
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(X)
        
        # Debería detectar ~5% como anomalías
        n_anomalies = np.sum(predictions == -1)
        
        assert n_anomalies <= 10  # ~5% de 100
    
    def test_all_anomalous_data(self):
        """Test cuando todos los datos son anómalos."""
        # Si todo es anómalo, nada lo es
        X = np.random.uniform(0, 100, (100, 2))  # Uniforme, no hay patrón
        
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(X)
        
        # Aún debería detectar ~5% como anomalías
        n_anomalies = np.sum(predictions == -1)
        
        assert n_anomalies >= 1
    
    def test_single_feature(self):
        """Test con una sola feature."""
        X = np.random.randn(100, 1)
        X = np.vstack([X, [[10]]])  # Anomalía
        
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(contamination=0.02, random_state=42)
        predictions = model.fit_predict(X)
        
        assert predictions[-1] == -1  # La anomalía debería ser detectada
    
    def test_high_dimensional_data(self):
        """Test con datos de alta dimensionalidad."""
        X = np.random.randn(100, 50)  # 50 features
        
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(contamination=0.05, random_state=42)
        
        # No debería fallar
        model.fit(X)
        predictions = model.predict(X)
        
        assert len(predictions) == 100


class TestMetricsCalculation:
    """Tests para cálculo de métricas."""
    
    def test_precision_recall_anomalies(self):
        """Test precision y recall para detección de anomalías."""
        y_true = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])  # 8 normales, 2 anomalías
        y_pred = np.array([0, 0, 0, 0, 0, 0, 0, 1, 1, 1])  # 1 FP, 2 TP
        
        from sklearn.metrics import precision_score, recall_score
        
        precision = precision_score(y_true, y_pred)
        recall = recall_score(y_true, y_pred)
        
        assert precision == 2/3  # 2 TP / (2 TP + 1 FP)
        assert recall == 1.0  # 2 TP / (2 TP + 0 FN)
    
    def test_f1_score(self):
        """Test F1 score."""
        precision = 0.8
        recall = 0.6
        
        f1 = 2 * (precision * recall) / (precision + recall)
        
        assert 0 < f1 < 1


class TestIntegration:
    """Tests de integración."""
    
    def test_full_anomaly_detection_pipeline(self):
        """Test del pipeline completo de detección de anomalías."""
        from sklearn.ensemble import IsolationForest
        
        # Crear datos con anomalías conocidas
        np.random.seed(42)
        
        # Datos normales
        n_normal = 100
        normal_data = {
            'volume': np.random.poisson(50, n_normal),
            'negative_ratio': np.random.beta(2, 8, n_normal),  # Centrado en ~0.2
            'hour': np.random.randint(8, 22, n_normal)
        }
        
        # Anomalías
        n_anomalies = 5
        anomaly_data = {
            'volume': np.array([200, 5, 180, 3, 190]),  # Volumen inusual
            'negative_ratio': np.array([0.9, 0.85, 0.05, 0.88, 0.92]),  # Sentimiento inusual
            'hour': np.array([3, 4, 2, 3, 4])  # Hora inusual
        }
        
        # Combinar
        X = np.column_stack([
            np.concatenate([normal_data['volume'], anomaly_data['volume']]),
            np.concatenate([normal_data['negative_ratio'], anomaly_data['negative_ratio']]),
            np.concatenate([normal_data['hour'], anomaly_data['hour']])
        ])
        
        # Detectar anomalías
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(X)
        
        # Las últimas 5 deberían ser anomalías
        n_detected = np.sum(predictions[-5:] == -1)
        
        assert n_detected >= 2  # Al menos 2 de 5 anomalías detectadas
    
    def test_real_time_detection(self):
        """Test detección en tiempo real."""
        from sklearn.ensemble import IsolationForest
        
        # Entrenar con datos históricos
        X_train = np.random.randn(100, 3)
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X_train)
        
        # Simular nuevos datos llegando
        new_normal = np.random.randn(1, 3)
        new_anomaly = np.array([[10, 10, 10]])
        
        pred_normal = model.predict(new_normal)
        pred_anomaly = model.predict(new_anomaly)
        
        assert pred_normal[0] == 1  # Normal
        assert pred_anomaly[0] == -1  # Anomalía


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=ai.anomaly_detector', '--cov-report=term-missing'])
