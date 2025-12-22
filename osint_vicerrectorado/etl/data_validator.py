"""
DataValidator - Módulo de validación de datos
Sistema de Analítica EMI

Proporciona funciones para validar datos antes de guardarlos:
- Validación de campos obligatorios
- Validación de tipos de datos
- Validación de rangos y formatos
- Generación de reportes de validación

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import logging

import pandas as pd


class DataValidator:
    """
    Validador de datos para el pipeline ETL.
    
    Asegura que los datos procesados cumplan con los requisitos
    antes de ser guardados en la base de datos.
    
    Attributes:
        config (dict): Configuración del validador
        logger (logging.Logger): Logger para registrar operaciones
        validation_errors (List[Dict]): Errores de validación encontrados
    """
    
    # Esquema de validación para datos procesados
    SCHEMA = {
        'id_dato_original': {
            'type': int,
            'required': True,
            'min': 1
        },
        'contenido_limpio': {
            'type': str,
            'required': True,
            'min_length': 5,
            'max_length': 10000
        },
        'fecha_publicacion_iso': {
            'type': datetime,
            'required': True
        },
        'longitud_texto': {
            'type': int,
            'required': False,
            'min': 0
        },
        'cantidad_palabras': {
            'type': int,
            'required': False,
            'min': 0
        },
        'mes': {
            'type': int,
            'required': False,
            'min': 1,
            'max': 12
        },
        'dia_semana': {
            'type': int,
            'required': False,
            'min': 0,
            'max': 6
        },
        'hora': {
            'type': int,
            'required': False,
            'min': 0,
            'max': 23
        },
        'engagement_total': {
            'type': int,
            'required': False,
            'min': 0
        },
        'engagement_normalizado': {
            'type': float,
            'required': False,
            'min': 0,
            'max': 100
        },
        'categoria_preliminar': {
            'type': str,
            'required': False,
            'allowed_values': ['Queja', 'Sugerencia', 'Felicitación', 
                              'Información', 'Evento', 'Académico', 'General']
        },
        'sentimiento_basico': {
            'type': str,
            'required': False,
            'allowed_values': ['positivo', 'negativo', 'neutral']
        }
    }
    
    def __init__(self, config: dict = None):
        """
        Inicializa el validador de datos.
        
        Args:
            config: Diccionario de configuración
        """
        self.config = config or {}
        self.logger = logging.getLogger("OSINT.DataValidator")
        self.validation_errors: List[Dict] = []
        
        self.logger.info("DataValidator inicializado")
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Valida un DataFrame completo.
        
        Args:
            df: DataFrame a validar
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (registros válidos, registros inválidos)
        """
        if df.empty:
            return df, pd.DataFrame()
        
        self.logger.info(f"Validando {len(df)} registros...")
        self.validation_errors = []
        
        valid_mask = pd.Series([True] * len(df), index=df.index)
        
        for idx, row in df.iterrows():
            is_valid, errors = self._validate_row(row, idx)
            if not is_valid:
                valid_mask[idx] = False
                self.validation_errors.extend(errors)
        
        valid_df = df[valid_mask].copy()
        invalid_df = df[~valid_mask].copy()
        
        self.logger.info(
            f"Validación completada: {len(valid_df)} válidos, {len(invalid_df)} inválidos"
        )
        
        return valid_df, invalid_df
    
    def _validate_row(self, row: pd.Series, row_idx: Any) -> Tuple[bool, List[Dict]]:
        """
        Valida una fila individual.
        
        Args:
            row: Fila a validar
            row_idx: Índice de la fila
            
        Returns:
            Tuple[bool, List[Dict]]: (es_válido, lista_de_errores)
        """
        errors = []
        is_valid = True
        
        for field, rules in self.SCHEMA.items():
            if field not in row.index:
                if rules.get('required', False):
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': 'Campo requerido no encontrado',
                        'value': None
                    })
                    is_valid = False
                continue
            
            value = row[field]
            field_valid, field_errors = self._validate_field(field, value, rules, row_idx)
            
            if not field_valid:
                is_valid = False
                errors.extend(field_errors)
        
        return is_valid, errors
    
    def _validate_field(self, field: str, value: Any, 
                        rules: Dict, row_idx: Any) -> Tuple[bool, List[Dict]]:
        """
        Valida un campo individual según sus reglas.
        
        Args:
            field: Nombre del campo
            value: Valor del campo
            rules: Reglas de validación
            row_idx: Índice de la fila
            
        Returns:
            Tuple[bool, List[Dict]]: (es_válido, lista_de_errores)
        """
        errors = []
        is_valid = True
        
        # Verificar si es requerido y está vacío
        if rules.get('required', False):
            if pd.isna(value) or value is None or (isinstance(value, str) and not value.strip()):
                errors.append({
                    'row_index': row_idx,
                    'field': field,
                    'error': 'Campo requerido está vacío',
                    'value': value
                })
                return False, errors
        
        # Si no es requerido y está vacío, es válido
        if pd.isna(value) or value is None:
            return True, []
        
        # Validar tipo
        expected_type = rules.get('type')
        if expected_type:
            if expected_type == int:
                if not self._is_int(value):
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Tipo incorrecto, esperado int',
                        'value': value
                    })
                    is_valid = False
            elif expected_type == float:
                if not self._is_numeric(value):
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Tipo incorrecto, esperado float',
                        'value': value
                    })
                    is_valid = False
            elif expected_type == str:
                if not isinstance(value, str):
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Tipo incorrecto, esperado str',
                        'value': value
                    })
                    is_valid = False
            elif expected_type == datetime:
                if not isinstance(value, (datetime, pd.Timestamp)):
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Tipo incorrecto, esperado datetime',
                        'value': value
                    })
                    is_valid = False
        
        # Validar rango numérico
        if is_valid and self._is_numeric(value):
            if 'min' in rules:
                if float(value) < rules['min']:
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Valor menor al mínimo permitido ({rules["min"]})',
                        'value': value
                    })
                    is_valid = False
            
            if 'max' in rules:
                if float(value) > rules['max']:
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Valor mayor al máximo permitido ({rules["max"]})',
                        'value': value
                    })
                    is_valid = False
        
        # Validar longitud de texto
        if is_valid and isinstance(value, str):
            if 'min_length' in rules:
                if len(value) < rules['min_length']:
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Texto muy corto (mínimo {rules["min_length"]} caracteres)',
                        'value': f'{value[:50]}...' if len(value) > 50 else value
                    })
                    is_valid = False
            
            if 'max_length' in rules:
                if len(value) > rules['max_length']:
                    errors.append({
                        'row_index': row_idx,
                        'field': field,
                        'error': f'Texto muy largo (máximo {rules["max_length"]} caracteres)',
                        'value': f'{value[:50]}...'
                    })
                    is_valid = False
        
        # Validar valores permitidos
        if is_valid and 'allowed_values' in rules:
            if value not in rules['allowed_values']:
                errors.append({
                    'row_index': row_idx,
                    'field': field,
                    'error': f'Valor no permitido',
                    'value': value,
                    'allowed': rules['allowed_values']
                })
                is_valid = False
        
        return is_valid, errors
    
    def _is_int(self, value: Any) -> bool:
        """Verifica si un valor es entero."""
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, np.integer)):
            return True
        if isinstance(value, float) and value.is_integer():
            return True
        try:
            int(value)
            return float(value) == int(value)
        except (ValueError, TypeError):
            return False
    
    def _is_numeric(self, value: Any) -> bool:
        """Verifica si un valor es numérico."""
        if isinstance(value, bool):
            return False
        if isinstance(value, (int, float, np.integer, np.floating)):
            return True
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def validate_required_columns(self, df: pd.DataFrame, 
                                   required: List[str]) -> Tuple[bool, List[str]]:
        """
        Verifica que el DataFrame tenga las columnas requeridas.
        
        Args:
            df: DataFrame a verificar
            required: Lista de columnas requeridas
            
        Returns:
            Tuple[bool, List[str]]: (todas_presentes, columnas_faltantes)
        """
        missing = [col for col in required if col not in df.columns]
        return len(missing) == 0, missing
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        Genera un reporte de los errores de validación.
        
        Returns:
            Dict: Reporte de validación
        """
        if not self.validation_errors:
            return {
                'total_errors': 0,
                'errors_by_field': {},
                'errors_by_type': {},
                'sample_errors': []
            }
        
        # Agrupar por campo
        errors_by_field = {}
        for error in self.validation_errors:
            field = error['field']
            if field not in errors_by_field:
                errors_by_field[field] = 0
            errors_by_field[field] += 1
        
        # Agrupar por tipo de error
        errors_by_type = {}
        for error in self.validation_errors:
            error_type = error['error']
            if error_type not in errors_by_type:
                errors_by_type[error_type] = 0
            errors_by_type[error_type] += 1
        
        return {
            'total_errors': len(self.validation_errors),
            'errors_by_field': errors_by_field,
            'errors_by_type': errors_by_type,
            'sample_errors': self.validation_errors[:10]  # Primeros 10 errores
        }
    
    def validate_for_database(self, data: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Valida una lista de diccionarios para inserción en BD.
        
        Args:
            data: Lista de diccionarios con datos
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (datos_válidos, datos_inválidos)
        """
        valid_data = []
        invalid_data = []
        
        for item in data:
            is_valid = True
            
            # Verificar campos obligatorios mínimos
            if not item.get('id_dato_original'):
                is_valid = False
            
            if not item.get('contenido_limpio'):
                is_valid = False
            
            if not item.get('fecha_publicacion_iso'):
                is_valid = False
            
            if is_valid:
                valid_data.append(item)
            else:
                invalid_data.append(item)
        
        return valid_data, invalid_data


