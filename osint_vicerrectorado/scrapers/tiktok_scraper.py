"""
TikTokScraper - Scraper para perfiles públicos de TikTok
Sistema de Analítica EMI

Recolecta videos públicos de perfiles de TikTok usando Playwright.
Implementa técnicas anti-detección específicas para TikTok.

Perfil objetivo:
- https://www.tiktok.com/@emilapazoficial

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import asyncio
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging

from scrapers.base_scraper import BaseScraper


class TikTokScraper(BaseScraper):
    """
    Scraper especializado para perfiles públicos de TikTok.
    
    Extrae videos, descripciones, fechas y métricas de engagement
    de perfiles públicos de TikTok usando Playwright.
    
    Attributes:
        username (str): Nombre de usuario de TikTok (sin @)
        account_name (str): Nombre descriptivo de la cuenta
        collected_videos (List[Dict]): Videos recolectados en la sesión
    """
    
    # Selectores CSS para elementos de TikTok (actualizados 2024)
    SELECTORS = {
        # Contenedor de videos en el perfil
        'video_container': 'div[data-e2e="user-post-item"], div[class*="DivItemContainer"]',
        # Link al video
        'video_link': 'a[href*="/video/"]',
        # Descripción del video (en página de video individual)
        'video_description': 'h1[data-e2e="video-desc"], span[class*="SpanText"]',
        # Métricas de engagement
        'like_count': 'strong[data-e2e="like-count"], span[data-e2e="like-count"]',
        'comment_count': 'strong[data-e2e="comment-count"], span[data-e2e="comment-count"]',
        'share_count': 'strong[data-e2e="share-count"], span[data-e2e="share-count"]',
        'view_count': 'strong[data-e2e="video-views"], span[data-e2e="video-views"]',
        # Información del autor
        'author_name': 'span[data-e2e="browse-username"], h2[data-e2e="user-title"]',
        'author_nickname': 'h1[data-e2e="user-subtitle"]',
        # Fecha del video
        'video_date': 'span[data-e2e="browser-nickname"] + span, span[class*="SpanOtherInfos"]',
        # Captcha/verificación
        'captcha': 'div[class*="captcha"], div[id*="captcha"]',
        # Cookie banner
        'cookie_banner': 'button[class*="cookie"], button:has-text("Accept")'
    }
    
    # User agents específicos para TikTok (móviles funcionan mejor)
    TIKTOK_USER_AGENTS = [
        # Mobile Chrome
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1",
        # Mobile Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        # Desktop Chrome (fallback)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, profile_url: str, account_name: str, config: dict):
        """
        Inicializa el scraper de TikTok.
        
        Args:
            profile_url: URL completa del perfil de TikTok
            account_name: Nombre descriptivo de la cuenta
            config: Configuración del scraper
        """
        super().__init__(
            source_name='TikTok',
            source_url=profile_url,
            config=config
        )
        
        # Usar user agents específicos para TikTok
        self.USER_AGENTS = self.TIKTOK_USER_AGENTS
        
        self.account_name = account_name
        self.username = self._extract_username(profile_url)
        self.collected_videos: List[Dict] = []
        
        self.logger.info(f"TikTokScraper inicializado para: @{self.username}")
    
    def _extract_username(self, url: str) -> str:
        """
        Extrae el nombre de usuario desde la URL de TikTok.
        
        Args:
            url: URL del perfil de TikTok
            
        Returns:
            str: Nombre de usuario (sin @)
        """
        match = re.search(r'tiktok\.com/@([^/?]+)', url)
        if match:
            return match.group(1)
        return 'unknown'
    
    async def setup_browser(self) -> None:
        """
        Configura el navegador con ajustes específicos para TikTok.
        
        TikTok requiere configuración adicional para evitar detección.
        """
        self.logger.info("Configurando navegador para TikTok...")
        
        from playwright.async_api import async_playwright
        
        scraping_config = self.config.get('scraping', {})
        headless = scraping_config.get('headless', True)
        
        self.playwright = await async_playwright().start()
        
        # Argumentos optimizados para TikTok
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
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-web-security',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # Configuración móvil para TikTok (mejor compatibilidad)
        user_agent = self.get_random_user_agent()
        is_mobile = 'Mobile' in user_agent or 'iPhone' in user_agent
        
        viewport = {'width': 390, 'height': 844} if is_mobile else {'width': 1920, 'height': 1080}
        
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='es-BO',
            timezone_id='America/La_Paz',
            is_mobile=is_mobile,
            has_touch=is_mobile,
            java_script_enabled=True,
        )
        
        # Scripts anti-detección específicos para TikTok
        await self.context.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Plugins realistas
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ]
            });
            
            // Idiomas
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-BO', 'es', 'en-US', 'en']
            });
            
            // Hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4
            });
            
            // Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            
            // Chrome object
            window.chrome = { runtime: {} };
            
            // Canvas fingerprint randomization
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width === 220 && this.height === 30) {
                    return originalToDataURL.apply(this, arguments) + Math.random().toString(36).substr(2, 5);
                }
                return originalToDataURL.apply(this, arguments);
            };
        """)
        
        self.page = await self.context.new_page()
        
        timeout = scraping_config.get('timeout_ms', 30000)
        self.page.set_default_timeout(timeout)
        
        self.logger.info(f"Navegador TikTok configurado. Mobile: {is_mobile}")
    
    async def handle_popups(self) -> None:
        """
        Maneja popups de cookies, login y captcha en TikTok.
        """
        try:
            await asyncio.sleep(2)
            
            # Aceptar cookies
            cookie_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("Aceptar")',
                'button[class*="cookie"]',
                'div[class*="cookie"] button',
            ]
            
            for selector in cookie_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        self.logger.info("Cookies aceptadas")
                        await asyncio.sleep(1)
                        break
                except:
                    pass
            
            # Cerrar modal de login si aparece
            login_close_selectors = [
                'button[data-e2e="modal-close-inner-button"]',
                'div[class*="DivCloseWrapper"] button',
                '[aria-label="Close"]',
            ]
            
            for selector in login_close_selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn and await btn.is_visible():
                        await btn.click()
                        self.logger.info("Modal de login cerrado")
                        await asyncio.sleep(1)
                        break
                except:
                    pass
            
            # Verificar si hay captcha
            captcha = await self.page.query_selector(self.SELECTORS['captcha'])
            if captcha:
                self.logger.warning("¡Captcha detectado! Esperando resolución manual...")
                # En producción, podrías integrar un servicio de resolución de captcha
                await asyncio.sleep(30)
                
        except Exception as e:
            self.logger.debug(f"Error manejando popups TikTok: {e}")
    
    async def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta videos públicos del perfil de TikTok.
        
        Proceso:
        1. Navega al perfil
        2. Maneja popups
        3. Hace scroll para cargar más videos
        4. Extrae información de cada video
        
        Args:
            limit: Número máximo de videos a recolectar
            
        Returns:
            List[Dict]: Lista de videos con su información
        """
        self.logger.info(f"Iniciando recolección de TikTok: @{self.username}")
        
        # Navegar al perfil
        success = await self.navigate_with_retry(self.source_url)
        if not success:
            self.logger.error(f"No se pudo acceder a {self.source_url}")
            return []
        
        # Manejar popups
        await self.handle_popups()
        
        # Esperar a que cargue el contenido
        try:
            await self.page.wait_for_selector('[data-e2e="user-post-item"]', timeout=15000)
        except:
            self.logger.warning("No se detectó grid de videos, intentando selectores alternativos...")
            try:
                await self.page.wait_for_selector('div[class*="DivItemContainer"]', timeout=10000)
            except:
                self.logger.error("No se pudo cargar el contenido del perfil")
        
        # Scroll y recolección
        max_scrolls = self.config.get('scraping', {}).get('max_scroll_attempts', 20)
        videos_found = 0
        scroll_count = 0
        
        while videos_found < limit and scroll_count < max_scrolls:
            # Obtener videos visibles en el grid
            video_links = await self.page.query_selector_all('a[href*="/video/"]')
            
            for link in video_links:
                if videos_found >= limit:
                    break
                
                try:
                    href = await link.get_attribute('href')
                    if href and '/video/' in href:
                        video_id = self._extract_video_id(href)
                        
                        # Verificar si ya lo tenemos
                        external_id = self.generate_external_id('tt', video_id)
                        if external_id not in [v['id_externo'] for v in self.collected_videos]:
                            # Obtener datos básicos del grid
                            video_data = await self._extract_video_from_grid(link, video_id)
                            
                            if video_data:
                                self.collected_videos.append(video_data)
                                videos_found += 1
                                
                except Exception as e:
                    self.logger.debug(f"Error extrayendo video: {e}")
                    continue
            
            self.logger.info(f"Videos recolectados: {videos_found}/{limit}")
            
            if videos_found >= limit:
                break
            
            # Hacer scroll
            await self.scroll_page(scroll_count=1)
            scroll_count += 1
            
            # Delay anti-detección
            await self.wait_random_delay()
        
        # Obtener detalles adicionales para algunos videos
        await self._enrich_video_data(min(5, len(self.collected_videos)))
        
        self.logger.info(f"Recolección completada: {len(self.collected_videos)} videos de @{self.username}")
        return self.collected_videos
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extrae el ID del video desde la URL.
        
        Args:
            url: URL del video de TikTok
            
        Returns:
            str: ID del video
        """
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    async def _extract_video_from_grid(self, element, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Extrae información básica de un video desde el grid del perfil.
        
        Args:
            element: Elemento del link del video
            video_id: ID del video
            
        Returns:
            Dict con datos del video o None
        """
        try:
            href = await element.get_attribute('href')
            video_url = f"https://www.tiktok.com{href}" if href.startswith('/') else href
            
            # Intentar obtener el conteo de views del grid
            parent = await element.evaluate_handle('el => el.parentElement')
            views = 0
            
            try:
                views_elem = await parent.query_selector('strong[data-e2e="video-views"]')
                if views_elem:
                    views_text = await views_elem.text_content()
                    views = self._parse_count(views_text)
            except:
                pass
            
            # Datos básicos del video
            return {
                'id_externo': self.generate_external_id('tt', video_id),
                'contenido_original': f"Video TikTok de @{self.username}",  # Se actualiza si obtenemos detalles
                'fecha_publicacion': datetime.now(),  # Se actualiza si obtenemos detalles
                'autor': self.username,
                'engagement_likes': 0,  # Se actualiza con detalles
                'engagement_comments': 0,
                'engagement_shares': 0,
                'tipo_contenido': 'video',
                'url_publicacion': video_url,
                'metadata_json': {
                    'platform': 'tiktok',
                    'username': self.username,
                    'account_name': self.account_name,
                    'video_id': video_id,
                    'views': views,
                    'scrape_timestamp': datetime.now().isoformat(),
                    'has_details': False
                }
            }
            
        except Exception as e:
            self.logger.debug(f"Error en _extract_video_from_grid: {e}")
            return None
    
    async def _enrich_video_data(self, count: int) -> None:
        """
        Enriquece los datos de videos visitando sus páginas individuales.
        
        Args:
            count: Número de videos a enriquecer
        """
        self.logger.info(f"Enriqueciendo datos de {count} videos...")
        
        for i, video in enumerate(self.collected_videos[:count]):
            try:
                video_url = video['url_publicacion']
                self.logger.debug(f"Visitando video {i+1}/{count}: {video_url}")
                
                # Navegar al video
                await self.page.goto(video_url, wait_until='domcontentloaded')
                await asyncio.sleep(2)
                
                # Manejar popups
                await self.handle_popups()
                
                # Extraer descripción
                desc_selectors = [
                    'h1[data-e2e="video-desc"]',
                    'span[data-e2e="video-desc"]',
                    'div[class*="DivVideoDescription"] span',
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_elem = await self.page.query_selector(selector)
                        if desc_elem:
                            desc = await desc_elem.text_content()
                            if desc and len(desc) > 5:
                                video['contenido_original'] = desc.strip()
                                break
                    except:
                        pass
                
                # Extraer métricas
                video['engagement_likes'] = await self._get_metric('like-count')
                video['engagement_comments'] = await self._get_metric('comment-count')
                video['engagement_shares'] = await self._get_metric('share-count')
                
                # Extraer fecha
                video['fecha_publicacion'] = await self._extract_video_date()
                
                # Marcar como enriquecido
                video['metadata_json']['has_details'] = True
                
                # Delay entre videos
                await self.wait_random_delay()
                
            except Exception as e:
                self.logger.debug(f"Error enriqueciendo video: {e}")
                continue
    
    async def _get_metric(self, metric_name: str) -> int:
        """
        Obtiene una métrica de engagement específica.
        
        Args:
            metric_name: Nombre del data-e2e del elemento
            
        Returns:
            int: Valor de la métrica
        """
        try:
            selectors = [
                f'strong[data-e2e="{metric_name}"]',
                f'span[data-e2e="{metric_name}"]',
            ]
            
            for selector in selectors:
                elem = await self.page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    return self._parse_count(text)
                    
        except Exception as e:
            self.logger.debug(f"Error obteniendo métrica {metric_name}: {e}")
        
        return 0
    
    def _parse_count(self, text: str) -> int:
        """
        Parsea texto de conteo a número (maneja K, M, etc).
        
        Args:
            text: Texto del conteo (ej: "1.2K", "500", "2M")
            
        Returns:
            int: Valor numérico
        """
        if not text:
            return 0
        
        text = text.strip().upper()
        
        try:
            # Manejar K (miles)
            if 'K' in text:
                num = float(text.replace('K', '').replace(',', '.').strip())
                return int(num * 1000)
            
            # Manejar M (millones)
            if 'M' in text:
                num = float(text.replace('M', '').replace(',', '.').strip())
                return int(num * 1000000)
            
            # Número directo
            return int(float(text.replace(',', '').strip()))
            
        except:
            return 0
    
    async def _extract_video_date(self) -> datetime:
        """
        Extrae la fecha de publicación del video.
        
        Returns:
            datetime: Fecha del video
        """
        try:
            # Buscar elemento de fecha
            date_selectors = [
                'span[data-e2e="browser-nickname"] + span',
                'span[class*="SpanOtherInfos"]',
            ]
            
            for selector in date_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        text = await elem.text_content()
                        return self._parse_relative_date(text)
                except:
                    pass
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo fecha: {e}")
        
        return datetime.now()
    
    def _parse_relative_date(self, text: str) -> datetime:
        """
        Parsea fechas relativas de TikTok.
        
        Args:
            text: Texto de fecha relativa (ej: "2d ago", "hace 3 horas")
            
        Returns:
            datetime: Fecha calculada
        """
        now = datetime.now()
        text = text.lower().strip()
        
        patterns = [
            (r'(\d+)\s*d', timedelta(days=1)),
            (r'(\d+)\s*h', timedelta(hours=1)),
            (r'(\d+)\s*m(?:in)?', timedelta(minutes=1)),
            (r'(\d+)\s*w', timedelta(weeks=1)),
            (r'(\d+)\s*mo', timedelta(days=30)),
            (r'(\d+)\s*y', timedelta(days=365)),
            (r'hace\s*(\d+)\s*día', timedelta(days=1)),
            (r'hace\s*(\d+)\s*hora', timedelta(hours=1)),
            (r'hace\s*(\d+)\s*semana', timedelta(weeks=1)),
        ]
        
        for pattern, delta in patterns:
            match = re.search(pattern, text)
            if match:
                amount = int(match.group(1))
                return now - (delta * amount)
        
        return now
    
    async def parse_post(self, element) -> Optional[Dict[str, Any]]:
        """
        Implementación del método abstracto.
        
        Args:
            element: Elemento del DOM
            
        Returns:
            Dict con datos del video
        """
        try:
            href = await element.get_attribute('href')
            if href and '/video/' in href:
                video_id = self._extract_video_id(href)
                return await self._extract_video_from_grid(element, video_id)
        except Exception as e:
            self.logger.error(f"Error en parse_post: {e}")
        return None


async def main():
    """Función de prueba para el scraper de TikTok."""
    import json
    
    # Cargar configuración
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Configurar logging básico
    logging.basicConfig(level=logging.INFO)
    
    # Probar con el perfil EMI La Paz
    scraper = TikTokScraper(
        profile_url="https://www.tiktok.com/@emilapazoficial",
        account_name="EMI La Paz Oficial",
        config=config
    )
    
    # Ejecutar recolección
    videos = await scraper.run(limit=10)
    
    print(f"\n=== Resultados ===")
    print(f"Total videos recolectados: {len(videos)}")
    
    for i, video in enumerate(videos[:3], 1):
        print(f"\n--- Video {i} ---")
        print(f"ID: {video['id_externo']}")
        print(f"Descripción: {video['contenido_original'][:100]}...")
        print(f"Likes: {video['engagement_likes']}")
        print(f"Comentarios: {video['engagement_comments']}")
        print(f"URL: {video['url_publicacion']}")


if __name__ == "__main__":
    asyncio.run(main())
