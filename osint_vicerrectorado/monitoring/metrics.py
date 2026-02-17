"""
Métricas Prometheus para el Sistema de Scrapers OSINT EMI

Define todas las métricas personalizadas para monitorear:
- Rendimiento de scrapers
- Estado de circuit breakers
- Rate limiting
- Errores y latencias

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from functools import wraps
from contextlib import contextmanager
import threading

# Intentar importar prometheus_client
try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, REGISTRY,
        generate_latest, CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Clases mock para cuando prometheus_client no está disponible
    class MockMetric:
        def __init__(self, *args, **kwargs):
            self._value = 0
            self._labels_values = {}
        
        def labels(self, *args, **kwargs):
            return self
        
        def inc(self, value=1):
            self._value += value
        
        def dec(self, value=1):
            self._value -= value
        
        def set(self, value):
            self._value = value
        
        def observe(self, value):
            pass
        
        def time(self):
            return self._timer_context()
        
        @contextmanager
        def _timer_context(self):
            yield
    
    Counter = Histogram = Gauge = Summary = Info = MockMetric
    REGISTRY = None


# =============================================================================
# DEFINICIÓN DE MÉTRICAS
# =============================================================================

# Registro personalizado para métricas de scrapers
if PROMETHEUS_AVAILABLE:
    SCRAPER_REGISTRY = CollectorRegistry()
else:
    SCRAPER_REGISTRY = None


# --- Métricas de Requests ---

scraper_requests_total = Counter(
    'scraper_requests_total',
    'Total de requests realizados por los scrapers',
    ['scraper_name', 'source', 'method', 'status_code'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_request_duration_seconds = Histogram(
    'scraper_request_duration_seconds',
    'Duración de requests de scrapers en segundos',
    ['scraper_name', 'source', 'operation'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Errores ---

scraper_errors_total = Counter(
    'scraper_errors_total',
    'Total de errores en scrapers',
    ['scraper_name', 'source', 'error_type', 'recoverable'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_retries_total = Counter(
    'scraper_retries_total',
    'Total de reintentos realizados',
    ['scraper_name', 'source', 'attempt_number'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Items Scrapeados ---

scraper_items_scraped_total = Counter(
    'scraper_items_scraped_total',
    'Total de items extraídos exitosamente',
    ['scraper_name', 'source', 'item_type'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_items_failed_total = Counter(
    'scraper_items_failed_total',
    'Total de items que fallaron al extraerse',
    ['scraper_name', 'source', 'failure_reason'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Circuit Breaker ---

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Estado actual del circuit breaker (0=closed, 1=open, 2=half-open)',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

circuit_breaker_failures_total = Counter(
    'circuit_breaker_failures_total',
    'Total de fallas registradas por el circuit breaker',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

circuit_breaker_state_changes_total = Counter(
    'circuit_breaker_state_changes_total',
    'Total de cambios de estado del circuit breaker',
    ['scraper_name', 'source', 'from_state', 'to_state'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Rate Limiter ---

rate_limiter_requests_total = Counter(
    'rate_limiter_requests_total',
    'Total de requests procesados por el rate limiter',
    ['scraper_name', 'source', 'result'],  # result: allowed, throttled, rejected
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

rate_limiter_throttled_total = Counter(
    'rate_limiter_throttled_total',
    'Total de requests throttled por rate limiting',
    ['scraper_name', 'source', 'reason'],  # reason: token_bucket, adaptive, 429_response
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

rate_limiter_current_rate = Gauge(
    'rate_limiter_current_rate_rpm',
    'Tasa actual del rate limiter en requests por minuto',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

rate_limiter_wait_time_seconds = Histogram(
    'rate_limiter_wait_time_seconds',
    'Tiempo de espera debido al rate limiter',
    ['scraper_name', 'source'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Timeout ---

timeout_total = Counter(
    'scraper_timeout_total',
    'Total de timeouts ocurridos',
    ['scraper_name', 'source', 'operation', 'timeout_type'],  # connect, read, total
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

timeout_duration_seconds = Gauge(
    'scraper_timeout_duration_seconds',
    'Configuración actual de timeout en segundos',
    ['scraper_name', 'source', 'timeout_type'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Estado General ---

active_scrapers = Gauge(
    'active_scrapers',
    'Número de scrapers actualmente ejecutándose',
    ['environment'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_last_success_timestamp = Gauge(
    'scraper_last_success_timestamp',
    'Timestamp del último scrape exitoso',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_last_run_timestamp = Gauge(
    'scraper_last_run_timestamp',
    'Timestamp de la última ejecución',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

scraper_health = Gauge(
    'scraper_health',
    'Estado de salud del scraper (1=healthy, 0=unhealthy)',
    ['scraper_name', 'source'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Métricas de Cola (Celery) ---

queue_tasks_total = Counter(
    'scraper_queue_tasks_total',
    'Total de tareas encoladas',
    ['queue_name', 'task_type', 'status'],  # status: queued, started, completed, failed
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

queue_task_duration_seconds = Histogram(
    'scraper_queue_task_duration_seconds',
    'Duración de tareas de cola en segundos',
    ['queue_name', 'task_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()

queue_pending_tasks = Gauge(
    'scraper_queue_pending_tasks',
    'Número de tareas pendientes en la cola',
    ['queue_name'],
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# --- Info Métrica ---

scraper_info = Info(
    'scraper',
    'Información del sistema de scrapers',
    registry=SCRAPER_REGISTRY
) if PROMETHEUS_AVAILABLE else MockMetric()


# =============================================================================
# CLASE DE MÉTRICAS AGREGADAS
# =============================================================================

@dataclass
class MetricsSnapshot:
    """Snapshot de métricas en un momento dado."""
    timestamp: float
    scraper_name: str
    source: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_items: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_rate: float = 0.0
    circuit_breaker_state: str = "closed"
    current_rate_rpm: float = 0.0


class ScraperMetrics:
    """
    Clase helper para registrar métricas de un scraper específico.
    
    Proporciona una interfaz simplificada para todas las métricas.
    
    Ejemplo:
        metrics = ScraperMetrics("facebook_scraper", "facebook.com")
        
        with metrics.track_request("fetch_posts"):
            response = await fetch_posts()
        
        metrics.record_items_scraped(len(posts), "post")
    """
    
    def __init__(self, scraper_name: str, source: str):
        self.scraper_name = scraper_name
        self.source = source
        self._lock = threading.Lock()
        
        # Estadísticas internas para cálculos
        self._request_latencies: List[float] = []
        self._max_latencies = 1000  # Mantener últimas 1000 latencias
        
    def record_request(
        self,
        method: str = "GET",
        status_code: int = 200,
        duration: Optional[float] = None,
        operation: str = "request"
    ):
        """Registra un request completado."""
        scraper_requests_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            method=method,
            status_code=str(status_code)
        ).inc()
        
        if duration is not None:
            scraper_request_duration_seconds.labels(
                scraper_name=self.scraper_name,
                source=self.source,
                operation=operation
            ).observe(duration)
            
            # Guardar latencia para estadísticas
            with self._lock:
                self._request_latencies.append(duration)
                if len(self._request_latencies) > self._max_latencies:
                    self._request_latencies = self._request_latencies[-self._max_latencies:]
    
    def record_error(
        self,
        error_type: str,
        recoverable: bool = True
    ):
        """Registra un error."""
        scraper_errors_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            error_type=error_type,
            recoverable=str(recoverable).lower()
        ).inc()
    
    def record_retry(self, attempt_number: int):
        """Registra un reintento."""
        scraper_retries_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            attempt_number=str(attempt_number)
        ).inc()
    
    def record_items_scraped(self, count: int, item_type: str = "item"):
        """Registra items extraídos exitosamente."""
        scraper_items_scraped_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            item_type=item_type
        ).inc(count)
    
    def record_items_failed(self, count: int, failure_reason: str):
        """Registra items que fallaron."""
        scraper_items_failed_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            failure_reason=failure_reason
        ).inc(count)
    
    def set_circuit_breaker_state(self, state: str):
        """
        Actualiza el estado del circuit breaker.
        
        Args:
            state: "closed", "open", o "half-open"
        """
        state_value = {"closed": 0, "open": 1, "half-open": 2}.get(state.lower(), 0)
        circuit_breaker_state.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(state_value)
    
    def record_circuit_breaker_failure(self):
        """Registra una falla del circuit breaker."""
        circuit_breaker_failures_total.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).inc()
    
    def record_circuit_breaker_state_change(self, from_state: str, to_state: str):
        """Registra un cambio de estado del circuit breaker."""
        circuit_breaker_state_changes_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            from_state=from_state,
            to_state=to_state
        ).inc()
    
    def record_rate_limit_request(self, result: str):
        """
        Registra un request procesado por el rate limiter.
        
        Args:
            result: "allowed", "throttled", o "rejected"
        """
        rate_limiter_requests_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            result=result
        ).inc()
    
    def record_throttle(self, reason: str, wait_time: float = 0.0):
        """Registra un throttle del rate limiter."""
        rate_limiter_throttled_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            reason=reason
        ).inc()
        
        if wait_time > 0:
            rate_limiter_wait_time_seconds.labels(
                scraper_name=self.scraper_name,
                source=self.source
            ).observe(wait_time)
    
    def set_current_rate(self, rpm: float):
        """Actualiza la tasa actual del rate limiter."""
        rate_limiter_current_rate.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(rpm)
    
    def record_timeout(self, operation: str, timeout_type: str):
        """Registra un timeout."""
        timeout_total.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            operation=operation,
            timeout_type=timeout_type
        ).inc()
    
    def set_timeout_config(self, timeout_type: str, seconds: float):
        """Actualiza la configuración de timeout."""
        timeout_duration_seconds.labels(
            scraper_name=self.scraper_name,
            source=self.source,
            timeout_type=timeout_type
        ).set(seconds)
    
    def record_success(self):
        """Registra un scrape exitoso."""
        scraper_last_success_timestamp.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(time.time())
        
        scraper_health.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(1)
    
    def record_run(self):
        """Registra una ejecución del scraper."""
        scraper_last_run_timestamp.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(time.time())
    
    def set_unhealthy(self):
        """Marca el scraper como unhealthy."""
        scraper_health.labels(
            scraper_name=self.scraper_name,
            source=self.source
        ).set(0)
    
    @contextmanager
    def track_request(self, operation: str = "request", method: str = "GET"):
        """
        Context manager para trackear automáticamente un request.
        
        Ejemplo:
            with metrics.track_request("fetch_posts"):
                response = await client.get(url)
        """
        start_time = time.time()
        status_code = 200
        error_occurred = False
        
        try:
            yield
        except Exception as e:
            error_occurred = True
            error_type = type(e).__name__
            self.record_error(error_type, recoverable=True)
            
            # Inferir status code del error si es posible
            if hasattr(e, 'status') or hasattr(e, 'status_code'):
                status_code = getattr(e, 'status', None) or getattr(e, 'status_code', 500)
            else:
                status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            if not error_occurred:
                status_code = 200
            self.record_request(
                method=method,
                status_code=status_code,
                duration=duration,
                operation=operation
            )
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Obtiene estadísticas de latencia."""
        with self._lock:
            if not self._request_latencies:
                return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
            
            sorted_latencies = sorted(self._request_latencies)
            n = len(sorted_latencies)
            
            return {
                "avg": sum(sorted_latencies) / n,
                "p50": sorted_latencies[int(n * 0.5)],
                "p95": sorted_latencies[int(n * 0.95)] if n > 20 else sorted_latencies[-1],
                "p99": sorted_latencies[int(n * 0.99)] if n > 100 else sorted_latencies[-1],
            }


