"""
TrendDetector - Detección de Tendencias Temporales
Sistema de Analítica EMI - Sprint 3

Este módulo implementa análisis de tendencias temporales usando:
- Prophet para series temporales con estacionalidad
- Statsmodels para análisis ARIMA complementario
- Detección de puntos de cambio
- Proyecciones futuras

Características:
- Análisis de tendencias de sentimiento a lo largo del tiempo
- Detección de estacionalidad (períodos académicos)
- Identificación de puntos de cambio abruptos
- Generación de forecasts con intervalos de confianza

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import find_peaks

# Intentar importar Prophet (puede no estar instalado)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

# Statsmodels para análisis alternativo
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.arima.model import ARIMA
import warnings

warnings.filterwarnings('ignore')


class TrendDetector:
    """
    Detector de tendencias temporales para métricas de opinión.
    
    Implementa análisis de series temporales con:
    - Detección de tendencias (creciente, decreciente, estable)
    - Identificación de estacionalidad
    - Detección de puntos de cambio
    - Forecasting con intervalos de confianza
    
    Attributes:
        model: Modelo Prophet entrenado
        data (pd.DataFrame): Serie temporal de datos
        trend_type (str): Tipo de tendencia detectada
        
    Example:
        >>> detector = TrendDetector()
        >>> detector.fit(sentiment_data, date_col='fecha', value_col='score')
        >>> trend = detector.analyze_trend()
        >>> forecast = detector.forecast(periods=30)
    """
    
    TREND_TYPES = {
        "increasing": "creciente",
        "decreasing": "decreciente",
        "stable": "estable",
        "volatile": "volátil"
    }
    
    def __init__(
        self,
        models_dir: str = None,
        seasonality_mode: str = "additive",
        changepoint_threshold: float = 0.05
    ):
        """
        Inicializa el detector de tendencias.
        
        Args:
            models_dir: Directorio para guardar modelos
            seasonality_mode: Modo de estacionalidad ('additive' o 'multiplicative')
            changepoint_threshold: Umbral para detección de cambios
        """
        self.logger = logging.getLogger("OSINT.AI.Trends")
        
        # Configurar directorio
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.seasonality_mode = seasonality_mode
        self.changepoint_threshold = changepoint_threshold
        
        # Modelos y datos
        self.prophet_model = None
        self.data = None
        self.forecast_df = None
        self.decomposition = None
        
        # Resultados de análisis
        self.trend_analysis = {}
        self.seasonality_analysis = {}
        self.change_points = []
        
        if not PROPHET_AVAILABLE:
            self.logger.warning(
                "Prophet no disponible. Usando statsmodels como alternativa."
            )
    
    def fit(
        self,
        data: Union[pd.DataFrame, List[Dict]],
        date_col: str = 'fecha',
        value_col: str = 'valor',
        freq: str = 'D'
    ) -> 'TrendDetector':
        """
        Ajusta el modelo con datos históricos.
        
        Args:
            data: DataFrame o lista de dicts con fechas y valores
            date_col: Nombre de columna de fecha
            value_col: Nombre de columna de valor
            freq: Frecuencia temporal ('D'=diario, 'W'=semanal, 'M'=mensual)
            
        Returns:
            Self para encadenamiento
        """
        self.logger.info("Preparando datos para análisis de tendencias...")
        
        # Convertir a DataFrame si es necesario
        if isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        # Validar columnas
        if date_col not in df.columns:
            raise ValueError(f"Columna '{date_col}' no encontrada")
        if value_col not in df.columns:
            raise ValueError(f"Columna '{value_col}' no encontrada")
        
        # Preparar datos
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        
        # Agregar por frecuencia
        df = df.set_index(date_col)
        df = df[[value_col]].resample(freq).mean()
        df = df.fillna(method='ffill').fillna(method='bfill')
        df = df.reset_index()
        
        # Renombrar para Prophet
        df.columns = ['ds', 'y']
        
        self.data = df
        self.freq = freq
        
        self.logger.info(
            f"Datos preparados: {len(df)} puntos temporales, "
            f"desde {df['ds'].min()} hasta {df['ds'].max()}"
        )
        
        # Entrenar modelo Prophet si está disponible
        if PROPHET_AVAILABLE and len(df) >= 10:
            self._fit_prophet()
        
        # Realizar descomposición
        if len(df) >= 14:  # Mínimo para descomposición
            self._decompose_series()
        
        return self
    
    def _fit_prophet(self):
        """Entrena modelo Prophet."""
        self.logger.info("Entrenando modelo Prophet...")
        
        self.prophet_model = Prophet(
            seasonality_mode=self.seasonality_mode,
            changepoint_prior_scale=self.changepoint_threshold,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95
        )
        
        # Añadir estacionalidad semestral (períodos académicos)
        self.prophet_model.add_seasonality(
            name='semestral',
            period=182.5,  # ~6 meses
            fourier_order=5
        )
        
        self.prophet_model.fit(self.data)
        self.logger.info("Modelo Prophet entrenado")
    
    def _decompose_series(self):
        """Descompone la serie temporal."""
        try:
            # Necesitamos al menos 2 períodos completos
            period = 7 if self.freq == 'D' else 4
            if len(self.data) < period * 2:
                period = max(2, len(self.data) // 2)
            
            series = self.data.set_index('ds')['y']
            
            self.decomposition = seasonal_decompose(
                series,
                model=self.seasonality_mode,
                period=period,
                extrapolate_trend='freq'
            )
            self.logger.info("Descomposición de serie completada")
        except Exception as e:
            self.logger.warning(f"No se pudo descomponer serie: {e}")
            self.decomposition = None
    
    def analyze_sentiment_trend(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Analiza la tendencia de sentimiento en un período.
        
        Args:
            start_date: Fecha de inicio (YYYY-MM-DD)
            end_date: Fecha de fin (YYYY-MM-DD)
            
        Returns:
            Dict con análisis de tendencia
        """
        if self.data is None:
            raise RuntimeError("Primero ejecute fit() con datos")
        
        # Filtrar por fechas si se especifican
        df = self.data.copy()
        
        if start_date:
            df = df[df['ds'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['ds'] <= pd.to_datetime(end_date)]
        
        if len(df) < 3:
            return {
                "error": "Datos insuficientes para análisis",
                "data_points": len(df)
            }
        
        # Calcular tendencia con regresión lineal
        x = np.arange(len(df))
        y = df['y'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Determinar tipo de tendencia
        if p_value > 0.05:
            trend_type = "estable"
            trend_strength = "no significativa"
        elif slope > 0:
            trend_type = "creciente"
            trend_strength = "significativa" if abs(r_value) > 0.5 else "débil"
        else:
            trend_type = "decreciente"
            trend_strength = "significativa" if abs(r_value) > 0.5 else "débil"
        
        # Calcular volatilidad
        volatility = df['y'].std() / df['y'].mean() if df['y'].mean() != 0 else 0
        
        # Estadísticas descriptivas
        self.trend_analysis = {
            "trend_type": trend_type,
            "trend_strength": trend_strength,
            "slope": float(slope),
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "confidence": float(1 - p_value) if p_value < 1 else 0,
            "volatility": float(volatility),
            "statistics": {
                "mean": float(df['y'].mean()),
                "std": float(df['y'].std()),
                "min": float(df['y'].min()),
                "max": float(df['y'].max()),
                "median": float(df['y'].median())
            },
            "period": {
                "start": df['ds'].min().isoformat(),
                "end": df['ds'].max().isoformat(),
                "data_points": len(df)
            },
            "interpretation": self._interpret_trend(
                trend_type, slope, r_value, volatility
            )
        }
        
        self.logger.info(f"Tendencia detectada: {trend_type} ({trend_strength})")
        
        return self.trend_analysis
    
    def _interpret_trend(
        self,
        trend_type: str,
        slope: float,
        r_value: float,
        volatility: float
    ) -> str:
        """Genera interpretación de la tendencia."""
        
        interpretations = {
            "creciente": "El sentimiento muestra una tendencia positiva, "
                        "indicando mejora en la percepción.",
            "decreciente": "El sentimiento muestra una tendencia negativa, "
                          "indicando deterioro en la percepción.",
            "estable": "El sentimiento se mantiene relativamente estable "
                      "sin cambios significativos."
        }
        
        base = interpretations.get(trend_type, "Tendencia no determinada.")
        
        if volatility > 0.5:
            base += " Se observa alta volatilidad, sugiriendo opiniones diversas."
        
        if abs(r_value) > 0.7:
            base += f" La tendencia es consistente (R²={r_value**2:.2f})."
        
        return base
    
    def detect_seasonality(self) -> Dict[str, Any]:
        """
        Detecta patrones estacionales en los datos.
        
        Returns:
            Dict con análisis de estacionalidad
        """
        if self.data is None:
            raise RuntimeError("Primero ejecute fit() con datos")
        
        result = {
            "has_seasonality": False,
            "patterns": [],
            "academic_periods": {}
        }
        
        if self.decomposition is not None:
            seasonal = self.decomposition.seasonal
            
            # Verificar si hay estacionalidad significativa
            seasonal_strength = 1 - (
                seasonal.var() / 
                (self.decomposition.resid.var() + seasonal.var() + 1e-10)
            )
            
            result["has_seasonality"] = seasonal_strength > 0.1
            result["seasonal_strength"] = float(seasonal_strength)
            
            # Detectar picos estacionales
            peaks, _ = find_peaks(seasonal.values, distance=7)
            troughs, _ = find_peaks(-seasonal.values, distance=7)
            
            if len(peaks) > 0:
                peak_dates = seasonal.index[peaks]
                result["patterns"].append({
                    "type": "picos",
                    "dates": [d.isoformat() for d in peak_dates[:5]],
                    "description": "Períodos de mayor actividad/sentimiento"
                })
            
            if len(troughs) > 0:
                trough_dates = seasonal.index[troughs]
                result["patterns"].append({
                    "type": "valles",
                    "dates": [d.isoformat() for d in trough_dates[:5]],
                    "description": "Períodos de menor actividad/sentimiento"
                })
        
        # Analizar períodos académicos
        df = self.data.copy()
        df['month'] = df['ds'].dt.month
        
        # Primer semestre (Feb-Jun) vs Segundo semestre (Ago-Dic)
        sem1_mask = df['month'].isin([2, 3, 4, 5, 6])
        sem2_mask = df['month'].isin([8, 9, 10, 11, 12])
        
        if sem1_mask.any() and sem2_mask.any():
            sem1_mean = df.loc[sem1_mask, 'y'].mean()
            sem2_mean = df.loc[sem2_mask, 'y'].mean()
            
            result["academic_periods"] = {
                "primer_semestre": {
                    "meses": "Febrero - Junio",
                    "media": float(sem1_mean),
                    "observaciones": int(sem1_mask.sum())
                },
                "segundo_semestre": {
                    "meses": "Agosto - Diciembre",
                    "media": float(sem2_mean),
                    "observaciones": int(sem2_mask.sum())
                },
                "diferencia": float(sem2_mean - sem1_mean),
                "interpretacion": (
                    "Mayor actividad en segundo semestre" 
                    if sem2_mean > sem1_mean 
                    else "Mayor actividad en primer semestre"
                )
            }
        
        self.seasonality_analysis = result
        self.logger.info(
            f"Estacionalidad detectada: {result['has_seasonality']}"
        )
        
        return result
    
    def forecast(
        self,
        periods: int = 30,
        freq: str = None
    ) -> Dict[str, Any]:
        """
        Genera proyección futura.
        
        Args:
            periods: Número de períodos a proyectar
            freq: Frecuencia de proyección
            
        Returns:
            Dict con forecast y intervalos de confianza
        """
        if self.data is None:
            raise RuntimeError("Primero ejecute fit() con datos")
        
        freq = freq or self.freq
        
        if PROPHET_AVAILABLE and self.prophet_model is not None:
            return self._forecast_prophet(periods)
        else:
            return self._forecast_arima(periods)
    
    def _forecast_prophet(self, periods: int) -> Dict[str, Any]:
        """Forecast usando Prophet."""
        self.logger.info(f"Generando forecast Prophet para {periods} períodos...")
        
        # Crear dataframe futuro
        future = self.prophet_model.make_future_dataframe(
            periods=periods,
            freq=self.freq
        )
        
        # Predecir
        forecast = self.prophet_model.predict(future)
        
        # Filtrar solo predicciones futuras
        last_date = self.data['ds'].max()
        future_forecast = forecast[forecast['ds'] > last_date]
        
        # Preparar resultado
        predictions = []
        for _, row in future_forecast.iterrows():
            predictions.append({
                "date": row['ds'].isoformat(),
                "predicted_value": float(row['yhat']),
                "lower_bound": float(row['yhat_lower']),
                "upper_bound": float(row['yhat_upper']),
                "trend": float(row['trend'])
            })
        
        self.forecast_df = forecast
        
        result = {
            "method": "Prophet",
            "periods": periods,
            "frequency": self.freq,
            "predictions": predictions,
            "summary": {
                "mean_prediction": float(future_forecast['yhat'].mean()),
                "min_prediction": float(future_forecast['yhat'].min()),
                "max_prediction": float(future_forecast['yhat'].max()),
                "confidence_interval": 0.95
            },
            "trend_direction": (
                "creciente" 
                if future_forecast['trend'].iloc[-1] > future_forecast['trend'].iloc[0]
                else "decreciente"
            )
        }
        
        return result
    
    def _forecast_arima(self, periods: int) -> Dict[str, Any]:
        """Forecast usando ARIMA como alternativa."""
        self.logger.info(f"Generando forecast ARIMA para {periods} períodos...")
        
        try:
            # Ajustar modelo ARIMA simple
            model = ARIMA(self.data['y'], order=(1, 1, 1))
            fitted = model.fit()
            
            # Predecir
            forecast = fitted.forecast(steps=periods)
            conf_int = fitted.get_forecast(steps=periods).conf_int()
            
            # Generar fechas futuras
            last_date = self.data['ds'].max()
            future_dates = pd.date_range(
                start=last_date + timedelta(days=1),
                periods=periods,
                freq=self.freq
            )
            
            predictions = []
            for i, date in enumerate(future_dates):
                predictions.append({
                    "date": date.isoformat(),
                    "predicted_value": float(forecast.iloc[i]),
                    "lower_bound": float(conf_int.iloc[i, 0]),
                    "upper_bound": float(conf_int.iloc[i, 1])
                })
            
            return {
                "method": "ARIMA(1,1,1)",
                "periods": periods,
                "frequency": self.freq,
                "predictions": predictions,
                "summary": {
                    "mean_prediction": float(forecast.mean()),
                    "min_prediction": float(forecast.min()),
                    "max_prediction": float(forecast.max()),
                    "confidence_interval": 0.95
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error en ARIMA: {e}")
            return {
                "error": str(e),
                "method": "ARIMA",
                "periods": periods
            }
    
    def identify_change_points(self) -> List[Dict[str, Any]]:
        """
        Identifica puntos de cambio abruptos en la serie.
        
        Returns:
            Lista de puntos de cambio detectados
        """
        if self.data is None:
            raise RuntimeError("Primero ejecute fit() con datos")
        
        self.change_points = []
        
        # Usar Prophet si está disponible
        if PROPHET_AVAILABLE and self.prophet_model is not None:
            changepoints = self.prophet_model.changepoints
            if changepoints is not None and len(changepoints) > 0:
                # Obtener magnitudes de cambio
                deltas = self.prophet_model.params['delta'].mean(axis=0)
                
                for i, cp in enumerate(changepoints):
                    if i < len(deltas):
                        magnitude = abs(float(deltas[i]))
                        if magnitude > self.changepoint_threshold:
                            self.change_points.append({
                                "date": cp.isoformat(),
                                "magnitude": magnitude,
                                "direction": "positivo" if deltas[i] > 0 else "negativo",
                                "significance": (
                                    "alta" if magnitude > 0.1 
                                    else "media" if magnitude > 0.05 
                                    else "baja"
                                )
                            })
        
        # Método alternativo: detección de cambios estadísticos
        if len(self.change_points) == 0:
            self.change_points = self._detect_statistical_changepoints()
        
        # Ordenar por fecha
        self.change_points.sort(
            key=lambda x: x['date'], 
            reverse=True
        )
        
        self.logger.info(
            f"Detectados {len(self.change_points)} puntos de cambio"
        )
        
        return self.change_points
    
    def _detect_statistical_changepoints(self) -> List[Dict[str, Any]]:
        """Detecta cambios usando método estadístico simple."""
        change_points = []
        
        df = self.data.copy()
        values = df['y'].values
        dates = df['ds'].values
        
        # Ventana móvil para detectar cambios
        window = max(3, len(values) // 10)
        
        for i in range(window, len(values) - window):
            before = values[i-window:i]
            after = values[i:i+window]
            
            # Test de diferencia de medias
            t_stat, p_value = stats.ttest_ind(before, after)
            
            if p_value < 0.05:
                mean_diff = after.mean() - before.mean()
                change_points.append({
                    "date": pd.Timestamp(dates[i]).isoformat(),
                    "magnitude": abs(float(mean_diff)),
                    "direction": "positivo" if mean_diff > 0 else "negativo",
                    "p_value": float(p_value),
                    "significance": (
                        "alta" if p_value < 0.01 
                        else "media" if p_value < 0.05 
                        else "baja"
                    )
                })
        
        # Eliminar puntos muy cercanos
        if len(change_points) > 1:
            filtered = [change_points[0]]
            for cp in change_points[1:]:
                last_date = pd.to_datetime(filtered[-1]['date'])
                curr_date = pd.to_datetime(cp['date'])
                if (curr_date - last_date).days > 7:  # Al menos 7 días de diferencia
                    filtered.append(cp)
            change_points = filtered
        
        return change_points
    
    def get_trend_summary(self) -> Dict[str, Any]:
        """
        Genera un resumen ejecutivo del análisis de tendencias.
        
        Returns:
            Dict con resumen completo
        """
        if self.data is None:
            raise RuntimeError("Primero ejecute fit() con datos")
        
        # Asegurar que tenemos los análisis
        if not self.trend_analysis:
            self.analyze_sentiment_trend()
        if not self.seasonality_analysis:
            self.detect_seasonality()
        if not self.change_points:
            self.identify_change_points()
        
        summary = {
            "period_analyzed": {
                "start": self.data['ds'].min().isoformat(),
                "end": self.data['ds'].max().isoformat(),
                "data_points": len(self.data)
            },
            "trend": self.trend_analysis,
            "seasonality": self.seasonality_analysis,
            "change_points": {
                "total": len(self.change_points),
                "recent": self.change_points[:3] if self.change_points else []
            },
            "key_insights": self._generate_insights(),
            "generated_at": datetime.now().isoformat()
        }
        
        return summary
    
    def _generate_insights(self) -> List[str]:
        """Genera insights clave del análisis."""
        insights = []
        
        # Insight de tendencia
        if self.trend_analysis:
            trend = self.trend_analysis.get('trend_type', 'desconocida')
            confidence = self.trend_analysis.get('confidence', 0)
            insights.append(
                f"La tendencia general es {trend} "
                f"con {confidence*100:.0f}% de confianza."
            )
        
        # Insight de estacionalidad
        if self.seasonality_analysis:
            if self.seasonality_analysis.get('has_seasonality'):
                insights.append(
                    "Se detectaron patrones estacionales significativos, "
                    "posiblemente relacionados con el calendario académico."
                )
        
        # Insight de cambios
        if self.change_points:
            recent = [
                cp for cp in self.change_points 
                if cp.get('significance') in ['alta', 'media']
            ][:2]
            if recent:
                insights.append(
                    f"Se identificaron {len(recent)} cambios significativos "
                    "recientes en la tendencia."
                )
        
        if not insights:
            insights.append("Datos insuficientes para generar insights.")
        
        return insights
    
    def save_model(self, path: str = None) -> str:
        """Guarda el modelo de tendencias."""
        save_path = Path(path) if path else self.models_dir / "trend_model.pkl"
        
        model_data = {
            "prophet_model": self.prophet_model,
            "trend_analysis": self.trend_analysis,
            "seasonality_analysis": self.seasonality_analysis,
            "change_points": self.change_points,
            "config": {
                "seasonality_mode": self.seasonality_mode,
                "changepoint_threshold": self.changepoint_threshold
            },
            "saved_at": datetime.now().isoformat()
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.logger.info(f"Modelo guardado en: {save_path}")
        return str(save_path)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Obtiene información del modelo."""
        return {
            "models_dir": str(self.models_dir),
            "prophet_available": PROPHET_AVAILABLE,
            "model_fitted": self.prophet_model is not None or self.data is not None,
            "data_points": len(self.data) if self.data is not None else 0,
            "config": {
                "seasonality_mode": self.seasonality_mode,
                "changepoint_threshold": self.changepoint_threshold
            }
        }


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Generar datos de ejemplo
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    
    # Simular sentimiento con tendencia y estacionalidad
    trend = np.linspace(0.5, 0.7, len(dates))
    seasonality = 0.1 * np.sin(2 * np.pi * np.arange(len(dates)) / 182.5)
    noise = np.random.normal(0, 0.05, len(dates))
    values = trend + seasonality + noise
    
    data = pd.DataFrame({
        'fecha': dates,
        'valor': values
    })
    
    # Crear detector
    detector = TrendDetector()
    
    # Ajustar
    print("Ajustando modelo...")
    detector.fit(data, date_col='fecha', value_col='valor')
    
    # Analizar tendencia
    print("\n--- Análisis de Tendencia ---")
    trend = detector.analyze_sentiment_trend()
    print(f"Tipo: {trend['trend_type']}")
    print(f"Confianza: {trend['confidence']:.2%}")
    print(f"Interpretación: {trend['interpretation']}")
    
    # Detectar estacionalidad
    print("\n--- Estacionalidad ---")
    seasonality = detector.detect_seasonality()
    print(f"Tiene estacionalidad: {seasonality['has_seasonality']}")
    
    # Forecast
    print("\n--- Forecast ---")
    forecast = detector.forecast(periods=30)
    print(f"Método: {forecast['method']}")
    print(f"Predicción media: {forecast['summary']['mean_prediction']:.4f}")
    
    # Puntos de cambio
    print("\n--- Puntos de Cambio ---")
    changes = detector.identify_change_points()
    print(f"Detectados: {len(changes)}")
    for cp in changes[:3]:
        print(f"  - {cp['date']}: {cp['direction']} ({cp['significance']})")
