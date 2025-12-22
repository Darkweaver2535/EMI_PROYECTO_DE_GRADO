"""
Paquete scrapers - Módulo de recolección OSINT
Sistema de Analítica EMI

Contiene los scrapers para Facebook y TikTok con técnicas anti-detección.
"""

from scrapers.base_scraper import BaseScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.tiktok_scraper import TikTokScraper

__all__ = ['BaseScraper', 'FacebookScraper', 'TikTokScraper']
