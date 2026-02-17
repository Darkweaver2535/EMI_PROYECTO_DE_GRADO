"""
Retry Manager - Gestión de reintentos con backoff exponencial
Sistema OSINT EMI - Sprint 6

Implementa estrategia de reintentos con:
- Backoff exponencial: aumenta tiempo entre reintentos
- Jitter: añade aleatoriedad para evitar thundering herd
- Clasificación de excepciones: retryable vs no-retryable

Estrategia de espera:
- Intento 1: inmediato
- Intento 2: espera 2^1 + jitter = 2-3 seg
- Intento 3: espera 2^2 + jitter = 4-6 seg
- Intento 4: espera 2^3 + jitter = 8-12 seg
- Max delay: 60 seg

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import logging
import random
import time
import asyncio
import functools
from datetime import datetime
from typing import Callable, Any, Optional, Tuple, Type, Union
from dataclasses import dataclass, field
import requests

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        wait_exponential,
        wait_random,
        retry_if_exception_type,
        retry_if_exception,
        before_sleep_log,
        after_log,
        RetryError
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    RetryError = Exception

logger = logging.getLogger('OSINT.resilience.retry_manager')


@dataclass
class RetryConfig:
    """Configuración para reintentos"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # Segundos
    max_delay: float = 60.0  # Segundos
    exponential_base: float = 2.0
    jitter_range: Tuple[float, float] = (0.0, 2.0)  # Min/max jitter en segundos
    
    # Excepciones que permiten retry
    retryable_exceptions: Tuple[Type[Exception], ...] = field(default_factory=lambda: (
        TimeoutError,
        ConnectionError,
        ConnectionResetError,
        ConnectionRefusedError,
        BrokenPipeError,
    ))
    
    # Excepciones que NO permiten retry (errores de lógica)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = field(default_factory=lambda: (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    ))


class RetryStats:
    """Estadísticas de reintentos"""
    
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_retries = 0
        self.retries_by_exception = {}
        self.last_retry_time = None
    
    def record_attempt(self, success: bool, exception_type: str = None):
        """Registra un intento"""
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
    
    def record_retry(self, exception_type: str):
        """Registra un reintento"""
        self.total_retries += 1
        self.retries_by_exception[exception_type] = \
            self.retries_by_exception.get(exception_type, 0) + 1
        self.last_retry_time = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        """Convierte estadísticas a diccionario"""
        return {
            'total_calls': self.total_calls,
            'successful_calls': self.successful_calls,
            'failed_calls': self.failed_calls,
            'total_retries': self.total_retries,
            'retries_by_exception': self.retries_by_exception,
            'last_retry_time': self.last_retry_time,
            'retry_rate': self.total_retries / max(self.total_calls, 1)
        }


