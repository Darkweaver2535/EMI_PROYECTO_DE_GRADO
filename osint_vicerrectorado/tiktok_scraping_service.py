#!/usr/bin/env python3
"""
🎵 SERVICIO DE SCRAPING TIKTOK CON EVENTOS EN TIEMPO REAL
=========================================================
Este servicio maneja el scraping de TikTok con comunicación 
en tiempo real hacia el frontend a través de Server-Sent Events.

El flujo es:
1. Frontend inicia scraping
2. Backend abre navegador y envía eventos de progreso
3. Si hay CAPTCHA, envía evento y espera confirmación
4. Frontend notifica cuando usuario resuelve CAPTCHA
5. Backend continúa extracción y envía progreso
"""

import asyncio
import sqlite3
import json
import random
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Generator
from dataclasses import dataclass, asdict
from enum import Enum

# Playwright
from playwright.async_api import async_playwright, BrowserContext, Page

# Configuración
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'data' / 'osint_emi.db'
COOKIES_FILE = BASE_DIR / 'data' / 'tiktok_cookies.json'
BROWSER_PROFILE = BASE_DIR / 'data' / 'tiktok_browser_profile'

# Delays para simular comportamiento humano
DELAYS = {
    'between_videos': (4, 8),
    'between_scroll': (0.6, 1.2),
    'after_page_load': (2, 4),
}


class EventType(Enum):
    """Tipos de eventos que se envían al frontend."""
    STARTED = "started"
    BROWSER_OPENING = "browser_opening"
    BROWSER_READY = "browser_ready"
    CAPTCHA_DETECTED = "captcha_detected"
    CAPTCHA_RESOLVED = "captcha_resolved"
    VIDEO_STARTED = "video_started"
    VIDEO_PROGRESS = "video_progress"
    VIDEO_COMPLETED = "video_completed"
    COMMENTS_EXTRACTED = "comments_extracted"
    ERROR = "error"
    COMPLETED = "completed"
    WAITING_USER = "waiting_user"


@dataclass
class ScrapingEvent:
    """Evento de scraping para enviar al frontend."""
    type: str
    message: str
    data: dict = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.data is None:
            self.data = {}
    
    def to_json(self) -> str:
        return json.dumps({
            'type': self.type,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp
        })


class TikTokScrapingSession:
    """
    Sesión de scraping de TikTok con comunicación en tiempo real.
    """
    
    def __init__(self, source_id: int):
        self.source_id = source_id
        self.session_id = f"tiktok_{source_id}_{int(datetime.now().timestamp())}"
        
        # Cola de eventos para SSE
        self.event_queue: queue.Queue = queue.Queue()
        
        # Estado de la sesión
        self.running = False
        self.paused = False
        self.cancelled = False
        self.waiting_for_user = False
        self.user_confirmed = False
        
        # Estadísticas
        self.stats = {
            'videos_total': 0,
            'videos_processed': 0,
            'comments_total': 0,
            'comments_extracted': 0,
            'errors': 0
        }
        
        # Browser
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
    def emit_event(self, event_type: EventType, message: str, data: dict = None):
        """Emite un evento a la cola para ser enviado al frontend."""
        event = ScrapingEvent(
            type=event_type.value,
            message=message,
            data=data or {}
        )
        self.event_queue.put(event)
        print(f"📤 [{event_type.value}] {message}")
    
    def get_events(self) -> Generator[str, None, None]:
        """Generador de eventos SSE."""
        while self.running or not self.event_queue.empty():
            try:
                event = self.event_queue.get(timeout=1)
                yield f"data: {event.to_json()}\n\n"
            except queue.Empty:
                # Heartbeat para mantener conexión
                yield f": heartbeat\n\n"
    
    def user_continue(self):
        """El usuario confirma que puede continuar (ej: resolvió CAPTCHA)."""
        self.user_confirmed = True
        self.waiting_for_user = False
        self.emit_event(
            EventType.CAPTCHA_RESOLVED,
            "Usuario confirmó resolución de CAPTCHA"
        )
    
    def cancel(self):
        """Cancela la sesión de scraping."""
        self.cancelled = True
        self.running = False
        self.emit_event(EventType.ERROR, "Scraping cancelado por el usuario")
    
    async def _wait_for_user(self, message: str, timeout: int = 300):
        """Espera confirmación del usuario."""
        self.waiting_for_user = True
        self.user_confirmed = False
        
        self.emit_event(
            EventType.WAITING_USER,
            message,
            {'timeout': timeout, 'requires_action': True}
        )
        
        # Esperar confirmación con timeout
        waited = 0
        while not self.user_confirmed and not self.cancelled and waited < timeout:
            await asyncio.sleep(0.5)
            waited += 0.5
        
        self.waiting_for_user = False
        return self.user_confirmed
    
    async def _check_captcha(self) -> bool:
        """Verifica si hay CAPTCHA en la página."""
        try:
            content = await self.page.content()
            lower_content = content.lower()
            
            captcha_indicators = [
                'captcha', 'verify', 'puzzle', 'slider',
                'verificación', 'verificacion', 'robot'
            ]
            
            return any(ind in lower_content for ind in captcha_indicators)
        except:
            return False
    
    async def _extract_comments_from_page(self, video_id: int) -> list:
        """Extrae comentarios de la página actual."""
        comments = []
        
        # Scroll para cargar comentarios
        for _ in range(8):
            scroll = random.randint(300, 500)
            await self.page.evaluate(f'window.scrollBy(0, {scroll})')
            await asyncio.sleep(random.uniform(*DELAYS['between_scroll']))
        
        # Selectores para comentarios
        selectors = [
            '[class*="DivCommentItemContainer"]',
            '[data-e2e="comment-item"]',
            '[class*="CommentItem"]',
        ]
        
        comment_elements = []
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    comment_elements = elements
                    break
            except:
                continue
        
        if not comment_elements:
            return comments
        
        # Extraer texto de comentarios
        for element in comment_elements[:50]:
            try:
                text = await element.inner_text()
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                if len(lines) < 2:
                    continue
                
                autor = lines[0]
                
                # Filtrar metadatos
                content_lines = []
                for line in lines[1:]:
                    line_lower = line.lower()
                    if any(x in line_lower for x in [
                        'reply', 'responder', 'like', 'me gusta',
                        'ago', 'hace', 'view', 'ver', 'hora',
                        'día', 'day', 'week', 'semana', 'mes', 'month'
                    ]):
                        continue
                    if line.replace(',', '').replace('.', '').isdigit():
                        continue
                    if len(line) < 2:
                        continue
                    content_lines.append(line)
                
                contenido = ' '.join(content_lines[:3]).strip()
                
                if contenido and len(contenido) > 2:
                    comments.append({
                        'autor': autor[:100],
                        'contenido': contenido[:2000],
                        'fecha': datetime.now().isoformat()
                    })
            except:
                continue
        
        return comments
    
    async def _save_comments(self, video_id: int, comments: list) -> int:
        """Guarda comentarios en la base de datos."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        saved = 0
        for c in comments:
            # Verificar duplicado
            cursor.execute(
                'SELECT 1 FROM comentario WHERE id_post = ? AND contenido = ?',
                (video_id, c['contenido'][:500])
            )
            if cursor.fetchone():
                continue
            
            cursor.execute('''
                INSERT INTO comentario 
                (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                VALUES (?, ?, ?, ?, ?, 0, 0)
            ''', (
                video_id,
                self.source_id,
                c['autor'],
                c['contenido'],
                c['fecha']
            ))
            saved += 1
        
        conn.commit()
        conn.close()
        return saved
    
    async def run(self):
        """Ejecuta el scraping interactivo."""
        self.running = True
        
        try:
            self.emit_event(
                EventType.STARTED,
                "Iniciando sesión de scraping TikTok",
                {'session_id': self.session_id, 'source_id': self.source_id}
            )
            
            # Obtener videos de la BD
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id_dato, url_publicacion, contenido_original, engagement_comments,
                       (SELECT COUNT(*) FROM comentario c WHERE c.id_post = d.id_dato) as extracted
                FROM dato_recolectado d
                WHERE id_fuente = ?
                ORDER BY id_dato
            ''', (self.source_id,))
            
            videos = cursor.fetchall()
            conn.close()
            
            if not videos:
                self.emit_event(
                    EventType.ERROR,
                    "No hay videos en la base de datos para esta fuente"
                )
                return
            
            # Filtrar videos que necesitan comentarios
            videos_to_process = [v for v in videos if v['extracted'] < v['engagement_comments']]
            
            self.stats['videos_total'] = len(videos_to_process)
            self.stats['comments_total'] = sum(v['engagement_comments'] - v['extracted'] for v in videos_to_process)
            
            if not videos_to_process:
                self.emit_event(
                    EventType.COMPLETED,
                    "¡Todos los videos ya tienen sus comentarios extraídos!",
                    {'stats': self.stats}
                )
                return
            
            # Emitir estado inicial
            self.emit_event(
                EventType.BROWSER_OPENING,
                f"Abriendo navegador... Se procesarán {len(videos_to_process)} videos",
                {
                    'videos_to_process': len(videos_to_process),
                    'videos_info': [
                        {
                            'id': v['id_dato'],
                            'description': (v['contenido_original'] or '')[:60],
                            'comments_expected': v['engagement_comments'],
                            'comments_extracted': v['extracted']
                        }
                        for v in videos_to_process
                    ]
                }
            )
            
            # Iniciar navegador
            async with async_playwright() as p:
                BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
                
                self.context = await p.chromium.launch_persistent_context(
                    user_data_dir=str(BROWSER_PROFILE),
                    headless=False,
                    viewport={'width': 1400, 'height': 900},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    locale='es-ES',
                    timezone_id='America/La_Paz',
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--lang=es-ES',
                    ]
                )
                
                self.page = await self.context.new_page()
                
                # Cargar cookies
                if COOKIES_FILE.exists():
                    try:
                        with open(COOKIES_FILE, 'r') as f:
                            raw_cookies = json.load(f)
                        
                        playwright_cookies = []
                        for cookie in raw_cookies:
                            same_site = cookie.get('sameSite', 'Lax')
                            if same_site in ['unspecified', '', None]:
                                same_site = 'Lax'
                            elif same_site == 'no_restriction':
                                same_site = 'None'
                            elif same_site not in ['Strict', 'Lax', 'None']:
                                same_site = 'Lax'
                            
                            pc = {
                                'name': cookie['name'],
                                'value': cookie['value'],
                                'domain': cookie.get('domain', '.tiktok.com'),
                                'path': cookie.get('path', '/'),
                                'secure': cookie.get('secure', False),
                                'httpOnly': cookie.get('httpOnly', False),
                                'sameSite': same_site
                            }
                            if 'expirationDate' in cookie:
                                pc['expires'] = cookie['expirationDate']
                            playwright_cookies.append(pc)
                        
                        await self.context.add_cookies(playwright_cookies)
                    except Exception as e:
                        self.emit_event(EventType.ERROR, f"Error cargando cookies: {e}")
                
                # Navegar a TikTok
                await self.page.goto('https://www.tiktok.com/', wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # Verificar CAPTCHA inicial
                if await self._check_captcha():
                    self.emit_event(
                        EventType.CAPTCHA_DETECTED,
                        "⚠️ Se detectó CAPTCHA. Por favor resuélvelo en el navegador que se abrió.",
                        {'requires_action': True}
                    )
                    
                    confirmed = await self._wait_for_user(
                        "Resuelve el CAPTCHA en el navegador y luego presiona 'Continuar'",
                        timeout=300
                    )
                    
                    if not confirmed:
                        self.emit_event(EventType.ERROR, "Tiempo de espera agotado para CAPTCHA")
                        return
                else:
                    self.emit_event(
                        EventType.BROWSER_READY,
                        "✅ Navegador listo. Iniciando extracción de comentarios...",
                        {'cookies_loaded': COOKIES_FILE.exists()}
                    )
                
                # Procesar cada video
                for i, video in enumerate(videos_to_process):
                    if self.cancelled:
                        break
                    
                    video_id = video['id_dato']
                    self.stats['videos_processed'] = i + 1
                    
                    self.emit_event(
                        EventType.VIDEO_STARTED,
                        f"Procesando video {i+1}/{len(videos_to_process)}",
                        {
                            'video_id': video_id,
                            'video_index': i + 1,
                            'video_total': len(videos_to_process),
                            'url': video['url_publicacion'],
                            'description': (video['contenido_original'] or '')[:100],
                            'expected_comments': video['engagement_comments'],
                            'extracted_before': video['extracted']
                        }
                    )
                    
                    try:
                        # Navegar al video
                        await self.page.goto(video['url_publicacion'], wait_until='domcontentloaded')
                        delay = random.uniform(*DELAYS['after_page_load'])
                        await asyncio.sleep(delay)
                        
                        # Verificar CAPTCHA
                        if await self._check_captcha():
                            self.emit_event(
                                EventType.CAPTCHA_DETECTED,
                                "⚠️ CAPTCHA detectado. Por favor resuélvelo.",
                                {'video_id': video_id, 'requires_action': True}
                            )
                            
                            confirmed = await self._wait_for_user(
                                "Resuelve el CAPTCHA y presiona 'Continuar'",
                                timeout=300
                            )
                            
                            if not confirmed:
                                continue
                        
                        # Extraer comentarios
                        self.emit_event(
                            EventType.VIDEO_PROGRESS,
                            "Extrayendo comentarios...",
                            {'video_id': video_id, 'status': 'extracting'}
                        )
                        
                        comments = await self._extract_comments_from_page(video_id)
                        
                        # Guardar comentarios
                        saved = await self._save_comments(video_id, comments)
                        self.stats['comments_extracted'] += saved
                        
                        self.emit_event(
                            EventType.VIDEO_COMPLETED,
                            f"Video completado: {saved} comentarios nuevos",
                            {
                                'video_id': video_id,
                                'comments_found': len(comments),
                                'comments_saved': saved,
                                'stats': self.stats
                            }
                        )
                        
                    except Exception as e:
                        self.stats['errors'] += 1
                        self.emit_event(
                            EventType.ERROR,
                            f"Error en video {video_id}: {str(e)}",
                            {'video_id': video_id, 'error': str(e)}
                        )
                    
                    # Delay entre videos
                    if i < len(videos_to_process) - 1:
                        delay = random.uniform(*DELAYS['between_videos'])
                        await asyncio.sleep(delay)
                
                # Cerrar navegador
                await self.context.close()
            
            # Completado
            self.emit_event(
                EventType.COMPLETED,
                f"🎉 Scraping completado. {self.stats['comments_extracted']} comentarios extraídos.",
                {'stats': self.stats}
            )
            
        except Exception as e:
            self.emit_event(
                EventType.ERROR,
                f"Error fatal: {str(e)}",
                {'error': str(e)}
            )
        finally:
            self.running = False


# Almacén global de sesiones activas
active_sessions: dict[str, TikTokScrapingSession] = {}


def start_tiktok_scraping(source_id: int) -> TikTokScrapingSession:
    """Inicia una nueva sesión de scraping."""
    session = TikTokScrapingSession(source_id)
    active_sessions[session.session_id] = session
    
    # Ejecutar en thread separado
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(session.run())
        loop.close()
    
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()
    
    return session


def get_session(session_id: str) -> Optional[TikTokScrapingSession]:
    """Obtiene una sesión existente."""
    return active_sessions.get(session_id)


def cleanup_session(session_id: str):
    """Limpia una sesión terminada."""
    if session_id in active_sessions:
        del active_sessions[session_id]
