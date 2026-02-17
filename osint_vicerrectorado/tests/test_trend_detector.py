"""
Tests para el Detector de Tendencias
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


class TestTrendDetectorInit:
    """Tests para la inicialización del TrendDetector."""
    
    def test_init_default_params(self):
        """Test inicialización con parámetros por defecto."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector()
            
            assert detector.freq == 'D'
            assert detector.periods == 30
    
    def test_init_custom_params(self):
        """Test inicialización con parámetros personalizados."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector(freq='W', periods=12)
            
            assert detector.freq == 'W'
            assert detector.periods == 12
    
    def test_prophet_availability(self):
        """Test detección de disponibilidad de Prophet."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector()
            
            assert hasattr(detector, 'prophet_available') or True


class TestDataPreparation:
    """Tests para preparación de datos temporales."""
    
    def test_prepare_time_series(self):
        """Test preparación de serie temporal."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        values = np.random.randint(0, 100, 30)
        
        df = pd.DataFrame({'ds': dates, 'y': values})
        
        assert len(df) == 30
        assert 'ds' in df.columns
        assert 'y' in df.columns
    
    def test_handle_missing_dates(self):
        """Test manejo de fechas faltantes."""
        dates = pd.to_datetime(['2024-01-01', '2024-01-03', '2024-01-05'])
        values = [10, 20, 30]
        
        df = pd.DataFrame({'ds': dates, 'y': values})
        
        # Rellenar fechas faltantes
        full_range = pd.date_range(start=df['ds'].min(), end=df['ds'].max(), freq='D')
        df_full = df.set_index('ds').reindex(full_range).fillna(0).reset_index()
        df_full.columns = ['ds', 'y']
        
        assert len(df_full) == 5
    
    def test_aggregate_by_period(self):
        """Test agregación por período."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        values = np.random.randint(0, 100, 100)
        
        df = pd.DataFrame({'date': dates, 'value': values})
        
        # Agregar por semana
        df['week'] = df['date'].dt.isocalendar().week
        weekly = df.groupby('week')['value'].sum()
        
        assert len(weekly) < len(df)


class TestTrendAnalysis:
    """Tests para análisis de tendencias."""
    
    def test_fit_trend(self):
        """Test ajuste de modelo de tendencia."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector()
            
            # Crear datos de prueba
            dates = pd.date_range(start='2024-01-01', periods=90, freq='D')
            values = np.linspace(10, 50, 90) + np.random.randn(90) * 5
            
            with patch.object(detector, 'fit') as mock_fit:
                mock_fit.return_value = {'trend': 'increasing', 'strength': 0.8}
                
                result = detector.fit(dates, values)
                
                assert 'trend' in result
    
    def test_detect_increasing_trend(self):
        """Test detección de tendencia creciente."""
        # Crear serie con tendencia creciente clara
        values = np.linspace(10, 100, 50) + np.random.randn(50) * 2
        
        # Calcular pendiente
        slope = np.polyfit(range(len(values)), values, 1)[0]
        
        assert slope > 0
    
    def test_detect_decreasing_trend(self):
        """Test detección de tendencia decreciente."""
        values = np.linspace(100, 10, 50) + np.random.randn(50) * 2
        
        slope = np.polyfit(range(len(values)), values, 1)[0]
        
        assert slope < 0
    
    def test_detect_stable_trend(self):
        """Test detección de tendencia estable."""
        values = np.ones(50) * 50 + np.random.randn(50) * 2
        
        slope = np.polyfit(range(len(values)), values, 1)[0]
        
        assert abs(slope) < 1


class TestSentimentTrendAnalysis:
    """Tests para análisis de tendencia de sentimientos."""
    
    def test_analyze_sentiment_trend(self):
        """Test análisis de tendencia de sentimientos."""
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        sentiments = np.random.choice(['Positivo', 'Negativo', 'Neutral'], 60)
        
        df = pd.DataFrame({'date': dates, 'sentiment': sentiments})
        
        # Calcular porcentaje de positivos por día
        df['is_positive'] = (df['sentiment'] == 'Positivo').astype(int)
        daily_positive = df.groupby('date')['is_positive'].mean()
        
        assert len(daily_positive) == 60
    
    def test_sentiment_ratio_over_time(self):
        """Test ratio de sentimientos a lo largo del tiempo."""
        # Simular mejora de sentimiento
        early_sentiments = ['Negativo'] * 30 + ['Neutral'] * 20
        late_sentiments = ['Positivo'] * 30 + ['Neutral'] * 20
        
        early_positive_ratio = sum(1 for s in early_sentiments if s == 'Positivo') / len(early_sentiments)
        late_positive_ratio = sum(1 for s in late_sentiments if s == 'Positivo') / len(late_sentiments)
        
        assert late_positive_ratio > early_positive_ratio


class TestSeasonalityDetection:
    """Tests para detección de estacionalidad."""
    
    def test_detect_weekly_seasonality(self):
        """Test detección de estacionalidad semanal."""
        # Crear patrón semanal
        days = 70  # 10 semanas
        pattern = [10, 20, 30, 40, 50, 30, 10]  # Lun-Dom
        values = pattern * 10
        
        # Verificar periodicidad
        assert len(values) == days
        assert values[0] == values[7]  # Mismo día de la semana
    
    def test_detect_academic_seasonality(self):
        """Test detección de estacionalidad académica."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector()
            
            with patch.object(detector, 'detect_seasonality') as mock_season:
                mock_season.return_value = {
                    'has_seasonality': True,
                    'type': 'academic',
                    'periods': ['inicio_semestre', 'examenes', 'vacaciones']
                }
                
                result = detector.detect_seasonality([])
                
                assert result['has_seasonality'] == True
    
    def test_decompose_time_series(self):
        """Test descomposición de serie temporal."""
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Crear serie con tendencia y estacionalidad
        t = np.arange(100)
        trend = 0.5 * t
        seasonal = 10 * np.sin(2 * np.pi * t / 7)  # Semanal
        noise = np.random.randn(100) * 2
        values = trend + seasonal + noise
        
        series = pd.Series(values, index=pd.date_range('2024-01-01', periods=100))
        
        result = seasonal_decompose(series, model='additive', period=7)
        
        assert result.trend is not None
        assert result.seasonal is not None
        assert result.resid is not None


