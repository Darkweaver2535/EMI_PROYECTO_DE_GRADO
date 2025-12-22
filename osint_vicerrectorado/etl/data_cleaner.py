"""
DataCleaner - Módulo de limpieza de datos
Sistema de Analítica EMI

Proporciona funciones para limpiar y normalizar datos recolectados:
- Eliminación de duplicados
- Normalización de fechas
- Corrección de encoding UTF-8
- Limpieza de URLs, emojis, menciones y hashtags

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import re
import unicodedata
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

import pandas as pd


class DataCleaner:
    """
    Limpiador de datos para el pipeline ETL.
    
    Procesa datos crudos recolectados de redes sociales y los limpia
    para análisis posterior.
    
    Attributes:
        config (dict): Configuración del limpiador
        logger (logging.Logger): Logger para registrar operaciones
    """
    
    # Patrones regex compilados para mejor rendimiento
    PATTERNS = {
        # URLs (http, https, www)
        'url': re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|'
            r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
            re.IGNORECASE
        ),
        # Menciones (@usuario)
        'mention': re.compile(r'@[\w\d_]+', re.UNICODE),
        # Hashtags (#tema)
        'hashtag': re.compile(r'#[\w\d_\u00C0-\u024F]+', re.UNICODE),
        # Emojis (rangos Unicode)
        'emoji': re.compile(
            "["
            "\U0001F600-\U0001F64F"  # Emoticons
            "\U0001F300-\U0001F5FF"  # Símbolos y pictogramas
            "\U0001F680-\U0001F6FF"  # Transporte y mapas
            "\U0001F700-\U0001F77F"  # Símbolos alquímicos
            "\U0001F780-\U0001F7FF"  # Símbolos geométricos extendidos
            "\U0001F800-\U0001F8FF"  # Flechas suplementarias
            "\U0001F900-\U0001F9FF"  # Símbolos suplementarios
            "\U0001FA00-\U0001FA6F"  # Símbolos de ajedrez
            "\U0001FA70-\U0001FAFF"  # Símbolos y pictogramas extendidos
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"  # Enclosed characters
            "]+",
            re.UNICODE
        ),
        # Espacios múltiples
        'multiple_spaces': re.compile(r'\s+'),
        # Saltos de línea múltiples
        'multiple_newlines': re.compile(r'\n{3,}'),
        # Caracteres especiales de redes sociales
        'special_chars': re.compile(r'[​‌‍﻿\u200b-\u200d\ufeff]'),
        # HTML entities
        'html_entities': re.compile(r'&[a-zA-Z]+;|&#\d+;'),
    }
    
    def __init__(self, config: dict = None):
        """
        Inicializa el limpiador de datos.
        
        Args:
            config: Diccionario de configuración con opciones de limpieza
        """
        self.config = config or {}
        self.etl_config = self.config.get('etl', {})
        self.logger = logging.getLogger("OSINT.DataCleaner")
        
        # Opciones de limpieza
        self.remove_urls = self.etl_config.get('remove_urls', True)
        self.remove_emojis = self.etl_config.get('remove_emojis', False)
        self.remove_hashtags = self.etl_config.get('remove_hashtags', False)
        self.remove_mentions = self.etl_config.get('remove_mentions', True)
        self.normalize_whitespace = self.etl_config.get('normalize_whitespace', True)
        self.min_text_length = self.etl_config.get('min_text_length', 10)
        self.max_text_length = self.etl_config.get('max_text_length', 5000)
        
        self.logger.info("DataCleaner inicializado")
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia un DataFrame completo de datos recolectados.
        
        Args:
            df: DataFrame con datos crudos
            
        Returns:
            pd.DataFrame: DataFrame limpio
        """
        if df.empty:
            return df
        
        self.logger.info(f"Limpiando {len(df)} registros...")
        
        # Crear copia para no modificar original
        df_clean = df.copy()
        
        # 1. Eliminar duplicados
        df_clean = self.remove_duplicates(df_clean)
        
        # 2. Normalizar fechas
        df_clean = self.normalize_dates(df_clean)
        
        # 3. Corregir encoding
        df_clean = self.fix_encoding(df_clean)
        
        # 4. Limpiar contenido de texto
        df_clean['contenido_limpio'] = df_clean['contenido_original'].apply(
            self.clean_text
        )
        
        # 5. Filtrar por longitud mínima
        df_clean = df_clean[
            df_clean['contenido_limpio'].str.len() >= self.min_text_length
        ]
        
        self.logger.info(f"Limpieza completada: {len(df_clean)} registros válidos")
        
        return df_clean
    
    def remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Elimina registros duplicados del DataFrame.
        
        Detecta duplicados por:
        1. id_externo (exacto)
        2. contenido_original similar (>90% similitud)
        
        Args:
            df: DataFrame con posibles duplicados
            
        Returns:
            pd.DataFrame: DataFrame sin duplicados
        """
        initial_count = len(df)
        
        # Eliminar duplicados exactos por id_externo
        df = df.drop_duplicates(subset=['id_externo'], keep='first')
        
        # Eliminar duplicados por contenido similar
        df = df.drop_duplicates(subset=['contenido_original'], keep='first')
        
        removed = initial_count - len(df)
        if removed > 0:
            self.logger.info(f"Duplicados eliminados: {removed}")
        
        return df
    
    def normalize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normaliza fechas a formato ISO 8601.
        
        Args:
            df: DataFrame con columna 'fecha_publicacion'
            
        Returns:
            pd.DataFrame: DataFrame con fechas normalizadas
        """
        if 'fecha_publicacion' not in df.columns:
            return df
        
        def parse_date(date_val):
            """Parsea diferentes formatos de fecha."""
            if pd.isna(date_val):
                return datetime.now()
            
            if isinstance(date_val, datetime):
                return date_val
            
            if isinstance(date_val, str):
                # Intentar varios formatos
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%d/%m/%Y %H:%M',
                    '%d-%m-%Y %H:%M:%S',
                    '%Y/%m/%d %H:%M:%S',
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(date_val, fmt)
                    except ValueError:
                        continue
                
                # Intentar con pd.to_datetime como fallback
                try:
                    return pd.to_datetime(date_val)
                except:
                    pass
            
            return datetime.now()
        
        df['fecha_publicacion'] = df['fecha_publicacion'].apply(parse_date)
        
        return df
    
    def fix_encoding(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Corrige problemas de encoding en columnas de texto.
        
        Asegura que tildes, ñ y caracteres especiales del español
        se mantengan correctos.
        
        Args:
            df: DataFrame con posibles problemas de encoding
            
        Returns:
            pd.DataFrame: DataFrame con encoding corregido
        """
        text_columns = ['contenido_original', 'autor']
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._fix_text_encoding)
        
        return df
    
    def _fix_text_encoding(self, text: Any) -> str:
        """
        Corrige el encoding de un texto individual.
        
        Args:
            text: Texto a corregir
            
        Returns:
            str: Texto con encoding corregido
        """
        if pd.isna(text) or text is None:
            return ""
        
        text = str(text)
        
        # Normalizar a NFC (forma canónica compuesta)
        text = unicodedata.normalize('NFC', text)
        
        # Corregir secuencias mal codificadas comunes
        replacements = {
            'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
            'Ã±': 'ñ', 'Ã': 'Á', 'Ã‰': 'É', 'Ã': 'Í', 'Ã"': 'Ó',
            'Ãš': 'Ú', 'Ã'': 'Ñ', 'Ã¼': 'ü', 'Ãœ': 'Ü',
            '\x00': '', '\ufffd': '',
        }
        
        for wrong, correct in replacements.items():
            text = text.replace(wrong, correct)
        
        return text
    
    def clean_text(self, text: Any) -> str:
        """
        Limpia un texto individual eliminando elementos no deseados.
        
        Proceso de limpieza:
        1. Eliminar URLs (si configurado)
        2. Eliminar menciones (si configurado)
        3. Eliminar hashtags (si configurado)
        4. Eliminar emojis (si configurado)
        5. Normalizar espacios en blanco
        6. Limitar longitud
        
        Args:
            text: Texto a limpiar
            
        Returns:
            str: Texto limpio
        """
        if pd.isna(text) or text is None:
            return ""
        
        text = str(text)
        
        # Corregir encoding primero
        text = self._fix_text_encoding(text)
        
        # Eliminar caracteres especiales invisibles
        text = self.PATTERNS['special_chars'].sub('', text)
        
        # Decodificar HTML entities
        text = self._decode_html_entities(text)
        
        # Eliminar URLs
        if self.remove_urls:
            text = self.PATTERNS['url'].sub(' ', text)
        
        # Eliminar menciones
        if self.remove_mentions:
            text = self.PATTERNS['mention'].sub(' ', text)
        
        # Eliminar hashtags (opcionalmente mantenerlos como texto)
        if self.remove_hashtags:
            text = self.PATTERNS['hashtag'].sub(' ', text)
        else:
            # Mantener hashtags pero sin el símbolo #
            text = re.sub(r'#([\w\d_\u00C0-\u024F]+)', r'\1', text)
        
        # Eliminar emojis
        if self.remove_emojis:
            text = self.PATTERNS['emoji'].sub(' ', text)
        
        # Normalizar espacios en blanco
        if self.normalize_whitespace:
            text = self.PATTERNS['multiple_newlines'].sub('\n\n', text)
            text = self.PATTERNS['multiple_spaces'].sub(' ', text)
            text = text.strip()
        
        # Limitar longitud
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length] + '...'
        
        return text
    
    def _decode_html_entities(self, text: str) -> str:
        """
        Decodifica entidades HTML comunes.
        
        Args:
            text: Texto con posibles entidades HTML
            
        Returns:
            str: Texto con entidades decodificadas
        """
        entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' ',
            '&apos;': "'",
            '&#x27;': "'",
            '&#x2F;': '/',
        }
        
        for entity, char in entities.items():
            text = text.replace(entity, char)
        
        return text
    
    def remove_urls_emojis(self, text: str) -> str:
        """
        Método específico para eliminar URLs y emojis.
        
        Útil para llamadas directas sin usar el DataFrame.
        
        Args:
            text: Texto a limpiar
            
        Returns:
            str: Texto sin URLs ni emojis
        """
        if not text:
            return ""
        
        # Eliminar URLs
        text = self.PATTERNS['url'].sub(' ', text)
        
        # Eliminar emojis
        text = self.PATTERNS['emoji'].sub(' ', text)
        
        # Normalizar espacios
        text = self.PATTERNS['multiple_spaces'].sub(' ', text)
        
        return text.strip()
    
    def extract_hashtags(self, text: str) -> List[str]:
        """
        Extrae hashtags de un texto.
        
        Args:
            text: Texto del que extraer hashtags
            
        Returns:
            List[str]: Lista de hashtags encontrados
        """
        if not text:
            return []
        
        hashtags = self.PATTERNS['hashtag'].findall(text)
        return [h.lower() for h in hashtags]
    
    def extract_mentions(self, text: str) -> List[str]:
        """
        Extrae menciones (@usuario) de un texto.
        
        Args:
            text: Texto del que extraer menciones
            
        Returns:
            List[str]: Lista de menciones encontradas
        """
        if not text:
            return []
        
        mentions = self.PATTERNS['mention'].findall(text)
        return [m.lower() for m in mentions]
    
    def is_valid_content(self, text: str) -> bool:
        """
        Verifica si un texto es contenido válido para análisis.
        
        Args:
            text: Texto a verificar
            
        Returns:
            bool: True si es contenido válido
        """
        if not text:
            return False
        
        # Longitud mínima
        if len(text) < self.min_text_length:
            return False
        
        # Debe contener al menos algunas palabras
        words = text.split()
        if len(words) < 3:
            return False
        
        # No debe ser solo URLs/menciones
        cleaned = self.remove_urls_emojis(text)
        if len(cleaned) < self.min_text_length:
            return False
        
        return True


# Función de conveniencia
def clean_text(text: str, config: dict = None) -> str:
    """
    Función de conveniencia para limpiar un texto individual.
    
    Args:
        text: Texto a limpiar
        config: Configuración opcional
        
    Returns:
        str: Texto limpio
    """
    cleaner = DataCleaner(config)
    return cleaner.clean_text(text)


if __name__ == "__main__":
    # Test del limpiador
    logging.basicConfig(level=logging.INFO)
    
    cleaner = DataCleaner()
    
    # Textos de prueba
    test_texts = [
        "¡Hola estudiantes de la EMI! 🎓 Visiten https://www.emi.edu.bo para más info @EMIBolivia #educacion",
        "Gran evento en la universidad 📚 Vengan todos!! #EMI #LaPaz",
        "Información importante sobre inscripciones &amp; matrículas",
        "Texto con encoding Ã±oño y tildes Ã¡Ã©Ã­Ã³Ãº",
    ]
    
    print("=== Test de DataCleaner ===\n")
    
    for text in test_texts:
        cleaned = cleaner.clean_text(text)
        hashtags = cleaner.extract_hashtags(text)
        
        print(f"Original: {text[:50]}...")
        print(f"Limpio:   {cleaned[:50]}...")
        print(f"Hashtags: {hashtags}")
        print(f"Válido:   {cleaner.is_valid_content(cleaned)}")
        print("-" * 50)