class RetryManager:
    """
    Gestiona reintentos con backoff exponencial + jitter.
    
    Proporciona decoradores y métodos para ejecutar funciones
    con reintentos automáticos, logging detallado y estadísticas.
    
    Ejemplo de uso:
        retry_mgr = RetryManager(source_name='facebook')
        
        @retry_mgr.with_retry
        async def fetch_posts():
            ...
        
        # O usando decorador estático
        @RetryManager.create_retry_decorator(max_attempts=5)
        async def another_function():
            ...
    """
    
    def __init__(self, source_name: str, config: Optional[RetryConfig] = None):
        """
        Inicializa el Retry Manager.
        
        Args:
            source_name: Nombre de la fuente para logging
            config: Configuración de reintentos (usa defaults si None)
        """
        self.source_name = source_name
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        
        logger.info(
            f"RetryManager inicializado para '{source_name}'",
            extra={
                'source': source_name,
                'max_attempts': self.config.max_attempts,
                'max_delay': self.config.max_delay
            }
        )
    
    @staticmethod
    def create_retry_decorator(
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        retry_exceptions: Tuple[Type[Exception], ...] = None
    ):
        """
        Crea decorador retry con configuración personalizada.
        
        Usa tenacity si está disponible, sino implementación fallback.
        
        Args:
            max_attempts: Número máximo de intentos
            initial_delay: Delay inicial en segundos
            max_delay: Delay máximo en segundos
            retry_exceptions: Excepciones que permiten retry
            
        Returns:
            Decorador aplicable a funciones sync o async
        """
        if retry_exceptions is None:
            retry_exceptions = (
                TimeoutError,
                ConnectionError,
                ConnectionResetError,
            )
        
        if TENACITY_AVAILABLE:
            return retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential_jitter(
                    initial=initial_delay,
                    max=max_delay,
                    jitter=random.uniform(0, 2)
                ),
                retry=retry_if_exception_type(retry_exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True
            )
        else:
            # Fallback sin tenacity
            return RetryManager._create_fallback_decorator(
                max_attempts=max_attempts,
                initial_delay=initial_delay,
                max_delay=max_delay,
                retry_exceptions=retry_exceptions
            )
    
    @staticmethod
    def _create_fallback_decorator(
        max_attempts: int,
        initial_delay: float,
        max_delay: float,
        retry_exceptions: Tuple[Type[Exception], ...]
    ):
        """Crea decorador fallback cuando tenacity no está disponible"""
        
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except retry_exceptions as e:
                        last_exception = e
                        
                        if attempt < max_attempts:
                            # Calcular delay con exponential backoff + jitter
                            delay = min(
                                initial_delay * (2 ** (attempt - 1)) + random.uniform(0, 2),
                                max_delay
                            )
                            
                            logger.warning(
                                f"Intento {attempt}/{max_attempts} falló: {e}. "
                                f"Reintentando en {delay:.2f}s",
                                extra={
                                    'attempt': attempt,
                                    'max_attempts': max_attempts,
                                    'delay': delay,
                                    'error': str(e)
                                }
                            )
                            
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"Todos los intentos fallaron ({max_attempts})",
                                extra={'error': str(e)}
                            )
                    except Exception as e:
                        # Excepción no retryable
                        logger.error(f"Error no retryable: {e}")
                        raise
                
                raise last_exception
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except retry_exceptions as e:
                        last_exception = e
                        
                        if attempt < max_attempts:
                            delay = min(
                                initial_delay * (2 ** (attempt - 1)) + random.uniform(0, 2),
                                max_delay
                            )
                            
                            logger.warning(
                                f"Intento {attempt}/{max_attempts} falló: {e}. "
                                f"Reintentando en {delay:.2f}s"
                            )
                            
                            time.sleep(delay)
                
                raise last_exception
            
            # Detectar si es async o sync
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def with_retry(self, func: Callable) -> Callable:
        """
        Decorador de instancia para aplicar reintentos.
        
        Args:
            func: Función a decorar
            
        Returns:
            Función decorada con reintentos
        """
        decorator = self.create_retry_decorator(
            max_attempts=self.config.max_attempts,
            initial_delay=self.config.initial_delay,
            max_delay=self.config.max_delay,
            retry_exceptions=self.config.retryable_exceptions
        )
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await decorator(func)(*args, **kwargs)
                self.stats.record_attempt(success=True)
                return result
            except Exception as e:
                self.stats.record_attempt(success=False, exception_type=type(e).__name__)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = decorator(func)(*args, **kwargs)
                self.stats.record_attempt(success=True)
                return result
            except Exception as e:
                self.stats.record_attempt(success=False, exception_type=type(e).__name__)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Ejecuta función async con reintentos.
        
        Args:
            func: Función/coroutine a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos keyword
            
        Returns:
            Resultado de la función
        """
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                self.stats.record_attempt(success=True)
                
                if attempt > 1:
                    logger.info(
                        f"Éxito en intento {attempt} para '{self.source_name}'",
                        extra={
                            'source': self.source_name,
                            'attempt': attempt
                        }
                    )
                
                return result
                
            except self.config.non_retryable_exceptions as e:
                # Error de lógica, no reintentar
                logger.error(
                    f"Error no retryable en '{self.source_name}': {e}",
                    extra={
                        'source': self.source_name,
                        'error_type': type(e).__name__,
                        'error': str(e)
                    }
                )
                self.stats.record_attempt(success=False, exception_type=type(e).__name__)
                raise
                
            except self.config.retryable_exceptions as e:
                last_exception = e
                self.stats.record_retry(type(e).__name__)
                
                if attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    
                    logger.warning(
                        f"Intento {attempt}/{self.config.max_attempts} falló para "
                        f"'{self.source_name}': {e}. Reintentando en {delay:.2f}s",
                        extra={
                            'source': self.source_name,
                            'attempt': attempt,
                            'max_attempts': self.config.max_attempts,
                            'delay': delay,
                            'error_type': type(e).__name__,
                            'error': str(e)
                        }
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Todos los intentos fallaron para '{self.source_name}' "
                        f"({self.config.max_attempts})",
                        extra={
                            'source': self.source_name,
                            'max_attempts': self.config.max_attempts,
                            'final_error': str(e)
                        }
                    )
                    self.stats.record_attempt(success=False, exception_type=type(e).__name__)
            
            except Exception as e:
                # Excepción inesperada, verificar si es retryable
                if self.should_retry(e):
                    last_exception = e
                    self.stats.record_retry(type(e).__name__)
                    
                    if attempt < self.config.max_attempts:
                        delay = self._calculate_delay(attempt)
                        logger.warning(f"Reintentando tras excepción: {e}")
                        await asyncio.sleep(delay)
                        continue
                
                self.stats.record_attempt(success=False, exception_type=type(e).__name__)
                raise
        
        # Si llegamos aquí, todos los intentos fallaron
        self.stats.record_attempt(success=False, exception_type=type(last_exception).__name__)
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        Calcula delay con backoff exponencial + jitter.
        
        Args:
            attempt: Número de intento actual (1-based)
            
        Returns:
            Delay en segundos
        """
        # Exponential backoff
        base_delay = self.config.initial_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Añadir jitter
        jitter = random.uniform(*self.config.jitter_range)
        
        # Aplicar límite máximo
        delay = min(base_delay + jitter, self.config.max_delay)
        
        return delay
    
    @staticmethod
    def should_retry(exception: Exception) -> bool:
        """
        Determina si una excepción permite reintento.
        
        Retryable:
        - Timeout, ConnectionError (problemas de red)
        - 5xx errors (errores de servidor)
        - 429 (rate limit - con backoff mayor)
        
        No retryable:
        - 4xx errors (excepto 429)
        - ValueError, TypeError (errores de lógica)
        
        Args:
            exception: Excepción a evaluar
            
        Returns:
            True si se debe reintentar, False si no
        """
        # Errores de red siempre son retryable
        retryable_types = (
            TimeoutError,
            ConnectionError,
            ConnectionResetError,
            ConnectionRefusedError,
            BrokenPipeError,
            asyncio.TimeoutError,
        )
        
        if isinstance(exception, retryable_types):
            return True
        
        # Errores HTTP
        try:
            # requests library
            if isinstance(exception, requests.exceptions.Timeout):
                return True
            if isinstance(exception, requests.exceptions.ConnectionError):
                return True
            if isinstance(exception, requests.exceptions.HTTPError):
                status_code = exception.response.status_code
                # 5xx = server error, retryable
                if 500 <= status_code < 600:
                    return True
                # 429 = rate limit, retryable
                if status_code == 429:
                    return True
                # Otros 4xx = client error, no retryable
                return False
        except (AttributeError, TypeError):
            pass
        
        # aiohttp errors
        try:
            import aiohttp
            if isinstance(exception, aiohttp.ClientError):
                return True
        except ImportError:
            pass
        
        # Errores de lógica nunca son retryable
        non_retryable_types = (
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            SyntaxError,
            NotImplementedError,
        )
        
        if isinstance(exception, non_retryable_types):
            return False
        
        # Por defecto, permitir retry para excepciones desconocidas
        return True
    
    @staticmethod
    def get_retry_after_from_response(response) -> Optional[int]:
        """
        Extrae valor Retry-After de headers de respuesta HTTP.
        
        Args:
            response: Objeto response (requests o aiohttp)
            
        Returns:
            Segundos a esperar, o None si no hay header
        """
        try:
            # Intentar obtener header Retry-After
            retry_after = None
            
            if hasattr(response, 'headers'):
                retry_after = response.headers.get('Retry-After')
            
            if retry_after:
                # Puede ser segundos o fecha HTTP
                try:
                    return int(retry_after)
                except ValueError:
                    # Es una fecha HTTP, parsear
                    from email.utils import parsedate_to_datetime
                    retry_date = parsedate_to_datetime(retry_after)
                    return max(0, int((retry_date - datetime.now()).total_seconds()))
        except Exception:
            pass
        
        return None
    
    def get_stats(self) -> dict:
        """Retorna estadísticas de reintentos"""
        stats = self.stats.to_dict()
        stats['source_name'] = self.source_name
        stats['config'] = {
            'max_attempts': self.config.max_attempts,
            'initial_delay': self.config.initial_delay,
            'max_delay': self.config.max_delay
        }
        return stats


# Decorador conveniente para uso simple
def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_exceptions: Tuple[Type[Exception], ...] = None
):
    """
    Decorador conveniente para aplicar reintentos a una función.
    
    Ejemplo:
        @with_retry(max_attempts=5)
        async def fetch_data():
            ...
    """
    return RetryManager.create_retry_decorator(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        retry_exceptions=retry_exceptions
    )


__all__ = [
    'RetryManager',
    'RetryConfig',
    'RetryStats',
    'with_retry'
]