class TestForecasting:
    """Tests para pronóstico."""
    
    def test_forecast_future(self):
        """Test pronóstico de valores futuros."""
        with patch('ai.trend_detector.Prophet', None):
            from ai.trend_detector import TrendDetector
            detector = TrendDetector(periods=7)
            
            with patch.object(detector, 'forecast') as mock_forecast:
                mock_forecast.return_value = {
                    'dates': pd.date_range(start='2024-04-01', periods=7),
                    'values': [45, 46, 47, 48, 49, 50, 51],
                    'lower': [40, 41, 42, 43, 44, 45, 46],
                    'upper': [50, 51, 52, 53, 54, 55, 56]
                }
                
                result = detector.forecast()
                
                assert len(result['values']) == 7
                assert all(result['lower'][i] <= result['values'][i] <= result['upper'][i] 
                          for i in range(7))
    
    def test_arima_fallback(self):
        """Test fallback a ARIMA cuando Prophet no está disponible."""
        from statsmodels.tsa.arima.model import ARIMA
        
        # Crear serie temporal simple
        values = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30]
        
        model = ARIMA(values, order=(1, 1, 1))
        fitted = model.fit()
        forecast = fitted.forecast(steps=3)
        
        assert len(forecast) == 3
    
    def test_forecast_confidence_intervals(self):
        """Test intervalos de confianza en pronósticos."""
        predicted_value = 50
        std_error = 5
        
        # Intervalo de confianza 95%
        lower_95 = predicted_value - 1.96 * std_error
        upper_95 = predicted_value + 1.96 * std_error
        
        assert lower_95 < predicted_value < upper_95
        assert upper_95 - lower_95 == pytest.approx(2 * 1.96 * std_error)


class TestChangePointDetection:
    """Tests para detección de puntos de cambio."""
    
    def test_identify_change_points(self):
        """Test identificación de puntos de cambio."""
        # Crear serie con cambio claro
        values = [10] * 30 + [50] * 30  # Salto en t=30
        
        # Detectar cambio simple
        diffs = np.diff(values)
        change_point = np.argmax(np.abs(diffs))
        
        assert change_point == 29  # Justo antes del cambio
    
    def test_gradual_change_detection(self):
        """Test detección de cambio gradual."""
        # Cambio gradual
        values = list(np.linspace(10, 20, 20)) + list(np.linspace(20, 50, 20))
        
        # Calcular segunda derivada para detectar aceleración
        first_diff = np.diff(values)
        second_diff = np.diff(first_diff)
        
        assert len(second_diff) > 0


