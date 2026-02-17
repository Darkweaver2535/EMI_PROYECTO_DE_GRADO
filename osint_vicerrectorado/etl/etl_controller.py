"""
ETLController - Controlador del pipeline ETL
Sistema de Analítica EMI

Orquesta el proceso completo de ETL:
1. Extract: Obtener datos no procesados de la BD
2. Transform: Aplicar limpieza y transformaciones
3. Load: Guardar datos procesados en la BD

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging

import pandas as pd

from etl.data_cleaner import DataCleaner
from etl.data_transformer import DataTransformer
from etl.data_validator import DataValidator
from database.db_writer import DatabaseWriter


class ETLController:
    """
    Controlador principal del pipeline ETL.
    
    Coordina los módulos de limpieza, transformación y validación
    para procesar datos recolectados y prepararlos para análisis.
    
    Attributes:
        config (dict): Configuración del sistema
        db (DatabaseWriter): Gestor de base de datos
        cleaner (DataCleaner): Módulo de limpieza
        transformer (DataTransformer): Módulo de transformación
        validator (DataValidator): Módulo de validación
        logger (logging.Logger): Logger para registrar operaciones
    """
    
    def __init__(self, config: dict = None, db: DatabaseWriter = None):
        """
        Inicializa el controlador ETL.
        
        Args:
            config: Diccionario de configuración
            db: Instancia de DatabaseWriter (opcional, se crea si no se proporciona)
        """
        self.config = config or {}
        self.logger = logging.getLogger("OSINT.ETLController")
        
        # Inicializar conexión a BD
        self.db = db or DatabaseWriter(config=config)
        
        # Inicializar módulos ETL
        self.cleaner = DataCleaner(config)
        self.transformer = DataTransformer(config)
        self.validator = DataValidator(config)
        
        # Configuración ETL
        self.batch_size = self.config.get('etl', {}).get('batch_size', 100)
        
        # Estadísticas de la ejecución
        self.stats = {
            'total_extracted': 0,
            'total_cleaned': 0,
            'total_transformed': 0,
            'total_validated': 0,
            'total_loaded': 0,
            'total_errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.logger.info("ETLController inicializado")
    
    def run(self, limit: int = None) -> Dict[str, Any]:
        """
        Ejecuta el pipeline ETL completo.
        
        Proceso:
        1. Extrae datos no procesados de la BD
        2. Aplica limpieza con DataCleaner
        3. Aplica transformaciones con DataTransformer
        4. Valida con DataValidator
        5. Guarda datos procesados en BD
        6. Marca datos originales como procesados
        
        Args:
            limit: Número máximo de registros a procesar (None = todos)
            
        Returns:
            Dict: Estadísticas y resultados del proceso
        """
        self.stats['start_time'] = datetime.now()
        log_id = self.db.log_execution('etl')
        
        try:
            self.logger.info(f"Iniciando pipeline ETL (batch_size={self.batch_size})")
            
            # 1. EXTRACT - Obtener datos no procesados
            raw_data = self._extract(limit)
            
            if raw_data.empty:
                self.logger.info("No hay datos pendientes de procesar")
                self._complete_log(log_id, True, 0, 0, 0)
                return self._get_results()
            
            self.stats['total_extracted'] = len(raw_data)
            self.logger.info(f"Extraídos {len(raw_data)} registros para procesar")
            
            # 2. CLEAN - Limpiar datos
            cleaned_data = self._clean(raw_data)
            self.stats['total_cleaned'] = len(cleaned_data)
            
            if cleaned_data.empty:
                self.logger.warning("Todos los registros fueron eliminados en limpieza")
                self._complete_log(log_id, True, len(raw_data), 0, len(raw_data))
                return self._get_results()
            
            # 3. TRANSFORM - Transformar datos
            transformed_data = self._transform(cleaned_data)
            self.stats['total_transformed'] = len(transformed_data)
            
            # 4. VALIDATE - Validar datos
            valid_data, invalid_data = self._validate(transformed_data)
            self.stats['total_validated'] = len(valid_data)
            self.stats['total_errors'] = len(invalid_data)
            
            if valid_data.empty:
                self.logger.warning("Ningún registro pasó la validación")
                self._complete_log(log_id, False, len(raw_data), 0, len(raw_data))
                return self._get_results()
            
            # 5. LOAD - Guardar en BD
            loaded_count = self._load(valid_data)
            self.stats['total_loaded'] = loaded_count
            
            self.stats['end_time'] = datetime.now()
            
            # Log de éxito
            self._complete_log(
                log_id, True, 
                len(raw_data), 
                loaded_count, 
                len(raw_data) - loaded_count
            )
            
            self.logger.info(
                f"Pipeline ETL completado: {loaded_count}/{len(raw_data)} registros procesados"
            )
            
            return self._get_results()
            
        except Exception as e:
            self.logger.error(f"Error en pipeline ETL: {e}")
            self.stats['end_time'] = datetime.now()
            self._complete_log(log_id, False, 0, 0, 0, str(e))
            raise
    
    def _extract(self, limit: int = None) -> pd.DataFrame:
        """
        Extrae datos no procesados de la base de datos.
        
        Args:
            limit: Número máximo de registros
            
        Returns:
            pd.DataFrame: Datos crudos
        """
        self.logger.info("EXTRACT: Obteniendo datos no procesados...")
        
        batch_limit = limit or self.batch_size
        raw_data = self.db.get_unprocessed_data(limit=batch_limit)
        
        if not raw_data:
            return pd.DataFrame()
        
        return pd.DataFrame(raw_data)
    
    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica limpieza a los datos.
        
        Args:
            df: DataFrame con datos crudos
            
        Returns:
            pd.DataFrame: Datos limpios
        """
        self.logger.info("CLEAN: Aplicando limpieza de datos...")
        
        cleaned_df = self.cleaner.clean_dataframe(df)
        
        self.logger.info(
            f"Limpieza: {len(df)} -> {len(cleaned_df)} registros "
            f"({len(df) - len(cleaned_df)} eliminados)"
        )
        
        return cleaned_df
    
    def _transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica transformaciones a los datos limpios.
        
        Args:
            df: DataFrame con datos limpios
            
        Returns:
            pd.DataFrame: Datos transformados
        """
        self.logger.info("TRANSFORM: Aplicando transformaciones...")
        
        transformed_df = self.transformer.transform_dataframe(df)
        
        # Log de resumen
        summary = self.transformer.get_transformation_summary(transformed_df)
        self.logger.info(f"Transformación completada. Categorías: {summary.get('categorias', {})}")
        
        # Renombrar id_dato a id_dato_original para que coincida con el esquema de base de datos
        if 'id_dato' in transformed_df.columns:
            transformed_df = transformed_df.rename(columns={'id_dato': 'id_dato_original'})
        
        return transformed_df
    
    def _validate(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Valida los datos transformados.
        
        Args:
            df: DataFrame con datos transformados
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (válidos, inválidos)
        """
        self.logger.info("VALIDATE: Validando datos...")
        
        valid_df, invalid_df = self.validator.validate_dataframe(df)
        
        if len(invalid_df) > 0:
            report = self.validator.get_validation_report()
            self.logger.warning(
                f"Validación: {len(valid_df)} válidos, {len(invalid_df)} inválidos. "
                f"Errores por campo: {report.get('errors_by_field', {})}"
            )
        
        return valid_df, invalid_df
    
    def _load(self, df: pd.DataFrame) -> int:
        """
        Carga los datos validados en la base de datos.
        
        Args:
            df: DataFrame con datos válidos
            
        Returns:
            int: Cantidad de registros cargados
        """
        self.logger.info("LOAD: Guardando datos procesados...")
        
        # Preparar datos para inserción
        processed_records = self._prepare_for_database(df)
        
        # Guardar en BD
        inserted, errors = self.db.save_processed_data(processed_records)
        
        if errors > 0:
            self.logger.warning(f"LOAD: {inserted} insertados, {errors} errores")
        else:
            self.logger.info(f"LOAD: {inserted} registros guardados exitosamente")
        
        return inserted
    
    def _prepare_for_database(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Prepara el DataFrame para inserción en la base de datos.
        
        Args:
            df: DataFrame con datos procesados
            
        Returns:
            List[Dict]: Lista de diccionarios listos para insertar
        """
        records = []
        
        for _, row in df.iterrows():
            # Convertir fecha_publicacion a string ISO si es datetime
            fecha_pub = row.get('fecha_publicacion_iso', row.get('fecha_publicacion'))
            if hasattr(fecha_pub, 'isoformat'):
                fecha_pub = fecha_pub.isoformat()
            elif pd.notna(fecha_pub):
                fecha_pub = str(fecha_pub)
            else:
                fecha_pub = None
            
            record = {
                'id_dato_original': int(row['id_dato_original']),
                'contenido_limpio': str(row.get('contenido_limpio', row.get('contenido_original', ''))),
                'longitud_texto': int(row.get('longitud_texto', 0)),
                'cantidad_palabras': int(row.get('cantidad_palabras', 0)),
                'fecha_publicacion_iso': fecha_pub,
                'anio': int(row['anio']) if pd.notna(row.get('anio')) else None,
                'mes': int(row['mes']) if pd.notna(row.get('mes')) else None,
                'dia_semana': int(row['dia_semana']) if pd.notna(row.get('dia_semana')) else None,
                'hora': int(row['hora']) if pd.notna(row.get('hora')) else None,
                'semestre': str(row.get('semestre', '')),
                'es_horario_laboral': bool(row.get('es_horario_laboral', False)),
                'engagement_total': int(row.get('engagement_total', 0)),
                'engagement_normalizado': float(row.get('engagement_normalizado', 0)),
                'ratio_engagement': float(row.get('ratio_engagement', 0)),
                'categoria_preliminar': str(row.get('categoria_preliminar', 'General')),
                'idioma_detectado': 'es',
                'contiene_mencion_emi': bool(row.get('contiene_mencion_emi', False)),
                'sentimiento_basico': str(row.get('sentimiento_basico', 'neutral'))
            }
            records.append(record)
        
        return records
    
    def _complete_log(self, log_id: int, success: bool, 
                      processed: int, successful: int, failed: int,
                      error_msg: str = None) -> None:
        """
        Completa el registro de log de ejecución.
        """
        # Convertir datetime a string para JSON
        stats_for_json = {}
        for key, value in self.stats.items():
            if hasattr(value, 'isoformat'):
                stats_for_json[key] = value.isoformat()
            else:
                stats_for_json[key] = value
        
        details = {
            'stats': stats_for_json,
            'validation_report': self.validator.get_validation_report() if self.validator.validation_errors else None
        }
        
        self.db.complete_execution_log(
            log_id, success, processed, successful, failed, error_msg, details
        )
    
    def _get_results(self) -> Dict[str, Any]:
        """
        Genera el diccionario de resultados del proceso.
        
        Returns:
            Dict: Resultados y estadísticas
        """
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        return {
            'success': self.stats['total_loaded'] > 0,
            'extracted': self.stats['total_extracted'],
            'cleaned': self.stats['total_cleaned'],
            'transformed': self.stats['total_transformed'],
            'validated': self.stats['total_validated'],
            'loaded': self.stats['total_loaded'],
            'errors': self.stats['total_errors'],
            'duration_seconds': duration,
            'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
            'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
        }
    
    def process_single_batch(self) -> Dict[str, Any]:
        """
        Procesa un solo batch de datos.
        
        Útil para ejecución incremental.
        
        Returns:
            Dict: Resultados del batch
        """
        return self.run(limit=self.batch_size)
    
    def process_all(self) -> Dict[str, Any]:
        """
        Procesa todos los datos pendientes en batches.
        
        Returns:
            Dict: Resultados totales
        """
        total_results = {
            'total_extracted': 0,
            'total_loaded': 0,
            'total_errors': 0,
            'batches_processed': 0
        }
        
        while True:
            batch_results = self.process_single_batch()
            
            if batch_results['extracted'] == 0:
                break
            
            total_results['total_extracted'] += batch_results['extracted']
            total_results['total_loaded'] += batch_results['loaded']
            total_results['total_errors'] += batch_results['errors']
            total_results['batches_processed'] += 1
            
            self.logger.info(
                f"Batch {total_results['batches_processed']}: "
                f"{batch_results['loaded']}/{batch_results['extracted']} procesados"
            )
            
            # Resetear stats para el siguiente batch
            self.stats = {
                'total_extracted': 0,
                'total_cleaned': 0,
                'total_transformed': 0,
                'total_validated': 0,
                'total_loaded': 0,
                'total_errors': 0,
                'start_time': None,
                'end_time': None
            }
        
        self.logger.info(
            f"Procesamiento completo: {total_results['total_loaded']} registros "
            f"en {total_results['batches_processed']} batches"
        )
        
        return total_results
    
    def get_pending_count(self) -> int:
        """
        Obtiene la cantidad de registros pendientes de procesar.
        
        Returns:
            int: Cantidad de registros sin procesar
        """
        stats = self.db.get_statistics()
        return stats.get('datos_recolectados', {}).get('pendientes', 0)
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self.db:
            self.db.close()


def run_etl(config: dict = None) -> Dict[str, Any]:
    """
    Función de conveniencia para ejecutar el pipeline ETL.
    
    Args:
        config: Configuración del sistema
        
    Returns:
        Dict: Resultados del proceso
    """
    controller = ETLController(config)
    try:
        return controller.run()
    finally:
        controller.close()


if __name__ == "__main__":
    # Test del controlador ETL
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Cargar configuración
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    
    print("=== Test de ETLController ===\n")
    
    controller = ETLController(config)
    
    # Verificar registros pendientes
    pending = controller.get_pending_count()
    print(f"Registros pendientes de procesar: {pending}")
    
    if pending > 0:
        print("\nEjecutando pipeline ETL...")
        results = controller.run()
        
        print("\n=== Resultados ===")
        for key, value in results.items():
            print(f"  {key}: {value}")
    else:
        print("\nNo hay datos pendientes. Ejecuta primero --collect para recolectar datos.")
    
    controller.close()
