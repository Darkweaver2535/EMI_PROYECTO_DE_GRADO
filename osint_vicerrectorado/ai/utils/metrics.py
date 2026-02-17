"""
AIMetrics - Utilidades de Métricas para Módulos de IA
Sistema de Analítica EMI - Sprint 3

Proporciona funciones para calcular y reportar métricas de evaluación
de los diferentes módulos de IA del sistema.

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score
)


class AIMetrics:
    """
    Calculador de métricas para módulos de IA.
    
    Proporciona métodos para calcular métricas de:
    - Clasificación (sentimientos)
    - Clustering (agrupamiento)
    - Regresión (tendencias)
    - Detección de anomalías
    
    Example:
        >>> metrics = AIMetrics()
        >>> result = metrics.classification_metrics(y_true, y_pred)
        >>> print(result['accuracy'])
    """
    
    def __init__(self):
        """Inicializa el calculador de métricas."""
        self.logger = logging.getLogger("OSINT.AI.Metrics")
    
    def classification_metrics(
        self,
        y_true: List[int],
        y_pred: List[int],
        labels: List[str] = None,
        average: str = 'weighted'
    ) -> Dict[str, Any]:
        """
        Calcula métricas de clasificación.
        
        Args:
            y_true: Etiquetas verdaderas
            y_pred: Etiquetas predichas
            labels: Nombres de las clases
            average: Tipo de promedio ('weighted', 'macro', 'micro')
            
        Returns:
            Dict con métricas de clasificación
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Métricas básicas
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average=average, zero_division=0)
        recall = recall_score(y_true, y_pred, average=average, zero_division=0)
        f1 = f1_score(y_true, y_pred, average=average, zero_division=0)
        
        # Matriz de confusión
        conf_matrix = confusion_matrix(y_true, y_pred)
        
        # Reporte por clase
        unique_labels = np.unique(np.concatenate([y_true, y_pred]))
        target_names = labels if labels else [f"Class_{i}" for i in unique_labels]
        
        report = classification_report(
            y_true, y_pred,
            target_names=target_names[:len(unique_labels)],
            output_dict=True,
            zero_division=0
        )
        
        # Métricas por clase
        per_class = {}
        precision_per_class, recall_per_class, f1_per_class, support = precision_recall_fscore_support(
            y_true, y_pred, average=None, zero_division=0
        )
        
        for i, label_idx in enumerate(unique_labels):
            label_name = target_names[i] if i < len(target_names) else f"Class_{label_idx}"
            per_class[label_name] = {
                "precision": float(precision_per_class[i]) if i < len(precision_per_class) else 0,
                "recall": float(recall_per_class[i]) if i < len(recall_per_class) else 0,
                "f1": float(f1_per_class[i]) if i < len(f1_per_class) else 0,
                "support": int(support[i]) if i < len(support) else 0
            }
        
        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "confusion_matrix": conf_matrix.tolist(),
            "per_class_metrics": per_class,
            "classification_report": report,
            "total_samples": len(y_true),
            "average_method": average,
            "timestamp": datetime.now().isoformat()
        }
    
    def clustering_metrics(
        self,
        X: np.ndarray,
        labels: np.ndarray,
        metric: str = 'euclidean'
    ) -> Dict[str, Any]:
        """
        Calcula métricas de clustering.
        
        Args:
            X: Datos de entrada (features)
            labels: Etiquetas de cluster asignadas
            metric: Métrica de distancia para silhouette
            
        Returns:
            Dict con métricas de clustering
        """
        # Convertir a numpy arrays
        X = np.array(X)
        labels = np.array(labels)
        
        # Verificar que hay más de un cluster
        unique_labels = np.unique(labels)
        n_clusters = len(unique_labels)
        
        if n_clusters < 2:
            return {
                "error": "Se necesitan al menos 2 clusters",
                "n_clusters": n_clusters
            }
        
        # Silhouette Score (-1 a 1, mayor es mejor)
        silhouette = silhouette_score(X, labels, metric=metric)
        
        # Calinski-Harabasz Index (mayor es mejor)
        calinski = calinski_harabasz_score(X, labels)
        
        # Davies-Bouldin Index (menor es mejor)
        davies_bouldin = davies_bouldin_score(X, labels)
        
        # Estadísticas por cluster
        cluster_stats = {}
        for label in unique_labels:
            mask = labels == label
            cluster_data = X[mask]
            
            cluster_stats[int(label)] = {
                "size": int(mask.sum()),
                "percentage": float(mask.sum() / len(labels) * 100),
                "centroid_distance_mean": float(
                    np.mean(np.linalg.norm(
                        cluster_data - cluster_data.mean(axis=0), axis=1
                    ))
                )
            }
        
        # Interpretación
        if silhouette >= 0.7:
            interpretation = "Estructura de clusters muy buena"
        elif silhouette >= 0.5:
            interpretation = "Estructura de clusters razonable"
        elif silhouette >= 0.25:
            interpretation = "Estructura de clusters débil"
        else:
            interpretation = "Sin estructura clara de clusters"
        
        return {
            "n_clusters": n_clusters,
            "silhouette_score": float(silhouette),
            "calinski_harabasz_score": float(calinski),
            "davies_bouldin_score": float(davies_bouldin),
            "cluster_stats": cluster_stats,
            "interpretation": interpretation,
            "quality_assessment": {
                "silhouette": "bueno" if silhouette >= 0.5 else "mejorable",
                "calinski": "bueno" if calinski > 100 else "mejorable",
                "davies_bouldin": "bueno" if davies_bouldin < 1 else "mejorable"
            },
            "total_samples": len(labels),
            "timestamp": datetime.now().isoformat()
        }
    
    def regression_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, Any]:
        """
        Calcula métricas de regresión/predicción.
        
        Args:
            y_true: Valores verdaderos
            y_pred: Valores predichos
            
        Returns:
            Dict con métricas de regresión
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Métricas
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        # MAPE (Mean Absolute Percentage Error)
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100 if mask.any() else 0
        
        # Correlación
        correlation = np.corrcoef(y_true, y_pred)[0, 1]
        
        # Interpretación
        if r2 >= 0.9:
            interpretation = "Predicción excelente"
        elif r2 >= 0.7:
            interpretation = "Predicción buena"
        elif r2 >= 0.5:
            interpretation = "Predicción moderada"
        else:
            interpretation = "Predicción débil"
        
        return {
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "r2_score": float(r2),
            "mape": float(mape),
            "correlation": float(correlation) if not np.isnan(correlation) else 0,
            "interpretation": interpretation,
            "total_samples": len(y_true),
            "timestamp": datetime.now().isoformat()
        }
    
    def anomaly_detection_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        scores: np.ndarray = None
    ) -> Dict[str, Any]:
        """
        Calcula métricas de detección de anomalías.
        
        Args:
            y_true: Etiquetas verdaderas (1=normal, -1=anomalía)
            y_pred: Etiquetas predichas
            scores: Scores de anomalía (opcional)
            
        Returns:
            Dict con métricas de detección de anomalías
        """
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        
        # Convertir a formato binario (1=anomalía, 0=normal)
        y_true_binary = (y_true == -1).astype(int)
        y_pred_binary = (y_pred == -1).astype(int)
        
        # Métricas de clasificación binaria
        precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
        recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
        f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
        
        # Matriz de confusión
        conf_matrix = confusion_matrix(y_true_binary, y_pred_binary)
        
        # True Positives, False Positives, etc.
        tn, fp, fn, tp = conf_matrix.ravel() if conf_matrix.size == 4 else (0, 0, 0, 0)
        
        # False Positive Rate
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        # Detection Rate (True Positive Rate)
        detection_rate = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        result = {
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "detection_rate": float(detection_rate),
            "false_positive_rate": float(fpr),
            "confusion_matrix": {
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp)
            },
            "total_samples": len(y_true),
            "anomalies_true": int(y_true_binary.sum()),
            "anomalies_predicted": int(y_pred_binary.sum()),
            "timestamp": datetime.now().isoformat()
        }
        
        # Estadísticas de scores si están disponibles
        if scores is not None:
            scores = np.array(scores)
            result["score_stats"] = {
                "mean": float(scores.mean()),
                "std": float(scores.std()),
                "min": float(scores.min()),
                "max": float(scores.max())
            }
        
        # Interpretación
        if precision >= 0.7 and recall >= 0.7:
            result["interpretation"] = "Detección de anomalías efectiva"
        elif precision >= 0.5:
            result["interpretation"] = "Detección moderada, ajustar sensibilidad"
        else:
            result["interpretation"] = "Detección débil, revisar modelo"
        
        return result
    
    def format_report(
        self,
        metrics: Dict[str, Any],
        title: str = "Reporte de Métricas"
    ) -> str:
        """
        Formatea métricas como reporte legible.
        
        Args:
            metrics: Dict con métricas
            title: Título del reporte
            
        Returns:
            String con reporte formateado
        """
        lines = [
            "=" * 60,
            f" {title}",
            "=" * 60,
            ""
        ]
        
        def format_value(key, value, indent=0):
            prefix = "  " * indent
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                for k, v in value.items():
                    format_value(k, v, indent + 1)
            elif isinstance(value, float):
                lines.append(f"{prefix}{key}: {value:.4f}")
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], list):
                lines.append(f"{prefix}{key}:")
                for row in value:
                    lines.append(f"{prefix}  {row}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        for key, value in metrics.items():
            if key not in ['classification_report', 'timestamp']:
                format_value(key, value)
        
        lines.extend(["", "=" * 60])
        
        return "\n".join(lines)
    
    def meets_target(
        self,
        metrics: Dict[str, Any],
        targets: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Verifica si las métricas cumplen los objetivos.
        
        Args:
            metrics: Dict con métricas calculadas
            targets: Dict con valores objetivo
            
        Returns:
            Dict con resultado de verificación
        """
        results = {
            "all_targets_met": True,
            "target_details": []
        }
        
        for metric_name, target_value in targets.items():
            actual_value = metrics.get(metric_name)
            
            if actual_value is None:
                met = False
                status = "No disponible"
            elif isinstance(target_value, tuple):
                # Rango (min, max)
                met = target_value[0] <= actual_value <= target_value[1]
                status = "Dentro del rango" if met else "Fuera del rango"
            else:
                # Valor mínimo
                met = actual_value >= target_value
                status = "Cumplido" if met else "No cumplido"
            
            if not met:
                results["all_targets_met"] = False
            
            results["target_details"].append({
                "metric": metric_name,
                "target": target_value,
                "actual": actual_value,
                "met": met,
                "status": status
            })
        
        return results


