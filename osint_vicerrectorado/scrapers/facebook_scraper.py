"""
FacebookScraper - Scraper para páginas públicas de Facebook
Sistema de Analítica EMI

Recolecta posts públicos de páginas de Facebook.
Usa facebook-scraper (librería) como método principal para obtener comentarios,
y Playwright como fallback.

Páginas objetivo:
- https://www.facebook.com/profile.php?id=61574626396439 (EMI Oficial)
- https://www.facebook.com/EMI.UALP (EMI UALP)

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

# Importar facebook-scraper para obtener comentarios
try:
    from facebook_scraper import get_posts, set_cookies
    FACEBOOK_SCRAPER_AVAILABLE = True
except ImportError:
    FACEBOOK_SCRAPER_AVAILABLE = False

from scrapers.base_scraper import BaseScraper


class FacebookScraper(BaseScraper):
    """
    Scraper especializado para páginas públicas de Facebook.
    
    Extrae posts, texto, imágenes, fechas y métricas de engagement
    de páginas públicas de Facebook sin autenticación.
    
    Attributes:
        page_id (str): ID o nombre de la página de Facebook
        collected_posts (List[Dict]): Posts recolectados en la sesión
    """
    
    # Selectores CSS para elementos de Facebook (actualizados 2024)
    # Facebook cambia frecuentemente sus clases, estos selectores son genéricos
    SELECTORS = {
        # Contenedor principal de posts
        'post_container': '[data-pagelet*="FeedUnit"], [role="article"]',
        # Texto del post
        'post_text': '[data-ad-preview="message"], [data-ad-comet-preview="message"], div[dir="auto"]',
        # Métricas de engagement
        'reactions': '[aria-label*="reaction"], [aria-label*="Me gusta"], [aria-label*="Like"]',
        'comments_count': 'a[href*="comment"], span:has-text("comentario")',
        'shares_count': 'a[href*="shares"], span:has-text("compartido"), span:has-text("veces compartido")',
        # Fecha
        'timestamp': 'a[href*="/posts/"] span, abbr[data-utime], span[id*="jsc"]',
        # Autor
        'author': 'h2 a[href*="facebook.com"], strong a, a[role="link"][tabindex="0"]',
        # Links de posts
        'post_link': 'a[href*="/posts/"], a[href*="/photos/"], a[href*="/videos/"]',
        # Imágenes
        'images': 'img[src*="scontent"], img[data-visualcompletion="media-vc-image"]',
        # Videos
        'videos': 'video, div[data-video-id]',
        # Login modal (para cerrar si aparece)
        'login_modal': '[role="dialog"] [aria-label="Cerrar"], [role="dialog"] [aria-label="Close"]',
        # Cookie banner
        'cookie_banner': 'button[data-cookiebanner="accept_button"], button[title*="cookie"]'
    }
    
    def __init__(self, page_url: str, page_name: str, config: dict):
        """
        Inicializa el scraper de Facebook.
        
        Args:
            page_url: URL completa de la página de Facebook
            page_name: Nombre descriptivo de la página
            config: Configuración del scraper
        """
        super().__init__(
            source_name='Facebook',
            source_url=page_url,
            config=config
        )
        self.page_name = page_name
        self.page_id = self._extract_page_id(page_url)
        self.collected_posts: List[Dict] = []
        self.use_fb_scraper = FACEBOOK_SCRAPER_AVAILABLE
        
        # Cargar configuración de cookies para login
        self.cookies_config = self._load_cookies_config()
        self.use_cookies = self.cookies_config.get('enabled', False)
        
        self.logger.info(f"FacebookScraper inicializado para: {page_name} (ID: {self.page_id})")
        if self.use_cookies:
            self.logger.info("🔐 Modo con cookies activado (extrae comentarios)")
    
    def _load_cookies_config(self) -> Dict:
        """Carga la configuración de cookies de Facebook."""
        import os
        cookies_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'facebook_cookies.json'
        )
        try:
            with open(cookies_path, 'r') as f:
                return json.load(f)
        except:
            return {'enabled': False}
    
    async def _apply_cookies(self) -> bool:
        """
        Aplica cookies de sesión de Facebook para acceder como usuario logueado.
        
        Returns:
            bool: True si las cookies se aplicaron correctamente
        """
        if not self.use_cookies or not self.cookies_config.get('cookies'):
            return False
        
        try:
            cookies = self.cookies_config.get('cookies', [])
            for cookie in cookies:
                if cookie.get('value', '').startswith('TU_'):
                    self.logger.warning("Cookies no configuradas - usando valores por defecto")
                    return False
                    
                await self.context.add_cookies([{
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.facebook.com'),
                    'path': '/'
                }])
            
            self.logger.info("✓ Cookies de Facebook aplicadas")
            return True
        except Exception as e:
            self.logger.warning(f"Error aplicando cookies: {e}")
            return False
    
    async def _extract_comments_from_post(self, post_url: str) -> List[Dict]:
        """
        Extrae comentarios de un post individual (requiere login).
        
        Args:
            post_url: URL del post
            
        Returns:
            Lista de comentarios extraídos
        """
        comments = []
        safety = self.cookies_config.get('safety_settings', {})
        max_comments = safety.get('max_comments_per_post', 10)
        
        try:
            # Navegar al post
            await self.page.goto(post_url, wait_until='domcontentloaded')
            await asyncio.sleep(3)
            
            # Buscar sección de comentarios
            comment_selectors = [
                'div[aria-label*="Comentar"]',
                'div[aria-label*="Comment"]', 
                'ul[class*="comment"]',
                'div[data-visualcompletion="ignore-dynamic"] > div > div'
            ]
            
            for selector in comment_selectors:
                comment_elements = await self.page.query_selector_all(selector)
                if comment_elements:
                    for elem in comment_elements[:max_comments]:
                        try:
                            text = await elem.inner_text()
                            if text and len(text) > 5:
                                comments.append({
                                    'texto': text[:500],
                                    'fecha': datetime.now().isoformat()
                                })
                        except:
                            continue
                    if comments:
                        break
            
            self.logger.debug(f"Extraídos {len(comments)} comentarios de {post_url}")
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo comentarios: {e}")
        
        return comments

    def _collect_with_fb_scraper(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Recolecta posts usando facebook-scraper (obtiene comentarios).
        
        Args:
            limit: Número máximo de posts
            
        Returns:
            List[Dict]: Posts con comentarios
        """
        self.logger.info(f"Usando facebook-scraper para {self.page_id}...")
        posts = []
        
        try:
            # Configurar opciones para obtener comentarios
            options = {
                "comments": True,  # Obtener comentarios
                "reactors": False,  # No necesitamos reactores individuales
                "allow_extra_requests": True,
                "progress": False,
            }
            
            # Obtener posts
            post_generator = get_posts(
                self.page_id,
                pages=min(limit // 5 + 1, 10),  # Aproximadamente 5 posts por página
                options=options,
                timeout=60
            )
            
            for post in post_generator:
                if len(posts) >= limit:
                    break
                    
                parsed = self._parse_fb_scraper_post(post)
                if parsed:
                    posts.append(parsed)
                    
            self.logger.info(f"facebook-scraper extrajo {len(posts)} posts con comentarios")
            return posts
            
        except Exception as e:
            self.logger.warning(f"facebook-scraper falló: {e}")
            return []
    
    def _parse_fb_scraper_post(self, post: Dict) -> Optional[Dict[str, Any]]:
        """
        Parsea un post de facebook-scraper al formato del sistema.
        """
        try:
            post_id = post.get('post_id', '') or str(hash(post.get('text', '')[:50]))
            
            # Extraer texto
            text = post.get('text', '') or post.get('post_text', '') or ''
            
            # Extraer fecha
            fecha = post.get('time')
            if not fecha:
                fecha = datetime.now()
            elif isinstance(fecha, str):
                try:
                    fecha = datetime.fromisoformat(fecha)
                except:
                    fecha = datetime.now()
            
            # Extraer métricas
            likes = post.get('likes', 0) or post.get('reactions', 0) or 0
            comments_count = post.get('comments', 0) or 0
            shares = post.get('shares', 0) or 0
            
            # Extraer comentarios reales
            comentarios_lista = []
            if 'comments_full' in post and post['comments_full']:
                for c in post['comments_full'][:20]:  # Limitar a 20 comentarios
                    comentarios_lista.append({
                        'autor': c.get('commenter_name', 'Anónimo'),
                        'texto': c.get('comment_text', ''),
                        'fecha': str(c.get('comment_time', '')),
                        'likes': c.get('comment_reaction_count', 0)
                    })
                comments_count = max(comments_count, len(comentarios_lista))
            
            return {
                'id_externo': self.generate_external_id('fb', post_id),
                'contenido_original': text[:5000],
                'fecha_publicacion': fecha,
                'autor': post.get('username', self.page_name),
                'engagement_likes': int(likes) if likes else 0,
                'engagement_comments': int(comments_count) if comments_count else 0,
                'engagement_shares': int(shares) if shares else 0,
                'tipo_contenido': 'post',
                'url_publicacion': post.get('post_url', f"https://facebook.com/{self.page_id}"),
                'metadata_json': {
                    'platform': 'facebook',
                    'page_id': self.page_id,
                    'page_name': self.page_name,
                    'post_id': post_id,
                    'has_image': bool(post.get('image')),
                    'has_video': bool(post.get('video')),
                    'comentarios': comentarios_lista,
                    'num_comentarios_extraidos': len(comentarios_lista),
                    'scrape_method': 'facebook-scraper',
                    'scrape_timestamp': datetime.now().isoformat()
                }
            }
        except Exception as e:
            self.logger.debug(f"Error parseando post fb-scraper: {e}")
            return None

    def _extract_page_id(self, url: str) -> str:
        """
        Extrae el ID o nombre de la página desde la URL.
        
        Args:
            url: URL de la página de Facebook
            
        Returns:
            str: ID o nombre de la página
        """
        # Patrón para profile.php?id=XXXXX
        id_match = re.search(r'profile\.php\?id=(\d+)', url)
        if id_match:
            return id_match.group(1)
        
        # Patrón para facebook.com/PAGENAME
        name_match = re.search(r'facebook\.com/([^/?]+)', url)
        if name_match:
            return name_match.group(1)
        
        return 'unknown'
    
    async def handle_popups(self) -> None:
        """
        Maneja popups de login, cookies y otros modales que bloquean el contenido.
        """
        try:
            # Esperar un momento para que carguen los popups
            await asyncio.sleep(2)
            
            # Intentar cerrar modal de login
            login_close = await self.page.query_selector(self.SELECTORS['login_modal'])
            if login_close:
                await login_close.click()
                self.logger.info("Modal de login cerrado")
                await asyncio.sleep(1)
            
            # Aceptar cookies si aparece el banner
            cookie_btn = await self.page.query_selector(self.SELECTORS['cookie_banner'])
            if cookie_btn:
                await cookie_btn.click()
                self.logger.info("Banner de cookies aceptado")
                await asyncio.sleep(1)
            
            # Cerrar cualquier otro modal con botón de cerrar
            close_buttons = await self.page.query_selector_all('[aria-label="Cerrar"], [aria-label="Close"]')
            for btn in close_buttons[:2]:  # Máximo 2 intentos
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                except:
                    pass
                    
        except Exception as e:
            self.logger.debug(f"Error manejando popups (no crítico): {e}")
    
    async def collect_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta posts públicos de la página de Facebook.
        
        Proceso:
        1. Intenta usar facebook-scraper (obtiene comentarios)
        2. Si falla, usa Playwright como fallback
        
        Args:
            limit: Número máximo de posts a recolectar
            
        Returns:
            List[Dict]: Lista de posts con su información
        """
        self.logger.info(f"Iniciando recolección de Facebook: {self.page_name}")
        
        # Método 1: Intentar con facebook-scraper (obtiene comentarios)
        if self.use_fb_scraper:
            self.logger.info("Usando facebook-scraper (permite extraer comentarios)...")
            posts = self._collect_with_fb_scraper(limit)
            if posts:
                self.collected_posts = posts
                self.logger.info(f"✓ facebook-scraper exitoso: {len(posts)} posts con comentarios")
                return self.collected_posts
            else:
                self.logger.warning("facebook-scraper no obtuvo resultados, usando Playwright...")
        
        # Método 2: Fallback a Playwright (con cookies si están disponibles)
        return await self._collect_with_playwright(limit)
    
    async def _collect_with_playwright(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Recolecta posts usando Playwright.
        Si hay cookies configuradas, extrae también comentarios.
        
        Args:
            limit: Número máximo de posts a recolectar
            
        Returns:
            List[Dict]: Lista de posts con su información
        """
        self.logger.info(f"Usando Playwright para: {self.page_name}")
        
        # Aplicar cookies si están disponibles
        cookies_applied = await self._apply_cookies()
        if cookies_applied:
            self.logger.info("🔐 Sesión con cookies - podrá extraer comentarios")
        
        # Navegar a la página
        success = await self.navigate_with_retry(self.source_url)
        if not success:
            self.logger.error(f"No se pudo acceder a {self.source_url}")
            return []
        
        # Manejar popups
        await self.handle_popups()
        
        # Esperar a que cargue el contenido principal
        try:
            await self.page.wait_for_selector('[role="main"]', timeout=10000)
        except:
            self.logger.warning("No se detectó contenedor principal, continuando...")
        
        # Configuración de seguridad
        safety = self.cookies_config.get('safety_settings', {})
        max_posts = min(limit, safety.get('max_posts_per_session', 20) if cookies_applied else limit)
        min_delay = safety.get('min_delay_seconds', 8) if cookies_applied else 3
        max_delay = safety.get('max_delay_seconds', 15) if cookies_applied else 7
        
        # Scroll para cargar más posts
        max_scrolls = self.config.get('scraping', {}).get('max_scroll_attempts', 20)
        posts_found = 0
        scroll_count = 0
        
        while posts_found < max_posts and scroll_count < max_scrolls:
            # Obtener HTML actual
            html_content = await self.get_page_html()
            
            # Parsear y extraer posts
            new_posts = await self._parse_posts_from_html(html_content, max_posts - posts_found)
            
            # Agregar nuevos posts únicos
            for post in new_posts:
                if post and post['id_externo'] not in [p['id_externo'] for p in self.collected_posts]:
                    self.collected_posts.append(post)
                    posts_found += 1
            
            self.logger.info(f"Posts recolectados: {posts_found}/{max_posts}")
            
            if posts_found >= max_posts:
                break
            
            # Hacer scroll
            await self.scroll_page(scroll_count=1)
            scroll_count += 1
            
            # Delay anti-detección (más largo con cookies)
            await asyncio.sleep(min_delay + (max_delay - min_delay) * asyncio.get_event_loop().time() % 1)
        
        # Si tenemos cookies, intentar extraer comentarios de los primeros posts
        if cookies_applied and self.collected_posts:
            self.logger.info("📝 Extrayendo comentarios de posts...")
            await self._enrich_posts_with_comments(min(5, len(self.collected_posts)))
        
        self.logger.info(f"Recolección completada: {len(self.collected_posts)} posts de {self.page_name}")
        return self.collected_posts
    
    async def _enrich_posts_with_comments(self, count: int) -> None:
        """
        Enriquece los posts con comentarios (requiere cookies).
        
        Args:
            count: Número de posts a enriquecer
        """
        safety = self.cookies_config.get('safety_settings', {})
        min_delay = safety.get('min_delay_seconds', 8)
        
        for i, post in enumerate(self.collected_posts[:count]):
            try:
                post_url = post.get('url_publicacion', '')
                if not post_url or 'facebook.com' not in post_url:
                    continue
                
                self.logger.debug(f"Extrayendo comentarios {i+1}/{count}: {post_url[:50]}...")
                
                # Extraer comentarios
                comments = await self._extract_comments_from_post(post_url)
                
                if comments:
                    # Actualizar metadata del post
                    if 'metadata_json' not in post:
                        post['metadata_json'] = {}
                    if isinstance(post['metadata_json'], str):
                        post['metadata_json'] = json.loads(post['metadata_json'])
                    
                    post['metadata_json']['comentarios'] = comments
                    post['metadata_json']['num_comentarios_extraidos'] = len(comments)
                    post['engagement_comments'] = max(post.get('engagement_comments', 0), len(comments))
                    
                    self.logger.info(f"  ✓ {len(comments)} comentarios extraídos")
                
                # Delay de seguridad entre posts
                await asyncio.sleep(min_delay)
                
            except Exception as e:
                self.logger.debug(f"Error enriqueciendo post: {e}")
                continue

    async def _parse_posts_from_html(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """
        Parsea el HTML para extraer información de posts.
        
        Args:
            html: Contenido HTML de la página
            limit: Número máximo de posts a extraer
            
        Returns:
            List[Dict]: Posts extraídos
        """
        soup = BeautifulSoup(html, 'lxml')
        posts = []
        
        # Buscar contenedores de posts
        post_containers = soup.select('[role="article"]')
        
        if not post_containers:
            # Fallback: buscar otros patrones
            post_containers = soup.select('div[data-pagelet*="Feed"]')
        
        self.logger.debug(f"Contenedores de post encontrados: {len(post_containers)}")
        
        for container in post_containers[:limit]:
            try:
                post_data = self._extract_post_data(container)
                if post_data and post_data.get('contenido_original'):
                    posts.append(post_data)
            except Exception as e:
                self.logger.debug(f"Error extrayendo post: {e}")
                continue
        
        return posts
    
    def _extract_post_data(self, container) -> Optional[Dict[str, Any]]:
        """
        Extrae datos de un contenedor de post individual.
        Filtra comentarios para evitar guardarlos como posts.
        
        Args:
            container: Elemento BeautifulSoup del post
            
        Returns:
            Dict con datos del post o None
        """
        try:
            # Verificar si es un comentario (anidado dentro de otro article)
            parent_article = container.find_parent('[role="article"]')
            if parent_article:
                # Este es un comentario, no un post principal
                return None
            
            # Extraer texto del post
            text_elements = container.select('div[dir="auto"]')
            text_content = ""
            for elem in text_elements:
                # Evitar textos muy cortos (probablemente UI elements)
                text = elem.get_text(strip=True)
                if len(text) > 20:  # Mínimo 20 caracteres
                    text_content = text
                    break
            
            if not text_content or len(text_content) < 10:
                return None
            
            # Generar ID único basado en contenido
            content_hash = hashlib.md5(text_content.encode()).hexdigest()[:16]
            external_id = self.generate_external_id('fb', f"{self.page_id}_{content_hash}")
            
            # Extraer autor
            author = self.page_name
            author_elem = container.select_one('h2 a, strong a, a[role="link"]')
            if author_elem:
                author = author_elem.get_text(strip=True) or self.page_name
            
            # Extraer fecha (intentar varios formatos)
            post_date = self._extract_date(container)
            
            # Extraer engagement
            likes = self._extract_engagement_count(container, 'like')
            comments = self._extract_engagement_count(container, 'comment')
            shares = self._extract_engagement_count(container, 'share')
            
            # Filtrar probable comentario: sin engagement y texto muy corto
            if likes == 0 and comments == 0 and shares == 0 and len(text_content) < 100:
                # Podría ser un comentario, verificar si tiene URL de post
                post_url = self._extract_post_url(container)
                if not post_url or 'comment' in str(post_url).lower():
                    return None
            
            # Determinar tipo de contenido
            content_type = 'texto'
            if container.select('video, div[data-video-id]'):
                content_type = 'video'
            elif container.select('img[src*="scontent"]'):
                content_type = 'imagen'
            
            # Extraer URL del post
            post_url = self._extract_post_url(container)
            
            # Metadata adicional
            metadata = {
                'page_id': self.page_id,
                'page_name': self.page_name,
                'scrape_timestamp': datetime.now().isoformat(),
                'has_image': bool(container.select('img[src*="scontent"]')),
                'has_video': bool(container.select('video')),
                'text_length': len(text_content)
            }
            
            return {
                'id_externo': external_id,
                'contenido_original': text_content,
                'fecha_publicacion': post_date,
                'autor': author,
                'engagement_likes': likes,
                'engagement_comments': comments,
                'engagement_shares': shares,
                'tipo_contenido': content_type,
                'url_publicacion': post_url or self.source_url,
                'metadata_json': metadata
            }
            
        except Exception as e:
            self.logger.debug(f"Error en _extract_post_data: {e}")
            return None
    
    def _extract_date(self, container) -> datetime:
        """
        Extrae la fecha de publicación del post.
        
        Intenta varios patrones comunes de Facebook.
        
        Args:
            container: Elemento del post
            
        Returns:
            datetime: Fecha del post (o fecha actual si no se encuentra)
        """
        try:
            # Buscar elemento abbr con data-utime (Unix timestamp)
            abbr = container.select_one('abbr[data-utime]')
            if abbr and abbr.get('data-utime'):
                timestamp = int(abbr['data-utime'])
                return datetime.fromtimestamp(timestamp)
            
            # Buscar texto de fecha relativa
            date_patterns = [
                (r'(\d+)\s*h', 'hours'),      # "2 h" = 2 horas
                (r'(\d+)\s*min', 'minutes'),   # "30 min"
                (r'(\d+)\s*d', 'days'),        # "3 d" = 3 días
                (r'(\d+)\s*sem', 'weeks'),     # "1 sem" = 1 semana
                (r'ayer', 'yesterday'),
                (r'hace\s*(\d+)\s*hora', 'hours'),
                (r'hace\s*(\d+)\s*día', 'days'),
            ]
            
            # Buscar en spans dentro del contenedor
            for span in container.select('span, a'):
                text = span.get_text(strip=True).lower()
                
                for pattern, unit in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        now = datetime.now()
                        
                        if unit == 'yesterday':
                            return now - timedelta(days=1)
                        
                        amount = int(match.group(1)) if match.lastindex else 1
                        
                        if unit == 'hours':
                            return now - timedelta(hours=amount)
                        elif unit == 'minutes':
                            return now - timedelta(minutes=amount)
                        elif unit == 'days':
                            return now - timedelta(days=amount)
                        elif unit == 'weeks':
                            return now - timedelta(weeks=amount)
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo fecha: {e}")
        
        # Default: fecha actual
        return datetime.now()
    
    def _extract_engagement_count(self, container, engagement_type: str) -> int:
        """
        Extrae conteo de engagement (likes, comments, shares).
        
        Args:
            container: Elemento del post
            engagement_type: Tipo de engagement ('like', 'comment', 'share')
            
        Returns:
            int: Cantidad de engagement
        """
        try:
            patterns = {
                'like': [
                    r'(\d+(?:[.,]\d+)?)\s*(?:K|k|mil)?\s*(?:me gusta|likes?|reacciones?)',
                    r'(\d+(?:[.,]\d+)?)\s*(?:K|k)',  # Solo número con K
                ],
                'comment': [
                    r'(\d+(?:[.,]\d+)?)\s*(?:K|k|mil)?\s*comentario',
                    r'(\d+)\s*comment',
                ],
                'share': [
                    r'(\d+(?:[.,]\d+)?)\s*(?:K|k|mil)?\s*(?:veces compartido|compartido|shares?)',
                    r'(\d+)\s*share',
                ]
            }
            
            # Buscar en todo el texto del contenedor
            text = container.get_text().lower()
            
            for pattern in patterns.get(engagement_type, []):
                match = re.search(pattern, text)
                if match:
                    num_str = match.group(1).replace(',', '.').replace(' ', '')
                    
                    # Manejar notación K (miles)
                    if 'k' in text[match.start():match.end()].lower() or 'mil' in text[match.start():match.end()].lower():
                        return int(float(num_str) * 1000)
                    
                    return int(float(num_str))
            
        except Exception as e:
            self.logger.debug(f"Error extrayendo {engagement_type}: {e}")
        
        return 0
    
    def _extract_post_url(self, container) -> Optional[str]:
        """
        Extrae la URL directa del post.
        
        Args:
            container: Elemento del post
            
        Returns:
            str: URL del post o None
        """
        try:
            # Buscar links a posts
            link_patterns = ['a[href*="/posts/"]', 'a[href*="/photos/"]', 'a[href*="/videos/"]']
            
            for pattern in link_patterns:
                link = container.select_one(pattern)
                if link and link.get('href'):
                    href = link['href']
                    if href.startswith('/'):
                        return f"https://www.facebook.com{href}"
                    return href
                    
        except Exception as e:
            self.logger.debug(f"Error extrayendo URL: {e}")
        
        return None
    
    async def parse_post(self, element) -> Optional[Dict[str, Any]]:
        """
        Implementación del método abstracto.
        Parsea un elemento de post individual (usado por la clase base).
        
        Args:
            element: Elemento del DOM
            
        Returns:
            Dict con datos del post
        """
        # Este método se usa cuando trabajamos con elementos Playwright directamente
        try:
            html = await element.inner_html()
            soup = BeautifulSoup(html, 'lxml')
            return self._extract_post_data(soup)
        except Exception as e:
            self.logger.error(f"Error en parse_post: {e}")
            return None


async def main():
    """Función de prueba para el scraper de Facebook."""
    import json
    
    # Cargar configuración
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Configurar logging básico
    logging.basicConfig(level=logging.INFO)
    
    # Probar con la página EMI.UALP
    scraper = FacebookScraper(
        page_url="https://www.facebook.com/EMI.UALP",
        page_name="EMI UALP",
        config=config
    )
    
    # Ejecutar recolección
    posts = await scraper.run(limit=10)
    
    print(f"\n=== Resultados ===")
    print(f"Total posts recolectados: {len(posts)}")
    
    for i, post in enumerate(posts[:3], 1):
        print(f"\n--- Post {i} ---")
        print(f"ID: {post['id_externo']}")
        print(f"Autor: {post['autor']}")
        print(f"Texto: {post['contenido_original'][:100]}...")
        print(f"Likes: {post['engagement_likes']}")
        print(f"Comentarios: {post['engagement_comments']}")


if __name__ == "__main__":
    asyncio.run(main())
