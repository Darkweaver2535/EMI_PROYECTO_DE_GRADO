"""
DataTransformer - Módulo de transformación de datos
Sistema de Analítica EMI

Proporciona funciones para transformar y enriquecer datos limpios:
- Extracción de características temporales
- Cálculo de métricas de texto
- Normalización de engagement
- Clasificación preliminar de contenido

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np


class DataTransformer:
    """
    Transformador de datos para el pipeline ETL.
    
    Enriquece los datos limpios con características adicionales
    útiles para análisis.
    
    Attributes:
        config (dict): Configuración del transformador
        logger (logging.Logger): Logger para registrar operaciones
    """
    
    # Palabras clave para clasificación preliminar
    CATEGORY_KEYWORDS = {
        'Queja': [
            'queja', 'malo', 'pésimo', 'terrible', 'problema', 'deficiente',
            'reclamo', 'insatisfecho', 'decepcionado', 'peor', 'horrible',
            'no funciona', 'no sirve', 'mal servicio', 'demora', 'tardanza'
        ],
        'Sugerencia': [
            'sugerencia', 'sugiero', 'propongo', 'debería', 'mejorar',
            'podría', 'sería bueno', 'recomiendo', 'idea', 'opinión',
            'creo que', 'pienso que', 'mejor si'
        ],
        'Felicitación': [
            'felicidades', 'excelente', 'genial', 'gracias', 'felicitaciones',
            'buen trabajo', 'increíble', 'orgullo', 'orgulloso', 'éxito',
            'lo mejor', 'maravilloso', 'fantástico', 'bravo', 'aplausos'
        ],
        'Información': [
            'información', 'informamos', 'comunicamos', 'aviso', 'anuncio',
            'convocatoria', 'inscripción', 'fecha', 'horario', 'requisito',
            'recordatorio', 'importante', 'atención', 'nota'
        ],
        'Evento': [
            'evento', 'actividad', 'ceremonia', 'graduación', 'aniversario',
            'conferencia', 'seminario', 'taller', 'curso', 'capacitación',
            'inauguración', 'clausura', 'competencia', 'campeonato'
        ],
        'Académico': [
            'clases', 'examen', 'nota', 'calificación', 'docente', 'profesor',
            'materia', 'carrera', 'semestre', 'matrícula', 'beca', 'tesis',
            'prácticas', 'laboratorio', 'biblioteca'
        ]
    }
    
    # Palabras clave relacionadas con EMI
    EMI_KEYWORDS = [
        'emi', 'escuela militar', 'ingeniería', 'militar', 'cadete',
        'vicerrectorado', 'rectorado', 'comando', 'bolivia', 'la paz',
        'cochabamba', 'santa cruz', 'ualp'
    ]
    
    def __init__(self, config: dict = None):
        """
        Inicializa el transformador de datos.
        
        Args:
            config: Diccionario de configuración
        """
        self.config = config or {}
        self.logger = logging.getLogger("OSINT.DataTransformer")
        self.logger.info("DataTransformer inicializado")
    
    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica todas las transformaciones a un DataFrame.
        
        Args:
            df: DataFrame con datos limpios
            
        Returns:
            pd.DataFrame: DataFrame transformado
        """
        if df.empty:
            return df
        
        self.logger.info(f"Transformando {len(df)} registros...")
        
        # Crear copia
        df_trans = df.copy()
        
        # 1. Extraer características temporales
        df_trans = self.extract_temporal_features(df_trans)
        
        # 2. Calcular métricas de texto
        df_trans = self.calculate_text_metrics(df_trans)
        
        # 3. Normalizar engagement
        df_trans = self.normalize_engagement(df_trans)
        
        # 4. Clasificar contenido
        df_trans = self.classify_content(df_trans)
        
        # 5. Detectar menciones de EMI
        df_trans = self.detect_emi_mentions(df_trans)
        
        # 6. Análisis de sentimiento básico
        df_trans = self.basic_sentiment_analysis(df_trans)
        
        self.logger.info(f"Transformación completada: {len(df_trans)} registros")
        
        return df_trans
    
    def extract_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrae características temporales de la fecha de publicación.
        
        Características extraídas:
        - anio: Año de publicación
        - mes: Mes (1-12)
        - dia_semana: Día de la semana (0=Lunes, 6=Domingo)
        - hora: Hora del día (0-23)
        - semestre: Semestre académico (YYYY-I o YYYY-II)
        - es_horario_laboral: Si fue en horario laboral
        
        Args:
            df: DataFrame con columna 'fecha_publicacion'
            
        Returns:
            pd.DataFrame: DataFrame con características temporales
        """
        if 'fecha_publicacion' not in df.columns:
            self.logger.warning("Columna 'fecha_publicacion' no encontrada")
            return df
        
        # Asegurar que las fechas son datetime
        df['fecha_publicacion'] = pd.to_datetime(df['fecha_publicacion'], errors='coerce')
        
        # Crear columna ISO
        df['fecha_publicacion_iso'] = df['fecha_publicacion']
        
        # Extraer componentes
        df['anio'] = df['fecha_publicacion'].dt.year
        df['mes'] = df['fecha_publicacion'].dt.month
        df['dia_semana'] = df['fecha_publicacion'].dt.dayofweek  # 0=Lunes
        df['hora'] = df['fecha_publicacion'].dt.hour
        
        # Calcular semestre académico
        # En Bolivia: Semestre I = Febrero-Julio, Semestre II = Agosto-Diciembre
        df['semestre'] = df.apply(
            lambda row: self._calculate_semester(row['anio'], row['mes']),
            axis=1
        )
        
        # Determinar si es horario laboral (Lun-Vie, 8:00-18:00)
        df['es_horario_laboral'] = df.apply(
            lambda row: self._is_work_hours(row['dia_semana'], row['hora']),
            axis=1
        )
        
        return df
    
    def _calculate_semester(self, year: int, month: int) -> str:
        """
        Calcula el semestre académico.
        
        Args:
            year: Año
            month: Mes
            
        Returns:
            str: Semestre en formato 'YYYY-I' o 'YYYY-II'
        """
        if pd.isna(year) or pd.isna(month):
            return f"{datetime.now().year}-I"
        
        year = int(year)
        month = int(month)
        
        # Semestre I: Febrero - Julio
        # Semestre II: Agosto - Diciembre/Enero
        if 2 <= month <= 7:
            return f"{year}-I"
        elif month >= 8:
            return f"{year}-II"
        else:  # Enero pertenece al semestre anterior
            return f"{year-1}-II"
    
    def _is_work_hours(self, day_of_week: int, hour: int) -> bool:
        """
        Determina si es horario laboral.
        
        Args:
            day_of_week: Día de la semana (0=Lunes)
            hour: Hora del día
            
        Returns:
            bool: True si es horario laboral
        """
        if pd.isna(day_of_week) or pd.isna(hour):
            return False
        
        # Lunes a Viernes (0-4), 8:00-18:00
        is_weekday = 0 <= day_of_week <= 4
        is_work_hour = 8 <= hour < 18
        
        return is_weekday and is_work_hour
    
    def calculate_text_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula métricas de texto.
        
        Métricas:
        - longitud_texto: Cantidad de caracteres
        - cantidad_palabras: Cantidad de palabras
        
        Args:
            df: DataFrame con columna 'contenido_limpio'
            
        Returns:
            pd.DataFrame: DataFrame con métricas de texto
        """
        text_column = 'contenido_limpio' if 'contenido_limpio' in df.columns else 'contenido_original'
        
        if text_column not in df.columns:
            self.logger.warning(f"Columna '{text_column}' no encontrada")
            return df
        
        # Longitud en caracteres
        df['longitud_texto'] = df[text_column].fillna('').str.len()
        
        # Cantidad de palabras
        df['cantidad_palabras'] = df[text_column].fillna('').apply(
            lambda x: len(str(x).split())
        )
        
        return df
    
    def normalize_engagement(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza métricas de engagement a escala 0-100.
        
        El engagement se normaliza por fuente para hacer comparables
        las métricas entre diferentes plataformas.
        
        Args:
            df: DataFrame con columnas de engagement
            
        Returns:
            pd.DataFrame: DataFrame con engagement normalizado
        """
        # Calcular engagement total
        engagement_columns = ['engagement_likes', 'engagement_comments', 'engagement_shares']
        existing_columns = [col for col in engagement_columns if col in df.columns]
        
        if not existing_columns:
            df['engagement_total'] = 0
            df['engagement_normalizado'] = 0.0
            return df
        
        # Reemplazar NaN con 0
        for col in existing_columns:
            df[col] = df[col].fillna(0).astype(int)
        
        # Calcular total
        df['engagement_total'] = df[existing_columns].sum(axis=1)
        
        # Normalizar por fuente (si existe la columna tipo_fuente)
        if 'tipo_fuente' in df.columns:
            df['engagement_normalizado'] = df.groupby('tipo_fuente')['engagement_total'].transform(
                lambda x: self._min_max_normalize(x, 0, 100)
            )
        else:
            # Normalización global
            df['engagement_normalizado'] = self._min_max_normalize(
                df['engagement_total'], 0, 100
            )
        
        # Calcular ratio engagement/views si hay views
        if 'engagement_views' in df.columns:
            df['engagement_views'] = df['engagement_views'].fillna(0).astype(int)
            df['ratio_engagement'] = df.apply(
                lambda row: (row['engagement_total'] / row['engagement_views'] * 100) 
                if row['engagement_views'] > 0 else 0,
                axis=1
            )
        else:
            df['ratio_engagement'] = 0.0
        
        return df
    
    def _min_max_normalize(self, series: pd.Series, new_min: float = 0, 
                           new_max: float = 100) -> pd.Series:
        """
        Normaliza una serie usando min-max scaling.
        
        Args:
            series: Serie a normalizar
            new_min: Nuevo valor mínimo
            new_max: Nuevo valor máximo
            
        Returns:
            pd.Series: Serie normalizada
        """
        old_min = series.min()
        old_max = series.max()
        
        if old_max == old_min:
            return pd.Series([new_min] * len(series), index=series.index)
        
        normalized = (series - old_min) / (old_max - old_min)
        scaled = normalized * (new_max - new_min) + new_min
        
        return scaled.round(2)
    
    def classify_content(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clasifica el contenido en categorías preliminares.
        
        Categorías:
        - Queja
        - Sugerencia
        - Felicitación
        - Información
        - Evento
        - Académico
        - General (default)
        
        Args:
            df: DataFrame con columna de texto
            
        Returns:
            pd.DataFrame: DataFrame con categoría preliminar
        """
        text_column = 'contenido_limpio' if 'contenido_limpio' in df.columns else 'contenido_original'
        
        if text_column not in df.columns:
            df['categoria_preliminar'] = 'General'
            return df
        
        df['categoria_preliminar'] = df[text_column].apply(self._classify_text)
        
        return df
    
    def _classify_text(self, text: str) -> str:
        """
        Clasifica un texto individual.
        
        Args:
            text: Texto a clasificar
            
        Returns:
            str: Categoría asignada
        """
        if not text or pd.isna(text):
            return 'General'
        
        text_lower = str(text).lower()
        
        # Buscar categoría con más coincidencias
        category_scores = {}
        
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            # Retornar categoría con mayor puntuación
            return max(category_scores, key=category_scores.get)
        
        return 'General'
    
    def detect_emi_mentions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detecta menciones directas de EMI en el contenido.
        
        Args:
            df: DataFrame con columna de texto
            
        Returns:
            pd.DataFrame: DataFrame con flag de mención EMI
        """
        text_column = 'contenido_limpio' if 'contenido_limpio' in df.columns else 'contenido_original'
        
        if text_column not in df.columns:
            df['contiene_mencion_emi'] = False
            return df
        
        df['contiene_mencion_emi'] = df[text_column].apply(
            lambda x: self._contains_emi_mention(str(x)) if x else False
        )
        
        return df
    
    def _contains_emi_mention(self, text: str) -> bool:
        """
        Verifica si un texto menciona EMI.
        
        Args:
            text: Texto a verificar
            
        Returns:
            bool: True si menciona EMI
        """
        text_lower = text.lower()
        
        for keyword in self.EMI_KEYWORDS:
            if keyword in text_lower:
                return True
        
        return False
    
    def basic_sentiment_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza un análisis de sentimiento básico basado en palabras clave.
        
        Este es un análisis simple; para Sprint 3 se implementará
        análisis más sofisticado con NLP.
        
        Args:
            df: DataFrame con columna de texto
            
        Returns:
            pd.DataFrame: DataFrame con sentimiento básico
        """
        text_column = 'contenido_limpio' if 'contenido_limpio' in df.columns else 'contenido_original'
        
        if text_column not in df.columns:
            df['sentimiento_basico'] = 'neutral'
            return df
        
        # Palabras positivas y negativas
        positive_words = [
            'excelente', 'bueno', 'genial', 'feliz', 'gracias', 'mejor',
            'increíble', 'éxito', 'orgullo', 'felicidades', 'logro',
            'satisfecho', 'contento', 'alegría', 'maravilloso'
        ]
        
        negative_words = [
            'malo', 'pésimo', 'terrible', 'problema', 'queja', 'molesto',
            'decepcionado', 'insatisfecho', 'peor', 'fracaso', 'falla',
            'deficiente', 'horrible', 'triste', 'enojado'
        ]
        
        def analyze_sentiment(text):
            if not text or pd.isna(text):
                return 'neutral'
            
            text_lower = str(text).lower()
            
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                return 'positivo'
            elif neg_count > pos_count:
                return 'negativo'
            else:
                return 'neutral'
        
        df['sentimiento_basico'] = df[text_column].apply(analyze_sentiment)
        
        return df
    
    def get_transformation_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Genera un resumen de las transformaciones aplicadas.
        
        Args:
            df: DataFrame transformado
            
        Returns:
            Dict: Resumen de transformaciones
        """
        summary = {
            'total_registros': len(df),
            'categorias': {},
            'sentimientos': {},
            'temporales': {},
            'engagement': {}
        }
        
        # Distribución de categorías
        if 'categoria_preliminar' in df.columns:
            summary['categorias'] = df['categoria_preliminar'].value_counts().to_dict()
        
        # Distribución de sentimientos
        if 'sentimiento_basico' in df.columns:
            summary['sentimientos'] = df['sentimiento_basico'].value_counts().to_dict()
        
        # Estadísticas temporales
        if 'semestre' in df.columns:
            summary['temporales']['por_semestre'] = df['semestre'].value_counts().to_dict()
        
        if 'dia_semana' in df.columns:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            dist_dias = df['dia_semana'].value_counts().sort_index()
            summary['temporales']['por_dia'] = {
                dias[i]: int(count) for i, count in dist_dias.items() if i < 7
            }
        
        # Estadísticas de engagement
        if 'engagement_normalizado' in df.columns:
            summary['engagement'] = {
                'promedio': round(df['engagement_normalizado'].mean(), 2),
                'maximo': round(df['engagement_normalizado'].max(), 2),
                'minimo': round(df['engagement_normalizado'].min(), 2)
            }
        
        # Menciones EMI
        if 'contiene_mencion_emi' in df.columns:
            summary['menciones_emi'] = int(df['contiene_mencion_emi'].sum())
        
        return summary


if __name__ == "__main__":
    # Test del transformador
    logging.basicConfig(level=logging.INFO)
    
    transformer = DataTransformer()
    
    # Crear DataFrame de prueba
    test_data = pd.DataFrame({
        'contenido_limpio': [
            'Excelente evento de la EMI, felicidades a todos los organizadores',
            'Queja por la demora en los trámites de inscripción',
            'Información sobre el nuevo semestre académico 2025',
            'Sugerencia para mejorar las instalaciones del laboratorio',
            'Gran ceremonia de graduación de los cadetes'
        ],
        'fecha_publicacion': [
            datetime(2025, 3, 15, 10, 30),
            datetime(2025, 4, 20, 14, 45),
            datetime(2025, 8, 1, 9, 0),
            datetime(2025, 9, 10, 16, 30),
            datetime(2025, 12, 5, 11, 0)
        ],
        'engagement_likes': [150, 25, 80, 45, 300],
        'engagement_comments': [30, 15, 10, 8, 50],
        'engagement_shares': [20, 5, 15, 3, 40]
    })
    
    # Aplicar transformaciones
    df_transformed = transformer.transform_dataframe(test_data)
    
    print("=== Test de DataTransformer ===\n")
    print("Columnas generadas:")
    print(df_transformed.columns.tolist())
    
    print("\nMuestra de datos transformados:")
    print(df_transformed[['contenido_limpio', 'semestre', 'categoria_preliminar', 
                          'sentimiento_basico', 'engagement_normalizado']].to_string())
    
    print("\nResumen:")
    summary = transformer.get_transformation_summary(df_transformed)
    for key, value in summary.items():
        print(f"  {key}: {value}")
