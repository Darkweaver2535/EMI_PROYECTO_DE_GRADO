"""
Logger Estructurado JSON - Sistema OSINT EMI

Proporciona logging estructurado en formato JSON para:
- Mejor integración con sistemas de log aggregation (ELK, Loki)
- Contexto enriquecido automáticamente
- Correlación de logs entre servicios

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

import os
import sys
import logging
import json
import time
import traceback
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
import threading
import uuid

# Intentar importar python-json-logger
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class LogConfig:
    """Configuración del logger."""
    level: str = "INFO"
    format: str = "json"  # "json" o "text"
    output: str = "stdout"  # "stdout", "stderr", "file", "both"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    include_timestamp: bool = True
    include_hostname: bool = True
    include_process: bool = True
    include_thread: bool = True
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> 'LogConfig':
        """Crea configuración desde variables de entorno."""
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            format=os.getenv('LOG_FORMAT', 'json'),
            output=os.getenv('LOG_OUTPUT', 'stdout'),
            file_path=os.getenv('LOG_FILE_PATH'),
            include_hostname=os.getenv('LOG_INCLUDE_HOSTNAME', 'true').lower() == 'true',
            include_process=os.getenv('LOG_INCLUDE_PROCESS', 'true').lower() == 'true',
            include_thread=os.getenv('LOG_INCLUDE_THREAD', 'true').lower() == 'true',
        )


# =============================================================================
# CONTEXTO DE LOG
# =============================================================================

class LogContext:
    """
    Gestiona contexto de log a nivel de thread.
    
    Permite agregar contexto que se incluirá automáticamente en todos los logs.
    
    Ejemplo:
        with LogContext.scope(request_id="abc123", user_id="user456"):
            logger.info("Processing request")
            # El log incluirá request_id y user_id automáticamente
    """
    
    _local = threading.local()
    
    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        """Obtiene el contexto actual del thread."""
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        return cls._local.context.copy()
    
    @classmethod
    def set(cls, key: str, value: Any):
        """Establece un valor en el contexto."""
        if not hasattr(cls._local, 'context'):
            cls._local.context = {}
        cls._local.context[key] = value
    
    @classmethod
    def remove(cls, key: str):
        """Elimina un valor del contexto."""
        if hasattr(cls._local, 'context') and key in cls._local.context:
            del cls._local.context[key]
    
    @classmethod
    def clear(cls):
        """Limpia todo el contexto."""
        cls._local.context = {}
    
    @classmethod
    @contextmanager
    def scope(cls, **kwargs):
        """
        Context manager para agregar contexto temporalmente.
        
        Ejemplo:
            with LogContext.scope(scraper_name="facebook"):
                logger.info("Starting scrape")
        """
        old_context = cls.get_context()
        
        try:
            if not hasattr(cls._local, 'context'):
                cls._local.context = {}
            cls._local.context.update(kwargs)
            yield
        finally:
            cls._local.context = old_context


# =============================================================================
# FORMATTER JSON PERSONALIZADO
# =============================================================================

class StructuredJSONFormatter(logging.Formatter):
    """
    Formatter que genera logs en formato JSON estructurado.
    
    Compatible con ELK Stack, Loki, y otros sistemas de log aggregation.
    """
    
    def __init__(
        self,
        config: LogConfig = None,
        **kwargs
    ):
        super().__init__()
        self.config = config or LogConfig()
        self._hostname = self._get_hostname() if self.config.include_hostname else None
    
    def _get_hostname(self) -> str:
        """Obtiene el hostname de la máquina."""
        import socket
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el log record como JSON."""
        # Estructura base del log
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Timestamp
        if self.config.include_timestamp:
            log_data["timestamp"] = datetime.utcfromtimestamp(record.created).isoformat() + "Z"
            log_data["timestamp_unix"] = record.created
        
        # Información de ubicación
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "module": record.module,
        }
        
        # Hostname
        if self._hostname:
            log_data["host"] = self._hostname
        
        # Proceso y thread
        if self.config.include_process:
            log_data["process"] = {
                "id": record.process,
                "name": record.processName,
            }
        
        if self.config.include_thread:
            log_data["thread"] = {
                "id": record.thread,
                "name": record.threadName,
            }
        
        # Excepción si existe
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": self.formatException(record.exc_info),
            }
        
        # Contexto del thread
        context = LogContext.get_context()
        if context:
            log_data["context"] = context
        
        # Campos extra del record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                'message', 'asctime'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_data["extra"] = extra_fields
        
        # Campos extra de configuración
        if self.config.extra_fields:
            log_data.update(self.config.extra_fields)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredTextFormatter(logging.Formatter):
    """Formatter de texto con colores para desarrollo."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        
        # Timestamp
        timestamp = datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Contexto
        context = LogContext.get_context()
        context_str = ""
        if context:
            context_items = [f"{k}={v}" for k, v in context.items()]
            context_str = f" [{', '.join(context_items)}]"
        
        # Mensaje formateado
        message = f"{color}{timestamp} | {record.levelname:8} | {record.name}:{record.lineno}{context_str} | {record.getMessage()}{self.RESET}"
        
        # Excepción si existe
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


# =============================================================================
# SCRAPER LOGGER
# =============================================================================

class ScraperLogger:
    """
    Logger especializado para scrapers con métodos de conveniencia.
    
    Proporciona logging estructurado con contexto automático de scraper.
    
    Ejemplo:
        logger = ScraperLogger("facebook_scraper", "facebook.com")
        
        logger.scrape_started()
        logger.request("GET", "https://facebook.com/page", status=200, duration=1.5)
        logger.items_extracted(50, "posts")
        logger.scrape_completed(success=True, items_count=50)
    """
    
    def __init__(
        self,
        scraper_name: str,
        source: str,
        logger: Optional[logging.Logger] = None
    ):
        self.scraper_name = scraper_name
        self.source = source
        self._logger = logger or logging.getLogger(f"scraper.{scraper_name}")
        self._run_id: Optional[str] = None
        self._start_time: Optional[float] = None
    
    def _log(
        self,
        level: int,
        message: str,
        **extra
    ):
        """Log interno con contexto de scraper."""
        extra_data = {
            "scraper_name": self.scraper_name,
            "source": self.source,
            **extra
        }
        
        if self._run_id:
            extra_data["run_id"] = self._run_id
        
        self._logger.log(level, message, extra=extra_data)
    
    def debug(self, message: str, **extra):
        """Log de nivel DEBUG."""
        self._log(logging.DEBUG, message, **extra)
    
    def info(self, message: str, **extra):
        """Log de nivel INFO."""
        self._log(logging.INFO, message, **extra)
    
    def warning(self, message: str, **extra):
        """Log de nivel WARNING."""
        self._log(logging.WARNING, message, **extra)
    
    def error(self, message: str, exc_info: bool = False, **extra):
        """Log de nivel ERROR."""
        self._logger.error(
            message,
            exc_info=exc_info,
            extra={
                "scraper_name": self.scraper_name,
                "source": self.source,
                "run_id": self._run_id,
                **extra
            }
        )
    
    def critical(self, message: str, exc_info: bool = True, **extra):
        """Log de nivel CRITICAL."""
        self._logger.critical(
            message,
            exc_info=exc_info,
            extra={
                "scraper_name": self.scraper_name,
                "source": self.source,
                "run_id": self._run_id,
                **extra
            }
        )
    
    # --- Métodos de Ciclo de Vida del Scraper ---
    
    def scrape_started(self, **extra):
        """Log de inicio de scrape."""
        self._run_id = str(uuid.uuid4())[:8]
        self._start_time = time.time()
        
        self.info(
            f"Scrape started for {self.source}",
            event="scrape_started",
            **extra
        )
    
    def scrape_completed(
        self,
        success: bool = True,
        items_count: int = 0,
        **extra
    ):
        """Log de finalización de scrape."""
        duration = time.time() - self._start_time if self._start_time else 0
        
        level = logging.INFO if success else logging.ERROR
        status = "completed" if success else "failed"
        
        self._log(
            level,
            f"Scrape {status} for {self.source}",
            event="scrape_completed",
            success=success,
            items_count=items_count,
            duration_seconds=round(duration, 3),
            **extra
        )
        
        self._run_id = None
        self._start_time = None
    
    # --- Métodos de Request ---
    
    def request(
        self,
        method: str,
        url: str,
        status: Optional[int] = None,
        duration: Optional[float] = None,
        **extra
    ):
        """Log de request HTTP."""
        self.debug(
            f"{method} {url}",
            event="http_request",
            http_method=method,
            url=url,
            status_code=status,
            duration_seconds=duration,
            **extra
        )
    
    def request_error(
        self,
        method: str,
        url: str,
        error: Exception,
        **extra
    ):
        """Log de error en request."""
        self.error(
            f"Request failed: {method} {url} - {error}",
            event="request_error",
            http_method=method,
            url=url,
            error_type=type(error).__name__,
            error_message=str(error),
            **extra
        )
    
    # --- Métodos de Items ---
    
    def items_extracted(
        self,
        count: int,
        item_type: str = "item",
        **extra
    ):
        """Log de items extraídos."""
        self.info(
            f"Extracted {count} {item_type}(s)",
            event="items_extracted",
            items_count=count,
            item_type=item_type,
            **extra
        )
    
    def item_parse_error(
        self,
        error: Exception,
        item_data: Optional[Dict] = None,
        **extra
    ):
        """Log de error parseando item."""
        self.warning(
            f"Failed to parse item: {error}",
            event="item_parse_error",
            error_type=type(error).__name__,
            error_message=str(error),
            item_data=item_data,
            **extra
        )
    
    # --- Métodos de Resiliencia ---
    
    def circuit_breaker_opened(self, reason: str = "", **extra):
        """Log cuando el circuit breaker se abre."""
        self.warning(
            f"Circuit breaker opened for {self.source}",
            event="circuit_breaker_opened",
            reason=reason,
            **extra
        )
    
    def circuit_breaker_closed(self, **extra):
        """Log cuando el circuit breaker se cierra."""
        self.info(
            f"Circuit breaker closed for {self.source}",
            event="circuit_breaker_closed",
            **extra
        )
    
    def retry_attempt(
        self,
        attempt: int,
        max_attempts: int,
        wait_time: float,
        error: Optional[Exception] = None,
        **extra
    ):
        """Log de intento de retry."""
        self.warning(
            f"Retry attempt {attempt}/{max_attempts}, waiting {wait_time:.2f}s",
            event="retry_attempt",
            attempt=attempt,
            max_attempts=max_attempts,
            wait_time_seconds=wait_time,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            **extra
        )
    
    def rate_limited(
        self,
        wait_time: float,
        reason: str = "",
        **extra
    ):
        """Log cuando se aplica rate limiting."""
        self.warning(
            f"Rate limited, waiting {wait_time:.2f}s",
            event="rate_limited",
            wait_time_seconds=wait_time,
            reason=reason,
            **extra
        )
    
    def timeout_occurred(
        self,
        operation: str,
        timeout_seconds: float,
        **extra
    ):
        """Log cuando ocurre un timeout."""
        self.warning(
            f"Timeout in {operation} after {timeout_seconds}s",
            event="timeout",
            operation=operation,
            timeout_seconds=timeout_seconds,
            **extra
        )
    
    # --- Context Manager ---
    
    @contextmanager
    def operation(self, name: str, **extra):
        """
        Context manager para trackear operaciones.
        
        Ejemplo:
            with logger.operation("fetch_posts"):
                posts = await fetch_posts()
        """
        start_time = time.time()
        self.debug(f"Starting operation: {name}", event="operation_start", operation=name, **extra)
        
        try:
            yield
            duration = time.time() - start_time
            self.debug(
                f"Completed operation: {name}",
                event="operation_complete",
                operation=name,
                duration_seconds=round(duration, 3),
                success=True,
                **extra
            )
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Failed operation: {name} - {e}",
                event="operation_failed",
                operation=name,
                duration_seconds=round(duration, 3),
                success=False,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
                **extra
            )
            raise


# =============================================================================
# SETUP Y FACTORY
# =============================================================================

_loggers: Dict[str, ScraperLogger] = {}
_configured = False


def setup_logging(
    config: Optional[LogConfig] = None,
    root_level: str = "INFO"
) -> None:
    """
    Configura el sistema de logging.
    
    Debe llamarse una vez al inicio de la aplicación.
    
    Args:
        config: Configuración de logging
        root_level: Nivel del logger root
    """
    global _configured
    
    if _configured:
        return
    
    config = config or LogConfig.from_env()
    
    # Determinar formatter
    if config.format == "json":
        formatter = StructuredJSONFormatter(config)
    else:
        formatter = ColoredTextFormatter()
    
    # Configurar handlers
    handlers = []
    
    if config.output in ("stdout", "both"):
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        handlers.append(stdout_handler)
    
    if config.output in ("stderr",):
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        handlers.append(stderr_handler)
    
    if config.output in ("file", "both") and config.file_path:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configurar logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, root_level.upper()))
    
    # Eliminar handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Agregar nuevos handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configurar loggers específicos de scrapers
    scraper_logger = logging.getLogger("scraper")
    scraper_logger.setLevel(getattr(logging, config.level.upper()))
    
    _configured = True


def get_logger(
    scraper_name: str,
    source: str
) -> ScraperLogger:
    """
    Obtiene o crea un logger para un scraper.
    
    Args:
        scraper_name: Nombre del scraper
        source: Fuente/dominio del scraper
        
    Returns:
        ScraperLogger configurado
    """
    key = f"{scraper_name}:{source}"
    
    if key not in _loggers:
        _loggers[key] = ScraperLogger(scraper_name, source)
    
    return _loggers[key]


def log_function_call(logger_name: str = None):
    """
    Decorador para loggear llamadas a funciones.
    
    Ejemplo:
        @log_function_call("scraper.facebook")
        def fetch_posts(page_id: str):
            ...
    """
    def decorator(func):
        nonlocal logger_name
        _logger = logging.getLogger(logger_name or func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            _logger.debug(f"Calling {func_name}", extra={
                "event": "function_call",
                "function": func_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                _logger.debug(f"Completed {func_name}", extra={
                    "event": "function_complete",
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": True
                })
                return result
            except Exception as e:
                duration = time.time() - start_time
                _logger.error(f"Failed {func_name}: {e}", extra={
                    "event": "function_failed",
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }, exc_info=True)
                raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            _logger.debug(f"Calling {func_name}", extra={
                "event": "function_call",
                "function": func_name,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                _logger.debug(f"Completed {func_name}", extra={
                    "event": "function_complete",
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": True
                })
                return result
            except Exception as e:
                duration = time.time() - start_time
                _logger.error(f"Failed {func_name}: {e}", extra={
                    "event": "function_failed",
                    "function": func_name,
                    "duration_seconds": round(duration, 3),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }, exc_info=True)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator
