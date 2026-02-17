#!/usr/bin/env python3
"""
🎵 SCRAPER ROBUSTO DE TIKTOK CON COMENTARIOS
============================================
Sistema profesional para extraer videos y comentarios de TikTok
con soporte para cookies de sesión y delays inteligentes.

Uso:
    python tiktok_scraper_robust.py --profile "@aborami.emi" --videos 5
    python tiktok_scraper_robust.py --cookies "tu_cookie_aqui"
"""

import asyncio
import json
import sqlite3
import os
import time
import random
import re
import subprocess
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Configuración de delays para evitar bans
DELAYS = {
    'between_videos': (8, 15),      # Segundos entre cada video
    'between_scroll': (1, 3),       # Segundos entre scrolls
    'after_page_load': (3, 6),      # Segundos después de cargar página
    'captcha_wait': 45,             # Segundos para resolver CAPTCHA manualmente
    'between_comments_batch': (2, 5), # Entre lotes de comentarios
}

# Archivo para guardar cookies
COOKIES_FILE = Path(__file__).parent / 'data' / 'tiktok_cookies.json'


class TikTokRobustScraper:
    """Scraper robusto de TikTok con anti-detección y soporte de cookies."""
    
    def __init__(self, cookies: Optional[str] = None, headless: bool = False):
        """
        Args:
            cookies: String de cookies de sesión de TikTok (opcional)
            headless: Si True, el navegador no se muestra (menos confiable)
        """
        self.cookies = cookies
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.db_path = Path(__file__).parent / 'data' / 'osint_emi.db'
        
    def _get_stealth_script(self) -> str:
        """Scripts JavaScript para evitar detección de bots."""
        return """
        // Ocultar webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Simular plugins reales
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ];
                plugins.item = (i) => plugins[i];
                plugins.namedItem = (n) => plugins.find(p => p.name === n);
                plugins.refresh = () => {};
                return plugins;
            }
        });
        
        // Simular idiomas
        Object.defineProperty(navigator, 'languages', {
            get: () => ['es-ES', 'es', 'en-US', 'en']
        });
        
        // Chrome runtime
        window.chrome = {
            runtime: {
                onConnect: { addListener: () => {} },
                onMessage: { addListener: () => {} }
            }
        };
        
        // Permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
        
        // WebGL Vendor/Renderer
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter.call(this, parameter);
        };
        
        // Ocultar automatización
        delete navigator.__proto__.webdriver;
        
        // Canvas fingerprint
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' && this.width === 220 && this.height === 30) {
                return originalToDataURL.apply(this, arguments);
            }
            return originalToDataURL.apply(this, arguments);
        };
        """
    
    def _random_delay(self, delay_type: str) -> float:
        """Genera un delay aleatorio para simular comportamiento humano."""
        min_delay, max_delay = DELAYS.get(delay_type, (2, 5))
        delay = random.uniform(min_delay, max_delay)
        return delay
    
    async def _setup_browser(self):
        """Configura el navegador con anti-detección y perfil persistente."""
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        
        # Directorio para datos persistentes del navegador
        user_data_dir = Path(__file__).parent / 'data' / 'browser_profile'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Usar launch_persistent_context para mantener sesión entre ejecuciones
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=self.headless,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='es-ES',
            timezone_id='America/La_Paz',
            color_scheme='light',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--lang=es-ES',
            ]
        )
        
        # Referencia al browser (es el mismo que context en persistent)
        self.browser = self.context
        
        # Inyectar scripts anti-detección
        await self.context.add_init_script(self._get_stealth_script())
        
        # Cargar cookies si están disponibles
        if self.cookies:
            await self._load_cookies()
        elif COOKIES_FILE.exists():
            await self._load_cookies_from_file()
        
        self.page = await self.context.new_page()
        
        # Configurar timeouts
        self.page.set_default_timeout(60000)
        
    async def _load_cookies(self):
        """Carga cookies de sesión desde string."""
        if not self.cookies:
            return
            
        try:
            # Parsear cookies (formato: "name1=value1; name2=value2")
            cookie_list = []
            for cookie_str in self.cookies.split(';'):
                if '=' in cookie_str:
                    name, value = cookie_str.strip().split('=', 1)
                    cookie_list.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.tiktok.com',
                        'path': '/'
                    })
            
            if cookie_list:
                await self.context.add_cookies(cookie_list)
                print(f"  🍪 Cargadas {len(cookie_list)} cookies de sesión")
                
                # Guardar para uso futuro
                self._save_cookies_to_file(cookie_list)
                
        except Exception as e:
            print(f"  ⚠️ Error cargando cookies: {e}")
    
    async def _load_cookies_from_file(self):
        """Carga cookies guardadas del archivo (formato EditThisCookie/Playwright)."""
        try:
            if COOKIES_FILE.exists():
                with open(COOKIES_FILE, 'r') as f:
                    raw_cookies = json.load(f)
                
                if raw_cookies:
                    # Convertir formato EditThisCookie a formato Playwright
                    playwright_cookies = []
                    for cookie in raw_cookies:
                        # Mapear sameSite
                        same_site = cookie.get('sameSite', 'Lax')
                        if same_site == 'unspecified':
                            same_site = 'Lax'
                        elif same_site == 'no_restriction':
                            same_site = 'None'
                        else:
                            same_site = same_site.capitalize() if same_site else 'Lax'
                        
                        playwright_cookie = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie.get('domain', '.tiktok.com'),
                            'path': cookie.get('path', '/'),
                            'secure': cookie.get('secure', False),
                            'httpOnly': cookie.get('httpOnly', False),
                            'sameSite': same_site
                        }
                        
                        # Añadir expires si existe
                        if 'expirationDate' in cookie and cookie['expirationDate']:
                            playwright_cookie['expires'] = cookie['expirationDate']
                        
                        playwright_cookies.append(playwright_cookie)
                    
                    await self.context.add_cookies(playwright_cookies)
                    print(f"  🍪 Cargadas {len(playwright_cookies)} cookies del archivo")
                    
                    # Mostrar cookies importantes
                    important_cookies = ['sessionid', 'msToken', 'tt_csrf_token', 'ttwid']
                    loaded_names = [c['name'] for c in playwright_cookies]
                    found = [n for n in important_cookies if n in loaded_names]
                    print(f"  ✓ Cookies importantes: {', '.join(found)}")
                    
        except Exception as e:
            print(f"  ⚠️ Error cargando cookies del archivo: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_cookies_to_file(self, cookies: list):
        """Guarda cookies para uso futuro."""
        try:
            COOKIES_FILE.parent.mkdir(exist_ok=True)
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookies, f)
        except Exception as e:
            print(f"  ⚠️ Error guardando cookies: {e}")
    
    async def _check_and_handle_captcha(self) -> bool:
        """Detecta y maneja CAPTCHA."""
        try:
            content = await self.page.content()
            captcha_indicators = ['captcha', 'verify', 'challenge', 'tiktok-verify']
            
            if any(ind in content.lower() for ind in captcha_indicators):
                print(f"\n  ⚠️  CAPTCHA DETECTADO!")
                print(f"  👆 Por favor, resuelve el CAPTCHA en el navegador...")
                print(f"  ⏱️  Esperando {DELAYS['captcha_wait']} segundos...")
                
                await self.page.wait_for_timeout(DELAYS['captcha_wait'] * 1000)
                
                # Verificar si se resolvió
                new_content = await self.page.content()
                if any(ind in new_content.lower() for ind in captcha_indicators):
                    print(f"  ❌ CAPTCHA no resuelto, continuando...")
                    return False
                else:
                    print(f"  ✅ CAPTCHA resuelto!")
                    return True
            
            return True
            
        except Exception as e:
            return True
    
    async def _human_scroll(self, scroll_count: int = 5):
        """Simula scroll humano para cargar comentarios."""
        for i in range(scroll_count):
            scroll_amount = random.randint(200, 400)
            await self.page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            
            delay = self._random_delay('between_scroll')
            await self.page.wait_for_timeout(int(delay * 1000))
    
    async def _initialize_session(self):
        """
        Inicializa la sesión visitando TikTok homepage primero.
        Esto ayuda a establecer las cookies correctamente antes de visitar videos.
        """
        try:
            print(f"    🏠 Inicializando sesión en TikTok...")
            
            # Visitar homepage primero
            await self.page.goto('https://www.tiktok.com/', wait_until='domcontentloaded')
            await self.page.wait_for_timeout(3000)
            
            # Verificar si hay CAPTCHA en homepage
            content = await self.page.content()
            if 'captcha' in content.lower() or 'verify' in content.lower():
                print(f"    ⚠️ CAPTCHA en homepage - esperando 30s para resolver manualmente...")
                await self.page.wait_for_timeout(30000)
            
            # Esperar un poco más para que las cookies se establezcan
            await self.page.wait_for_timeout(2000)
            
            # Verificar si estamos logueados
            if 'login' not in await self.page.url.lower():
                print(f"    ✅ Sesión establecida correctamente")
                return True
            else:
                print(f"    ⚠️ No se pudo establecer sesión")
                return False
                
        except Exception as e:
            print(f"    ❌ Error inicializando sesión: {e}")
            return False
    
    async def extract_comments_from_video(self, video_url: str, max_comments: int = 50) -> List[Dict]:
        """
        Extrae comentarios de un video de TikTok.
        
        Args:
            video_url: URL completa del video
            max_comments: Máximo de comentarios a extraer
            
        Returns:
            Lista de diccionarios con datos de comentarios
        """
        comments = []
        
        try:
            print(f"    🌐 Abriendo: {video_url[:60]}...")
            
            # Navegar al video
            await self.page.goto(video_url, wait_until='domcontentloaded')
            
            # Delay post-carga
            delay = self._random_delay('after_page_load')
            print(f"    ⏱️  Esperando {delay:.1f}s...")
            await self.page.wait_for_timeout(int(delay * 1000))
            
            # Verificar CAPTCHA
            captcha_ok = await self._check_and_handle_captcha()
            if not captcha_ok:
                return comments
            
            # Scroll para cargar comentarios
            print(f"    📜 Cargando comentarios...")
            await self._human_scroll(5)
            
            # Intentar múltiples selectores
            selectors = [
                '[class*="DivCommentItemContainer"]',
                '[data-e2e="comment-item"]',
                '[class*="CommentItem"]',
                '[class*="CommentListContainer"] > div > div',
                'div[class*="comment"]',
            ]
            
            comment_elements = []
            used_selector = None
            
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        comment_elements = elements
                        used_selector = selector
                        break
                except:
                    continue
            
            if not comment_elements:
                print(f"    ⚠️ No se encontraron comentarios en el DOM")
                return comments
            
            print(f"    ✓ Encontrados {len(comment_elements)} elementos")
            
            # Extraer datos de cada comentario
            for idx, element in enumerate(comment_elements[:max_comments]):
                try:
                    # Obtener todo el texto del elemento
                    full_text = await element.inner_text()
                    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                    
                    if len(lines) < 2:
                        continue
                    
                    # Primera línea suele ser el autor
                    autor = lines[0]
                    
                    # Filtrar líneas que son claramente metadatos
                    content_lines = []
                    for line in lines[1:]:
                        line_lower = line.lower()
                        # Ignorar métricas y botones
                        if any(x in line_lower for x in [
                            'reply', 'responder', 'like', 'me gusta', 
                            'ago', 'hace', 'view', 'ver', 'hora',
                            'día', 'day', 'week', 'semana', 'mes', 'month'
                        ]):
                            continue
                        # Ignorar números solos (conteos)
                        if line.replace(',', '').replace('.', '').isdigit():
                            continue
                        # Ignorar líneas muy cortas
                        if len(line) < 2:
                            continue
                        content_lines.append(line)
                    
                    contenido = ' '.join(content_lines[:3]).strip()
                    
                    # Validar que tenemos contenido real
                    if contenido and len(contenido) > 2 and autor:
                        comments.append({
                            'autor': autor[:100],
                            'contenido': contenido[:2000],
                            'likes': 0,
                            'fecha': datetime.now().isoformat(),
                            'plataforma': 'tiktok'
                        })
                        
                except Exception as e:
                    continue
            
            # Delay entre lotes
            if comments:
                delay = self._random_delay('between_comments_batch')
                await self.page.wait_for_timeout(int(delay * 1000))
            
            print(f"    ✅ Extraídos {len(comments)} comentarios válidos")
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:100]}")
        
        return comments
    
    def get_videos_with_ytdlp(self, profile_url: str, max_videos: int = 5) -> List[Dict]:
        """Obtiene lista de videos usando yt-dlp."""
        script_dir = Path(__file__).parent
        venv_path = script_dir / 'venv' / 'bin' / 'yt-dlp'
        ytdlp_cmd = str(venv_path) if venv_path.exists() else 'yt-dlp'
        
        videos = []
        
        try:
            # Obtener lista de videos
            cmd = [
                ytdlp_cmd,
                '--flat-playlist',
                '--dump-json',
                '--no-download',
                '--playlist-end', str(max_videos),
                profile_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"❌ Error yt-dlp: {result.stderr[:200] if result.stderr else 'desconocido'}")
                return videos
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        video_id = data.get('id', '')
                        uploader = data.get('uploader', 'user')
                        
                        videos.append({
                            'id': video_id,
                            'url': f"https://www.tiktok.com/@{uploader}/video/{video_id}",
                            'uploader': uploader,
                            'title': data.get('title', ''),
                        })
                    except:
                        pass
            
            # Obtener detalles completos de cada video
            for video in videos:
                try:
                    detail_cmd = [ytdlp_cmd, '--dump-json', '--no-download', video['url']]
                    detail_result = subprocess.run(detail_cmd, capture_output=True, text=True, timeout=60)
                    
                    if detail_result.returncode == 0 and detail_result.stdout.strip():
                        data = json.loads(detail_result.stdout.strip())
                        video['description'] = data.get('description', '') or data.get('title', '')
                        video['likes'] = data.get('like_count', 0) or 0
                        video['comments_count'] = data.get('comment_count', 0) or 0
                        video['shares'] = data.get('repost_count', 0) or 0
                        video['views'] = data.get('view_count', 0) or 0
                        video['timestamp'] = data.get('timestamp')
                        video['duration'] = data.get('duration', 0)
                        video['music'] = data.get('track', '')
                        video['artist'] = data.get('artist', '')
                except Exception as e:
                    video['description'] = video.get('title', 'Video TikTok')
                    video['likes'] = 0
                    video['comments_count'] = 0
                    video['shares'] = 0
                    video['views'] = 0
            
        except subprocess.TimeoutExpired:
            print("❌ Timeout en yt-dlp")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        return videos
    
    async def scrape_profile(self, profile_url: str, max_videos: int = 5, source_id: int = None) -> Dict:
        """
        Scraping completo de un perfil de TikTok.
        
        Args:
            profile_url: URL del perfil (ej: https://www.tiktok.com/@aborami.emi)
            max_videos: Número de videos a procesar
            source_id: ID de la fuente en la BD (opcional)
            
        Returns:
            Diccionario con estadísticas del scraping
        """
        stats = {
            'videos_processed': 0,
            'comments_extracted': 0,
            'videos_saved': 0,
            'comments_saved': 0,
            'errors': []
        }
        
        print(f"\n{'='*70}")
        print(f"  🎵 SCRAPING TIKTOK ROBUSTO")
        print(f"  📍 Perfil: {profile_url}")
        print(f"  📹 Videos: {max_videos}")
        print(f"  🍪 Cookies: {'Sí' if self.cookies or COOKIES_FILE.exists() else 'No'}")
        print(f"{'='*70}\n")
        
        # PASO 1: Obtener videos con yt-dlp
        print("📹 PASO 1: Obteniendo lista de videos...")
        videos = self.get_videos_with_ytdlp(profile_url, max_videos)
        
        if not videos:
            print("❌ No se encontraron videos")
            return stats
        
        print(f"   ✓ {len(videos)} videos encontrados\n")
        
        # Mostrar videos
        for i, v in enumerate(videos):
            desc = v.get('description', '')[:50]
            comments = v.get('comments_count', 0)
            print(f"   [{i+1}] {desc}... ({comments} comentarios)")
        
        # PASO 2: Configurar navegador
        print(f"\n🌐 PASO 2: Iniciando navegador con anti-detección...")
        await self._setup_browser()
        print("   ✓ Navegador listo\n")
        
        # PASO 3: Extraer comentarios de cada video
        print(f"💬 PASO 3: Extrayendo comentarios de cada video...")
        
        all_results = []
        
        for i, video in enumerate(videos):
            print(f"\n{'─'*50}")
            print(f"  [{i+1}/{len(videos)}] {video.get('description', 'Video')[:40]}...")
            print(f"  📊 Reportados: {video.get('comments_count', 0)} comentarios")
            
            # Extraer comentarios
            comments = await self.extract_comments_from_video(video['url'], max_comments=50)
            
            stats['videos_processed'] += 1
            stats['comments_extracted'] += len(comments)
            
            # Guardar en BD si tenemos source_id
            if source_id and (video or comments):
                saved = self._save_to_database(source_id, video, comments)
                stats['videos_saved'] += saved['videos']
                stats['comments_saved'] += saved['comments']
            
            all_results.append({
                'video': video,
                'comments': comments
            })
            
            # Delay entre videos (importante para evitar ban)
            if i < len(videos) - 1:
                delay = self._random_delay('between_videos')
                print(f"\n  ⏱️  Esperando {delay:.1f}s antes del siguiente video...")
                await self.page.wait_for_timeout(int(delay * 1000))
        
        # Cerrar navegador
        await self._cleanup()
        
        # Resumen
        print(f"\n{'='*70}")
        print(f"  🎉 SCRAPING COMPLETADO")
        print(f"  📹 Videos procesados: {stats['videos_processed']}")
        print(f"  💬 Comentarios extraídos: {stats['comments_extracted']}")
        if source_id:
            print(f"  💾 Videos guardados: {stats['videos_saved']}")
            print(f"  💾 Comentarios guardados: {stats['comments_saved']}")
        print(f"{'='*70}\n")
        
        return stats
    
    def _save_to_database(self, source_id: int, video: Dict, comments: List[Dict]) -> Dict:
        """Guarda video y comentarios en la base de datos."""
        saved = {'videos': 0, 'comments': 0}
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Verificar si el video ya existe
            external_id = f"tt_{video['id']}"
            cursor.execute(
                'SELECT id_dato FROM dato_recolectado WHERE id_externo = ?',
                (external_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                post_id = existing['id_dato']
            else:
                # Insertar video
                timestamp = video.get('timestamp')
                fecha = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO dato_recolectado 
                    (id_fuente, id_externo, fecha_publicacion, fecha_recoleccion, 
                     contenido_original, autor, engagement_likes, engagement_comments,
                     engagement_shares, engagement_views, tipo_contenido, url_publicacion,
                     metadata_json, procesado)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, 'video', ?, ?, 0)
                ''', (
                    source_id,
                    external_id,
                    fecha,
                    video.get('description', '')[:2000],
                    video.get('uploader', 'TikTok User'),
                    video.get('likes', 0),
                    video.get('comments_count', 0),
                    video.get('shares', 0),
                    video.get('views', 0),
                    video['url'],
                    json.dumps({
                        'platform': 'tiktok',
                        'video_id': video['id'],
                        'duration': video.get('duration', 0),
                        'music': video.get('music', ''),
                        'artist': video.get('artist', ''),
                    })
                ))
                post_id = cursor.lastrowid
                saved['videos'] = 1
            
            # Insertar comentarios
            for comment in comments:
                # Verificar duplicado
                cursor.execute(
                    'SELECT 1 FROM comentario WHERE id_post = ? AND contenido = ?',
                    (post_id, comment['contenido'][:500])
                )
                if cursor.fetchone():
                    continue
                
                cursor.execute('''
                    INSERT INTO comentario 
                    (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    post_id,
                    source_id,
                    comment['autor'],
                    comment['contenido'],
                    comment['fecha'],
                    comment['likes']
                ))
                saved['comments'] += 1
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"    ⚠️ Error guardando en BD: {e}")
        
        return saved
    
    async def _cleanup(self):
        """Limpia recursos."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass


async def scrape_tiktok_profile(
    profile_url: str,
    max_videos: int = 5,
    source_id: int = None,
    cookies: str = None,
    headless: bool = False
) -> Dict:
    """
    Función principal para scraping de TikTok.
    
    Args:
        profile_url: URL del perfil
        max_videos: Número de videos
        source_id: ID de fuente en BD
        cookies: Cookies de sesión (opcional)
        headless: Navegador sin ventana
        
    Returns:
        Estadísticas del scraping
    """
    scraper = TikTokRobustScraper(cookies=cookies, headless=headless)
    return await scraper.scrape_profile(profile_url, max_videos, source_id)


def run_scraper(profile_url: str, max_videos: int = 5, source_id: int = None, cookies: str = None):
    """Ejecuta el scraper de forma síncrona."""
    return asyncio.run(scrape_tiktok_profile(
        profile_url=profile_url,
        max_videos=max_videos,
        source_id=source_id,
        cookies=cookies,
        headless=False  # Visible para mejor evasión
    ))


# =====================================================
# ENDPOINT PARA GUARDAR COOKIES
# =====================================================

def save_tiktok_cookies(cookies_string: str) -> bool:
    """
    Guarda cookies de TikTok para uso futuro.
    
    Args:
        cookies_string: String de cookies (ej: "sessionid=xxx; tt_csrf_token=yyy")
        
    Returns:
        True si se guardaron correctamente
    """
    try:
        cookie_list = []
        for cookie_str in cookies_string.split(';'):
            if '=' in cookie_str:
                name, value = cookie_str.strip().split('=', 1)
                cookie_list.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.tiktok.com',
                    'path': '/'
                })
        
        if cookie_list:
            COOKIES_FILE.parent.mkdir(exist_ok=True)
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookie_list, f, indent=2)
            print(f"✅ Guardadas {len(cookie_list)} cookies en {COOKIES_FILE}")
            return True
            
    except Exception as e:
        print(f"❌ Error guardando cookies: {e}")
    
    return False


# =====================================================
# MAIN
# =====================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Scraper robusto de TikTok')
    parser.add_argument('--profile', '-p', default='https://www.tiktok.com/@aborami.emi',
                       help='URL del perfil de TikTok')
    parser.add_argument('--videos', '-v', type=int, default=5,
                       help='Número de videos a procesar')
    parser.add_argument('--cookies', '-c', type=str, default=None,
                       help='String de cookies de sesión')
    parser.add_argument('--source-id', '-s', type=int, default=5,
                       help='ID de la fuente en la BD')
    parser.add_argument('--save-cookies', action='store_true',
                       help='Solo guardar cookies y salir')
    
    args = parser.parse_args()
    
    if args.save_cookies and args.cookies:
        save_tiktok_cookies(args.cookies)
    else:
        stats = run_scraper(
            profile_url=args.profile,
            max_videos=args.videos,
            source_id=args.source_id,
            cookies=args.cookies
        )
        print(f"\nResultado: {stats}")
