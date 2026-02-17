"""
Módulo de Monitoring - Sistema OSINT EMI Bolivia

Este módulo proporciona:
- Exportador de métricas Prometheus
- Métricas personalizadas para scrapers
- Logger estructurado JSON

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

from .metrics import (
    ScraperMetrics,
    MetricsRegistry,
    # Métricas individuales
    scraper_requests_total,
    scraper_request_duration_seconds,
    scraper_errors_total,
    scraper_items_scraped_total,
    circuit_breaker_state,
    rate_limiter_requests_total,
    rate_limiter_throttled_total,
    active_scrapers,
    scraper_last_success_timestamp,
)

from .prometheus_exporter import (
    PrometheusExporter,
    create_metrics_app,
    start_metrics_server,
)

from .logger import (
    ScraperLogger,
    setup_logging,
    get_logger,
    LogContext,
)

__all__ = [
    # Métricas
    'ScraperMetrics',
    'MetricsRegistry',
    'scraper_requests_total',
    'scraper_request_duration_seconds',
    'scraper_errors_total',
    'scraper_items_scraped_total',
    'circuit_breaker_state',
    'rate_limiter_requests_total',
    'rate_limiter_throttled_total',
    'active_scrapers',
    'scraper_last_success_timestamp',
    # Exportador
    'PrometheusExporter',
    'create_metrics_app',
    'start_metrics_server',
    # Logger
    'ScraperLogger',
    'setup_logging',
    'get_logger',
    'LogContext',
]

__version__ = '1.0.0'
