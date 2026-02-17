#!/usr/bin/env python3
"""
Extractor de comentarios de TikTok usando TikTokApi
Basado en: https://github.com/davidteather/TikTok-Api
"""

import asyncio
import json
import sqlite3
import os
from datetime import datetime

# Intentar importar TikTokApi
try:
    from TikTokApi import TikTokApi
    TIKTOK_API_AVAILABLE = True
except ImportError:
    TIKTOK_API_AVAILABLE = False
    print("TikTokApi no disponible, instalando...")


async def get_video_comments(video_url: str, max_comments: int = 50) -> list:
    """
    Extrae comentarios de un video de TikTok usando TikTokApi.
    
    Args:
        video_url: URL del video (ej: https://www.tiktok.com/@user/video/123456)
        max_comments: Máximo de comentarios a extraer
        
    Returns:
        Lista de comentarios con texto, autor, likes, fecha
    """
    comments = []
    
    if not TIKTOK_API_AVAILABLE:
        print("TikTokApi no está instalado")
        return comments
    
    # Extraer video_id de la URL
    video_id = video_url.split('/video/')[-1].split('?')[0]
    
    print(f"  Extrayendo comentarios del video {video_id}...")
    
    try:
        async with TikTokApi() as api:
            # Crear sesiones con Playwright
            await api.create_sessions(
                ms_tokens=[None],  # Sin token
                num_sessions=1,
                sleep_after=3,
                headless=True,  # Sin ventana
                browser="chromium"
            )
            
            # Obtener video
            video = api.video(id=video_id)
            
            # Obtener comentarios
            count = 0
            async for comment in video.comments(count=max_comments):
                try:
                    comment_data = comment.as_dict
                    
                    # Extraer datos del comentario
                    autor = comment_data.get('user', {}).get('nickname', 'Usuario')
                    if not autor:
                        autor = comment_data.get('user', {}).get('unique_id', 'Usuario')
                    
                    texto = comment_data.get('text', '')
                    likes = comment_data.get('digg_count', 0)
                    
                    # Fecha
                    create_time = comment_data.get('create_time', 0)
                    if create_time:
                        fecha = datetime.fromtimestamp(create_time).isoformat()
                    else:
                        fecha = datetime.now().isoformat()
                    
                    if texto.strip():
                        comments.append({
                            'autor': str(autor)[:100],
                            'contenido': texto[:2000],
                            'likes': int(likes) if likes else 0,
                            'fecha': fecha,
                            'plataforma': 'tiktok',
                            'video_id': video_id
                        })
                        count += 1
                        
                        if count >= max_comments:
                            break
                            
                except Exception as e:
                    continue
            
            print(f"  ✓ Extraídos {len(comments)} comentarios")
            
    except Exception as e:
        print(f"  ❌ Error con TikTokApi: {e}")
        # Intentar método alternativo
        comments = await get_comments_alternative(video_id, max_comments)
    
    return comments


