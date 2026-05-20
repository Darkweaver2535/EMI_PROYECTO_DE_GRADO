"""
Módulo de Recolección de Datos - Sistema OSINT EMI
===================================================

Recolecta datos de redes sociales usando la API de Apify.
Apify maneja proxies, CAPTCHAs y anti-detección automáticamente.

Componentes:
- BaseCollector: Clase base con interfaz común para todos los collectors
- ApifyClient: Cliente genérico para interactuar con la API de Apify
- FacebookCollector: Recolecta posts y comentarios de Facebook vía Apify
- TikTokCollector: Recolecta videos y comentarios de TikTok vía Apify

Autor: Sistema OSINT EMI
Fecha: Mayo 2026
"""

from scrapers.base_collector import BaseCollector

__all__ = [
    'BaseCollector',
]
