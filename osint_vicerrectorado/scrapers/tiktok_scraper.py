"""
TikTokScraper - Scraper para perfiles públicos de TikTok
Sistema de Analítica EMI

Recolecta videos públicos de perfiles de TikTok usando yt-dlp (método principal)
y Playwright como fallback. yt-dlp es más confiable y evita CAPTCHAs.

Perfil objetivo:
- https://www.tiktok.com/@emilapazoficial

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import asyncio
import re
import json
import hashlib
import subprocess
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import logging

from scrapers.base_scraper import BaseScraper


class TikTokScraper(BaseScraper):
    """
    Scraper especializado para perfiles públicos de TikTok.
    
    Usa yt-dlp como método principal (evita CAPTCHAs) y Playwright como fallback.
    Extrae videos, descripciones, fechas y métricas de engagement.
    
    Attributes:
        username (str): Nombre de usuario de TikTok (sin @)
        account_name (str): Nombre descriptivo de la cuenta
        collected_videos (List[Dict]): Videos recolectados en la sesión
        use_ytdlp (bool): Si usar yt-dlp como método principal
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
        self.use_ytdlp = True  # Usar yt-dlp por defecto (evita CAPTCHA)
        
        # Cargar cookies de TikTok si están disponibles
        self.cookies_config = self._load_cookies_config()
        self.use_cookies = self.cookies_config.get('enabled', False)
        
        self.logger.info(f"TikTokScraper inicializado para: @{self.username}")
        if self.use_cookies:
            self.logger.info("🔐 Modo con cookies activado (evita CAPTCHA)")
    
    def _load_cookies_config(self) -> Dict:
        """Carga la configuración de cookies de TikTok."""
        try:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 'config', 'tiktok_cookies.json'
            )
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.debug(f"No se pudo cargar config de cookies: {e}")
        return {'enabled': False}
    
    async def _apply_cookies(self) -> bool:
        """Aplica las cookies de TikTok al contexto del navegador."""
        if not self.use_cookies or not self.cookies_config.get('cookies'):
            return False
        
        try:
            cookies_dict = self.cookies_config.get('cookies', {})
            cookies_list = []
            
            for name, data in cookies_dict.items():
                cookie = {
                    'name': name,
                    'value': data.get('value', ''),
                    'domain': data.get('domain', '.tiktok.com'),
                    'path': data.get('path', '/'),
                }
                cookies_list.append(cookie)
            
            if cookies_list and self.context:
                await self.context.add_cookies(cookies_list)
                self.logger.info(f"✓ {len(cookies_list)} cookies de TikTok aplicadas")
                return True
        except Exception as e:
            self.logger.warning(f"Error aplicando cookies de TikTok: {e}")
        
        return False

    async def _load_and_apply_cookies(self) -> bool:
        """Carga y aplica las cookies de TikTok al navegador."""
        if not self.use_cookies:
            return False
        
        return await self._apply_cookies()

    def _check_ytdlp_available(self) -> bool:
        """Verifica si yt-dlp está disponible."""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                   capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _collect_with_ytdlp(self, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Recolecta videos usando yt-dlp (método principal, evita CAPTCHA).
        
        Args:
            limit: Número máximo de videos a recolectar
            
        Returns:
            List[Dict]: Lista de videos con información
        """
        self.logger.info(f"Usando yt-dlp para extraer datos de @{self.username}...")
        
        try:
            # Comando yt-dlp para extraer metadatos sin descargar
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--no-download',
                '--playlist-end', str(limit),
                '--extractor-args', 'tiktok:api_hostname=api22-normal-c-alisg.tiktokv.com',
                self.source_url
            ]
            
            self.logger.debug(f"Ejecutando: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                self.logger.warning(f"yt-dlp retornó código {result.returncode}")
                if result.stderr:
                    self.logger.debug(f"stderr: {result.stderr[:500]}")
                return []
            
            videos = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    video = self._parse_ytdlp_entry(data)
                    if video:
                        videos.append(video)
                except json.JSONDecodeError:
                    continue
            
            self.logger.info(f"yt-dlp extrajo {len(videos)} videos")
            return videos
            
        except subprocess.TimeoutExpired:
            self.logger.error("yt-dlp timeout - TikTok puede estar bloqueando")
            return []
        except Exception as e:
            self.logger.error(f"Error con yt-dlp: {e}")
            return []
    
    def _parse_ytdlp_entry(self, data: Dict) -> Optional[Dict[str, Any]]:
        """
        Parsea una entrada de yt-dlp al formato del sistema.
        
        Args:
            data: Datos JSON de yt-dlp
            
        Returns:
            Dict con datos formateados o None
        """
        try:
            video_id = data.get('id', '')
            
            # Extraer fecha
            timestamp = data.get('timestamp')
            if timestamp:
                fecha = datetime.fromtimestamp(timestamp)
            else:
                fecha = datetime.now()
            
            # Extraer métricas
            likes = data.get('like_count', 0) or 0
            comments = data.get('comment_count', 0) or 0
            shares = data.get('repost_count', 0) or data.get('share_count', 0) or 0
            views = data.get('view_count', 0) or 0
            
            # Descripción/título
            descripcion = data.get('title', '') or data.get('description', '') or f"Video de @{self.username}"
            
            return {
                'id_externo': self.generate_external_id('tt', video_id),
                'contenido_original': descripcion[:2000],  # Limitar longitud
                'fecha_publicacion': fecha,
                'autor': data.get('uploader', self.username),
                'engagement_likes': int(likes),
                'engagement_comments': int(comments),
                'engagement_shares': int(shares),
                'engagement_views': int(views),
                'tipo_contenido': 'video',
                'url_publicacion': data.get('webpage_url', f"https://www.tiktok.com/@{self.username}/video/{video_id}"),
                'metadata_json': {
                    'platform': 'tiktok',
                    'username': self.username,
                    'account_name': self.account_name,
                    'video_id': video_id,
                    'duration': data.get('duration', 0),
                    'views': int(views),
                    'music': data.get('track', ''),
                    'hashtags': data.get('tags', []),
                    'scrape_method': 'yt-dlp',
                    'scrape_timestamp': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.debug(f"Error parseando entrada yt-dlp: {e}")
            return None

    async def _extract_comments_from_video(self, video_url: str, max_comments: int = 50) -> List[Dict]:
        """
        Extrae comentarios de un video individual de TikTok.
        Usa cookies si están disponibles para evitar CAPTCHA.
        
        Args:
            video_url: URL del video
            max_comments: Número máximo de comentarios a extraer
            
        Returns:
            Lista de comentarios extraídos
        """
        comments = []
        
        try:
            # Navegar al video
            self.logger.debug(f"Navegando a: {video_url}")
            await self.page.goto(video_url, wait_until='networkidle', timeout=45000)
            await asyncio.sleep(5)
            
            # Manejar popups
            await self.handle_popups()
            
            # Hacer click en el ícono de comentarios si existe
            try:
                comment_icon = await self.page.query_selector('[data-e2e="comment-icon"]')
                if comment_icon:
                    await comment_icon.click()
                    await asyncio.sleep(3)
            except:
                pass
            
            # Buscar contenedores de comentarios con múltiples selectores
            comment_containers = await self.page.query_selector_all(
                '[class*="CommentItem"], [class*="DivCommentItem"], [data-e2e="comment-level-1"]'
            )
            
            if not comment_containers:
                # Intentar scroll para cargar comentarios
                await self.page.evaluate('window.scrollTo(0, 500)')
                await asyncio.sleep(2)
                comment_containers = await self.page.query_selector_all(
                    '[class*="CommentItem"], [class*="DivCommentItem"]'
                )
            
            self.logger.debug(f"Contenedores de comentarios encontrados: {len(comment_containers)}")
            
            for elem in comment_containers[:max_comments]:
                try:
                    # Obtener todo el texto del contenedor
                    full_text = await elem.inner_text()
                    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                    
                    if len(lines) >= 2:
                        # Estructura típica: autor, comentario, tiempo, likes
                        autor = lines[0]
                        texto = lines[1]
                        
                        # Filtrar si parece ser contenido válido
                        if (len(texto) > 2 and 
                            not texto.isdigit() and 
                            texto.lower() not in ['reply', 'responder', 'like', 'me gusta']):
                            
                            comments.append({
                                'texto': texto,
                                'autor': autor,
                                'likes': 0,
                                'fecha': datetime.now().isoformat()
                            })
                            
                except Exception as e:
                    self.logger.debug(f"Error extrayendo comentario individual: {e}")
                    continue
            
            if comments:
                self.logger.debug(f"Extraídos {len(comments)} comentarios de {video_url}")
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo comentarios de {video_url}: {e}")
        
        return comments

    async def _enrich_videos_with_comments(self, videos: List[Dict], max_videos: int = 10) -> List[Dict]:
        """
        Enriquece los videos con comentarios extraídos.
        
        Args:
            videos: Lista de videos
            max_videos: Número máximo de videos a enriquecer con comentarios
            
        Returns:
            Videos enriquecidos con comentarios
        """
        if not videos:
            return videos
        
        self.logger.info(f"📝 Extrayendo comentarios de {min(max_videos, len(videos))} videos...")
        
        # Configurar navegador si no está configurado
        if not self.page:
            await self.setup_browser()
        
        # Aplicar cookies si están disponibles
        if self.use_cookies:
            cookies_applied = await self._apply_cookies()
            if cookies_applied:
                self.logger.info("🔐 Cookies aplicadas - CAPTCHA debería estar evitado")
        
        for i, video in enumerate(videos[:max_videos]):
            try:
                video_url = video.get('url_publicacion', '')
                if not video_url:
                    continue
                
                self.logger.debug(f"  Extrayendo comentarios {i+1}/{min(max_videos, len(videos))}...")
                
                # Extraer comentarios
                comments = await self._extract_comments_from_video(video_url, max_comments=30)
                
                if comments:
                    # Agregar a metadata
                    if 'metadata_json' not in video:
                        video['metadata_json'] = {}
                    if isinstance(video['metadata_json'], str):
                        video['metadata_json'] = json.loads(video['metadata_json'])
                    
                    video['metadata_json']['comentarios'] = comments
                    video['metadata_json']['num_comentarios_extraidos'] = len(comments)
                    
                    self.logger.info(f"  ✓ {len(comments)} comentarios extraídos del video {i+1}")
                
                # Delay entre videos
                await asyncio.sleep(3)
                
            except Exception as e:
                self.logger.debug(f"Error enriqueciendo video: {e}")
                continue
        
        return videos

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
        Usa playwright-stealth para máxima evasión de CAPTCHAs.
        """
        self.logger.info("Configurando navegador para TikTok...")
        
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        
        scraping_config = self.config.get('scraping', {})
        headless = scraping_config.get('headless', True)
        
        self.playwright = await async_playwright().start()
        
        # Argumentos optimizados para TikTok (anti-detección)
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
            '--window-size=1920,1080',
        ]
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # Usar desktop para TikTok (mejor para ver comentarios)
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=user_agent,
            locale='es-BO',
            timezone_id='America/La_Paz',
            java_script_enabled=True,
            bypass_csp=True,
        )
        
        self.page = await self.context.new_page()
        
        # Aplicar playwright-stealth para evadir detección
        stealth = Stealth()
        await stealth.apply_stealth_async(self.page)
        
        # Cargar y aplicar cookies si existen
        await self._load_and_apply_cookies()
        
        timeout = scraping_config.get('timeout_ms', 30000)
        self.page.set_default_timeout(timeout)
        
        self.logger.info("Navegador TikTok configurado con stealth mode")
    
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
        1. Intenta usar yt-dlp (evita CAPTCHA)
        2. Extrae comentarios con Playwright
        3. Si falla yt-dlp, usa Playwright como fallback completo
        
        Args:
            limit: Número máximo de videos a recolectar
            
        Returns:
            List[Dict]: Lista de videos con su información
        """
        self.logger.info(f"Iniciando recolección de TikTok: @{self.username}")
        
        # Método 1: Intentar con yt-dlp (más confiable, evita CAPTCHA)
        if self.use_ytdlp and self._check_ytdlp_available():
            self.logger.info("Usando yt-dlp (método anti-CAPTCHA)...")
            videos = self._collect_with_ytdlp(limit)
            if videos:
                self.collected_videos = videos
                self.logger.info(f"✓ yt-dlp exitoso: {len(videos)} videos recolectados")
                
                # Extraer comentarios con Playwright (yt-dlp solo da conteo)
                try:
                    await self.setup_browser()
                    self.collected_videos = await self._enrich_videos_with_comments(
                        self.collected_videos, 
                        max_videos=min(10, len(videos))  # Máximo 10 videos para no tardar mucho
                    )
                except Exception as e:
                    self.logger.warning(f"No se pudieron extraer comentarios: {e}")
                finally:
                    await self.close_browser()
                
                return self.collected_videos
            else:
                self.logger.warning("yt-dlp no obtuvo resultados, intentando Playwright...")
        
        # Método 2: Fallback a Playwright
        return await self._collect_with_playwright(limit)
    
    async def _collect_with_playwright(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta videos usando Playwright (fallback si yt-dlp falla).
        
        Args:
            limit: Número máximo de videos a recolectar
            
        Returns:
            List[Dict]: Lista de videos con su información
        """
        self.logger.info(f"Usando Playwright para @{self.username}...")
        
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