async def get_comments_alternative(video_id: str, max_comments: int = 50) -> list:
    """
    Método alternativo usando Playwright directamente con anti-detección.
    """
    from playwright.async_api import async_playwright
    import random
    
    comments = []
    video_url = f"https://www.tiktok.com/@user/video/{video_id}"
    
    print(f"  Intentando método alternativo con Playwright...")
    
    try:
        async with async_playwright() as p:
            # Usar Chromium con stealth mode
            browser = await p.chromium.launch(
                headless=False,  # Visible para evitar detección
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 900},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='es-BO',
                timezone_id='America/La_Paz',
            )
            
            # Inyectar scripts anti-detección
            await context.add_init_script("""
                // Ocultar webdriver
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                
                // Ocultar plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Ocultar languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-ES', 'es', 'en-US', 'en']
                });
                
                // Chrome runtime
                window.chrome = { runtime: {} };
                
                // Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
            """)
            
            page = await context.new_page()
            
            # Navegar al video
            print(f"    Navegando a: {video_url}")
            await page.goto(video_url, wait_until='networkidle', timeout=60000)
            
            # Esperar un poco
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # Verificar CAPTCHA
            captcha_present = await page.query_selector('[class*="captcha"], [id*="captcha"]')
            if captcha_present:
                print(f"    ⚠️ CAPTCHA detectado, esperando resolución manual...")
                await page.wait_for_timeout(30000)  # 30 segundos para resolver
            
            # Scroll para cargar comentarios
            for i in range(5):
                await page.evaluate('window.scrollBy(0, 300)')
                await page.wait_for_timeout(random.randint(1000, 2000))
            
            # Buscar contenedor de comentarios con varios selectores
            selectors = [
                '[data-e2e="comment-item"]',
                '[class*="DivCommentItemContainer"]',
                '[class*="CommentItemWrapper"]',
                'div[class*="comment-item"]',
            ]
            
            comment_elements = []
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        comment_elements = elements
                        print(f"    ✓ Encontrados {len(elements)} elementos con: {selector}")
                        break
                except:
                    continue
            
            # Extraer comentarios del DOM
            for element in comment_elements[:max_comments]:
                try:
                    text = await element.inner_text()
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    
                    if len(lines) >= 2:
                        autor = lines[0]
                        # Buscar el texto del comentario (excluir métricas)
                        contenido_lines = []
                        for line in lines[1:]:
                            if not any(x in line.lower() for x in ['reply', 'responder', 'like', 'me gusta', 'ago', 'hace']):
                                if not line.isdigit() and len(line) > 1:
                                    contenido_lines.append(line)
                        
                        contenido = ' '.join(contenido_lines[:3])
                        
                        if contenido.strip():
                            comments.append({
                                'autor': autor[:100],
                                'contenido': contenido[:2000],
                                'likes': 0,
                                'fecha': datetime.now().isoformat(),
                                'plataforma': 'tiktok',
                                'video_id': video_id
                            })
                except:
                    continue
            
            await browser.close()
            print(f"    ✓ Extraídos {len(comments)} comentarios (método alternativo)")
            
    except Exception as e:
        print(f"    ❌ Error método alternativo: {e}")
    
    return comments


async def scrape_tiktok_with_comments(profile_url: str, max_videos: int = 5) -> list:
    """
    Scraping completo de TikTok: videos + comentarios reales.
    """
    import subprocess
    import re
    
    posts = []
    
    # Obtener path del yt-dlp
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(script_dir, 'venv', 'bin', 'yt-dlp')
    ytdlp_cmd = venv_path if os.path.exists(venv_path) else 'yt-dlp'
    
    print(f"\n{'='*60}")
    print(f"🎵 SCRAPING TIKTOK CON COMENTARIOS REALES")
    print(f"   Perfil: {profile_url}")
    print(f"   Videos: {max_videos}")
    print(f"{'='*60}\n")
    
    # PASO 1: Obtener lista de videos con yt-dlp
    print(f"📹 PASO 1: Extrayendo videos...")
    
    cmd = [ytdlp_cmd, '--flat-playlist', '--dump-json', '--no-download', 
           '--playlist-end', str(max_videos), profile_url]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode != 0:
        print(f"❌ Error yt-dlp")
        return []
    
    video_list = []
    for line in result.stdout.strip().split('\n'):
        if line:
            try:
                video_list.append(json.loads(line))
            except:
                pass
    
    print(f"   ✓ {len(video_list)} videos encontrados\n")
    
    # PASO 2: Para cada video, obtener detalles y comentarios
    print(f"💬 PASO 2: Extrayendo comentarios de cada video...")
    
    for i, data in enumerate(video_list):
        video_id = data.get('id', '')
        uploader = data.get('uploader', 'user')
        video_url = f"https://www.tiktok.com/@{uploader}/video/{video_id}"
        
        print(f"\n[{i+1}/{len(video_list)}] Video: {video_id}")
        
        # Obtener detalles completos
        detail_cmd = [ytdlp_cmd, '--dump-json', '--no-download', video_url]
        detail_result = subprocess.run(detail_cmd, capture_output=True, text=True, timeout=60)
        
        if detail_result.returncode == 0 and detail_result.stdout.strip():
            try:
                data = json.loads(detail_result.stdout.strip())
            except:
                pass
        
        # Extraer datos
        timestamp = data.get('timestamp')
        fecha = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()
        
        likes = data.get('like_count', 0) or 0
        comments_count = data.get('comment_count', 0) or 0
        shares = data.get('repost_count', 0) or 0
        views = data.get('view_count', 0) or 0
        
        descripcion = data.get('description', '') or data.get('title', '') or "Video TikTok"
        hashtags = re.findall(r'#(\w+)', descripcion)
        
        print(f"  📝 {descripcion[:60]}...")
        print(f"  📊 {views:,} views | {likes:,} likes | {comments_count} comentarios")
        
        # EXTRAER COMENTARIOS REALES
        comentarios = []
        if comments_count > 0:
            print(f"  💬 Extrayendo comentarios textuales...")
            comentarios = await get_video_comments(video_url, max_comments=30)
        
        post = {
            'id_externo': f"tt_{video_id}",
            'contenido': descripcion[:2000],
            'fecha': fecha,
            'autor': uploader,
            'likes': int(likes),
            'comentarios_count': int(comments_count),
            'shares': int(shares),
            'views': int(views),
            'url': video_url,
            'tipo': 'video',
            'hashtags': hashtags,
            'comentarios': comentarios
        }
        
        posts.append(post)
        print(f"  ✅ Procesado: {len(comentarios)} comentarios extraídos")
    
    total_comments = sum(len(p.get('comentarios', [])) for p in posts)
    print(f"\n🎉 COMPLETADO: {len(posts)} videos, {total_comments} comentarios extraídos")
    
    return posts


