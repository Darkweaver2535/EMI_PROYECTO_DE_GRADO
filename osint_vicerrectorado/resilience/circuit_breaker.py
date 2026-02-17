"""
Circuit Breaker - Patrón de resiliencia para scrapers
Sistema OSINT EMI - Sprint 6

Implementa el patrón Circuit Breaker para proteger contra fallos en cascada:
- CLOSED: Operación normal, requests pasan
- OPEN: Tras N fallos consecutivos, bloquea requests (fail-fast)
- HALF_OPEN: Tras timeout, permite prueba de recuperación

Referencias:
- Martin Fowler: https://martinfowler.com/bliki/CircuitBreaker.html
- pybreaker docs: https://pybreaker.readthedocs.io/

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import logging
import threading
from datetime import datetime
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from enum import Enum

try:
    from pybreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerError
    PYBREAKER_AVAILABLE = True
except ImportError:
    PYBREAKER_AVAILABLE = False
    CircuitBreakerError = Exception

logger = logging.getLogger('OSINT.resilience.circuit_breaker')


class CircuitState(Enum):
    """Estados del Circuit Breaker"""
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


@dataclass
class CircuitBreakerConfig:
    """Configuración del Circuit Breaker"""
    failure_threshold: int = 5  # Fallos antes de abrir
    timeout_duration: int = 300  # Segundos en estado OPEN antes de HALF_OPEN
    expected_exception: tuple = (Exception,)  # Excepciones que cuentan como fallo
    exclude_exceptions: tuple = ()  # Excepciones que NO cuentan como fallo


class ScraperCircuitBreakerListener:
    """
    Listener personalizado para eventos del Circuit Breaker.
    
    Proporciona logging detallado y capacidad de enviar alertas
    cuando el estado del circuito cambia.
    """
    
    def __init__(self, alert_callback: Optional[Callable] = None):
        """
        Args:
            alert_callback: Función a llamar cuando circuito se abre
                           Signature: callback(source_name: str, message: str)
        """
        self.alert_callback = alert_callback
        self.state_history: list = []
        self._lock = threading.Lock()
    
    def state_change(self, cb, old_state, new_state):
        """
        Callback invocado cuando el estado del circuito cambia.
        
        Args:
            cb: Instancia del CircuitBreaker
            old_state: Estado anterior
            new_state: Nuevo estado
        """
        timestamp = datetime.now().isoformat()
        
        with self._lock:
            self.state_history.append({
                'timestamp': timestamp,
                'source': cb.name,
                'from_state': old_state.name if hasattr(old_state, 'name') else str(old_state),
                'to_state': new_state.name if hasattr(new_state, 'name') else str(new_state)
            })
        
        # Mantener solo las últimas 100 transiciones
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]
        
        old_name = old_state.name if hasattr(old_state, 'name') else str(old_state)
        new_name = new_state.name if hasattr(new_state, 'name') else str(new_state)
        
        logger.warning(
            f"Circuit breaker '{cb.name}' cambió de estado: {old_name} → {new_name}",
            extra={
                'source': cb.name,
                'old_state': old_name,
                'new_state': new_name,
                'timestamp': timestamp
            }
        )
        
        # Enviar alerta crítica si circuito se abre
        if new_name == 'open':
            message = f"🚨 Circuit breaker ABIERTO para {cb.name}. " \
                     f"Fuente deshabilitada temporalmente por fallos consecutivos."
            
            logger.critical(message, extra={'source': cb.name, 'event': 'circuit_open'})
            
            if self.alert_callback:
                try:
                    self.alert_callback(cb.name, message)
                except Exception as e:
                    logger.error(f"Error enviando alerta: {e}")
        
        # Log cuando circuito se recupera
        elif new_name == 'closed' and old_name in ('open', 'half_open'):
            message = f"✅ Circuit breaker RECUPERADO para {cb.name}. " \
                     f"Fuente habilitada nuevamente."
            
            logger.info(message, extra={'source': cb.name, 'event': 'circuit_recovered'})
    
    def failure(self, cb, exc):
        """Callback cuando ocurre un fallo"""
        logger.warning(
            f"Fallo registrado en circuit breaker '{cb.name}': {type(exc).__name__}",
            extra={
                'source': cb.name,
                'error_type': type(exc).__name__,
                'error_message': str(exc)
            }
        )
    
    def success(self, cb):
        """Callback cuando operación es exitosa"""
        logger.debug(
            f"Operación exitosa en circuit breaker '{cb.name}'",
            extra={'source': cb.name}
        )


class ScraperCircuitBreaker:
    """
    Circuit Breaker wrapper para scrapers OSINT.
    
    Proporciona protección fail-fast cuando una fuente está experimentando
    problemas, evitando sobrecarga del sistema y permitiendo recuperación.
    
    Estados:
    - CLOSED: Operación normal, todas las requests pasan
    - OPEN: Tras N fallos consecutivos, rechaza requests inmediatamente
    - HALF_OPEN: Tras timeout, permite una request de prueba
    
    Ejemplo de uso:
        cb = ScraperCircuitBreaker(
            source_name='facebook',
            failure_threshold=5,
            timeout_duration=300
        )
        
        try:
            result = cb.call(scraper.fetch_posts, url)
        except CircuitBreakerError:
            # Circuito abierto, manejar gracefully
            return []
    """
    
    # Registry global de circuit breakers
    _registry: Dict[str, 'ScraperCircuitBreaker'] = {}
    _registry_lock = threading.Lock()
    
    def __init__(
        self,
        source_name: str,
        failure_threshold: int = 5,
        timeout_duration: int = 300,
        expected_exception: tuple = (Exception,),
        exclude_exceptions: tuple = (),
        alert_callback: Optional[Callable] = None
    ):
        """
        Inicializa el Circuit Breaker para una fuente específica.
        
        Args:
            source_name: Nombre único de la fuente OSINT
            failure_threshold: Número de fallos consecutivos antes de abrir
            timeout_duration: Segundos en estado OPEN antes de pasar a HALF_OPEN
            expected_exception: Excepciones que cuentan como fallo
            exclude_exceptions: Excepciones que NO cuentan como fallo
            alert_callback: Función para enviar alertas
        """
        self.source_name = source_name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            timeout_duration=timeout_duration,
            expected_exception=expected_exception,
            exclude_exceptions=exclude_exceptions
        )
        
        self.listener = ScraperCircuitBreakerListener(alert_callback)
        
        # Estadísticas
        self._stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'rejected_calls': 0,
            'last_failure_time': None,
            'last_success_time': None
        }
        self._stats_lock = threading.Lock()
        
        if PYBREAKER_AVAILABLE:
            self.breaker = CircuitBreaker(
                name=source_name,
                fail_max=failure_threshold,
                reset_timeout=timeout_duration,
                exclude=list(exclude_exceptions),
                listeners=[self.listener]
            )
        else:
            # Implementación fallback sin pybreaker
            self.breaker = None
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            logger.warning(
                "pybreaker no disponible, usando implementación fallback",
                extra={'source': source_name}
            )
        
        # Registrar en registry global
        with self._registry_lock:
            self._registry[source_name] = self
        
        logger.info(
            f"Circuit breaker inicializado para '{source_name}'",
            extra={
                'source': source_name,
                'failure_threshold': failure_threshold,
                'timeout_duration': timeout_duration
            }
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta función protegida por el circuit breaker.
        
        Si circuito OPEN → lanza CircuitBreakerError inmediatamente
        Si circuito CLOSED/HALF_OPEN → ejecuta función
        
        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos keyword
            
        Returns:
            Resultado de la función
            
        Raises:
            CircuitBreakerError: Si circuito está abierto
            Exception: Cualquier excepción de la función
        """
        with self._stats_lock:
            self._stats['total_calls'] += 1
        
        try:
            if self.breaker:
                result = self.breaker.call(func, *args, **kwargs)
            else:
                result = self._fallback_call(func, *args, **kwargs)
            
            with self._stats_lock:
                self._stats['successful_calls'] += 1
                self._stats['last_success_time'] = datetime.now().isoformat()
            
            return result
            
        except CircuitBreakerError:
            with self._stats_lock:
                self._stats['rejected_calls'] += 1
            
            logger.warning(
                f"Request rechazada: circuit breaker '{self.source_name}' está ABIERTO",
                extra={'source': self.source_name, 'event': 'request_rejected'}
            )
            raise
            
        except Exception as e:
            with self._stats_lock:
                self._stats['failed_calls'] += 1
                self._stats['last_failure_time'] = datetime.now().isoformat()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Versión async de call() para funciones asíncronas.
        
        Args:
            func: Coroutine function a ejecutar
            *args: Argumentos posicionales
            **kwargs: Argumentos keyword
            
        Returns:
            Resultado de la coroutine
        """
        with self._stats_lock:
            self._stats['total_calls'] += 1
        
        try:
            if self.is_open:
                with self._stats_lock:
                    self._stats['rejected_calls'] += 1
                raise CircuitBreakerError(f"Circuit breaker '{self.source_name}' está abierto")
            
            result = await func(*args, **kwargs)
            
            with self._stats_lock:
                self._stats['successful_calls'] += 1
                self._stats['last_success_time'] = datetime.now().isoformat()
            
            # Registrar éxito (para pybreaker)
            if self.breaker:
                self._record_success()
            else:
                self._fallback_record_success()
            
            return result
            
        except CircuitBreakerError:
            raise
            
        except Exception as e:
            with self._stats_lock:
                self._stats['failed_calls'] += 1
                self._stats['last_failure_time'] = datetime.now().isoformat()
            
            # Registrar fallo
            if self.breaker:
                self._record_failure(e)
            else:
                self._fallback_record_failure(e)
            raise
    
    def _fallback_call(self, func: Callable, *args, **kwargs) -> Any:
        """Implementación fallback cuando pybreaker no está disponible"""
        import time
        
        # Verificar si debemos pasar a HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self.config.timeout_duration:
                    self._state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker '{self.source_name}' pasó a HALF_OPEN")
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.source_name}' está abierto"
                    )
        
        try:
            result = func(*args, **kwargs)
            
            # Éxito en HALF_OPEN → CLOSED
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.source_name}' recuperado: CLOSED")
            
            return result
            
        except self.config.exclude_exceptions:
            raise
            
        except self.config.expected_exception as e:
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.source_name}' ABIERTO tras {self._failure_count} fallos"
                )
            raise
    
    def _fallback_record_success(self):
        """Registra éxito en implementación fallback"""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
    
    def _fallback_record_failure(self, exc: Exception):
        """Registra fallo en implementación fallback"""
        import time
        
        if isinstance(exc, self.config.exclude_exceptions):
            return
        
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
    
    def _record_success(self):
        """Registra éxito para pybreaker"""
        # pybreaker maneja esto automáticamente en call()
        pass
    
    def _record_failure(self, exc: Exception):
        """Registra fallo para pybreaker"""
        # pybreaker maneja esto automáticamente en call()
        pass
    
    @property
    def is_open(self) -> bool:
        """Verifica si el circuito está abierto"""
        if self.breaker:
            return self.breaker.current_state.name == 'open'
        return self._state == CircuitState.OPEN
    
    @property
    def is_closed(self) -> bool:
        """Verifica si el circuito está cerrado"""
        if self.breaker:
            return self.breaker.current_state.name == 'closed'
        return self._state == CircuitState.CLOSED
    
    @property
    def is_half_open(self) -> bool:
        """Verifica si el circuito está en half-open"""
        if self.breaker:
            return self.breaker.current_state.name == 'half_open'
        return self._state == CircuitState.HALF_OPEN
    
    @property
    def current_state(self) -> str:
        """Retorna el estado actual del circuito"""
        if self.breaker:
            return self.breaker.current_state.name
        return self._state.value
    
    @property
    def failure_count(self) -> int:
        """Retorna el conteo actual de fallos"""
        if self.breaker:
            return self.breaker.fail_counter
        return self._failure_count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del circuit breaker.
        
        Returns:
            Dict con estadísticas de uso
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        stats['current_state'] = self.current_state
        stats['failure_count'] = self.failure_count
        stats['source_name'] = self.source_name
        stats['config'] = {
            'failure_threshold': self.config.failure_threshold,
            'timeout_duration': self.config.timeout_duration
        }
        
        return stats
    
    def reset(self):
        """Resetea el circuit breaker a estado CLOSED"""
        if self.breaker and hasattr(self.breaker, 'close'):
            self.breaker.close()
        else:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
        
        logger.info(
            f"Circuit breaker '{self.source_name}' reseteado manualmente",
            extra={'source': self.source_name}
        )
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """
        Retorna estadísticas de todos los circuit breakers registrados.
        
        Returns:
            Dict con stats de cada circuit breaker
        """
        with cls._registry_lock:
            return {
                name: cb.get_stats()
                for name, cb in cls._registry.items()
            }
    
    @classmethod
    def get_circuit_breaker(cls, source_name: str) -> Optional['ScraperCircuitBreaker']:
        """
        Obtiene un circuit breaker del registry por nombre.
        
        Args:
            source_name: Nombre de la fuente
            
        Returns:
            ScraperCircuitBreaker o None si no existe
        """
        with cls._registry_lock:
            return cls._registry.get(source_name)


# Exportar excepción para uso externo
__all__ = [
    'ScraperCircuitBreaker',
    'ScraperCircuitBreakerListener',
    'CircuitBreakerConfig',
    'CircuitState',
    'CircuitBreakerError'
]
