"""
ResilientBaseScraper - Clase base con resiliencia para scrapers OSINT
Sistema de Analítica EMI - Sprint 6 Hardening

Extiende BaseScraper agregando:
- Circuit Breaker para fail-fast
- Rate Limiting adaptativo
- Retry con exponential backoff
- Timeouts configurables
- Métricas Prometheus
- Logging estructurado JSON

Autor: Sistema OSINT EMI
Versión: 2.0.0 (Sprint 6)
"""

import asyncio
import os
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
import logging
import aiohttp

# Importar módulos de resiliencia
try:
    from resilience import (
        ScraperCircuitBreaker, CircuitBreakerConfig,
        RetryManager, RetryConfig,
        AdaptiveRateLimiter, RateLimitConfig,
        TimeoutManager, TimeoutConfig
    )
    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

# Importar módulos de monitoring
try:
    from monitoring import (
        ScraperMetrics, MetricsRegistry,
        ScraperLogger, get_logger, setup_logging
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Playwright (opcional para scraping con browser)
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class ResilientScraperConfig:
    """Configuración completa para un scraper resiliente."""
    # Identificación
    source_name: str
    source_url: str
    
    # Scraping básico
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    delay_min_seconds: float = 2.0
    delay_max_seconds: float = 5.0
    scroll_pause_seconds: float = 2.0
    timeout_ms: int = 30000
    
    # Rate Limiting
    requests_per_minute: int = 60
    adaptive_rate_limiting: bool = True
    min_rpm: int = 10
    max_rpm: int = 120
    
    # Circuit Breaker
    failure_threshold: int = 5
    circuit_timeout_seconds: int = 300
    
    # Retry
    max_retries: int = 3
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 60.0
    
    # Timeouts
    connect_timeout: float = 10.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0
    
    # Selectores CSS (con fallbacks)
    css_selectors: Dict[str, List[str]] = field(default_factory=dict)
    
    # Extra
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResilientScraperConfig':
        """Crea configuración desde diccionario."""
        return cls(
            source_name=data.get('source_name', 'unknown'),
            source_url=data.get('source_url', ''),
            headless=data.get('headless', True),
            viewport_width=data.get('viewport_width', 1920),
            viewport_height=data.get('viewport_height', 1080),
            delay_min_seconds=data.get('delay_min_seconds', 2.0),
            delay_max_seconds=data.get('delay_max_seconds', 5.0),
            scroll_pause_seconds=data.get('scroll_pause_seconds', 2.0),
            timeout_ms=data.get('timeout_ms', 30000),
            requests_per_minute=data.get('requests_per_minute', 60),
            adaptive_rate_limiting=data.get('adaptive_rate_limiting', True),
            min_rpm=data.get('min_rpm', 10),
            max_rpm=data.get('max_rpm', 120),
            failure_threshold=data.get('failure_threshold', 5),
            circuit_timeout_seconds=data.get('circuit_timeout_seconds', 300),
            max_retries=data.get('max_retries', 3),
            initial_retry_delay=data.get('initial_retry_delay', 1.0),
            max_retry_delay=data.get('max_retry_delay', 60.0),
            connect_timeout=data.get('connect_timeout', 10.0),
            read_timeout=data.get('read_timeout', 30.0),
            total_timeout=data.get('total_timeout', 60.0),
            css_selectors=data.get('css_selectors', {}),
            extra_config=data.get('extra_config', {})
        )


# =============================================================================
# SCRAPER BASE RESILIENTE
# =============================================================================

class ResilientBaseScraper(ABC):
    """
    Clase base abstracta para scrapers con resiliencia completa.
    
    Características:
    - Circuit Breaker: Falla rápido cuando un servicio no responde
    - Rate Limiting: Adapta la velocidad según respuestas 429
    - Retry: Reintentos con backoff exponencial + jitter
    - Timeouts: Timeouts configurables por operación
    - Métricas: Integración con Prometheus
    - Logging: Logs estructurados JSON
    
    Uso:
        class FacebookScraper(ResilientBaseScraper):
            async def collect_data(self, limit: int) -> List[Dict]:
                # Implementación específica
                pass
        
        config = ResilientScraperConfig(
            source_name="facebook",
            source_url="https://facebook.com/page"
        )
        scraper = FacebookScraper(config)
        data = await scraper.run(limit=100)
    """
    
    # User-Agents para rotación
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    
    def __init__(self, config: ResilientScraperConfig):
        """
        Inicializa el scraper con configuración resiliente.
        
        Args:
            config: Configuración del scraper
        """
        self.config = config
        self.source_name = config.source_name
        self.source_url = config.source_url
        
        # Logger
        if MONITORING_AVAILABLE:
            setup_logging()
            self.logger = get_logger(config.source_name, config.source_url)
        else:
            self.logger = logging.getLogger(f"scraper.{config.source_name}")
        
        # Métricas
        if MONITORING_AVAILABLE:
            self.metrics = MetricsRegistry().get_or_create(
                config.source_name, 
                config.source_url
            )
        else:
            self.metrics = None
        
        # Componentes de resiliencia
        self._setup_resilience()
        
        # Playwright (se inicializa en setup)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # aiohttp session para requests HTTP directos
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # Estadísticas
        self.stats = {
            'requests_made': 0,
            'items_collected': 0,
            'errors': 0,
            'retries': 0,
            'rate_limit_hits': 0,
            'circuit_opens': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _setup_resilience(self):
        """Configura componentes de resiliencia."""
        if not RESILIENCE_AVAILABLE:
            self.circuit_breaker = None
            self.rate_limiter = None
            self.retry_manager = None
            self.timeout_manager = None
            return
        
        # Circuit Breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=self.config.failure_threshold,
            timeout_duration=self.config.circuit_timeout_seconds,
            expected_exceptions=(
                Exception,
                aiohttp.ClientError,
                asyncio.TimeoutError
            )
        )
        self.circuit_breaker = ScraperCircuitBreaker(
            name=self.config.source_name,
            source=self.config.source_url,
            config=cb_config
        )
        
        # Rate Limiter
        rl_config = RateLimitConfig(
            requests_per_minute=self.config.requests_per_minute,
            adaptive=self.config.adaptive_rate_limiting,
            min_rpm=self.config.min_rpm,
            max_rpm=self.config.max_rpm
        )
        self.rate_limiter = AdaptiveRateLimiter(
            name=self.config.source_name,
            source=self.config.source_url,
            config=rl_config
        )
        
        # Retry Manager
        retry_config = RetryConfig(
            max_attempts=self.config.max_retries,
            initial_delay=self.config.initial_retry_delay,
            max_delay=self.config.max_retry_delay
        )
        self.retry_manager = RetryManager(
            name=self.config.source_name,
            source=self.config.source_url,
            config=retry_config
        )
        
        # Timeout Manager
        timeout_config = TimeoutConfig(
            connect_timeout=self.config.connect_timeout,
            read_timeout=self.config.read_timeout,
            total_timeout=self.config.total_timeout
        )
        self.timeout_manager = TimeoutManager(
            name=self.config.source_name,
            source=self.config.source_url,
            config=timeout_config
        )
    
    # =========================================================================
    # MÉTODOS DE UTILIDAD
    # =========================================================================
    
    def get_random_user_agent(self) -> str:
        """Selecciona un User-Agent aleatorio."""
        return random.choice(self.USER_AGENTS)
    
    def get_random_delay(self) -> float:
        """Genera un delay aleatorio."""
        return random.uniform(
            self.config.delay_min_seconds,
            self.config.delay_max_seconds
        )
    
    async def wait_random_delay(self):
        """Espera un tiempo aleatorio."""
        delay = self.get_random_delay()
        if hasattr(self.logger, 'debug'):
            self.logger.debug(f"Waiting {delay:.2f}s")
        await asyncio.sleep(delay)
    
    def _get_css_selector(self, element_name: str) -> str:
        """
        Obtiene el selector CSS para un elemento, con fallback.
        
        Args:
            element_name: Nombre del elemento en css_selectors
            
        Returns:
            Primer selector que exista, o string vacío
        """
        selectors = self.config.css_selectors.get(element_name, [])
        if isinstance(selectors, str):
            return selectors
        return selectors[0] if selectors else ""
    
    async def _try_selectors(self, selectors: List[str], timeout: int = 5000) -> Optional[Any]:
        """
        Intenta múltiples selectores CSS hasta encontrar uno que funcione.
        
        Args:
            selectors: Lista de selectores CSS a probar
            timeout: Timeout por selector en ms
            
        Returns:
            Elemento encontrado o None
        """
        if not self.page:
            return None
        
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(
                    selector, 
                    timeout=timeout,
                    state='visible'
                )
                if element:
                    return element
            except Exception:
                continue
        
        return None
    
    # =========================================================================
    # HTTP REQUESTS CON RESILIENCIA
    # =========================================================================
    
    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea una sesión HTTP."""
        if self._http_session is None or self._http_session.closed:
            timeout = aiohttp.ClientTimeout(
                connect=self.config.connect_timeout,
                sock_read=self.config.read_timeout,
                total=self.config.total_timeout
            )
            self._http_session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': self.get_random_user_agent()}
            )
        return self._http_session
    
    async def http_get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Realiza un GET HTTP con resiliencia completa.
        
        Incluye:
        - Circuit Breaker check
        - Rate Limiting
        - Retry con backoff
        - Timeout management
        - Métricas
        
        Args:
            url: URL a consultar
            headers: Headers adicionales
            **kwargs: Argumentos adicionales para aiohttp
            
        Returns:
            Response de aiohttp
            
        Raises:
            Exception si todos los reintentos fallan
        """
        # Verificar circuit breaker
        if self.circuit_breaker and self.circuit_breaker.is_open:
            self.stats['circuit_opens'] += 1
            if self.metrics:
                self.metrics.set_circuit_breaker_state("open")
            raise Exception(f"Circuit breaker open for {self.source_name}")
        
        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire_async()
        
        session = await self._get_http_session()
        
        async def _do_request():
            start_time = time.time()
            
            try:
                async with session.get(url, headers=headers, **kwargs) as response:
                    duration = time.time() - start_time
                    
                    self.stats['requests_made'] += 1
                    
                    # Métricas
                    if self.metrics:
                        self.metrics.record_request(
                            method="GET",
                            status_code=response.status,
                            duration=duration
                        )
                    
                    # Manejar rate limiting
                    if response.status == 429:
                        self.stats['rate_limit_hits'] += 1
                        if self.rate_limiter:
                            self.rate_limiter.on_rate_limit_response(dict(response.headers))
                        if self.metrics:
                            self.metrics.record_throttle("429_response")
                        raise aiohttp.ClientResponseError(
                            response.request_info,
                            response.history,
                            status=429,
                            message="Rate limited"
                        )
                    
                    # Registrar éxito en circuit breaker
                    if self.circuit_breaker and response.status < 500:
                        self.circuit_breaker._record_success()
                    
                    return response
                    
            except Exception as e:
                # Registrar falla en circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker._record_failure()
                    if self.circuit_breaker.is_open:
                        if self.metrics:
                            self.metrics.set_circuit_breaker_state("open")
                
                if self.metrics:
                    self.metrics.record_error(type(e).__name__)
                
                raise
        
        # Ejecutar con retry
        if self.retry_manager:
            return await self.retry_manager.execute_with_retry(_do_request)
        else:
            return await _do_request()
    
    async def http_post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> aiohttp.ClientResponse:
        """Realiza un POST HTTP con resiliencia."""
        if self.circuit_breaker and self.circuit_breaker.is_open:
            raise Exception(f"Circuit breaker open for {self.source_name}")
        
        if self.rate_limiter:
            await self.rate_limiter.acquire_async()
        
        session = await self._get_http_session()
        
        async def _do_request():
            async with session.post(
                url, 
                data=data, 
                json=json_data, 
                headers=headers, 
                **kwargs
            ) as response:
                self.stats['requests_made'] += 1
                
                if response.status == 429:
                    self.stats['rate_limit_hits'] += 1
                    if self.rate_limiter:
                        self.rate_limiter.on_rate_limit_response(dict(response.headers))
                    raise aiohttp.ClientResponseError(
                        response.request_info,
                        response.history,
                        status=429
                    )
                
                return response
        
        if self.retry_manager:
            return await self.retry_manager.execute_with_retry(_do_request)
        return await _do_request()
    
    # =========================================================================
    # BROWSER (PLAYWRIGHT)
    # =========================================================================
    
    async def setup_browser(self):
        """Configura el navegador Playwright con opciones anti-detección."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed")
        
        if hasattr(self.logger, 'info'):
            self.logger.info("Setting up browser...")
        
        self.playwright = await async_playwright().start()
        
        browser_args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-gpu',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            args=browser_args
        )
        
        user_agent = self.get_random_user_agent()
        self.context = await self.browser.new_context(
            viewport={
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            user_agent=user_agent,
            locale='es-BO',
            timezone_id='America/La_Paz',
        )
        
        # Scripts anti-detección
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.config.timeout_ms)
        
        if hasattr(self.logger, 'info'):
            self.logger.info(f"Browser ready with UA: {user_agent[:50]}...")
    
    async def close_browser(self):
        """Cierra el navegador y libera recursos."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        if hasattr(self.logger, 'info'):
            self.logger.info("Browser closed")
    
    async def navigate_with_retry(self, url: str) -> bool:
        """Navega a una URL con resiliencia."""
        if not self.page:
            return False
        
        async def _navigate():
            response = await self.page.goto(url, wait_until='domcontentloaded')
            if not response or not response.ok:
                raise Exception(f"Navigation failed: {response.status if response else 'no response'}")
            return True
        
        try:
            if self.retry_manager:
                return await self.retry_manager.execute_with_retry(_navigate)
            return await _navigate()
        except Exception as e:
            if hasattr(self.logger, 'error'):
                self.logger.error(f"Navigation failed: {e}")
            return False
    
    async def scroll_page(self, scroll_count: int = 5):
        """Realiza scroll con comportamiento humano."""
        if not self.page:
            return
        
        for i in range(scroll_count):
            scroll_amount = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(
                self.config.scroll_pause_seconds + random.uniform(0.5, 1.5)
            )
    
    # =========================================================================
    # MÉTODOS ABSTRACTOS
    # =========================================================================
    
    @abstractmethod
    async def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta datos de la fuente.
        
        Debe ser implementado por cada scraper específico.
        
        Args:
            limit: Número máximo de items a recolectar
            
        Returns:
            Lista de diccionarios con datos recolectados
        """
        pass
    
    @abstractmethod
    async def parse_post(self, element) -> Optional[Dict[str, Any]]:
        """
        Parsea un elemento individual.
        
        Args:
            element: Elemento DOM a parsear
            
        Returns:
            Diccionario con datos o None si falla
        """
        pass
    
    # =========================================================================
    # EJECUCIÓN PRINCIPAL
    # =========================================================================
    
    async def run(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ejecuta el proceso completo de scraping con resiliencia.
        
        Args:
            limit: Número máximo de elementos
            
        Returns:
            Lista de datos recolectados
        """
        self.stats['start_time'] = datetime.now()
        collected_data = []
        
        if hasattr(self.logger, 'scrape_started'):
            self.logger.scrape_started()
        
        try:
            # Setup browser si es necesario
            if self.page is None and PLAYWRIGHT_AVAILABLE:
                await self.setup_browser()
            
            # Recolección de datos
            collected_data = await self.collect_data(limit)
            
            self.stats['items_collected'] = len(collected_data)
            
            # Métricas de éxito
            if self.metrics:
                self.metrics.record_success()
                self.metrics.record_items_scraped(len(collected_data))
            
            if hasattr(self.logger, 'scrape_completed'):
                self.logger.scrape_completed(
                    success=True,
                    items_count=len(collected_data)
                )
                
        except Exception as e:
            self.stats['errors'] += 1
            
            if self.metrics:
                self.metrics.record_error(type(e).__name__)
                self.metrics.set_unhealthy()
            
            if hasattr(self.logger, 'scrape_completed'):
                self.logger.scrape_completed(success=False, items_count=0)
            
            raise
            
        finally:
            # Cerrar recursos
            await self.close_browser()
            
            if self._http_session and not self._http_session.closed:
                await self._http_session.close()
            
            self.stats['end_time'] = datetime.now()
            
            # Log estadísticas
            if self.stats['start_time'] and self.stats['end_time']:
                duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
                if hasattr(self.logger, 'info'):
                    self.logger.info(
                        f"Stats: {self.stats['items_collected']} items, "
                        f"{self.stats['requests_made']} requests, "
                        f"{self.stats['errors']} errors, "
                        f"{duration:.2f}s"
                    )
        
        return collected_data
    
    async def run_async_scrape(self, **kwargs) -> Dict[str, Any]:
        """
        Método para ser usado con el orquestador.
        
        Returns:
            Diccionario con resultado del scrape
        """
        limit = kwargs.get('limit', 100)
        
        try:
            data = await self.run(limit=limit)
            return {
                'success': True,
                'items_count': len(data),
                'data': data,
                'stats': self.stats
            }
        except Exception as e:
            return {
                'success': False,
                'items_count': 0,
                'error': str(e),
                'error_type': type(e).__name__,
                'stats': self.stats
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de la sesión."""
        stats = self.stats.copy()
        
        # Agregar stats de resiliencia
        if self.circuit_breaker:
            stats['circuit_breaker'] = self.circuit_breaker.get_stats()
        if self.rate_limiter:
            rl_stats = self.rate_limiter.get_stats()
            stats['rate_limiter'] = {
                'current_rpm': rl_stats.current_rpm,
                'throttled_requests': rl_stats.throttled_requests
            }
        if self.retry_manager:
            retry_stats = self.retry_manager.get_stats()
            stats['retry_manager'] = {
                'total_retries': retry_stats.total_retries,
                'failed_calls': retry_stats.failed_calls
            }
        
        return stats


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_resilient_scraper(
    scraper_class: type,
    config_dict: Dict[str, Any]
) -> ResilientBaseScraper:
    """
    Factory function para crear un scraper resiliente.
    
    Args:
        scraper_class: Clase del scraper (debe heredar de ResilientBaseScraper)
        config_dict: Diccionario de configuración
        
    Returns:
        Instancia del scraper configurado
    """
    config = ResilientScraperConfig.from_dict(config_dict)
    return scraper_class(config)
