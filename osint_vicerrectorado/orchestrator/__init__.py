"""
Módulo Orchestrator - Sistema OSINT EMI Bolivia

Proporciona ejecución concurrente de scrapers con:
- Async/await con asyncio + aiohttp
- Gestión de ciclo de vida de scrapers
- Integración con resiliencia y métricas

Autor: Sistema OSINT EMI
Versión: 1.0.0
"""

from .scraper_orchestrator import (
    ScraperOrchestrator,
    OrchestratorConfig,
    ScraperTask,
    ScraperResult,
    OrchestratorStats,
)

__all__ = [
    'ScraperOrchestrator',
    'OrchestratorConfig',
    'ScraperTask',
    'ScraperResult',
    'OrchestratorStats',
]

__version__ = '1.0.0'