def save_to_database(posts, source_id=5):
    """Guardar posts y comentarios en la base de datos."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, 'data', 'osint_emi.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    posts_added = 0
    comments_added = 0
    
    for post in posts:
        try:
            external_id = post['id_externo']
            
            # Verificar si existe
            cursor.execute('SELECT id_dato FROM dato_recolectado WHERE id_externo = ?', (external_id,))
            existing = cursor.fetchone()
            
            if existing:
                post_id = existing[0]
                # Actualizar métricas
                cursor.execute('''
                    UPDATE dato_recolectado SET
                    engagement_likes = ?, engagement_comments = ?, 
                    engagement_shares = ?, engagement_views = ?
                    WHERE id_dato = ?
                ''', (post['likes'], post['comentarios_count'], post['shares'], post['views'], post_id))
            else:
                # Insertar nuevo
                cursor.execute('''
                    INSERT INTO dato_recolectado 
                    (id_fuente, id_externo, fecha_publicacion, fecha_recoleccion,
                     contenido_original, autor, engagement_likes, engagement_comments,
                     engagement_shares, engagement_views, tipo_contenido, url_publicacion,
                     metadata_json, procesado)
                    VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ''', (
                    source_id, external_id, post['fecha'],
                    post['contenido'], post['autor'],
                    post['likes'], post['comentarios_count'], post['shares'], post['views'],
                    'video', post['url'], json.dumps({'hashtags': post.get('hashtags', [])})
                ))
                post_id = cursor.lastrowid
                posts_added += 1
            
            # Guardar comentarios
            for c in post.get('comentarios', []):
                try:
                    # Verificar si ya existe el comentario (por contenido + autor)
                    cursor.execute('''
                        SELECT id_comentario FROM comentario 
                        WHERE id_post = ? AND autor = ? AND contenido = ?
                    ''', (post_id, c['autor'], c['contenido']))
                    
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO comentario 
                            (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                            VALUES (?, ?, ?, ?, ?, ?, 0)
                        ''', (post_id, source_id, c['autor'], c['contenido'], c.get('fecha'), c.get('likes', 0)))
                        comments_added += 1
                except sqlite3.IntegrityError:
                    continue
            
        except Exception as e:
            print(f"  Error guardando: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Guardado: {posts_added} posts nuevos, {comments_added} comentarios nuevos")
    return posts_added, comments_added


async def main():
    """Función principal para testing."""
    TIKTOK_URL = "https://www.tiktok.com/@emilapazoficial"
    MAX_VIDEOS = 5
    
    print("\n" + "="*60)
    print("   EXTRACTOR DE COMENTARIOS DE TIKTOK")
    print("="*60)
    
    posts = await scrape_tiktok_with_comments(TIKTOK_URL, MAX_VIDEOS)
    
    if posts:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN")
        print(f"{'='*60}")
        
        for i, p in enumerate(posts, 1):
            num_comments = len(p.get('comentarios', []))
            print(f"\n{i}. {p['contenido'][:50]}...")
            print(f"   👁️ {p['views']:,} views | ❤️ {p['likes']:,} likes | 💬 {num_comments} comentarios")
            
            # Mostrar primeros comentarios
            for c in p.get('comentarios', [])[:3]:
                print(f"   └─ @{c['autor']}: {c['contenido'][:50]}...")
        
        # Guardar en BD
        save_to_database(posts)
    else:
        print("❌ No se obtuvieron posts")


if __name__ == '__main__':
    asyncio.run(main())
