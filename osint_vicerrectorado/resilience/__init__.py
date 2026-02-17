"""
Módulo de Resiliencia - Sistema OSINT EMI
Sprint 6: Hardening y Automatización

Este módulo proporciona componentes de resiliencia para el sistema de recolección:
- Circuit Breaker: Protección contra fallos en cascada
- Retry Manager: Reintentos con backoff exponencial + jitter
- Rate Limiter: Control adaptativo de tasa de requests
- Timeout Manager: Gestión de timeouts configurables

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

from .circuit_breaker import ScraperCircuitBreaker, ScraperCircuitBreakerListener
from .retry_manager import RetryManager, RetryConfig
from .rate_limiter import AdaptiveRateLimiter, RateLimitConfig
from .timeout_manager import TimeoutManager, TimeoutConfig

__all__ = [
    'ScraperCircuitBreaker',
    'ScraperCircuitBreakerListener',
    'RetryManager',
    'RetryConfig',
    'AdaptiveRateLimiter',
    'RateLimitConfig',
    'TimeoutManager',
    'TimeoutConfig'
]

__version__ = '1.0.0'
