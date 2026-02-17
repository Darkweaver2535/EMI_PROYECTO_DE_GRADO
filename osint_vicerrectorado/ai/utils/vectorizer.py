"""
TextVectorizer - Utilidades de Vectorización de Texto
Sistema de Analítica EMI - Sprint 3

Proporciona funciones de vectorización de texto para los módulos de IA.
Incluye TF-IDF, embeddings y preprocesamiento de texto.

Autor: Sistema OSINT EMI
Fecha: Enero 2025
"""

import os
import re
import logging
import pickle
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import TruncatedSVD, PCA
import unicodedata


class TextVectorizer:
    """
    Vectorizador de texto con múltiples métodos.
    
    Proporciona vectorización de texto usando:
    - TF-IDF (Term Frequency - Inverse Document Frequency)
    - Bag of Words (Count Vectorizer)
    - Reducción de dimensionalidad (SVD/PCA)
    
    Attributes:
        vectorizer: Vectorizador entrenado
        method (str): Método de vectorización
        dim_reduction: Modelo de reducción de dimensionalidad
        
    Example:
        >>> vectorizer = TextVectorizer(method='tfidf')
        >>> vectors = vectorizer.fit_transform(texts)
        >>> new_vectors = vectorizer.transform(new_texts)
    """
    
    # Stopwords en español
    SPANISH_STOPWORDS = [
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
        'aquí', 'tienen', 'tiene', 'mas', 'cada', 'vez', 'siendo', 'mismo',
        'misma', 'mismos', 'mismas'
    ]
    
    def __init__(
        self,
        method: str = 'tfidf',
        max_features: int = 5000,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 2,
        max_df: float = 0.95,
        use_stopwords: bool = True,
        lowercase: bool = True,
        strip_accents: bool = True,
        n_components: int = None,
        random_state: int = 42
    ):
        """
        Inicializa el vectorizador.
        
        Args:
            method: Método de vectorización ('tfidf', 'count')
            max_features: Número máximo de features
            ngram_range: Rango de n-gramas
            min_df: Frecuencia mínima de documento
            max_df: Frecuencia máxima de documento
            use_stopwords: Usar stopwords en español
            lowercase: Convertir a minúsculas
            strip_accents: Eliminar acentos
            n_components: Dimensiones tras reducción (None para no reducir)
            random_state: Semilla para reproducibilidad
        """
        self.logger = logging.getLogger("OSINT.AI.Vectorizer")
        
        self.method = method
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self.use_stopwords = use_stopwords
        self.lowercase = lowercase
        self.strip_accents = strip_accents
        self.n_components = n_components
        self.random_state = random_state
        
        # Inicializar vectorizador
        stopwords = self.SPANISH_STOPWORDS if use_stopwords else None
        
        if method == 'tfidf':
            self.vectorizer = TfidfVectorizer(
                max_features=max_features,
                ngram_range=ngram_range,
                min_df=min_df,
                max_df=max_df,
                stop_words=stopwords,
                lowercase=lowercase,
                strip_accents='unicode' if strip_accents else None
            )
        elif method == 'count':
            self.vectorizer = CountVectorizer(
                max_features=max_features,
                ngram_range=ngram_range,
                min_df=min_df,
                max_df=max_df,
                stop_words=stopwords,
                lowercase=lowercase,
                strip_accents='unicode' if strip_accents else None
            )
        else:
            raise ValueError(f"Método no soportado: {method}")
        
        # Reducción de dimensionalidad
        self.dim_reduction = None
        if n_components:
            self.dim_reduction = TruncatedSVD(
                n_components=n_components,
                random_state=random_state
            )
        
        # Estado
        self.is_fitted = False
        self.vocabulary_ = None
        self.feature_names_ = None
        
        self.logger.info(f"TextVectorizer inicializado (method={method})")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocesa texto antes de vectorización.
        
        Args:
            text: Texto a preprocesar
            
        Returns:
            Texto preprocesado
        """
        if not text:
            return ""
        
        # Convertir a string
        text = str(text)
        
        # Eliminar URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text)
        
        # Eliminar menciones y hashtags (mantener texto)
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#(\w+)', r'\1', text)
        
        # Eliminar emojis
        text = self._remove_emojis(text)
        
        # Eliminar caracteres especiales pero mantener espacios
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Eliminar múltiples espacios
        text = re.sub(r'\s+', ' ', text)
        
        # Strip
        text = text.strip()
        
        return text
    
    def _remove_emojis(self, text: str) -> str:
        """Elimina emojis del texto."""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)
    
    def fit(self, texts: List[str]) -> 'TextVectorizer':
        """
        Ajusta el vectorizador con los textos proporcionados.
        
        Args:
            texts: Lista de textos para entrenar
            
        Returns:
            Self para encadenamiento
        """
        self.logger.info(f"Ajustando vectorizador con {len(texts)} textos...")
        
        # Preprocesar
        processed = [self.preprocess_text(t) for t in texts]
        
        # Filtrar vacíos
        processed = [t for t in processed if t.strip()]
        
        if len(processed) < 2:
            raise ValueError("Se necesitan al menos 2 textos no vacíos")
        
        # Ajustar vectorizador
        self.vectorizer.fit(processed)
        self.vocabulary_ = self.vectorizer.vocabulary_
        self.feature_names_ = self.vectorizer.get_feature_names_out()
        
        # Ajustar reducción si está configurada
        if self.dim_reduction:
            vectors = self.vectorizer.transform(processed)
            self.dim_reduction.fit(vectors)
        
        self.is_fitted = True
        
        self.logger.info(
            f"Vectorizador ajustado. Vocabulario: {len(self.vocabulary_)} términos"
        )
        
        return self
    
    def transform(
        self,
        texts: List[str],
        return_sparse: bool = False
    ) -> np.ndarray:
        """
        Transforma textos a vectores.
        
        Args:
            texts: Lista de textos a transformar
            return_sparse: Si retornar matriz sparse
            
        Returns:
            Array de vectores
        """
        if not self.is_fitted:
            raise RuntimeError("Vectorizador no ajustado. Ejecute fit() primero.")
        
        # Preprocesar
        processed = [self.preprocess_text(t) for t in texts]
        
        # Transformar
        vectors = self.vectorizer.transform(processed)
        
        # Reducir dimensionalidad si está configurada
        if self.dim_reduction:
            vectors = self.dim_reduction.transform(vectors)
            return vectors
        
        if return_sparse:
            return vectors
        
        return vectors.toarray()
    
    def fit_transform(
        self,
        texts: List[str],
        return_sparse: bool = False
    ) -> np.ndarray:
        """
        Ajusta y transforma en un solo paso.
        
        Args:
            texts: Lista de textos
            return_sparse: Si retornar matriz sparse
            
        Returns:
            Array de vectores
        """
        self.fit(texts)
        return self.transform(texts, return_sparse)
    
    def get_feature_names(self) -> List[str]:
        """
        Obtiene los nombres de las features.
        
        Returns:
            Lista de nombres de features
        """
        if self.feature_names_ is None:
            raise RuntimeError("Vectorizador no ajustado")
        return list(self.feature_names_)
    
    def get_top_terms(
        self,
        vector: np.ndarray,
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Obtiene los términos más importantes de un vector.
        
        Args:
            vector: Vector TF-IDF
            top_n: Número de términos a retornar
            
        Returns:
            Lista de tuplas (término, peso)
        """
        if self.feature_names_ is None:
            raise RuntimeError("Vectorizador no ajustado")
        
        # Aplanar si es necesario
        if len(vector.shape) > 1:
            vector = vector.flatten()
        
        # Obtener índices de mayor peso
        top_indices = vector.argsort()[-top_n:][::-1]
        
        return [
            (self.feature_names_[i], float(vector[i]))
            for i in top_indices
            if vector[i] > 0
        ]
    
    def calculate_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """
        Calcula similaridad coseno entre dos textos.
        
        Args:
            text1: Primer texto
            text2: Segundo texto
            
        Returns:
            Similaridad coseno (0-1)
        """
        if not self.is_fitted:
            raise RuntimeError("Vectorizador no ajustado")
        
        vectors = self.transform([text1, text2])
        
        # Similaridad coseno
        dot_product = np.dot(vectors[0], vectors[1])
        norm1 = np.linalg.norm(vectors[0])
        norm2 = np.linalg.norm(vectors[1])
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def save(self, path: str) -> str:
        """
        Guarda el vectorizador entrenado.
        
        Args:
            path: Ruta donde guardar
            
        Returns:
            Ruta del archivo guardado
        """
        if not self.is_fitted:
            raise RuntimeError("Vectorizador no ajustado")
        
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "vectorizer": self.vectorizer,
            "dim_reduction": self.dim_reduction,
            "vocabulary_": self.vocabulary_,
            "feature_names_": self.feature_names_,
            "config": {
                "method": self.method,
                "max_features": self.max_features,
                "ngram_range": self.ngram_range,
                "n_components": self.n_components
            },
            "saved_at": datetime.now().isoformat()
        }
        
        with open(save_path, 'wb') as f:
            pickle.dump(data, f)
        
        self.logger.info(f"Vectorizador guardado en: {save_path}")
        return str(save_path)
    
    def load(self, path: str) -> 'TextVectorizer':
        """
        Carga un vectorizador guardado.
        
        Args:
            path: Ruta del archivo
            
        Returns:
            Self con modelo cargado
        """
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        self.vectorizer = data["vectorizer"]
        self.dim_reduction = data.get("dim_reduction")
        self.vocabulary_ = data["vocabulary_"]
        self.feature_names_ = data["feature_names_"]
        self.is_fitted = True
        
        config = data.get("config", {})
        self.method = config.get("method", self.method)
        
        self.logger.info(f"Vectorizador cargado desde: {path}")
        return self
    
    def get_info(self) -> Dict[str, Any]:
        """
        Obtiene información del vectorizador.
        
        Returns:
            Dict con información del modelo
        """
        return {
            "method": self.method,
            "is_fitted": self.is_fitted,
            "max_features": self.max_features,
            "ngram_range": self.ngram_range,
            "vocabulary_size": len(self.vocabulary_) if self.vocabulary_ else 0,
            "has_dim_reduction": self.dim_reduction is not None,
            "n_components": self.n_components
        }


# Ejemplo de uso standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Textos de ejemplo
    texts = [
        "La EMI es una excelente universidad",
        "Los profesores de ingeniería son muy buenos",
        "La biblioteca necesita más libros actualizados",
        "El campus tiene buenas instalaciones deportivas",
        "La cafetería tiene precios accesibles"
    ]
    
    # Crear vectorizador
    vectorizer = TextVectorizer(method='tfidf', max_features=1000)
    
    # Ajustar y transformar
    print("Vectorizando textos...")
    vectors = vectorizer.fit_transform(texts)
    
    print(f"\nForma de vectores: {vectors.shape}")
    print(f"Vocabulario: {vectorizer.get_info()['vocabulary_size']} términos")
    
    # Top términos para cada texto
    print("\n--- Top términos por texto ---")
    for i, text in enumerate(texts):
        terms = vectorizer.get_top_terms(vectors[i], top_n=5)
        print(f"\n{text[:50]}...")
        for term, weight in terms:
            print(f"  {term}: {weight:.4f}")
    
    # Similaridad
    print("\n--- Similaridad ---")
    sim = vectorizer.calculate_similarity(texts[0], texts[1])
    print(f"Texto 0 vs Texto 1: {sim:.4f}")
