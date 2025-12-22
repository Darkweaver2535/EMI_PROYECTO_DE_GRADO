"""
BaseScraper - Clase base abstracta para scrapers OSINT
Sistema de Analítica EMI

Esta clase implementa el patrón Template Method y proporciona:
- Técnicas anti-detección (User-Agent rotation, delays aleatorios)
- Gestión de navegador Playwright con configuración stealth
- Manejo de errores con retry exponencial
- Logging estructurado

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:
    print("Playwright no instalado. Ejecutar: pip install playwright && playwright install chromium")


class BaseScraper(ABC):
    """
    Clase base abstracta para todos los scrapers OSINT.
    
    Implementa técnicas anti-detección y proporciona métodos comunes
    para la recolección de datos de redes sociales.
    
    Attributes:
        source_name (str): Nombre de la fuente OSINT (ej: 'Facebook', 'TikTok')
        source_url (str): URL base de la fuente
        config (dict): Configuración del scraper
        logger (logging.Logger): Logger para registrar operaciones
        browser (Browser): Instancia del navegador Playwright
        context (BrowserContext): Contexto del navegador
        page (Page): Página activa del navegador
    """
    
    # Lista de User-Agents reales para rotación (actualizada 2024)
    USER_AGENTS = [
        # Chrome en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        # Chrome en macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox en macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari en macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge en Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Chrome en Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Mobile User Agents (para variedad)
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    ]
    
    def __init__(self, source_name: str, source_url: str, config: dict):
        """
        Inicializa el scraper base.
        
        Args:
            source_name: Nombre identificador de la fuente (ej: 'Facebook')
            source_url: URL de la página/perfil a scrapear
            config: Diccionario con configuración del scraper
        """
        self.source_name = source_name
        self.source_url = source_url
        self.config = config
        self.logger = logging.getLogger(f"OSINT.{self.__class__.__name__}")
        
        # Instancias de Playwright (se inicializan en setup)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Estadísticas de scraping
        self.stats = {
            'requests_made': 0,
            'items_collected': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        self.logger.info(f"Scraper inicializado para {source_name}: {source_url}")
    
    def get_random_user_agent(self) -> str:
        """
        Selecciona un User-Agent aleatorio de la lista.
        
        Returns:
            str: User-Agent string aleatorio
        """
        return random.choice(self.USER_AGENTS)
    
    def get_random_delay(self) -> float:
        """
        Genera un delay aleatorio dentro del rango configurado.
        
        Returns:
            float: Segundos de delay a esperar
        """
        scraping_config = self.config.get('scraping', {})
        min_delay = scraping_config.get('delay_min_seconds', 3)
        max_delay = scraping_config.get('delay_max_seconds', 7)
        return random.uniform(min_delay, max_delay)
    
    async def setup_browser(self) -> None:
        """
        Configura e inicializa el navegador Playwright con opciones anti-detección.
        
        Aplica las siguientes técnicas stealth:
        - User-Agent aleatorio
        - Viewport realista
        - Deshabilitación de webdriver flag
        - Timezone y locale consistentes
        """
        self.logger.info("Iniciando configuración del navegador...")
        
        scraping_config = self.config.get('scraping', {})
        headless = scraping_config.get('headless', True)
        viewport = scraping_config.get('viewport', {'width': 1920, 'height': 1080})
        
        self.playwright = await async_playwright().start()
        
        # Argumentos para evadir detección
        browser_args = [
            '--no-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-setuid-sandbox',
            '--no-first-run',
            '--no-zygote',
            '--deterministic-fetch',
            '--disable-features=IsolateOrigins',
            '--disable-site-isolation-trials',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # Crear contexto con configuración anti-detección
        user_agent = self.get_random_user_agent()
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='es-BO',  # Bolivia
            timezone_id='America/La_Paz',
            permissions=['geolocation'],
            geolocation={'latitude': -16.5000, 'longitude': -68.1500},  # La Paz
            color_scheme='light',
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            accept_downloads=False
        )
        
        # Inyectar scripts anti-detección
        await self.context.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Ocultar plugins vacíos
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Ocultar idiomas
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-BO', 'es', 'en-US', 'en']
            });
            
            // Chrome runtime
            window.chrome = {
                runtime: {}
            };
            
            // Permisos
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        self.page = await self.context.new_page()
        
        # Configurar timeout
        timeout = scraping_config.get('timeout_ms', 30000)
        self.page.set_default_timeout(timeout)
        
        self.logger.info(f"Navegador configurado. User-Agent: {user_agent[:50]}...")
    
    async def close_browser(self) -> None:
        """Cierra el navegador y libera recursos."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        
        self.logger.info("Navegador cerrado correctamente")
    
    async def wait_random_delay(self) -> None:
        """Espera un tiempo aleatorio para simular comportamiento humano."""
        delay = self.get_random_delay()
        self.logger.debug(f"Esperando {delay:.2f} segundos...")
        await asyncio.sleep(delay)
    
    async def scroll_page(self, scroll_count: int = 5) -> None:
        """
        Realiza scroll en la página para cargar contenido dinámico.
        
        Args:
            scroll_count: Número de veces a hacer scroll
        """
        scraping_config = self.config.get('scraping', {})
        scroll_pause = scraping_config.get('scroll_pause_seconds', 2)
        
        for i in range(scroll_count):
            # Scroll con velocidad variable (más humano)
            scroll_amount = random.randint(300, 700)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            
            # Pausa variable entre scrolls
            await asyncio.sleep(scroll_pause + random.uniform(0.5, 1.5))
            
            self.logger.debug(f"Scroll {i+1}/{scroll_count} completado")
    
    async def navigate_with_retry(self, url: str, max_retries: int = 3) -> bool:
        """
        Navega a una URL con reintentos en caso de error.
        
        Args:
            url: URL a visitar
            max_retries: Número máximo de reintentos
            
        Returns:
            bool: True si la navegación fue exitosa
        """
        retry_delay = self.config.get('scraping', {}).get('retry_delay_seconds', 5)
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Navegando a {url} (intento {attempt + 1}/{max_retries})")
                
                response = await self.page.goto(url, wait_until='domcontentloaded')
                
                if response and response.ok:
                    self.stats['requests_made'] += 1
                    await self.wait_random_delay()
                    return True
                else:
                    status = response.status if response else 'No response'
                    self.logger.warning(f"Respuesta no exitosa: {status}")
                    
            except Exception as e:
                self.logger.error(f"Error en navegación (intento {attempt + 1}): {str(e)}")
                self.stats['errors'] += 1
            
            if attempt < max_retries - 1:
                # Backoff exponencial
                wait_time = retry_delay * (2 ** attempt)
                self.logger.info(f"Reintentando en {wait_time} segundos...")
                await asyncio.sleep(wait_time)
        
        return False
    
    async def get_page_html(self) -> str:
        """
        Obtiene el HTML completo de la página actual.
        
        Returns:
            str: Contenido HTML de la página
        """
        return await self.page.content()
    
    async def take_screenshot(self, filename: str) -> None:
        """
        Toma una captura de pantalla de la página actual.
        
        Args:
            filename: Nombre del archivo de imagen
        """
        await self.page.screenshot(path=f"logs/screenshots/{filename}")
        self.logger.info(f"Screenshot guardado: {filename}")
    
    def generate_external_id(self, platform: str, unique_id: str) -> str:
        """
        Genera un ID externo único para el registro.
        
        Args:
            platform: Plataforma de origen (fb, tt, ig)
            unique_id: ID único del post/video
            
        Returns:
            str: ID externo formateado
        """
        return f"{platform}_{unique_id}"
    
    @abstractmethod
    async def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta datos de la fuente OSINT.
        
        Este método debe ser implementado por cada scraper específico.
        
        Args:
            limit: Número máximo de elementos a recolectar
            
        Returns:
            List[Dict]: Lista de diccionarios con los datos recolectados
            
        Estructura esperada de cada dict:
            {
                'id_externo': str,          # ID único de la plataforma
                'contenido_original': str,   # Texto del post/video
                'fecha_publicacion': datetime,
                'autor': str,
                'engagement_likes': int,
                'engagement_comments': int,
                'engagement_shares': int,
                'tipo_contenido': str,       # 'texto', 'imagen', 'video'
                'url_publicacion': str,
                'metadata_json': dict
            }
        """
        pass
    
    @abstractmethod
    async def parse_post(self, element) -> Optional[Dict[str, Any]]:
        """
        Parsea un elemento de post/video individual.
        
        Args:
            element: Elemento del DOM a parsear
            
        Returns:
            Dict con los datos del post o None si falla
        """
        pass
    
    async def run(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Ejecuta el proceso completo de scraping.
        
        Este es el método principal que orquesta todo el proceso:
        1. Inicializa el navegador
        2. Navega a la URL objetivo
        3. Recolecta los datos
        4. Cierra el navegador
        
        Args:
            limit: Número máximo de elementos a recolectar
            
        Returns:
            List[Dict]: Datos recolectados
        """
        self.stats['start_time'] = datetime.now()
        collected_data = []
        
        try:
            # Setup del navegador
            await self.setup_browser()
            
            # Recolección de datos
            collected_data = await self.collect_data(limit)
            
            self.stats['items_collected'] = len(collected_data)
            self.logger.info(f"Recolección completada: {len(collected_data)} elementos")
            
        except Exception as e:
            self.logger.error(f"Error durante scraping: {str(e)}")
            self.stats['errors'] += 1
            raise
            
        finally:
            # Siempre cerrar el navegador
            await self.close_browser()
            self.stats['end_time'] = datetime.now()
            
            # Log de estadísticas finales
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            self.logger.info(
                f"Estadísticas: {self.stats['items_collected']} items, "
                f"{self.stats['requests_made']} requests, "
                f"{self.stats['errors']} errores, "
                f"{duration:.2f}s duración"
            )
        
        return collected_data
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna las estadísticas de la sesión de scraping.
        
        Returns:
            Dict con estadísticas de la sesión
        """
        return self.stats.copy()
