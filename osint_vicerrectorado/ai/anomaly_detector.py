"""
AnomalyDetector - Detección de Anomalías con Isolation Forest
Sistema de Analítica EMI - Sprint 3

Este módulo implementa detección de anomalías usando:
- Isolation Forest para detección de outliers
- Sistema de severidad (baja, media, alta, crítica)
- Generación de alertas automáticas
- Detección en múltiples métricas

Características:
- Detección de picos/caídas anormales
- Identificación de comportamientos atípicos
- Clasificación de severidad
- Integración con sistema de alertas

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
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


class AnomalySeverity(Enum):
    """Niveles de severidad para anomalías."""
    LOW = "baja"
    MEDIUM = "media"
    HIGH = "alta"
    CRITICAL = "critica"


class AnomalyType(Enum):
    """Tipos de anomalías detectables."""
    SPIKE = "pico"
    DROP = "caida"
    VOLUME_SURGE = "volumen_anormal"
    SENTIMENT_SHIFT = "cambio_sentimiento"
    ENGAGEMENT_ANOMALY = "engagement_anormal"
    PATTERN_BREAK = "ruptura_patron"
    OUTLIER = "outlier"


class AnomalyDetector:
    """
    Detector de anomalías basado en Isolation Forest.
    
    Implementa detección de comportamientos atípicos con:
    - Detección multivariada de outliers
    - Sistema de clasificación de severidad
    - Generación automática de alertas
    - Persistencia de modelos
    
    Attributes:
        model (IsolationForest): Modelo de detección entrenado
        scaler (StandardScaler): Escalador de características
        anomaly_threshold (float): Umbral de anomalía
        
    Example:
        >>> detector = AnomalyDetector()
        >>> detector.fit(historical_data)
        >>> anomalies = detector.detect_anomalies(new_data)
        >>> for anomaly in anomalies:
        ...     alert = detector.generate_alert(anomaly)
    """
    
    # Umbrales de severidad basados en anomaly_score
    SEVERITY_THRESHOLDS = {
        AnomalySeverity.CRITICAL: -0.7,
        AnomalySeverity.HIGH: -0.5,
        AnomalySeverity.MEDIUM: -0.3,
        AnomalySeverity.LOW: -0.1
    }
    
    def __init__(
        self,
        models_dir: str = None,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        """
        Inicializa el detector de anomalías.
        
        Args:
            models_dir: Directorio para guardar modelos
            contamination: Proporción esperada de anomalías (0-0.5)
            n_estimators: Número de árboles en el forest
            random_state: Semilla para reproducibilidad
        """
        self.logger = logging.getLogger("OSINT.AI.Anomaly")
        
        # Configurar directorio
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        
        # Modelo y preprocesamiento
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        
        # Estado
        self.is_fitted = False
        self.feature_names = None
        self.baseline_stats = {}
        self.detected_anomalies = []
        self.alerts_generated = []
        
        self.logger.info(
            f"AnomalyDetector inicializado (contamination={contamination})"
        )
    
    def fit(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        feature_cols: List[str] = None
    ) -> 'AnomalyDetector':
        """
        Entrena el modelo con datos históricos normales.
        
        Args:
            data: DataFrame o array con características
            feature_cols: Nombres de columnas a usar como features
            
        Returns:
            Self para encadenamiento
        """
        self.logger.info("Entrenando modelo de detección de anomalías...")
        
        # Preparar datos
        if isinstance(data, pd.DataFrame):
            if feature_cols:
                X = data[feature_cols].values
                self.feature_names = feature_cols
            else:
                # Usar solo columnas numéricas
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                X = data[numeric_cols].values
                self.feature_names = list(numeric_cols)
        else:
            X = data
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        
        # Eliminar filas con NaN
        mask = ~np.isnan(X).any(axis=1)
        X = X[mask]
        
        if len(X) < 10:
            raise ValueError(f"Se necesitan al menos 10 muestras, hay {len(X)}")
        
        # Escalar características
        X_scaled = self.scaler.fit_transform(X)
        
        # Calcular estadísticas baseline
        for i, name in enumerate(self.feature_names):
            self.baseline_stats[name] = {
                "mean": float(np.mean(X[:, i])),
                "std": float(np.std(X[:, i])),
                "min": float(np.min(X[:, i])),
                "max": float(np.max(X[:, i])),
                "median": float(np.median(X[:, i])),
                "q1": float(np.percentile(X[:, i], 25)),
                "q3": float(np.percentile(X[:, i], 75))
            }
        
        # Entrenar modelo
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        self.logger.info(
            f"Modelo entrenado con {len(X)} muestras, "
            f"{len(self.feature_names)} features"
        )
        
        return self
    
    def detect_anomalies(
        self,
        data: Union[pd.DataFrame, np.ndarray, Dict],
        return_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Detecta anomalías en nuevos datos.
        
        Args:
            data: Datos a analizar
            return_scores: Si incluir scores de anomalía
            
        Returns:
            Lista de anomalías detectadas
        """
        if not self.is_fitted:
            raise RuntimeError("Primero entrene el modelo con fit()")
        
        self.logger.info("Detectando anomalías...")
        
        # Preparar datos
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        elif isinstance(data, np.ndarray):
            data = pd.DataFrame(data, columns=self.feature_names)
        
        # Obtener features
        if self.feature_names:
            missing_cols = set(self.feature_names) - set(data.columns)
            if missing_cols:
                # Rellenar columnas faltantes con medias
                for col in missing_cols:
                    data[col] = self.baseline_stats.get(col, {}).get('mean', 0)
            X = data[self.feature_names].values
        else:
            X = data.select_dtypes(include=[np.number]).values
        
        # Escalar
        X_scaled = self.scaler.transform(X)
        
        # Predecir
        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)
        
        # Procesar resultados
        self.detected_anomalies = []
        
        for i in range(len(data)):
            if predictions[i] == -1:  # Anomalía detectada
                anomaly = self._create_anomaly_record(
                    data.iloc[i] if isinstance(data, pd.DataFrame) else data[i],
                    scores[i],
                    i
                )
                self.detected_anomalies.append(anomaly)
        
        self.logger.info(f"Detectadas {len(self.detected_anomalies)} anomalías")
        
        return self.detected_anomalies
    
    def _create_anomaly_record(
        self,
        record: Union[pd.Series, np.ndarray],
        score: float,
        index: int
    ) -> Dict[str, Any]:
        """Crea registro detallado de anomalía."""
        
        # Determinar severidad
        severity = self.calculate_severity(score)
        
        # Determinar tipo de anomalía
        anomaly_type = self._classify_anomaly_type(record, score)
        
        # Crear registro
        anomaly = {
            "id": f"anomaly_{datetime.now().strftime('%Y%m%d%H%M%S')}_{index}",
            "type": anomaly_type.value,
            "severity": severity.value,
            "anomaly_score": float(score),
            "detected_at": datetime.now().isoformat(),
            "index": index,
            "affected_metrics": [],
            "values": {},
            "deviations": {}
        }
        
        # Analizar cada feature
        if isinstance(record, pd.Series):
            values = record.to_dict()
        else:
            values = {self.feature_names[i]: record[i] for i in range(len(record))}
        
        for name, value in values.items():
            if name in self.baseline_stats:
                baseline = self.baseline_stats[name]
                if baseline['std'] > 0:
                    z_score = (value - baseline['mean']) / baseline['std']
                else:
                    z_score = 0
                
                anomaly["values"][name] = float(value) if not pd.isna(value) else None
                anomaly["deviations"][name] = {
                    "z_score": float(z_score),
                    "deviation_percent": float(
                        (value - baseline['mean']) / baseline['mean'] * 100
                    ) if baseline['mean'] != 0 else 0,
                    "is_anomalous": abs(z_score) > 2
                }
                
                if abs(z_score) > 2:
                    anomaly["affected_metrics"].append({
                        "metric": name,
                        "value": float(value) if not pd.isna(value) else None,
                        "expected": baseline['mean'],
                        "z_score": float(z_score)
                    })
        
        # Descripción
        anomaly["description"] = self._generate_description(anomaly)
        
        return anomaly
    
    def _classify_anomaly_type(
        self,
        record: Union[pd.Series, np.ndarray],
        score: float
    ) -> AnomalyType:
        """Clasifica el tipo de anomalía basado en el patrón."""
        
        if isinstance(record, pd.Series):
            values = record.to_dict()
        else:
            values = {
                self.feature_names[i]: record[i] 
                for i in range(len(record))
            }
        
        # Detectar picos/caídas
        high_deviations = []
        low_deviations = []
        
        for name, value in values.items():
            if name in self.baseline_stats and not pd.isna(value):
                baseline = self.baseline_stats[name]
                if baseline['std'] > 0:
                    z_score = (value - baseline['mean']) / baseline['std']
                    if z_score > 2:
                        high_deviations.append(name)
                    elif z_score < -2:
                        low_deviations.append(name)
        
        # Clasificar
        if 'engagement' in str(values) or 'likes' in str(values):
            if high_deviations:
                return AnomalyType.ENGAGEMENT_ANOMALY
            elif low_deviations:
                return AnomalyType.DROP
        
        if 'sentimiento' in str(values) or 'sentiment' in str(values):
            return AnomalyType.SENTIMENT_SHIFT
        
        if 'volumen' in str(values) or 'count' in str(values):
            if high_deviations:
                return AnomalyType.VOLUME_SURGE
        
        if len(high_deviations) > len(low_deviations):
            return AnomalyType.SPIKE
        elif len(low_deviations) > len(high_deviations):
            return AnomalyType.DROP
        
        return AnomalyType.OUTLIER
    
    def calculate_severity(
        self,
        anomaly_score: float
    ) -> AnomalySeverity:
        """
        Calcula el nivel de severidad basado en el score.
        
        Args:
            anomaly_score: Score de anomalía de Isolation Forest
            
        Returns:
            Nivel de severidad
        """
        if anomaly_score <= self.SEVERITY_THRESHOLDS[AnomalySeverity.CRITICAL]:
            return AnomalySeverity.CRITICAL
        elif anomaly_score <= self.SEVERITY_THRESHOLDS[AnomalySeverity.HIGH]:
            return AnomalySeverity.HIGH
        elif anomaly_score <= self.SEVERITY_THRESHOLDS[AnomalySeverity.MEDIUM]:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW
    
    def _generate_description(self, anomaly: Dict) -> str:
        """Genera descripción legible de la anomalía."""
        
        severity_desc = {
            "critica": "⚠️ CRÍTICO:",
            "alta": "🔴 ALTA:",
            "media": "🟡 MEDIA:",
            "baja": "🟢 BAJA:"
        }
        
        type_desc = {
            "pico": "Pico anormal detectado",
            "caida": "Caída anormal detectada",
            "volumen_anormal": "Volumen de actividad anormal",
            "cambio_sentimiento": "Cambio brusco en sentimiento",
            "engagement_anormal": "Engagement fuera de lo normal",
            "ruptura_patron": "Ruptura de patrón habitual",
            "outlier": "Valor atípico detectado"
        }
        
        prefix = severity_desc.get(anomaly['severity'], "")
        type_text = type_desc.get(anomaly['type'], "Anomalía detectada")
        
        affected = anomaly.get('affected_metrics', [])
        if affected:
            metrics_text = ", ".join([
                f"{m['metric']} (z={m['z_score']:.1f})" 
                for m in affected[:3]
            ])
            return f"{prefix} {type_text}. Métricas afectadas: {metrics_text}"
        
        return f"{prefix} {type_text}."
    
    def generate_alert(
        self,
        anomaly: Dict[str, Any],
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        """
        Genera una alerta para una anomalía detectada.
        
        Args:
            anomaly: Registro de anomalía
            include_recommendations: Si incluir recomendaciones
            
        Returns:
            Dict con información de la alerta
        """
        alert = {
            "alert_id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "anomaly_id": anomaly.get('id'),
            "severity": anomaly.get('severity'),
            "type": anomaly.get('type'),
            "title": self._get_alert_title(anomaly),
            "description": anomaly.get('description'),
            "created_at": datetime.now().isoformat(),
            "status": "new",
            "requires_action": anomaly.get('severity') in ['alta', 'critica'],
            "affected_metrics": anomaly.get('affected_metrics', []),
            "anomaly_score": anomaly.get('anomaly_score')
        }
        
        if include_recommendations:
            alert["recommendations"] = self._get_recommendations(anomaly)
        
        self.alerts_generated.append(alert)
        
        self.logger.info(
            f"Alerta generada: {alert['title']} (severidad: {alert['severity']})"
        )
        
        return alert
    
    def _get_alert_title(self, anomaly: Dict) -> str:
        """Genera título para la alerta."""
        type_titles = {
            "pico": "Pico anormal de actividad",
            "caida": "Caída anormal de métricas",
            "volumen_anormal": "Volumen de publicaciones anormal",
            "cambio_sentimiento": "Cambio brusco de sentimiento",
            "engagement_anormal": "Engagement fuera de lo común",
            "ruptura_patron": "Ruptura de patrón detectada",
            "outlier": "Valor atípico detectado"
        }
        return type_titles.get(anomaly.get('type'), "Anomalía detectada")
    
    def _get_recommendations(self, anomaly: Dict) -> List[str]:
        """Genera recomendaciones basadas en el tipo de anomalía."""
        
        recommendations = {
            "pico": [
                "Investigar las publicaciones del período afectado",
                "Verificar si hay eventos externos que expliquen el pico",
                "Analizar el contenido que generó mayor interacción"
            ],
            "caida": [
                "Revisar posibles problemas técnicos en las fuentes",
                "Analizar si coincide con períodos de baja actividad (vacaciones)",
                "Verificar cambios en algoritmos de las plataformas"
            ],
            "volumen_anormal": [
                "Revisar las fuentes de datos para posibles duplicados",
                "Verificar si hay campañas o eventos en curso",
                "Analizar el contenido de las publicaciones adicionales"
            ],
            "cambio_sentimiento": [
                "Identificar publicaciones que causaron el cambio",
                "Analizar comentarios y reacciones específicas",
                "Preparar comunicación institucional si es negativo"
            ],
            "engagement_anormal": [
                "Identificar contenido viral si es positivo",
                "Buscar posibles crisis de reputación si es negativo",
                "Analizar demografía de interacciones"
            ],
            "ruptura_patron": [
                "Comparar con períodos similares anteriores",
                "Verificar integridad de los datos recolectados",
                "Investigar factores externos"
            ],
            "outlier": [
                "Verificar la validez del dato",
                "Analizar el contexto específico",
                "Monitorear si el patrón continúa"
            ]
        }
        
        base_recommendations = recommendations.get(
            anomaly.get('type'), 
            ["Investigar la anomalía detectada"]
        )
        
        # Añadir recomendaciones por severidad
        if anomaly.get('severity') in ['alta', 'critica']:
            base_recommendations.insert(0, "⚠️ Acción inmediata requerida")
            base_recommendations.append("Notificar al equipo de comunicación")
        
        return base_recommendations
    
    def get_anomaly_summary(
        self,
        time_period: str = "all"
    ) -> Dict[str, Any]:
        """
        Genera resumen de anomalías detectadas.
        
        Args:
            time_period: Período a resumir ('day', 'week', 'month', 'all')
            
        Returns:
            Dict con resumen de anomalías
        """
        anomalies = self.detected_anomalies
        
        # Filtrar por período si es necesario
        if time_period != "all" and anomalies:
            now = datetime.now()
            if time_period == "day":
                cutoff = now - timedelta(days=1)
            elif time_period == "week":
                cutoff = now - timedelta(weeks=1)
            elif time_period == "month":
                cutoff = now - timedelta(days=30)
            else:
                cutoff = datetime.min
            
            anomalies = [
                a for a in anomalies 
                if datetime.fromisoformat(a['detected_at']) >= cutoff
            ]
        
        # Contar por tipo y severidad
        by_type = {}
        by_severity = {}
        
        for a in anomalies:
            t = a.get('type', 'unknown')
            s = a.get('severity', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
            by_severity[s] = by_severity.get(s, 0) + 1
        
        summary = {
            "period": time_period,
            "total_anomalies": len(anomalies),
            "by_type": by_type,
            "by_severity": by_severity,
            "critical_count": by_severity.get('critica', 0),
            "high_count": by_severity.get('alta', 0),
            "requires_attention": by_severity.get('critica', 0) + by_severity.get('alta', 0),
            "recent_anomalies": anomalies[:5] if anomalies else [],
            "generated_at": datetime.now().isoformat()
        }
        
        return summary
    
    def evaluate(
        self,
        data: pd.DataFrame,
        labels: List[int] = None
    ) -> Dict[str, Any]:
        """
        Evalúa el rendimiento del detector si hay etiquetas disponibles.
        
        Args:
            data: Datos de prueba
            labels: Etiquetas reales (1=normal, -1=anomalía)
            
        Returns:
            Dict con métricas de evaluación
        """
        if not self.is_fitted:
            raise RuntimeError("Modelo no entrenado")
        
        # Obtener predicciones
        X = data[self.feature_names].values if self.feature_names else data.values
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)
        
        evaluation = {
            "total_samples": len(data),
            "predicted_anomalies": int((predictions == -1).sum()),
            "anomaly_rate": float((predictions == -1).mean()),
            "score_stats": {
                "mean": float(scores.mean()),
                "std": float(scores.std()),
                "min": float(scores.min()),
                "max": float(scores.max())
            }
        }
        
        if labels is not None:
            from sklearn.metrics import (
                precision_score, recall_score, f1_score,
                confusion_matrix
            )
            
            # Convertir predicciones a formato binario (1=anomalía)
            pred_binary = (predictions == -1).astype(int)
            true_binary = (np.array(labels) == -1).astype(int)
            
            evaluation["with_labels"] = {
                "precision": float(precision_score(true_binary, pred_binary, zero_division=0)),
                "recall": float(recall_score(true_binary, pred_binary, zero_division=0)),
                "f1": float(f1_score(true_binary, pred_binary, zero_division=0)),
                "confusion_matrix": confusion_matrix(true_binary, pred_binary).tolist()
            }
        
        return evaluation
    
    def save_model(self, path: str = None) -> str:
        """Guarda el modelo de detección."""
        save_path = Path(path) if path else self.models_dir / "anomaly_model.pkl"
        
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_names": self.feature_names,
            "baseline_stats": self.baseline_stats,
            "config": {
                "contamination": self.contamination,
                "n_estimators": self.n_estimators,
                "random_state": self.random_state
            },
            "saved_at": datetime.now().isoformat()
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.logger.info(f"Modelo guardado en: {save_path}")
        return str(save_path)
    
    def load_model(self, path: str = None) -> bool:
        """Carga un modelo guardado."""
        load_path = Path(path) if path else self.models_dir / "anomaly_model.pkl"
        
        if not load_path.exists():
            self.logger.warning(f"Modelo no encontrado: {load_path}")
            return False
        
        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_names = model_data["feature_names"]
        self.baseline_stats = model_data["baseline_stats"]
        self.is_fitted = True
        
        self.logger.info(f"Modelo cargado desde: {load_path}")
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """Obtiene información del modelo."""
        return {
            "models_dir": str(self.models_dir),
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names,
            "config": {
                "contamination": self.contamination,
                "n_estimators": self.n_estimators
            },
            "baseline_stats": self.baseline_stats,
            "anomalies_detected": len(self.detected_anomalies),
            "alerts_generated": len(self.alerts_generated)
        }


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Generar datos de ejemplo
    np.random.seed(42)
    n_samples = 100
    
    # Datos normales
    normal_data = pd.DataFrame({
        'engagement': np.random.normal(100, 20, n_samples),
        'sentiment_score': np.random.normal(0.6, 0.1, n_samples),
        'post_count': np.random.normal(10, 3, n_samples),
        'likes': np.random.normal(500, 100, n_samples)
    })
    
    # Añadir algunas anomalías
    anomaly_data = pd.DataFrame({
        'engagement': [250, 20, 300],  # Picos y caída
        'sentiment_score': [0.2, 0.9, 0.1],  # Cambios bruscos
        'post_count': [30, 2, 50],  # Volumen anormal
        'likes': [1500, 50, 2000]  # Engagement anormal
    })
    
    test_data = pd.concat([normal_data, anomaly_data], ignore_index=True)
    
    # Crear detector
    detector = AnomalyDetector(contamination=0.05)
    
    # Entrenar con datos normales
    print("Entrenando detector...")
    detector.fit(normal_data)
    
    # Detectar anomalías
    print("\nDetectando anomalías...")
    anomalies = detector.detect_anomalies(test_data)
    
    print(f"\nAnomalías detectadas: {len(anomalies)}")
    for anomaly in anomalies:
        print(f"\n{anomaly['description']}")
        print(f"  Tipo: {anomaly['type']}")
        print(f"  Severidad: {anomaly['severity']}")
        print(f"  Score: {anomaly['anomaly_score']:.4f}")
    
    # Generar alertas
    print("\n--- Alertas ---")
    for anomaly in anomalies[:2]:
        alert = detector.generate_alert(anomaly)
        print(f"\n📢 {alert['title']}")
        print(f"   Severidad: {alert['severity']}")
        if alert.get('recommendations'):
            print("   Recomendaciones:")
            for rec in alert['recommendations'][:2]:
                print(f"     - {rec}")
    
    # Resumen
    print("\n--- Resumen ---")
    summary = detector.get_anomaly_summary()
    print(f"Total: {summary['total_anomalies']}")
    print(f"Por severidad: {summary['by_severity']}")
    print(f"Requieren atención: {summary['requires_attention']}")
