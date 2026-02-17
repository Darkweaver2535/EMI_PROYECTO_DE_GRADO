"""
Timeout Manager - Gestión de timeouts configurables
Sistema OSINT EMI - Sprint 6

Proporciona gestión centralizada de timeouts:
- Configuración por fuente/operación
- Timeouts adaptativos basados en latencia histórica
- Context managers para aplicar timeouts
- Métricas de timeouts

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import asyncio
import logging
import threading
import time
import signal
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from functools import wraps
from collections import deque

logger = logging.getLogger('OSINT.resilience.timeout_manager')


@dataclass
class TimeoutConfig:
    """Configuración de timeout para una operación"""
    connect_timeout: float = 10.0  # Timeout para conexión
    read_timeout: float = 30.0  # Timeout para lectura
    total_timeout: float = 60.0  # Timeout total de operación
    adaptive: bool = True  # Ajustar basado en latencia
    adaptive_factor: float = 1.5  # Factor sobre latencia promedio
    min_timeout: float = 5.0  # Timeout mínimo
    max_timeout: float = 300.0  # Timeout máximo
    
    def to_aiohttp_timeout(self):
        """Convierte a aiohttp.ClientTimeout"""
        try:
            import aiohttp
            return aiohttp.ClientTimeout(
                connect=self.connect_timeout,
                sock_read=self.read_timeout,
                total=self.total_timeout
            )
        except ImportError:
            return None
    
    def to_requests_timeout(self) -> tuple:
        """Convierte a tuple para requests library"""
        return (self.connect_timeout, self.read_timeout)


@dataclass
class TimeoutStats:
    """Estadísticas de timeouts"""
    total_operations: int = 0
    successful_operations: int = 0
    timeout_operations: int = 0
    latencies: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def avg_latency(self) -> float:
        """Latencia promedio en segundos"""
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)
    
    @property
    def p95_latency(self) -> float:
        """Latencia percentil 95"""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]
    
    @property
    def timeout_rate(self) -> float:
        """Tasa de timeouts"""
        if self.total_operations == 0:
            return 0.0
        return self.timeout_operations / self.total_operations
    
    def to_dict(self) -> dict:
        return {
            'total_operations': self.total_operations,
            'successful_operations': self.successful_operations,
            'timeout_operations': self.timeout_operations,
            'timeout_rate': round(self.timeout_rate, 4),
            'avg_latency_ms': round(self.avg_latency * 1000, 2),
            'p95_latency_ms': round(self.p95_latency * 1000, 2)
        }


class TimeoutError(Exception):
    """Excepción para operaciones que exceden timeout"""
    
    def __init__(self, message: str, operation: str = None, timeout: float = None):
        super().__init__(message)
        self.operation = operation
        self.timeout = timeout


class TimeoutManager:
    """
    Gestiona timeouts configurables para operaciones de scraping.
    
    Features:
    - Timeouts por fuente/operación
    - Adaptación automática basada en latencia
    - Context managers sync y async
    - Métricas detalladas
    
    Ejemplo:
        tm = TimeoutManager(source_name='facebook')
        
        # Usando context manager
        async with tm.timeout_context('fetch_posts', timeout=30):
            posts = await fetch_posts()
        
        # Usando decorador
        @tm.with_timeout(timeout=30)
        async def fetch_data():
            ...
    """
    
    # Registry global
    _registry: Dict[str, 'TimeoutManager'] = {}
    _registry_lock = threading.Lock()
    
    def __init__(
        self,
        source_name: str,
        default_config: Optional[TimeoutConfig] = None
    ):
        """
        Inicializa el Timeout Manager.
        
        Args:
            source_name: Nombre de la fuente
            default_config: Configuración por defecto
        """
        self.source_name = source_name
        self.default_config = default_config or TimeoutConfig()
        
        # Configuraciones por operación
        self.operation_configs: Dict[str, TimeoutConfig] = {}
        
        # Estadísticas por operación
        self.operation_stats: Dict[str, TimeoutStats] = {}
        
        # Lock para thread safety
        self._lock = threading.Lock()
        
        # Registrar en registry global
        with self._registry_lock:
            self._registry[source_name] = self
        
        logger.info(
            f"TimeoutManager inicializado para '{source_name}'",
            extra={
                'source': source_name,
                'default_timeout': self.default_config.total_timeout
            }
        )
    
    def configure_operation(
        self,
        operation: str,
        config: Optional[TimeoutConfig] = None,
        **kwargs
    ):
        """
        Configura timeout para una operación específica.
        
        Args:
            operation: Nombre de la operación
            config: Configuración completa o None para usar kwargs
            **kwargs: Parámetros individuales de TimeoutConfig
        """
        if config is None:
            # Crear config a partir de kwargs
            config = TimeoutConfig(**{
                **self.default_config.__dict__,
                **kwargs
            })
        
        self.operation_configs[operation] = config
        self.operation_stats[operation] = TimeoutStats()
        
        logger.debug(
            f"Configurado timeout para '{operation}': {config.total_timeout}s",
            extra={'source': self.source_name, 'operation': operation}
        )
    
    def get_timeout(self, operation: str = None) -> float:
        """
        Obtiene timeout para una operación.
        
        Si adaptive está habilitado, ajusta basado en latencia histórica.
        
        Args:
            operation: Nombre de la operación
            
        Returns:
            Timeout en segundos
        """
        config = self.operation_configs.get(operation, self.default_config)
        
        if not config.adaptive:
            return config.total_timeout
        
        # Obtener estadísticas
        stats = self.operation_stats.get(operation, TimeoutStats())
        
        if stats.avg_latency == 0:
            return config.total_timeout
        
        # Calcular timeout adaptativo
        adaptive_timeout = stats.p95_latency * config.adaptive_factor
        
        # Aplicar límites
        timeout = max(config.min_timeout, min(adaptive_timeout, config.max_timeout))
        
        return timeout
    
    def get_config(self, operation: str = None) -> TimeoutConfig:
        """Obtiene configuración para una operación"""
        return self.operation_configs.get(operation, self.default_config)
    
    @asynccontextmanager
    async def timeout_context(
        self,
        operation: str = 'default',
        timeout: Optional[float] = None
    ):
        """
        Context manager async para aplicar timeout.
        
        Args:
            operation: Nombre de la operación
            timeout: Timeout específico (None = usar configurado)
            
        Yields:
            None
            
        Raises:
            TimeoutError: Si la operación excede el timeout
        """
        effective_timeout = timeout or self.get_timeout(operation)
        stats = self._get_or_create_stats(operation)
        
        start_time = time.monotonic()
        
        try:
            async with asyncio.timeout(effective_timeout):
                yield
            
            # Operación exitosa
            elapsed = time.monotonic() - start_time
            self._record_success(operation, elapsed)
            
        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start_time
            self._record_timeout(operation, elapsed)
            
            raise TimeoutError(
                f"Operación '{operation}' excedió timeout de {effective_timeout}s",
                operation=operation,
                timeout=effective_timeout
            )
    
    @contextmanager
    def timeout_context_sync(
        self,
        operation: str = 'default',
        timeout: Optional[float] = None
    ):
        """
        Context manager sync para aplicar timeout usando signals.
        
        Nota: Solo funciona en el thread principal en Unix.
        
        Args:
            operation: Nombre de la operación
            timeout: Timeout específico
        """
        effective_timeout = timeout or self.get_timeout(operation)
        stats = self._get_or_create_stats(operation)
        
        start_time = time.monotonic()
        
        def timeout_handler(signum, frame):
            raise TimeoutError(
                f"Operación '{operation}' excedió timeout de {effective_timeout}s",
                operation=operation,
                timeout=effective_timeout
            )
        
        # Configurar signal handler (solo funciona en thread principal)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(effective_timeout))
        except (ValueError, AttributeError):
            # No estamos en thread principal o no es Unix
            pass
        
        try:
            yield
            
            # Cancelar alarm
            try:
                signal.alarm(0)
            except (ValueError, AttributeError):
                pass
            
            # Registrar éxito
            elapsed = time.monotonic() - start_time
            self._record_success(operation, elapsed)
            
        except TimeoutError:
            elapsed = time.monotonic() - start_time
            self._record_timeout(operation, elapsed)
            raise
            
        finally:
            # Restaurar handler
            if old_handler is not None:
                try:
                    signal.signal(signal.SIGALRM, old_handler)
                except (ValueError, AttributeError):
                    pass
    
    def with_timeout(
        self,
        operation: str = 'default',
        timeout: Optional[float] = None
    ):
        """
        Decorador para aplicar timeout a funciones.
        
        Args:
            operation: Nombre de la operación
            timeout: Timeout específico
            
        Returns:
            Decorador
        """
        def decorator(func: Callable):
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapper(*args, **kwargs):
                    async with self.timeout_context(operation, timeout):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                @wraps(func)
                def sync_wrapper(*args, **kwargs):
                    with self.timeout_context_sync(operation, timeout):
                        return func(*args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    def _get_or_create_stats(self, operation: str) -> TimeoutStats:
        """Obtiene o crea estadísticas para una operación"""
        if operation not in self.operation_stats:
            self.operation_stats[operation] = TimeoutStats()
        return self.operation_stats[operation]
    
    def _record_success(self, operation: str, elapsed: float):
        """Registra operación exitosa"""
        with self._lock:
            stats = self._get_or_create_stats(operation)
            stats.total_operations += 1
            stats.successful_operations += 1
            stats.latencies.append(elapsed)
            
            logger.debug(
                f"Operación '{operation}' completada en {elapsed:.3f}s",
                extra={
                    'source': self.source_name,
                    'operation': operation,
                    'elapsed': elapsed
                }
            )
    
    def _record_timeout(self, operation: str, elapsed: float):
        """Registra timeout"""
        with self._lock:
            stats = self._get_or_create_stats(operation)
            stats.total_operations += 1
            stats.timeout_operations += 1
            
            logger.warning(
                f"Timeout en operación '{operation}' después de {elapsed:.3f}s",
                extra={
                    'source': self.source_name,
                    'operation': operation,
                    'elapsed': elapsed
                }
            )
    
    def get_stats(self, operation: str = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de timeouts.
        
        Args:
            operation: Operación específica o None para todas
            
        Returns:
            Dict con estadísticas
        """
        if operation:
            stats = self._get_or_create_stats(operation)
            return {
                'source': self.source_name,
                'operation': operation,
                **stats.to_dict()
            }
        
        # Todas las operaciones
        return {
            'source': self.source_name,
            'operations': {
                op: stats.to_dict()
                for op, stats in self.operation_stats.items()
            }
        }
    
    def reset_stats(self, operation: str = None):
        """Resetea estadísticas"""
        with self._lock:
            if operation:
                self.operation_stats[operation] = TimeoutStats()
            else:
                for op in self.operation_stats:
                    self.operation_stats[op] = TimeoutStats()
    
    @classmethod
    def get_manager(cls, source_name: str) -> Optional['TimeoutManager']:
        """Obtiene manager del registry"""
        with cls._registry_lock:
            return cls._registry.get(source_name)
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Obtiene estadísticas de todos los managers"""
        with cls._registry_lock:
            return {
                name: manager.get_stats()
                for name, manager in cls._registry.items()
            }


# Función helper para crear timeout fácilmente
def timeout(seconds: float):
    """
    Decorador simple para timeout.
    
    Ejemplo:
        @timeout(30)
        async def slow_operation():
            ...
    """
    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    async with asyncio.timeout(seconds):
                        return await func(*args, **kwargs)
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Function {func.__name__} timed out after {seconds}s",
                        operation=func.__name__,
                        timeout=seconds
                    )
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Para sync, usamos signal (solo Unix, thread principal)
                def handler(signum, frame):
                    raise TimeoutError(
                        f"Function {func.__name__} timed out after {seconds}s",
                        operation=func.__name__,
                        timeout=seconds
                    )
                
                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.alarm(int(seconds))
                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)
                    return result
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
            
            return sync_wrapper
    
    return decorator


__all__ = [
    'TimeoutManager',
    'TimeoutConfig',
    'TimeoutStats',
    'TimeoutError',
    'timeout'
]
