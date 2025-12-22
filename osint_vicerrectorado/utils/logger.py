"""
Logger - Configuración de logging para el sistema
Sistema de Analítica EMI

Proporciona:
- Configuración centralizada de logging
- Rotación automática de archivos de log
- Formato estructurado para análisis
- Handlers para consola y archivo

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """
    Formatter personalizado que genera logs en formato JSON.
    
    Útil para análisis automatizado y sistemas de monitoreo.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro de log como JSON.
        
        Args:
            record: Registro de log
            
        Returns:
            str: Log formateado como JSON
        """
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Agregar campos extra si existen
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Formatter con colores para la consola.
    
    Mejora la legibilidad de los logs en terminal.
    """
    
    # Códigos de color ANSI
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Verde
        'WARNING': '\033[33m',   # Amarillo
        'ERROR': '\033[31m',     # Rojo
        'CRITICAL': '\033[41m',  # Fondo rojo
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatea el registro con colores.
        
        Args:
            record: Registro de log
            
        Returns:
            str: Log formateado con colores
        """
        # Obtener color para el nivel
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formatear mensaje
        record.levelname = f"{color}{record.levelname}{reset}"
        
        return super().format(record)


def setup_logger(
    name: str = "OSINT",
    log_file: str = None,
    level: int = logging.INFO,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    json_format: bool = False,
    console_output: bool = True
) -> logging.Logger:
    """
    Configura y retorna un logger con las opciones especificadas.
    
    Args:
        name: Nombre del logger
        log_file: Ruta al archivo de log (None = solo consola)
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_file_size_mb: Tamaño máximo del archivo de log en MB
        backup_count: Número de archivos de backup a mantener
        json_format: Si True, usa formato JSON para archivo
        console_output: Si True, también muestra logs en consola
        
    Returns:
        logging.Logger: Logger configurado
    """
    # Obtener o crear logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicar handlers si ya está configurado
    if logger.handlers:
        return logger
    
    # Formato estándar
    standard_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Handler para consola
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Usar formato con colores si la terminal lo soporta
        if sys.stdout.isatty():
            console_formatter = ColoredFormatter(standard_format, datefmt=date_format)
        else:
            console_formatter = logging.Formatter(standard_format, datefmt=date_format)
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Handler para archivo
    if log_file:
        # Crear directorio si no existe
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,  # Convertir MB a bytes
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Formato para archivo
        if json_format:
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(standard_format, datefmt=date_format)
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_daily_logger(
    name: str = "OSINT",
    log_dir: str = "logs",
    level: int = logging.INFO,
    backup_count: int = 30
) -> logging.Logger:
    """
    Configura un logger con rotación diaria de archivos.
    
    Crea un nuevo archivo de log cada día.
    
    Args:
        name: Nombre del logger
        log_dir: Directorio para archivos de log
        level: Nivel de logging
        backup_count: Días de logs a mantener
        
    Returns:
        logging.Logger: Logger configurado
    """
    # Crear directorio si no existe
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicar handlers
    if logger.handlers:
        return logger
    
    # Formato
    standard_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Handler de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    if sys.stdout.isatty():
        console_handler.setFormatter(ColoredFormatter(standard_format, datefmt=date_format))
    else:
        console_handler.setFormatter(logging.Formatter(standard_format, datefmt=date_format))
    logger.addHandler(console_handler)
    
    # Handler con rotación diaria
    log_file = os.path.join(log_dir, f"{name.lower()}.log")
    
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d"
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(standard_format, datefmt=date_format))
    
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "OSINT") -> logging.Logger:
    """
    Obtiene un logger existente o crea uno básico.
    
    Args:
        name: Nombre del logger
        
    Returns:
        logging.Logger: Logger
    """
    logger = logging.getLogger(name)
    
    # Si no tiene handlers, configurar uno básico
    if not logger.handlers:
        logger = setup_logger(name)
    
    return logger


def configure_from_config(config: dict) -> logging.Logger:
    """
    Configura el logging desde un diccionario de configuración.
    
    Args:
        config: Diccionario con configuración de logging
        
    Returns:
        logging.Logger: Logger configurado
    """
    log_config = config.get('logging', {})
    
    level_str = log_config.get('level', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)
    
    return setup_logger(
        name="OSINT",
        log_file=log_config.get('file_path', 'logs/osint_system.log'),
        level=level,
        max_file_size_mb=log_config.get('max_file_size_mb', 10),
        backup_count=log_config.get('backup_count', 5),
        json_format=log_config.get('json_format', False),
        console_output=True
    )


class LoggerAdapter(logging.LoggerAdapter):
    """
    Adapter para agregar contexto extra a los logs.
    
    Útil para incluir información como source_id, batch_id, etc.
    """
    
    def process(self, msg, kwargs):
        """
        Procesa el mensaje agregando el contexto extra.
        """
        extra = self.extra.copy()
        
        # Agregar extra a kwargs si existe
        if 'extra' in kwargs:
            extra.update(kwargs['extra'])
        kwargs['extra'] = extra
        
        # Prefijo con contexto
        context_str = ' '.join([f"[{k}={v}]" for k, v in self.extra.items()])
        return f"{context_str} {msg}", kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Obtiene un logger con contexto adicional.
    
    Args:
        name: Nombre del logger
        **context: Contexto adicional (ej: source='facebook', batch_id=123)
        
    Returns:
        LoggerAdapter: Logger con contexto
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


# Función para log de recolección con formato específico
def log_collection(source: str, items: int, duration: float, status: str = "success") -> None:
    """
    Registra una operación de recolección con formato específico.
    
    Args:
        source: Fuente de datos (facebook, tiktok)
        items: Cantidad de items recolectados
        duration: Duración en segundos
        status: Estado de la operación
    """
    logger = get_logger("OSINT.Collection")
    
    if status == "success":
        logger.info(
            f"Recolección [{source.upper()}]: {items} items en {duration:.2f}s"
        )
    elif status == "partial":
        logger.warning(
            f"Recolección parcial [{source.upper()}]: {items} items en {duration:.2f}s"
        )
    else:
        logger.error(
            f"Recolección fallida [{source.upper()}]: {status}"
        )


# Función para log de ETL con formato específico
def log_etl(stage: str, input_count: int, output_count: int, duration: float = None) -> None:
    """
    Registra una etapa del pipeline ETL.
    
    Args:
        stage: Etapa del ETL (extract, clean, transform, load)
        input_count: Registros de entrada
        output_count: Registros de salida
        duration: Duración en segundos
    """
    logger = get_logger("OSINT.ETL")
    
    diff = input_count - output_count
    duration_str = f" ({duration:.2f}s)" if duration else ""
    
    if diff == 0:
        logger.info(
            f"ETL [{stage.upper()}]: {input_count} -> {output_count}{duration_str}"
        )
    elif diff > 0:
        logger.info(
            f"ETL [{stage.upper()}]: {input_count} -> {output_count} (-{diff}){duration_str}"
        )
    else:
        logger.warning(
            f"ETL [{stage.upper()}]: {input_count} -> {output_count} (+{abs(diff)}){duration_str}"
        )


if __name__ == "__main__":
    # Test del sistema de logging
    print("=== Test de Logger ===\n")
    
    # Configurar logger
    logger = setup_logger(
        name="OSINT.Test",
        log_file="logs/test.log",
        level=logging.DEBUG
    )
    
    # Probar diferentes niveles
    logger.debug("Este es un mensaje de DEBUG")
    logger.info("Este es un mensaje de INFO")
    logger.warning("Este es un mensaje de WARNING")
    logger.error("Este es un mensaje de ERROR")
    
    # Logger con contexto
    ctx_logger = get_context_logger("OSINT.Test", source="facebook", batch=123)
    ctx_logger.info("Mensaje con contexto")
    
    # Log de recolección
    log_collection("facebook", 50, 125.5)
    log_collection("tiktok", 20, 60.3)
    
    # Log de ETL
    log_etl("extract", 100, 100, 1.5)
    log_etl("clean", 100, 95, 0.8)
    log_etl("transform", 95, 95, 2.1)
    log_etl("load", 95, 92, 1.2)
    
    print("\nLogs guardados en logs/test.log")
