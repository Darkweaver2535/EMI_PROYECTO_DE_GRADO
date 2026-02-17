"""
ClusteringEngine - Motor de Clustering de Opiniones con K-Means
Sistema de Analítica EMI - Sprint 3

Este módulo implementa clustering de opiniones estudiantiles usando:
- Vectorización TF-IDF para representación de textos
- K-Means para agrupamiento
- Métodos del codo y silhouette para selección óptima de k
- Extracción de términos representativos por cluster

Características:
- Determinación automática del número óptimo de clusters
- Interpretación semántica de cada cluster
- Persistencia de modelos vectorizadores y clusterers
- Predicción de cluster para nuevos textos

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import json
import logging
import pickle
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.decomposition import PCA
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)


class ClusteringEngine:
    """
    Motor de clustering para análisis de opiniones.
    
    Implementa agrupamiento de textos usando TF-IDF + K-Means con:
    - Selección automática de número óptimo de clusters
    - Extracción de términos representativos
    - Evaluación con múltiples métricas
    - Persistencia de modelos
    
    Attributes:
        vectorizer (TfidfVectorizer): Vectorizador TF-IDF entrenado
        kmeans (KMeans): Modelo de clustering entrenado
        n_clusters (int): Número actual de clusters
        models_dir (Path): Directorio para modelos serializados
        
    Example:
        >>> engine = ClusteringEngine()
        >>> texts = ["opinión 1", "opinión 2", ...]
        >>> engine.vectorize_texts(texts)
        >>> optimal_k = engine.find_optimal_k()
        >>> engine.fit_clusters(optimal_k)
        >>> keywords = engine.get_cluster_keywords(0)
    """
    
    def __init__(
        self,
        models_dir: str = None,
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_df: float = 0.95,
        random_state: int = 42
    ):
        """
        Inicializa el motor de clustering.
        
        Args:
            models_dir: Directorio para guardar modelos
            max_features: Número máximo de features TF-IDF
            ngram_range: Rango de n-gramas (unigrams y bigrams)
            min_df: Frecuencia mínima de documento
            max_df: Frecuencia máxima de documento
            random_state: Semilla para reproducibilidad
        """
        self.logger = logging.getLogger("OSINT.AI.Clustering")
        
        # Configurar directorio de modelos
        if models_dir:
            self.models_dir = Path(models_dir)
        else:
            self.models_dir = Path(__file__).parent / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Parámetros del vectorizador
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.random_state = random_state
        
        # Inicializar vectorizador
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            strip_accents='unicode',
            lowercase=True,
            stop_words=self._get_spanish_stopwords()
        )
        
        # Modelo y datos
        self.kmeans = None
        self.n_clusters = None
        self.tfidf_matrix = None
        self.feature_names = None
        self.texts = None
        
        # Métricas de evaluación
        self.evaluation_metrics = {}
        self.elbow_scores = {}
        self.silhouette_scores = {}
        
        self.logger.info("ClusteringEngine inicializado")
    
    def _get_spanish_stopwords(self) -> List[str]:
        """
        Retorna lista de stopwords en español.
        
        Returns:
            Lista de palabras vacías en español
        """
        return [
            'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 
            'por', 'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 
            'más', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta',
            'entre', 'cuando', 'muy', 'sin', 'sobre', 'también', 'me', 'hasta',
            'hay', 'donde', 'quien', 'desde', 'todo', 'nos', 'durante', 'todos',
            'uno', 'les', 'ni', 'contra', 'otros', 'ese', 'eso', 'ante', 'ellos',
            'e', 'esto', 'mí', 'antes', 'algunos', 'qué', 'unos', 'yo', 'otro',
            'otras', 'otra', 'él', 'tanto', 'esa', 'estos', 'mucho', 'quienes',
            'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas', 'algunas',
            'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu', 'tus',
            'ellas', 'nosotras', 'vosotros', 'vosotras', 'os', 'mío', 'tuyo',
            'suyo', 'nuestro', 'vuestro', 'esos', 'esas', 'estoy', 'estás',
            'está', 'estamos', 'estáis', 'están', 'he', 'has', 'ha', 'hemos',
            'habéis', 'han', 'sido', 'ser', 'es', 'son', 'fue', 'fueron', 'era',
            'solo', 'así', 'ahora', 'bien', 'si', 'ver', 'hacer', 'puede',
            'aquí', 'tienen', 'tiene', 'hay', 'mas', 'ya', 'cada', 'vez',
            'siendo', 'cual', 'cuales', 'mismo', 'misma', 'mismos', 'mismas'
        ]
    
    def vectorize_texts(self, texts: List[str]) -> np.ndarray:
        """
        Vectoriza textos usando TF-IDF.
        
        Args:
            texts: Lista de textos a vectorizar
            
        Returns:
            Matriz TF-IDF sparse convertida a dense
        """
        if not texts:
            raise ValueError("Lista de textos vacía")
        
        self.logger.info(f"Vectorizando {len(texts)} textos...")
        
        # Filtrar textos vacíos
        self.texts = [str(t).strip() for t in texts if t and str(t).strip()]
        
        if len(self.texts) < 10:
            raise ValueError(f"Se necesitan al menos 10 textos, hay {len(self.texts)}")
        
        # Ajustar y transformar
        self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)
        self.feature_names = self.vectorizer.get_feature_names_out()
        
        self.logger.info(
            f"Vectorización completada: {self.tfidf_matrix.shape[0]} docs, "
            f"{self.tfidf_matrix.shape[1]} features"
        )
        
        return self.tfidf_matrix.toarray()
    
    def find_optimal_k(
        self,
        max_k: int = 10,
        min_k: int = 2
    ) -> Dict[str, Any]:
        """
        Encuentra el número óptimo de clusters usando método del codo y silhouette.
        
        Args:
            max_k: Número máximo de clusters a evaluar
            min_k: Número mínimo de clusters
            
        Returns:
            Dict con k óptimo y métricas de evaluación
        """
        if self.tfidf_matrix is None:
            raise RuntimeError("Primero ejecute vectorize_texts()")
        
        n_samples = self.tfidf_matrix.shape[0]
        max_k = min(max_k, n_samples - 1)
        
        self.logger.info(f"Buscando k óptimo entre {min_k} y {max_k}...")
        
        inertias = []
        silhouette_scores = []
        calinski_scores = []
        davies_scores = []
        
        for k in range(min_k, max_k + 1):
            kmeans = KMeans(
                n_clusters=k,
                random_state=self.random_state,
                n_init=10,
                max_iter=300
            )
            labels = kmeans.fit_predict(self.tfidf_matrix)
            
            # Inercia (para método del codo)
            inertias.append(kmeans.inertia_)
            
            # Silhouette score
            sil_score = silhouette_score(self.tfidf_matrix, labels)
            silhouette_scores.append(sil_score)
            
            # Calinski-Harabasz score
            ch_score = calinski_harabasz_score(
                self.tfidf_matrix.toarray(), labels
            )
            calinski_scores.append(ch_score)
            
            # Davies-Bouldin score (menor es mejor)
            db_score = davies_bouldin_score(
                self.tfidf_matrix.toarray(), labels
            )
            davies_scores.append(db_score)
            
            self.logger.debug(
                f"k={k}: silhouette={sil_score:.4f}, "
                f"calinski={ch_score:.2f}, davies={db_score:.4f}"
            )
        
        # Determinar k óptimo combinando métricas
        # Normalizar scores
        sil_normalized = np.array(silhouette_scores)
        sil_normalized = (sil_normalized - sil_normalized.min()) / (
            sil_normalized.max() - sil_normalized.min() + 1e-10
        )
        
        ch_normalized = np.array(calinski_scores)
        ch_normalized = (ch_normalized - ch_normalized.min()) / (
            ch_normalized.max() - ch_normalized.min() + 1e-10
        )
        
        db_normalized = np.array(davies_scores)
        db_normalized = 1 - (db_normalized - db_normalized.min()) / (
            db_normalized.max() - db_normalized.min() + 1e-10
        )
        
        # Score combinado (mayor peso a silhouette)
        combined_score = (
            0.5 * sil_normalized + 
            0.3 * ch_normalized + 
            0.2 * db_normalized
        )
        
        optimal_idx = np.argmax(combined_score)
        optimal_k = min_k + optimal_idx
        
        # Guardar métricas
        self.elbow_scores = {
            k: float(inertias[i]) 
            for i, k in enumerate(range(min_k, max_k + 1))
        }
        self.silhouette_scores = {
            k: float(silhouette_scores[i]) 
            for i, k in enumerate(range(min_k, max_k + 1))
        }
        
        result = {
            "optimal_k": optimal_k,
            "silhouette_score": silhouette_scores[optimal_idx],
            "calinski_score": calinski_scores[optimal_idx],
            "davies_score": davies_scores[optimal_idx],
            "all_k_scores": {
                k: {
                    "inertia": float(inertias[i]),
                    "silhouette": float(silhouette_scores[i]),
                    "calinski": float(calinski_scores[i]),
                    "davies": float(davies_scores[i])
                }
                for i, k in enumerate(range(min_k, max_k + 1))
            },
            "recommendation": self._get_k_recommendation(
                optimal_k, silhouette_scores[optimal_idx]
            )
        }
        
        self.logger.info(
            f"K óptimo encontrado: {optimal_k} "
            f"(silhouette: {silhouette_scores[optimal_idx]:.4f})"
        )
        
        return result
    
    def _get_k_recommendation(
        self, 
        k: int, 
        silhouette: float
    ) -> str:
        """
        Genera recomendación basada en métricas.
        
        Args:
            k: Número de clusters
            silhouette: Score de silhouette
            
        Returns:
            Recomendación textual
        """
        if silhouette >= 0.7:
            quality = "excelente"
        elif silhouette >= 0.5:
            quality = "buena"
        elif silhouette >= 0.3:
            quality = "aceptable"
        else:
            quality = "baja"
        
        return (
            f"Se recomienda usar k={k} clusters. "
            f"La calidad de separación es {quality} (silhouette={silhouette:.4f}). "
            f"{'Los clusters están bien definidos.' if silhouette >= 0.5 else 'Considere revisar los datos o ajustar parámetros.'}"
        )
    
    def fit_clusters(self, k: int = None) -> Dict[str, Any]:
        """
        Entrena el modelo K-Means con el número de clusters especificado.
        
        Args:
            k: Número de clusters (si es None, usa el óptimo encontrado)
            
        Returns:
            Dict con información del clustering realizado
        """
        if self.tfidf_matrix is None:
            raise RuntimeError("Primero ejecute vectorize_texts()")
        
        if k is None and self.silhouette_scores:
            k = max(self.silhouette_scores, key=self.silhouette_scores.get)
        elif k is None:
            k = 5  # Default
        
        self.n_clusters = k
        self.logger.info(f"Entrenando K-Means con k={k}...")
        
        # Entrenar modelo
        self.kmeans = KMeans(
            n_clusters=k,
            random_state=self.random_state,
            n_init=10,
            max_iter=300
        )
        
        self.cluster_labels = self.kmeans.fit_predict(self.tfidf_matrix)
        
        # Calcular métricas
        silhouette = silhouette_score(self.tfidf_matrix, self.cluster_labels)
        calinski = calinski_harabasz_score(
            self.tfidf_matrix.toarray(), self.cluster_labels
        )
        davies = davies_bouldin_score(
            self.tfidf_matrix.toarray(), self.cluster_labels
        )
        
        # Estadísticas por cluster
        cluster_stats = {}
        for i in range(k):
            cluster_mask = self.cluster_labels == i
            cluster_size = int(cluster_mask.sum())
            cluster_texts = [
                self.texts[j] for j in range(len(self.texts)) 
                if cluster_mask[j]
            ]
            
            # Distancias al centroide
            cluster_points = self.tfidf_matrix[cluster_mask].toarray()
            centroid = self.kmeans.cluster_centers_[i]
            distances = np.linalg.norm(cluster_points - centroid, axis=1)
            
            cluster_stats[i] = {
                "size": cluster_size,
                "percentage": float(cluster_size / len(self.texts) * 100),
                "avg_distance_to_centroid": float(distances.mean()),
                "max_distance_to_centroid": float(distances.max()),
                "keywords": self.get_cluster_keywords(i, top_n=10)
            }
        
        self.evaluation_metrics = {
            "n_clusters": k,
            "silhouette_score": float(silhouette),
            "calinski_harabasz_score": float(calinski),
            "davies_bouldin_score": float(davies),
            "total_texts": len(self.texts),
            "cluster_stats": cluster_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(
            f"Clustering completado. Silhouette: {silhouette:.4f}"
        )
        
        return self.evaluation_metrics
    
    def predict_cluster(self, text: str) -> Dict[str, Any]:
        """
        Asigna un nuevo texto al cluster más cercano.
        
        Args:
            text: Texto a clasificar
            
        Returns:
            Dict con cluster asignado y distancia
        """
        if self.kmeans is None:
            raise RuntimeError("Primero entrene el modelo con fit_clusters()")
        
        # Vectorizar texto
        text_vector = self.vectorizer.transform([text])
        
        # Predecir cluster
        cluster = int(self.kmeans.predict(text_vector)[0])
        
        # Calcular distancia al centroide
        centroid = self.kmeans.cluster_centers_[cluster]
        distance = float(np.linalg.norm(
            text_vector.toarray()[0] - centroid
        ))
        
        # Obtener keywords del cluster
        keywords = self.get_cluster_keywords(cluster, top_n=5)
        
        return {
            "text": text[:200] + "..." if len(text) > 200 else text,
            "cluster_id": cluster,
            "distance_to_centroid": distance,
            "cluster_keywords": keywords,
            "cluster_description": f"Cluster {cluster}: {', '.join(keywords)}"
        }
    
    def get_cluster_keywords(
        self, 
        cluster_id: int, 
        top_n: int = 10
    ) -> List[str]:
        """
        Obtiene los términos más representativos de un cluster.
        
        Args:
            cluster_id: ID del cluster
            top_n: Número de términos a retornar
            
        Returns:
            Lista de términos más importantes
        """
        if self.kmeans is None or self.feature_names is None:
            raise RuntimeError("Primero entrene el modelo con fit_clusters()")
        
        if cluster_id < 0 or cluster_id >= self.n_clusters:
            raise ValueError(f"cluster_id debe estar entre 0 y {self.n_clusters - 1}")
        
        # Obtener centroide del cluster
        centroid = self.kmeans.cluster_centers_[cluster_id]
        
        # Ordenar features por peso en el centroide
        top_indices = centroid.argsort()[-top_n:][::-1]
        
        keywords = [self.feature_names[i] for i in top_indices]
        
        return keywords
    
    def get_cluster_texts(
        self, 
        cluster_id: int, 
        max_texts: int = None
    ) -> List[str]:
        """
        Obtiene los textos pertenecientes a un cluster.
        
        Args:
            cluster_id: ID del cluster
            max_texts: Máximo número de textos a retornar
            
        Returns:
            Lista de textos del cluster
        """
        if self.kmeans is None:
            raise RuntimeError("Primero entrene el modelo con fit_clusters()")
        
        cluster_mask = self.cluster_labels == cluster_id
        cluster_texts = [
            self.texts[i] for i in range(len(self.texts))
            if cluster_mask[i]
        ]
        
        if max_texts:
            cluster_texts = cluster_texts[:max_texts]
        
        return cluster_texts
    
    def evaluate_clustering(self) -> Dict[str, Any]:
        """
        Evalúa el clustering actual con múltiples métricas.
        
        Returns:
            Dict con métricas de evaluación detalladas
        """
        if self.kmeans is None:
            raise RuntimeError("Primero entrene el modelo con fit_clusters()")
        
        return self.evaluation_metrics
    
    def get_cluster_summary(self) -> List[Dict[str, Any]]:
        """
        Genera un resumen interpretable de todos los clusters.
        
        Returns:
            Lista de resúmenes por cluster
        """
        if self.kmeans is None:
            raise RuntimeError("Primero entrene el modelo con fit_clusters()")
        
        summaries = []
        
        for i in range(self.n_clusters):
            keywords = self.get_cluster_keywords(i, top_n=5)
            texts = self.get_cluster_texts(i, max_texts=3)
            
            stats = self.evaluation_metrics["cluster_stats"].get(i, {})
            
            summary = {
                "cluster_id": i,
                "name": f"Cluster {i}: {keywords[0].title() if keywords else 'N/A'}",
                "description": f"Opiniones relacionadas con: {', '.join(keywords)}",
                "size": stats.get("size", 0),
                "percentage": stats.get("percentage", 0),
                "top_keywords": keywords,
                "example_texts": texts,
                "avg_cohesion": stats.get("avg_distance_to_centroid", 0)
            }
            
            summaries.append(summary)
        
        # Ordenar por tamaño
        summaries.sort(key=lambda x: x["size"], reverse=True)
        
        return summaries
    
    def reduce_dimensions(
        self, 
        n_components: int = 2
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Reduce dimensionalidad para visualización.
        
        Args:
            n_components: Número de dimensiones (2 o 3)
            
        Returns:
            Tupla de (datos_reducidos, centroides_reducidos)
        """
        if self.tfidf_matrix is None or self.kmeans is None:
            raise RuntimeError("Primero entrene el modelo")
        
        pca = PCA(n_components=n_components, random_state=self.random_state)
        
        # Reducir datos
        data_reduced = pca.fit_transform(self.tfidf_matrix.toarray())
        
        # Reducir centroides
        centroids_reduced = pca.transform(self.kmeans.cluster_centers_)
        
        return data_reduced, centroids_reduced
    
    def save_model(self, path: str = None) -> str:
        """
        Guarda el vectorizador y modelo de clustering.
        
        Args:
            path: Ruta donde guardar
            
        Returns:
            Ruta del archivo guardado
        """
        if self.vectorizer is None or self.kmeans is None:
            raise RuntimeError("No hay modelo para guardar")
        
        save_path = Path(path) if path else self.models_dir / "clustering_model.pkl"
        
        model_data = {
            "vectorizer": self.vectorizer,
            "kmeans": self.kmeans,
            "n_clusters": self.n_clusters,
            "feature_names": self.feature_names,
            "evaluation_metrics": self.evaluation_metrics,
            "config": {
                "max_features": self.max_features,
                "ngram_range": self.ngram_range,
                "min_df": self.min_df,
                "max_df": self.max_df,
                "random_state": self.random_state
            },
            "saved_at": datetime.now().isoformat()
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.logger.info(f"Modelo guardado en: {save_path}")
        return str(save_path)
    
    def load_model(self, path: str = None) -> bool:
        """
        Carga un modelo previamente guardado.
        
        Args:
            path: Ruta del archivo a cargar
            
        Returns:
            True si la carga fue exitosa
        """
        load_path = Path(path) if path else self.models_dir / "clustering_model.pkl"
        
        if not load_path.exists():
            self.logger.warning(f"No se encontró modelo en: {load_path}")
            return False
        
        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.vectorizer = model_data["vectorizer"]
        self.kmeans = model_data["kmeans"]
        self.n_clusters = model_data["n_clusters"]
        self.feature_names = model_data["feature_names"]
        self.evaluation_metrics = model_data.get("evaluation_metrics", {})
        
        self.logger.info(f"Modelo cargado desde: {load_path}")
        return True
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo actual.
        
        Returns:
            Dict con información del modelo
        """
        info = {
            "models_dir": str(self.models_dir),
            "is_fitted": self.kmeans is not None,
            "n_clusters": self.n_clusters,
            "config": {
                "max_features": self.max_features,
                "ngram_range": self.ngram_range,
                "min_df": self.min_df,
                "max_df": self.max_df
            }
        }
        
        if self.tfidf_matrix is not None:
            info["n_documents"] = self.tfidf_matrix.shape[0]
            info["n_features"] = self.tfidf_matrix.shape[1]
        
        if self.evaluation_metrics:
            info["evaluation_metrics"] = {
                "silhouette_score": self.evaluation_metrics.get("silhouette_score"),
                "calinski_harabasz_score": self.evaluation_metrics.get("calinski_harabasz_score"),
                "davies_bouldin_score": self.evaluation_metrics.get("davies_bouldin_score")
            }
        
        return info


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Datos de ejemplo
    sample_texts = [
        "La biblioteca de la EMI tiene muy buenos recursos",
        "Los libros de la biblioteca están desactualizados",
        "Excelente servicio en biblioteca, muy recomendado",
        "Las aulas están en mal estado, falta mantenimiento",
        "Los laboratorios necesitan actualización de equipos",
        "Los profesores de matemáticas son muy buenos",
        "La cafetería tiene precios accesibles",
        "El campus es muy seguro, hay vigilancia 24/7",
        "Los baños necesitan limpieza urgente",
        "La inscripción fue rápida y sin problemas",
        "El sistema de notas online funciona muy bien",
        "Los profesores de ingeniería son expertos en su área",
        "Falta estacionamiento para estudiantes",
        "Los deportes están muy bien organizados",
        "La cancha de fútbol es excelente"
    ]
    
    # Crear engine
    engine = ClusteringEngine()
    
    # Vectorizar
    print("Vectorizando textos...")
    engine.vectorize_texts(sample_texts)
    
    # Encontrar k óptimo
    print("\nBuscando k óptimo...")
    optimal_result = engine.find_optimal_k(max_k=6)
    print(f"K óptimo: {optimal_result['optimal_k']}")
    print(f"Silhouette: {optimal_result['silhouette_score']:.4f}")
    
    # Entrenar con k óptimo
    print("\nEntrenando modelo...")
    metrics = engine.fit_clusters(optimal_result['optimal_k'])
    
    # Mostrar resumen
    print("\n--- Resumen de Clusters ---")
    for summary in engine.get_cluster_summary():
        print(f"\n{summary['name']}")
        print(f"  Tamaño: {summary['size']} ({summary['percentage']:.1f}%)")
        print(f"  Keywords: {', '.join(summary['top_keywords'])}")
    
    # Predecir nuevo texto
    print("\n--- Predicción de nuevo texto ---")
    new_text = "La biblioteca necesita más computadoras"
    prediction = engine.predict_cluster(new_text)
    print(f"Texto: {new_text}")
    print(f"Cluster: {prediction['cluster_id']}")
    print(f"Keywords: {', '.join(prediction['cluster_keywords'])}")