# Importar numpy para validación de tipos
import numpy as np


if __name__ == "__main__":
    # Test del validador
    logging.basicConfig(level=logging.INFO)
    
    validator = DataValidator()
    
    # Crear DataFrame de prueba con algunos datos inválidos
    test_data = pd.DataFrame({
        'id_dato_original': [1, 2, 3, None, 5],  # None es inválido
        'contenido_limpio': [
            'Este es un texto válido de prueba',
            'ab',  # Muy corto
            'Otro texto válido para validación',
            'Texto cuatro',
            ''  # Vacío
        ],
        'fecha_publicacion_iso': [
            datetime.now(),
            datetime.now(),
            'no es fecha',  # Tipo incorrecto
            datetime.now(),
            datetime.now()
        ],
        'mes': [1, 15, 6, 8, 12],  # 15 es inválido
        'engagement_normalizado': [50.0, -10.0, 80.0, 150.0, 30.0]  # -10 y 150 inválidos
    })
    
    print("=== Test de DataValidator ===\n")
    print(f"Registros de entrada: {len(test_data)}")
    
    valid_df, invalid_df = validator.validate_dataframe(test_data)
    
    print(f"Registros válidos: {len(valid_df)}")
    print(f"Registros inválidos: {len(invalid_df)}")
    
    report = validator.get_validation_report()
    print(f"\nTotal de errores: {report['total_errors']}")
    print(f"Errores por campo: {report['errors_by_field']}")