class MetricsRegistry:
    """
    Registro global de métricas para todos los scrapers.
    
    Permite acceder a métricas de cualquier scraper desde cualquier parte del código.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._metrics: Dict[str, ScraperMetrics] = {}
                cls._instance._initialized = False
            return cls._instance
    
    def initialize(self, info: Dict[str, str] = None):
        """Inicializa el registro con información del sistema."""
        if not self._initialized and PROMETHEUS_AVAILABLE:
            default_info = {
                "version": "1.0.0",
                "environment": "production",
                "system": "osint_emi"
            }
            if info:
                default_info.update(info)
            
            try:
                scraper_info.info(default_info)
            except Exception:
                pass  # Info ya establecida
            
            self._initialized = True
    
    def get_or_create(self, scraper_name: str, source: str) -> ScraperMetrics:
        """Obtiene o crea métricas para un scraper."""
        key = f"{scraper_name}:{source}"
        
        if key not in self._metrics:
            with self._lock:
                if key not in self._metrics:
                    self._metrics[key] = ScraperMetrics(scraper_name, source)
        
        return self._metrics[key]
    
    def get_all_metrics(self) -> Dict[str, ScraperMetrics]:
        """Obtiene todas las métricas registradas."""
        return self._metrics.copy()
    
    def set_active_scrapers(self, count: int, environment: str = "production"):
        """Actualiza el número de scrapers activos."""
        active_scrapers.labels(environment=environment).set(count)
    
    def increment_active_scrapers(self, environment: str = "production"):
        """Incrementa el contador de scrapers activos."""
        active_scrapers.labels(environment=environment).inc()
    
    def decrement_active_scrapers(self, environment: str = "production"):
        """Decrementa el contador de scrapers activos."""
        active_scrapers.labels(environment=environment).dec()


# =============================================================================
# DECORADORES DE MÉTRICAS
# =============================================================================

def track_duration(
    scraper_name: str,
    source: str,
    operation: str = "request"
) -> Callable:
    """
    Decorador para trackear la duración de una función.
    
    Ejemplo:
        @track_duration("facebook_scraper", "facebook.com", "fetch_posts")
        async def fetch_posts():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                scraper_request_duration_seconds.labels(
                    scraper_name=scraper_name,
                    source=source,
                    operation=operation
                ).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                scraper_request_duration_seconds.labels(
                    scraper_name=scraper_name,
                    source=source,
                    operation=operation
                ).observe(duration)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def count_errors(
    scraper_name: str,
    source: str,
    error_type: str = "unknown"
) -> Callable:
    """
    Decorador para contar errores de una función.
    
    Ejemplo:
        @count_errors("facebook_scraper", "facebook.com", "parse_error")
        def parse_html(html):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                scraper_errors_total.labels(
                    scraper_name=scraper_name,
                    source=source,
                    error_type=error_type or type(e).__name__,
                    recoverable="true"
                ).inc()
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                scraper_errors_total.labels(
                    scraper_name=scraper_name,
                    source=source,
                    error_type=error_type or type(e).__name__,
                    recoverable="true"
                ).inc()
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def generate_metrics() -> bytes:
    """Genera la salida de métricas en formato Prometheus."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest(SCRAPER_REGISTRY)
    return b""


def get_content_type() -> str:
    """Obtiene el content type para métricas Prometheus."""
    if PROMETHEUS_AVAILABLE:
        return CONTENT_TYPE_LATEST
    return "text/plain"


def reset_all_metrics():
    """Resetea todas las métricas (útil para tests)."""
    # Las métricas de Prometheus no se pueden resetear fácilmente
    # Esta función es principalmente para tests
    pass