def precision_recall_fscore_support(y_true, y_pred, average=None, zero_division=0):
    """Wrapper para importación más limpia."""
    from sklearn.metrics import precision_recall_fscore_support as prfs
    return prfs(y_true, y_pred, average=average, zero_division=zero_division)


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    metrics = AIMetrics()
    
    # Métricas de clasificación
    print("\n=== Métricas de Clasificación ===")
    y_true = [0, 0, 1, 1, 2, 2, 0, 1, 2]
    y_pred = [0, 1, 1, 1, 2, 0, 0, 1, 2]
    labels = ["Negativo", "Neutral", "Positivo"]
    
    class_metrics = metrics.classification_metrics(y_true, y_pred, labels)
    print(f"Accuracy: {class_metrics['accuracy']:.4f}")
    print(f"F1 Score: {class_metrics['f1_score']:.4f}")
    
    # Verificar objetivos
    targets = {"accuracy": 0.85, "f1_score": 0.80}
    target_check = metrics.meets_target(class_metrics, targets)
    print(f"\nObjetivos cumplidos: {target_check['all_targets_met']}")
    for detail in target_check['target_details']:
        print(f"  {detail['metric']}: {detail['status']}")
    
    # Métricas de clustering
    print("\n=== Métricas de Clustering ===")
    np.random.seed(42)
    X = np.random.randn(100, 5)
    cluster_labels = np.random.randint(0, 3, 100)
    
    clust_metrics = metrics.clustering_metrics(X, cluster_labels)
    print(f"Silhouette: {clust_metrics['silhouette_score']:.4f}")
    print(f"Interpretación: {clust_metrics['interpretation']}")
    
    # Métricas de regresión
    print("\n=== Métricas de Regresión ===")
    y_true_reg = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y_pred_reg = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
    
    reg_metrics = metrics.regression_metrics(y_true_reg, y_pred_reg)
    print(f"R²: {reg_metrics['r2_score']:.4f}")
    print(f"RMSE: {reg_metrics['rmse']:.4f}")
    print(f"Interpretación: {reg_metrics['interpretation']}")
