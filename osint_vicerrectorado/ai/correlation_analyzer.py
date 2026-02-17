"""
CorrelationAnalyzer - Análisis de Correlaciones Estadísticas
Sistema de Analítica EMI - Sprint 3

Este módulo implementa análisis de correlaciones entre variables usando:
- Correlación de Pearson para variables continuas
- Tests de significancia estadística (p-value)
- Visualización de matriz de correlación
- Identificación de relaciones significativas

Características:
- Cálculo de matriz de correlación
- Filtrado por significancia estadística
- Interpretación automática de correlaciones
- Exportación de resultados

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import pearsonr, spearmanr, kendalltau
import warnings

warnings.filterwarnings('ignore')


class CorrelationAnalyzer:
    """
    Analizador de correlaciones estadísticas entre variables.
    
    Implementa análisis de correlación con:
    - Cálculo de correlación Pearson, Spearman y Kendall
    - Tests de significancia estadística
    - Identificación automática de correlaciones significativas
    - Interpretación de resultados
    
    Attributes:
        correlation_matrix (pd.DataFrame): Matriz de correlaciones
        p_value_matrix (pd.DataFrame): Matriz de p-values
        significant_correlations (List): Correlaciones significativas
        
    Example:
        >>> analyzer = CorrelationAnalyzer()
        >>> result = analyzer.calculate_correlation_matrix(data)
        >>> significant = analyzer.identify_significant_correlations()
    """
    
    # Umbrales de interpretación
    CORRELATION_THRESHOLDS = {
        "muy_fuerte": 0.9,
        "fuerte": 0.7,
        "moderada": 0.5,
        "debil": 0.3,
        "muy_debil": 0.1
    }
    
    def __init__(
        self,
        significance_level: float = 0.05,
        min_correlation: float = 0.3,
        method: str = "pearson"
    ):
        """
        Inicializa el analizador de correlaciones.
        
        Args:
            significance_level: Nivel de significancia (default: 0.05)
            min_correlation: Correlación mínima para considerar significativa
            method: Método de correlación ('pearson', 'spearman', 'kendall')
        """
        self.logger = logging.getLogger("OSINT.AI.Correlation")
        
        self.significance_level = significance_level
        self.min_correlation = min_correlation
        self.method = method
        
        # Resultados
        self.correlation_matrix = None
        self.p_value_matrix = None
        self.data = None
        self.feature_names = None
        self.significant_correlations = []
        self.analysis_results = {}
        
        self.logger.info(
            f"CorrelationAnalyzer inicializado (method={method}, "
            f"alpha={significance_level})"
        )
    
    def calculate_correlation_matrix(
        self,
        data: Union[pd.DataFrame, np.ndarray],
        columns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula la matriz de correlación para los datos.
        
        Args:
            data: DataFrame o array con variables numéricas
            columns: Columnas específicas a analizar
            
        Returns:
            Dict con matriz de correlación y p-values
        """
        self.logger.info("Calculando matriz de correlación...")
        
        # Preparar datos
        if isinstance(data, np.ndarray):
            if columns:
                df = pd.DataFrame(data, columns=columns)
            else:
                df = pd.DataFrame(data)
        else:
            df = data.copy()
        
        # Seleccionar columnas numéricas
        if columns:
            df = df[columns]
        else:
            df = df.select_dtypes(include=[np.number])
        
        self.data = df
        self.feature_names = list(df.columns)
        
        # Eliminar filas con NaN
        df = df.dropna()
        
        if len(df) < 3:
            raise ValueError("Se necesitan al menos 3 observaciones")
        
        n_features = len(self.feature_names)
        
        # Inicializar matrices
        corr_matrix = np.zeros((n_features, n_features))
        p_matrix = np.zeros((n_features, n_features))
        
        # Calcular correlaciones y p-values
        for i in range(n_features):
            for j in range(n_features):
                if i == j:
                    corr_matrix[i, j] = 1.0
                    p_matrix[i, j] = 0.0
                else:
                    corr, p_value = self._calculate_correlation(
                        df.iloc[:, i].values,
                        df.iloc[:, j].values
                    )
                    corr_matrix[i, j] = corr
                    p_matrix[i, j] = p_value
        
        self.correlation_matrix = pd.DataFrame(
            corr_matrix,
            index=self.feature_names,
            columns=self.feature_names
        )
        
        self.p_value_matrix = pd.DataFrame(
            p_matrix,
            index=self.feature_names,
            columns=self.feature_names
        )
        
        self.analysis_results = {
            "method": self.method,
            "n_samples": len(df),
            "n_features": n_features,
            "correlation_matrix": self.correlation_matrix.to_dict(),
            "p_value_matrix": self.p_value_matrix.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Matriz calculada: {n_features}x{n_features}, "
            f"{len(df)} observaciones"
        )
        
        return self.analysis_results
    
    def _calculate_correlation(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> Tuple[float, float]:
        """
        Calcula correlación y p-value entre dos variables.
        
        Args:
            x: Primera variable
            y: Segunda variable
            
        Returns:
            Tupla de (correlación, p-value)
        """
        # Eliminar NaN pareados
        mask = ~(np.isnan(x) | np.isnan(y))
        x_clean = x[mask]
        y_clean = y[mask]
        
        if len(x_clean) < 3:
            return 0.0, 1.0
        
        try:
            if self.method == "pearson":
                corr, p_value = pearsonr(x_clean, y_clean)
            elif self.method == "spearman":
                corr, p_value = spearmanr(x_clean, y_clean)
            elif self.method == "kendall":
                corr, p_value = kendalltau(x_clean, y_clean)
            else:
                corr, p_value = pearsonr(x_clean, y_clean)
            
            return float(corr), float(p_value)
        except Exception:
            return 0.0, 1.0
    
    def identify_significant_correlations(
        self,
        threshold: float = None,
        p_threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Identifica correlaciones estadísticamente significativas.
        
        Args:
            threshold: Umbral mínimo de correlación (default: min_correlation)
            p_threshold: Umbral de p-value (default: significance_level)
            
        Returns:
            Lista de correlaciones significativas
        """
        if self.correlation_matrix is None:
            raise RuntimeError("Primero calcule la matriz con calculate_correlation_matrix()")
        
        threshold = threshold or self.min_correlation
        p_threshold = p_threshold or self.significance_level
        
        self.significant_correlations = []
        
        for i, var1 in enumerate(self.feature_names):
            for j, var2 in enumerate(self.feature_names):
                if i >= j:  # Evitar duplicados y diagonal
                    continue
                
                corr = self.correlation_matrix.loc[var1, var2]
                p_value = self.p_value_matrix.loc[var1, var2]
                
                if abs(corr) >= threshold and p_value <= p_threshold:
                    self.significant_correlations.append({
                        "variable_1": var1,
                        "variable_2": var2,
                        "correlation": float(corr),
                        "p_value": float(p_value),
                        "is_significant": p_value <= p_threshold,
                        "direction": "positiva" if corr > 0 else "negativa",
                        "strength": self._interpret_strength(corr),
                        "interpretation": self._generate_interpretation(
                            var1, var2, corr, p_value
                        )
                    })
        
        # Ordenar por magnitud de correlación
        self.significant_correlations.sort(
            key=lambda x: abs(x['correlation']),
            reverse=True
        )
        
        self.logger.info(
            f"Encontradas {len(self.significant_correlations)} "
            f"correlaciones significativas"
        )
        
        return self.significant_correlations
    
    def _interpret_strength(self, correlation: float) -> str:
        """Interpreta la fuerza de la correlación."""
        abs_corr = abs(correlation)
        
        if abs_corr >= self.CORRELATION_THRESHOLDS["muy_fuerte"]:
            return "muy fuerte"
        elif abs_corr >= self.CORRELATION_THRESHOLDS["fuerte"]:
            return "fuerte"
        elif abs_corr >= self.CORRELATION_THRESHOLDS["moderada"]:
            return "moderada"
        elif abs_corr >= self.CORRELATION_THRESHOLDS["debil"]:
            return "débil"
        else:
            return "muy débil"
    
    def _generate_interpretation(
        self,
        var1: str,
        var2: str,
        correlation: float,
        p_value: float
    ) -> str:
        """Genera interpretación textual de la correlación."""
        
        direction = "positiva" if correlation > 0 else "negativa"
        strength = self._interpret_strength(correlation)
        
        if correlation > 0:
            relation = "aumenta cuando la otra también aumenta"
        else:
            relation = "aumenta cuando la otra disminuye"
        
        significance = (
            "estadísticamente significativa" 
            if p_value <= self.significance_level 
            else "no significativa"
        )
        
        interpretation = (
            f"Existe una correlación {direction} {strength} entre '{var1}' y '{var2}' "
            f"(r={correlation:.3f}, p={p_value:.4f}). "
            f"Esta relación es {significance} al nivel α={self.significance_level}. "
            f"En términos prácticos, una variable {relation}."
        )
        
        return interpretation
    
    def test_statistical_significance(
        self,
        var1: str = None,
        var2: str = None
    ) -> Dict[str, Any]:
        """
        Realiza test de significancia estadística para correlaciones.
        
        Args:
            var1: Primera variable (None para todas)
            var2: Segunda variable (None para todas)
            
        Returns:
            Dict con resultados del test
        """
        if self.correlation_matrix is None:
            raise RuntimeError("Primero calcule la matriz de correlación")
        
        results = {
            "significance_level": self.significance_level,
            "method": self.method,
            "tests": []
        }
        
        if var1 and var2:
            # Test específico
            corr = self.correlation_matrix.loc[var1, var2]
            p_value = self.p_value_matrix.loc[var1, var2]
            
            results["tests"].append({
                "variable_1": var1,
                "variable_2": var2,
                "correlation": float(corr),
                "p_value": float(p_value),
                "is_significant": p_value <= self.significance_level,
                "null_hypothesis": f"No existe correlación entre {var1} y {var2}",
                "conclusion": (
                    "Se rechaza H0: Existe correlación significativa"
                    if p_value <= self.significance_level
                    else "No se rechaza H0: No hay evidencia de correlación"
                )
            })
        else:
            # Todos los pares
            for i, v1 in enumerate(self.feature_names):
                for j, v2 in enumerate(self.feature_names):
                    if i >= j:
                        continue
                    
                    corr = self.correlation_matrix.loc[v1, v2]
                    p_value = self.p_value_matrix.loc[v1, v2]
                    
                    results["tests"].append({
                        "variable_1": v1,
                        "variable_2": v2,
                        "correlation": float(corr),
                        "p_value": float(p_value),
                        "is_significant": p_value <= self.significance_level
                    })
        
        # Resumen
        significant_count = sum(
            1 for t in results["tests"] if t["is_significant"]
        )
        results["summary"] = {
            "total_tests": len(results["tests"]),
            "significant_correlations": significant_count,
            "percentage_significant": (
                significant_count / len(results["tests"]) * 100 
                if results["tests"] else 0
            )
        }
        
        return results
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """
        Genera resumen completo del análisis de correlaciones.
        
        Returns:
            Dict con resumen ejecutivo
        """
        if self.correlation_matrix is None:
            raise RuntimeError("Primero calcule la matriz de correlación")
        
        if not self.significant_correlations:
            self.identify_significant_correlations()
        
        # Estadísticas de la matriz
        corr_values = self.correlation_matrix.values
        upper_triangle = corr_values[np.triu_indices_from(corr_values, k=1)]
        
        summary = {
            "analysis_config": {
                "method": self.method,
                "significance_level": self.significance_level,
                "min_correlation_threshold": self.min_correlation
            },
            "data_info": {
                "n_variables": len(self.feature_names),
                "variable_names": self.feature_names,
                "n_samples": len(self.data) if self.data is not None else 0
            },
            "correlation_statistics": {
                "mean_correlation": float(upper_triangle.mean()),
                "median_correlation": float(np.median(upper_triangle)),
                "std_correlation": float(upper_triangle.std()),
                "max_correlation": float(upper_triangle.max()),
                "min_correlation": float(upper_triangle.min()),
                "range": float(upper_triangle.max() - upper_triangle.min())
            },
            "significant_findings": {
                "total_pairs": len(upper_triangle),
                "significant_pairs": len(self.significant_correlations),
                "percentage_significant": (
                    len(self.significant_correlations) / len(upper_triangle) * 100
                    if len(upper_triangle) > 0 else 0
                ),
                "strongest_positive": None,
                "strongest_negative": None
            },
            "key_insights": self._generate_insights(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Encontrar correlaciones más fuertes
        if self.significant_correlations:
            positive = [c for c in self.significant_correlations if c['correlation'] > 0]
            negative = [c for c in self.significant_correlations if c['correlation'] < 0]
            
            if positive:
                summary["significant_findings"]["strongest_positive"] = {
                    "variables": [positive[0]['variable_1'], positive[0]['variable_2']],
                    "correlation": positive[0]['correlation'],
                    "interpretation": positive[0]['interpretation']
                }
            
            if negative:
                strongest_neg = min(negative, key=lambda x: x['correlation'])
                summary["significant_findings"]["strongest_negative"] = {
                    "variables": [strongest_neg['variable_1'], strongest_neg['variable_2']],
                    "correlation": strongest_neg['correlation'],
                    "interpretation": strongest_neg['interpretation']
                }
        
        return summary
    
    def _generate_insights(self) -> List[str]:
        """Genera insights clave del análisis."""
        insights = []
        
        if not self.significant_correlations:
            insights.append(
                "No se encontraron correlaciones significativas entre las variables."
            )
            return insights
        
        # Insight sobre correlaciones fuertes
        strong = [
            c for c in self.significant_correlations 
            if abs(c['correlation']) >= 0.7
        ]
        if strong:
            insights.append(
                f"Se encontraron {len(strong)} correlaciones fuertes (|r| ≥ 0.7)."
            )
        
        # Insight sobre direcciones
        positive_count = sum(
            1 for c in self.significant_correlations 
            if c['correlation'] > 0
        )
        negative_count = len(self.significant_correlations) - positive_count
        
        if positive_count > negative_count:
            insights.append(
                f"Predominan las correlaciones positivas ({positive_count}) "
                f"sobre las negativas ({negative_count})."
            )
        elif negative_count > positive_count:
            insights.append(
                f"Predominan las correlaciones negativas ({negative_count}) "
                f"sobre las positivas ({positive_count})."
            )
        
        # Insight sobre variables más correlacionadas
        var_counts = {}
        for c in self.significant_correlations:
            for v in [c['variable_1'], c['variable_2']]:
                var_counts[v] = var_counts.get(v, 0) + 1
        
        if var_counts:
            most_correlated = max(var_counts, key=var_counts.get)
            insights.append(
                f"La variable '{most_correlated}' tiene más correlaciones "
                f"significativas ({var_counts[most_correlated]})."
            )
        
        return insights
    
    def get_correlation_pairs(
        self,
        min_correlation: float = None,
        max_correlation: float = None,
        only_significant: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Obtiene pares de variables según criterios de filtrado.
        
        Args:
            min_correlation: Correlación mínima absoluta
            max_correlation: Correlación máxima absoluta
            only_significant: Solo correlaciones significativas
            
        Returns:
            Lista de pares de correlación filtrados
        """
        if self.correlation_matrix is None:
            raise RuntimeError("Primero calcule la matriz de correlación")
        
        pairs = []
        
        for i, var1 in enumerate(self.feature_names):
            for j, var2 in enumerate(self.feature_names):
                if i >= j:
                    continue
                
                corr = self.correlation_matrix.loc[var1, var2]
                p_value = self.p_value_matrix.loc[var1, var2]
                
                # Filtrar por significancia
                if only_significant and p_value > self.significance_level:
                    continue
                
                # Filtrar por correlación mínima
                if min_correlation and abs(corr) < min_correlation:
                    continue
                
                # Filtrar por correlación máxima
                if max_correlation and abs(corr) > max_correlation:
                    continue
                
                pairs.append({
                    "variable_1": var1,
                    "variable_2": var2,
                    "correlation": float(corr),
                    "p_value": float(p_value),
                    "strength": self._interpret_strength(corr)
                })
        
        return sorted(pairs, key=lambda x: abs(x['correlation']), reverse=True)
    
    def export_results(
        self,
        output_dir: str = None,
        format: str = "json"
    ) -> str:
        """
        Exporta resultados del análisis.
        
        Args:
            output_dir: Directorio de salida
            format: Formato de exportación ('json', 'csv')
            
        Returns:
            Ruta del archivo exportado
        """
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(__file__).parent / "outputs"
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            filename = output_path / f"correlations_{timestamp}.json"
            results = {
                "summary": self.get_correlation_summary(),
                "significant_correlations": self.significant_correlations,
                "correlation_matrix": self.correlation_matrix.to_dict() if self.correlation_matrix is not None else None,
                "p_value_matrix": self.p_value_matrix.to_dict() if self.p_value_matrix is not None else None
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        elif format == "csv":
            filename = output_path / f"correlations_{timestamp}.csv"
            if self.correlation_matrix is not None:
                self.correlation_matrix.to_csv(filename)
        
        else:
            raise ValueError(f"Formato no soportado: {format}")
        
        self.logger.info(f"Resultados exportados a: {filename}")
        return str(filename)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Obtiene información del analizador."""
        return {
            "method": self.method,
            "significance_level": self.significance_level,
            "min_correlation": self.min_correlation,
            "has_data": self.data is not None,
            "n_features": len(self.feature_names) if self.feature_names else 0,
            "significant_correlations_found": len(self.significant_correlations)
        }


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Generar datos de ejemplo con correlaciones conocidas
    np.random.seed(42)
    n = 100
    
    # Variables con correlaciones conocidas
    engagement = np.random.normal(100, 20, n)
    likes = engagement * 5 + np.random.normal(0, 30, n)  # Correlación positiva fuerte
    sentiment = engagement * 0.01 + np.random.normal(0.6, 0.1, n)  # Correlación positiva moderada
    comments = np.random.normal(20, 10, n)  # Sin correlación
    shares = likes * 0.1 + np.random.normal(0, 10, n)  # Correlación positiva
    
    data = pd.DataFrame({
        'engagement': engagement,
        'likes': likes,
        'sentiment': sentiment,
        'comments': comments,
        'shares': shares
    })
    
    # Crear analizador
    analyzer = CorrelationAnalyzer(significance_level=0.05, min_correlation=0.3)
    
    # Calcular matriz
    print("Calculando matriz de correlación...")
    analyzer.calculate_correlation_matrix(data)
    
    # Identificar correlaciones significativas
    print("\n--- Correlaciones Significativas ---")
    significant = analyzer.identify_significant_correlations()
    
    for corr in significant:
        print(f"\n{corr['variable_1']} ↔ {corr['variable_2']}")
        print(f"  r = {corr['correlation']:.3f} ({corr['strength']}, {corr['direction']})")
        print(f"  p-value = {corr['p_value']:.4f}")
    
    # Tests de significancia
    print("\n--- Tests de Significancia ---")
    tests = analyzer.test_statistical_significance()
    print(f"Total tests: {tests['summary']['total_tests']}")
    print(f"Significativos: {tests['summary']['significant_correlations']}")
    
    # Resumen
    print("\n--- Resumen ---")
    summary = analyzer.get_correlation_summary()
    print(f"Variables: {summary['data_info']['n_variables']}")
    print(f"Correlación media: {summary['correlation_statistics']['mean_correlation']:.3f}")
    print(f"Correlaciones significativas: {summary['significant_findings']['significant_pairs']}")
    
    # Insights
    print("\n--- Insights ---")
    for insight in summary['key_insights']:
        print(f"  • {insight}")