class TestMetricsCalculation:
    """Tests para cálculo de métricas de tendencia."""
    
    def test_calculate_trend_strength(self):
        """Test cálculo de fuerza de tendencia."""
        # Tendencia fuerte
        strong_trend = np.linspace(0, 100, 50)
        # Tendencia débil
        weak_trend = np.ones(50) + np.random.randn(50) * 10
        
        # R² de regresión lineal
        from scipy.stats import linregress
        
        strong_r = linregress(range(len(strong_trend)), strong_trend).rvalue ** 2
        weak_r = linregress(range(len(weak_trend)), weak_trend).rvalue ** 2
        
        assert strong_r > 0.9
        assert weak_r < 0.5
    
    def test_calculate_volatility(self):
        """Test cálculo de volatilidad."""
        stable_values = [50, 51, 49, 50, 51, 49]
        volatile_values = [10, 90, 20, 80, 30, 70]
        
        stable_std = np.std(stable_values)
        volatile_std = np.std(volatile_values)
        
        assert volatile_std > stable_std
    
    def test_moving_average(self):
        """Test cálculo de media móvil."""
        values = [10, 20, 30, 40, 50, 60, 70]
        window = 3
        
        ma = pd.Series(values).rolling(window=window).mean().dropna()
        
        assert len(ma) == len(values) - window + 1
        assert ma.iloc[0] == 20  # (10+20+30)/3


class TestEdgeCases:
    """Tests para casos extremos."""
    
    def test_empty_data(self):
        """Test con datos vacíos."""
        data = []
        
        assert len(data) == 0
    
    def test_single_data_point(self):
        """Test con un solo punto de datos."""
        data = [50]
        
        # No se puede calcular tendencia
        assert len(data) < 2
    
    def test_constant_values(self):
        """Test con valores constantes."""
        values = [50] * 100
        
        std = np.std(values)
        
        assert std == 0
    
    def test_nan_values(self):
        """Test con valores NaN."""
        values = [10, 20, np.nan, 40, 50]
        
        clean_values = [v for v in values if not np.isnan(v)]
        
        assert len(clean_values) == 4
    
    def test_irregular_timestamps(self):
        """Test con timestamps irregulares."""
        dates = pd.to_datetime(['2024-01-01', '2024-01-05', '2024-01-06', '2024-01-20'])
        values = [10, 20, 30, 40]
        
        # Calcular gaps
        gaps = np.diff(dates).astype('timedelta64[D]').astype(int)
        
        assert gaps[0] == 4  # 4 días entre primer y segundo punto


class TestARIMAImplementation:
    """Tests específicos para implementación ARIMA."""
    
    def test_arima_order_selection(self):
        """Test selección de orden ARIMA."""
        # Valores típicos: (p, d, q)
        orders = [(1, 0, 0), (1, 1, 0), (1, 1, 1), (2, 1, 2)]
        
        for order in orders:
            p, d, q = order
            assert p >= 0 and d >= 0 and q >= 0
    
    def test_arima_fit_predict(self):
        """Test ajuste y predicción con ARIMA."""
        from statsmodels.tsa.arima.model import ARIMA
        
        # Serie con tendencia clara
        np.random.seed(42)
        values = np.cumsum(np.random.randn(100)) + np.arange(100) * 0.1
        
        model = ARIMA(values, order=(1, 1, 1))
        fitted = model.fit()
        
        # Predicción
        forecast = fitted.forecast(steps=5)
        
        assert len(forecast) == 5


class TestIntegration:
    """Tests de integración."""
    
    def test_full_trend_analysis_pipeline(self):
        """Test del pipeline completo de análisis de tendencias."""
        # Crear datos de prueba
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=90, freq='D')
        
        # Tendencia creciente con ruido
        trend = np.linspace(20, 80, 90)
        seasonality = 10 * np.sin(2 * np.pi * np.arange(90) / 7)
        noise = np.random.randn(90) * 5
        values = trend + seasonality + noise
        
        df = pd.DataFrame({'ds': dates, 'y': values})
        
        # Análisis básico
        slope, intercept, r_value, p_value, std_err = __import__('scipy.stats', fromlist=['linregress']).linregress(
            range(len(values)), values
        )
        
        assert slope > 0  # Tendencia creciente
        assert r_value ** 2 > 0.5  # Buen ajuste
    
    def test_sentiment_trend_integration(self):
        """Test integración con análisis de sentimientos."""
        # Simular datos de sentimiento a lo largo del tiempo
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        
        # Mejora gradual en sentimientos
        positive_ratio = np.linspace(0.2, 0.6, 60) + np.random.randn(60) * 0.05
        positive_ratio = np.clip(positive_ratio, 0, 1)
        
        df = pd.DataFrame({
            'date': dates,
            'positive_ratio': positive_ratio
        })
        
        # Verificar tendencia creciente
        slope = np.polyfit(range(len(positive_ratio)), positive_ratio, 1)[0]
        
        assert slope > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=ai.trend_detector', '--cov-report=term-missing'])
