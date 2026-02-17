"""
Adaptive Rate Limiter - Control inteligente de tasa de requests
Sistema OSINT EMI - Sprint 6

Implementa rate limiting que se adapta dinámicamente:
- Normal: respeta límite configurado (ej. 200 req/min)
- Detecta 429: reduce rate automáticamente
- Tras recuperación: incrementa gradualmente

Features:
- Token bucket algorithm
- Adaptive throttling basado en respuestas
- Respeta headers X-RateLimit-* y Retry-After
- Backpressure cuando downstream está saturado

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import asyncio
import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Deque
from contextlib import contextmanager, asynccontextmanager

logger = logging.getLogger('OSINT.resilience.rate_limiter')


@dataclass
class RateLimitConfig:
    """Configuración del rate limiter"""
    requests_per_minute: int = 200
    requests_per_second: float = 0  # Calculado automáticamente
    burst_size: int = 10  # Requests permitidos en ráfaga
    adaptive: bool = True  # Activar adaptación automática
    min_rpm: int = 10  # RPM mínimo (nunca bajar de esto)
    recovery_factor: float = 1.1  # Factor de incremento en recuperación
    reduction_factor: float = 0.5  # Factor de reducción ante 429
    recovery_delay: int = 300  # Segundos antes de intentar recuperar rate
    
    def __post_init__(self):
        if self.requests_per_second == 0:
            self.requests_per_second = self.requests_per_minute / 60.0


@dataclass
class RateLimitStats:
    """Estadísticas del rate limiter"""
    total_requests: int = 0
    allowed_requests: int = 0
    throttled_requests: int = 0
    rate_limit_hits: int = 0  # Veces que se detectó 429
    current_rpm: float = 0
    total_wait_time: float = 0
    last_429_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'total_requests': self.total_requests,
            'allowed_requests': self.allowed_requests,
            'throttled_requests': self.throttled_requests,
            'rate_limit_hits': self.rate_limit_hits,
            'current_rpm': self.current_rpm,
            'total_wait_time_seconds': round(self.total_wait_time, 2),
            'last_429_time': self.last_429_time.isoformat() if self.last_429_time else None,
            'throttle_rate': self.throttled_requests / max(self.total_requests, 1)
        }


class AdaptiveRateLimiter:
    """
    Rate limiter que se adapta dinámicamente según respuestas del servidor.
    
    Algoritmo:
    1. Token bucket para control de tasa
    2. Detección de 429 → reduce rate 50%
    3. Tras 5 min sin 429 → incrementa 10% gradualmente
    4. Respeta headers Retry-After y X-RateLimit-*
    
    Ejemplo de uso:
        limiter = AdaptiveRateLimiter(requests_per_minute=200)
        
        async def fetch():
            await limiter.acquire()
            response = await make_request()
            limiter.record_response(response)
            return response
    """
    
    def __init__(
        self,
        requests_per_minute: int = 200,
        adaptive: bool = True,
        source_name: str = 'default'
    ):
        """
        Inicializa el rate limiter adaptativo.
        
        Args:
            requests_per_minute: Límite de requests por minuto
            adaptive: Si True, ajusta automáticamente según respuestas
            source_name: Nombre de la fuente para logging
        """
        self.source_name = source_name
        self.config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            adaptive=adaptive
        )
        
        self.base_rpm = requests_per_minute
        self.current_rpm = requests_per_minute
        
        # Token bucket
        self.tokens = float(self.config.burst_size)
        self.max_tokens = float(self.config.burst_size)
        self.last_token_time = time.monotonic()
        
        # Historial de requests (para cálculo de rate real)
        self.request_times: Deque[datetime] = deque(maxlen=requests_per_minute)
        
        # Estadísticas
        self.stats = RateLimitStats(current_rpm=requests_per_minute)
        
        # Thread safety
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock() if asyncio.get_event_loop_policy() else None
        
        # Headers de rate limit del servidor
        self.server_rate_info: Dict[str, Any] = {}
        
        logger.info(
            f"AdaptiveRateLimiter inicializado para '{source_name}'",
            extra={
                'source': source_name,
                'rpm': requests_per_minute,
                'adaptive': adaptive
            }
        )
    
    def _refill_tokens(self):
        """Recarga tokens basado en tiempo transcurrido"""
        now = time.monotonic()
        elapsed = now - self.last_token_time
        self.last_token_time = now
        
        # Calcular tokens a añadir basado en rate actual
        tokens_per_second = self.current_rpm / 60.0
        new_tokens = elapsed * tokens_per_second
        
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
    
    def acquire(self) -> float:
        """
        Solicita permiso para hacer request (versión síncrona).
        
        Bloquea si es necesario hasta que haya tokens disponibles.
        
        Returns:
            float: Tiempo que se esperó (0 si no hubo espera)
        """
        with self._lock:
            self.stats.total_requests += 1
            wait_time = 0.0
            
            # Limpiar requests antiguos
            self._clean_old_requests()
            
            # Refrescar tokens
            self._refill_tokens()
            
            # Si no hay tokens, calcular espera
            if self.tokens < 1.0:
                tokens_needed = 1.0 - self.tokens
                tokens_per_second = self.current_rpm / 60.0
                wait_time = tokens_needed / tokens_per_second
                
                logger.debug(
                    f"Rate limit: esperando {wait_time:.3f}s",
                    extra={
                        'source': self.source_name,
                        'wait_time': wait_time,
                        'current_rpm': self.current_rpm
                    }
                )
                
                self.stats.throttled_requests += 1
                self.stats.total_wait_time += wait_time
                
                # Esperar
                time.sleep(wait_time)
                self._refill_tokens()
            
            # Consumir token
            self.tokens -= 1.0
            self.stats.allowed_requests += 1
            self.request_times.append(datetime.now())
            
            return wait_time
    
    async def acquire_async(self) -> float:
        """
        Solicita permiso para hacer request (versión async).
        
        Returns:
            float: Tiempo que se esperó (0 si no hubo espera)
        """
        # Usar lock async si está disponible
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        
        async with self._async_lock:
            self.stats.total_requests += 1
            wait_time = 0.0
            
            # Limpiar requests antiguos
            self._clean_old_requests()
            
            # Refrescar tokens
            self._refill_tokens()
            
            # Si no hay tokens, calcular espera
            if self.tokens < 1.0:
                tokens_needed = 1.0 - self.tokens
                tokens_per_second = max(self.current_rpm / 60.0, 0.1)
                wait_time = tokens_needed / tokens_per_second
                
                logger.debug(
                    f"Rate limit async: esperando {wait_time:.3f}s",
                    extra={
                        'source': self.source_name,
                        'wait_time': wait_time
                    }
                )
                
                self.stats.throttled_requests += 1
                self.stats.total_wait_time += wait_time
                
                # Esperar async
                await asyncio.sleep(wait_time)
                self._refill_tokens()
            
            # Consumir token
            self.tokens -= 1.0
            self.stats.allowed_requests += 1
            self.request_times.append(datetime.now())
            
            return wait_time
    
    def handle_429_error(self, retry_after: Optional[int] = None):
        """
        Maneja respuesta 429 (Too Many Requests).
        
        Reduce el rate y opcionalmente espera según Retry-After.
        
        Args:
            retry_after: Segundos sugeridos por header Retry-After
        """
        with self._lock:
            self.stats.rate_limit_hits += 1
            self.stats.last_429_time = datetime.now()
            
            old_rpm = self.current_rpm
            
            if self.config.adaptive:
                # Reducir rate según factor configurado
                self.current_rpm = max(
                    int(self.current_rpm * self.config.reduction_factor),
                    self.config.min_rpm
                )
                
                logger.warning(
                    f"Rate limit exceeded en '{self.source_name}'. "
                    f"Reduciendo RPM: {old_rpm} → {self.current_rpm}",
                    extra={
                        'source': self.source_name,
                        'old_rpm': old_rpm,
                        'new_rpm': self.current_rpm,
                        'retry_after': retry_after
                    }
                )
            
            self.stats.current_rpm = self.current_rpm
            
            # Si server sugiere delay, esperar
            if retry_after and retry_after > 0:
                logger.info(
                    f"Esperando {retry_after}s según Retry-After header",
                    extra={'source': self.source_name, 'retry_after': retry_after}
                )
                time.sleep(retry_after)
    
    async def handle_429_error_async(self, retry_after: Optional[int] = None):
        """Versión async de handle_429_error"""
        # Actualizar stats (síncrono)
        with self._lock:
            self.stats.rate_limit_hits += 1
            self.stats.last_429_time = datetime.now()
            
            old_rpm = self.current_rpm
            
            if self.config.adaptive:
                self.current_rpm = max(
                    int(self.current_rpm * self.config.reduction_factor),
                    self.config.min_rpm
                )
                
                logger.warning(
                    f"Rate limit exceeded en '{self.source_name}'. "
                    f"Reduciendo RPM: {old_rpm} → {self.current_rpm}"
                )
            
            self.stats.current_rpm = self.current_rpm
        
        # Esperar async si hay retry_after
        if retry_after and retry_after > 0:
            logger.info(f"Esperando {retry_after}s según Retry-After")
            await asyncio.sleep(retry_after)
    
    def handle_success(self):
        """
        Registra request exitosa y considera incrementar rate.
        
        Si ha pasado suficiente tiempo sin errores 429, incrementa
        gradualmente el rate hacia el valor base.
        """
        with self._lock:
            if not self.config.adaptive:
                return
            
            # Si no hay 429 reciente, considerar incrementar
            if self.stats.last_429_time:
                elapsed = (datetime.now() - self.stats.last_429_time).total_seconds()
                
                if elapsed > self.config.recovery_delay:
                    # Suficiente tiempo sin problemas, incrementar rate
                    if self.current_rpm < self.base_rpm:
                        old_rpm = self.current_rpm
                        self.current_rpm = min(
                            int(self.current_rpm * self.config.recovery_factor),
                            self.base_rpm
                        )
                        
                        if self.current_rpm != old_rpm:
                            logger.info(
                                f"Recuperando rate para '{self.source_name}': "
                                f"{old_rpm} → {self.current_rpm}",
                                extra={
                                    'source': self.source_name,
                                    'old_rpm': old_rpm,
                                    'new_rpm': self.current_rpm
                                }
                            )
                        
                        self.stats.current_rpm = self.current_rpm
    
    def record_response(self, response) -> None:
        """
        Registra respuesta HTTP y ajusta rate si es necesario.
        
        Extrae información de headers de rate limit:
        - X-RateLimit-Remaining
        - X-RateLimit-Reset
        - Retry-After
        
        Args:
            response: Objeto response HTTP (requests o aiohttp)
        """
        try:
            status_code = getattr(response, 'status_code', None) or getattr(response, 'status', None)
            
            if status_code == 429:
                retry_after = self._get_retry_after(response)
                self.handle_429_error(retry_after)
                return
            
            if status_code and 200 <= status_code < 300:
                self.handle_success()
            
            # Extraer info de rate limit del servidor
            self._parse_rate_limit_headers(response)
            
        except Exception as e:
            logger.debug(f"Error procesando response: {e}")
    
    def _get_retry_after(self, response) -> Optional[int]:
        """Extrae valor Retry-After de response"""
        try:
            headers = getattr(response, 'headers', {})
            retry_after = headers.get('Retry-After') or headers.get('retry-after')
            
            if retry_after:
                try:
                    return int(retry_after)
                except ValueError:
                    # Es una fecha HTTP
                    from email.utils import parsedate_to_datetime
                    retry_date = parsedate_to_datetime(retry_after)
                    return max(0, int((retry_date - datetime.now()).total_seconds()))
        except Exception:
            pass
        
        return None
    
    def _parse_rate_limit_headers(self, response):
        """Extrae headers de rate limit del servidor"""
        try:
            headers = getattr(response, 'headers', {})
            
            # Headers comunes de rate limit
            remaining = headers.get('X-RateLimit-Remaining') or headers.get('x-ratelimit-remaining')
            limit = headers.get('X-RateLimit-Limit') or headers.get('x-ratelimit-limit')
            reset = headers.get('X-RateLimit-Reset') or headers.get('x-ratelimit-reset')
            
            if remaining is not None:
                self.server_rate_info['remaining'] = int(remaining)
            if limit is not None:
                self.server_rate_info['limit'] = int(limit)
            if reset is not None:
                self.server_rate_info['reset'] = reset
            
            # Ajustar rate si estamos cerca del límite
            if remaining is not None and int(remaining) < 10:
                logger.warning(
                    f"Cerca del rate limit del servidor: {remaining} requests restantes",
                    extra={
                        'source': self.source_name,
                        'remaining': remaining
                    }
                )
                
        except Exception:
            pass
    
    def _clean_old_requests(self):
        """Elimina requests más antiguos que 1 minuto"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        while self.request_times and self.request_times[0] < cutoff:
            self.request_times.popleft()
    
    @property
    def requests_in_last_minute(self) -> int:
        """Retorna número de requests en el último minuto"""
        self._clean_old_requests()
        return len(self.request_times)
    
    @property
    def current_rate(self) -> float:
        """Retorna rate actual (requests por minuto)"""
        return self.current_rpm
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del rate limiter"""
        stats = self.stats.to_dict()
        stats['source_name'] = self.source_name
        stats['base_rpm'] = self.base_rpm
        stats['current_rpm'] = self.current_rpm
        stats['requests_last_minute'] = self.requests_in_last_minute
        stats['tokens_available'] = round(self.tokens, 2)
        stats['server_rate_info'] = self.server_rate_info
        return stats
    
    def reset(self):
        """Resetea el rate limiter a valores iniciales"""
        with self._lock:
            self.current_rpm = self.base_rpm
            self.tokens = float(self.config.burst_size)
            self.request_times.clear()
            self.stats = RateLimitStats(current_rpm=self.base_rpm)
            self.server_rate_info = {}
            
            logger.info(
                f"Rate limiter '{self.source_name}' reseteado",
                extra={'source': self.source_name}
            )
    
    @contextmanager
    def rate_limited(self):
        """
        Context manager para operaciones rate limited.
        
        Ejemplo:
            with limiter.rate_limited():
                response = requests.get(url)
        """
        self.acquire()
        try:
            yield
        finally:
            pass
    
    @asynccontextmanager
    async def rate_limited_async(self):
        """
        Context manager async para operaciones rate limited.
        
        Ejemplo:
            async with limiter.rate_limited_async():
                response = await session.get(url)
        """
        await self.acquire_async()
        try:
            yield
        finally:
            pass


class BackpressureController:
    """
    Controlador de backpressure para cuando el downstream está saturado.
    
    Monitorea una cola o sistema downstream y pausa el upstream
    cuando el downstream no puede procesar más datos.
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        pause_threshold: float = 0.8,  # Pausar al 80% de capacidad
        resume_threshold: float = 0.5,  # Reanudar al 50% de capacidad
        check_interval: float = 1.0  # Segundos entre checks
    ):
        self.max_queue_size = max_queue_size
        self.pause_threshold = pause_threshold
        self.resume_threshold = resume_threshold
        self.check_interval = check_interval
        
        self.is_paused = False
        self.current_queue_size = 0
        self._lock = threading.Lock()
    
    def update_queue_size(self, size: int):
        """Actualiza el tamaño actual de la cola downstream"""
        with self._lock:
            self.current_queue_size = size
            
            fill_ratio = size / self.max_queue_size
            
            if not self.is_paused and fill_ratio >= self.pause_threshold:
                self.is_paused = True
                logger.warning(
                    f"Backpressure activado: cola al {fill_ratio*100:.1f}%",
                    extra={'queue_size': size, 'max_size': self.max_queue_size}
                )
            
            elif self.is_paused and fill_ratio <= self.resume_threshold:
                self.is_paused = False
                logger.info(
                    f"Backpressure desactivado: cola al {fill_ratio*100:.1f}%",
                    extra={'queue_size': size, 'max_size': self.max_queue_size}
                )
    
    async def wait_if_paused(self):
        """Espera si backpressure está activo"""
        while self.is_paused:
            logger.debug("Esperando por backpressure...")
            await asyncio.sleep(self.check_interval)
    
    def should_pause(self) -> bool:
        """Verifica si se debe pausar por backpressure"""
        return self.is_paused


__all__ = [
    'AdaptiveRateLimiter',
    'RateLimitConfig',
    'RateLimitStats',
    'BackpressureController'
]
