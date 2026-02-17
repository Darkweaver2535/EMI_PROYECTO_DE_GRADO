#!/usr/bin/env python3
"""
Scraping de TikTok con extracción de comentarios usando API no oficial
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import subprocess
import json
import asyncio
import requests
from datetime import datetime
import re

# Configuración
TIKTOK_URL = "https://www.tiktok.com/@emilapazoficial"
MAX_VIDEOS = 5


def get_tiktok_comments_api(video_id: str, max_comments: int = 50) -> list:
    """
    Intenta extraer comentarios usando una API pública de TikTok
    """
    comments = []
    
    # Intentar múltiples métodos
    methods = [
        lambda: get_comments_method1(video_id, max_comments),
        lambda: get_comments_method2(video_id, max_comments),
    ]
    
    for method in methods:
        try:
            comments = method()
            if comments:
                return comments
        except Exception as e:
            continue
    
    return comments


def get_comments_method1(video_id: str, max_comments: int) -> list:
    """Método 1: API interna de TikTok"""
    comments = []
    
    # Headers para simular navegador
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Referer': f'https://www.tiktok.com/@user/video/{video_id}',
    }
    
    url = f"https://www.tiktok.com/api/comment/list/?aweme_id={video_id}&count=50"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for c in data.get('comments', [])[:max_comments]:
                comments.append({
                    'autor': c.get('user', {}).get('nickname', 'Usuario'),
                    'contenido': c.get('text', ''),
                    'likes': c.get('digg_count', 0),
                    'fecha': datetime.fromtimestamp(c.get('create_time', 0)).isoformat() if c.get('create_time') else datetime.now().isoformat(),
                    'plataforma': 'tiktok'
                })
    except:
        pass
    
    return comments


def get_comments_method2(video_id: str, max_comments: int) -> list:
    """Método 2: Web scraping básico del HTML"""
    comments = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    }
    
    url = f"https://www.tiktok.com/@user/video/{video_id}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            html = response.text
            
            # Buscar datos de SIGI_STATE (TikTok embebe datos JSON en el HTML)
            match = re.search(r'<script id="SIGI_STATE" type="application/json">(.+?)</script>', html)
            if match:
                data = json.loads(match.group(1))
                
                # Extraer comentarios del estado
                comment_data = data.get('Comment', {}).get('comments', {})
                for cid, c in comment_data.items():
                    comments.append({
                        'autor': c.get('user', 'Usuario'),
                        'contenido': c.get('text', ''),
                        'likes': c.get('digg_count', 0),
                        'fecha': datetime.now().isoformat(),
                        'plataforma': 'tiktok'
                    })
    except:
        pass
    
    return comments[:max_comments]


async def extract_comments_playwright(video_url: str, max_comments: int = 30) -> list:
    """
    Extrae comentarios usando Playwright con configuración anti-bot
    """
    from playwright.async_api import async_playwright
    import random
    
    comments = []
    
    try:
        async with async_playwright() as p:
            # Usar Chromium en modo visible para evitar detección
            browser = await p.chromium.launch(
                headless=False,  # Visible para evitar detección
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 900},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                locale='es-BO',
            )
            
            # Ocultar automatización
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = await context.new_page()
            
            print(f"    🔍 Abriendo: {video_url}")
            
            await page.goto(video_url, wait_until='networkidle', timeout=45000)
            await page.wait_for_timeout(random.randint(5000, 8000))
            
            # Scroll para cargar comentarios
            for _ in range(5):
                await page.evaluate('window.scrollBy(0, 300)')
                await page.wait_for_timeout(1500)
            
            # Buscar comentarios con varios selectores
            selectors = [
                '[data-e2e="comment-item"]',
                '[class*="DivCommentItemContainer"]',
                '[class*="CommentItemContainer"]',
            ]
            
            comment_elements = []
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        comment_elements = elements
                        print(f"    ✓ Encontrados {len(elements)} elementos")
                        break
                except:
                    continue
            
            # Procesar elementos encontrados
            for element in comment_elements[:max_comments]:
                try:
                    text = await element.inner_text()
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    
                    if len(lines) >= 2:
                        autor = lines[0]
                        contenido = ' '.join(lines[1:-1]) if len(lines) > 2 else lines[1]
                        
                        comments.append({
                            'autor': autor[:100],
                            'contenido': contenido[:2000],
                            'likes': 0,
                            'fecha': datetime.now().isoformat(),
                            'plataforma': 'tiktok'
                        })
                except:
                    continue
            
            await browser.close()
            
    except Exception as e:
        print(f"    ❌ Error Playwright: {e}")
    
    return comments


def scrape_tiktok(profile_url: str, max_videos: int = 5):
    """
    Scraping completo de TikTok
    """
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'yt-dlp')
    ytdlp_cmd = venv_path if os.path.exists(venv_path) else 'yt-dlp'
    
    posts = []
    
    print(f"\n{'='*60}")
    print(f"🎵 SCRAPING TIKTOK: {profile_url}")
    print(f"{'='*60}\n")
    
    # Extraer videos
    print(f"📹 Extrayendo {max_videos} videos...")
    
    cmd = [ytdlp_cmd, '--flat-playlist', '--dump-json', '--no-download', '--playlist-end', str(max_videos), profile_url]
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
    
    # Procesar cada video
    for i, data in enumerate(video_list):
        video_id = data.get('id', '')
        video_url = f"https://www.tiktok.com/@{data.get('uploader', 'user')}/video/{video_id}"
        
        print(f"\n[{i+1}/{len(video_list)}] Video: {video_id}")
        
        # Obtener detalles completos
        detail_cmd = [ytdlp_cmd, '--dump-json', '--no-download', video_url]
        detail_result = subprocess.run(detail_cmd, capture_output=True, text=True, timeout=60)
        
        if detail_result.returncode == 0 and detail_result.stdout.strip():
            try:
                data = json.loads(detail_result.stdout.strip())
            except:
                pass
        
        # Datos del video
        timestamp = data.get('timestamp')
        fecha = datetime.fromtimestamp(timestamp).isoformat() if timestamp else datetime.now().isoformat()
        
        likes = data.get('like_count', 0) or 0
        comments_count = data.get('comment_count', 0) or 0
        shares = data.get('repost_count', 0) or 0
        views = data.get('view_count', 0) or 0
        
        descripcion = data.get('description', '') or data.get('title', '') or "Video TikTok"
        
        print(f"  📝 {descripcion[:70]}...")
        print(f"  📊 {views:,} views | {likes:,} likes | {comments_count} comments")
        
        # Extraer hashtags
        hashtags = re.findall(r'#(\w+)', descripcion)
        
        # Intentar extraer comentarios
        comentarios = []
        if comments_count > 0:
            print(f"  💬 Intentando extraer comentarios...")
            
            # Método 1: API
            comentarios = get_tiktok_comments_api(video_id, 30)
            
            # Método 2: Playwright si no funcionó
            if not comentarios:
                print(f"     API no funcionó, intentando Playwright...")
                try:
                    comentarios = asyncio.run(extract_comments_playwright(video_url, 30))
                except Exception as e:
                    print(f"     Playwright tampoco funcionó: {e}")
        
        post = {
            'id_externo': f"tt_{video_id}",
            'contenido': descripcion[:2000],
            'fecha': fecha,
            'autor': data.get('uploader', 'TikTok User'),
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
        print(f"  ✅ Procesado con {len(comentarios)} comentarios")
    
    return posts


def save_to_database(posts, source_id=5):
    """Guardar en base de datos"""
    import sqlite3
    
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'osint_emi.db')
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
                cursor.execute('''
                    UPDATE dato_recolectado SET
                    engagement_likes = ?, engagement_comments = ?, engagement_shares = ?, engagement_views = ?
                    WHERE id_dato = ?
                ''', (post['likes'], post['comentarios_count'], post['shares'], post['views'], post_id))
            else:
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
                    cursor.execute('''
                        INSERT INTO comentario 
                        (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                        VALUES (?, ?, ?, ?, ?, ?, 0)
                    ''', (post_id, source_id, c['autor'], c['contenido'], c.get('fecha'), c.get('likes', 0)))
                    comments_added += 1
                except:
                    continue
            
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ BD: {posts_added} posts nuevos, {comments_added} comentarios")
    return posts_added, comments_added


if __name__ == '__main__':
    print("\n" + "="*60)
    print("   SCRAPING TIKTOK - VIDEOS Y COMENTARIOS")
    print("="*60)
    
    posts = scrape_tiktok(TIKTOK_URL, MAX_VIDEOS)
    
    if posts:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN")
        print(f"{'='*60}")
        
        total_comments = sum(len(p.get('comentarios', [])) for p in posts)
        
        for i, p in enumerate(posts, 1):
            print(f"\n{i}. {p['contenido'][:60]}...")
            print(f"   👁️ {p['views']:,} views | ❤️ {p['likes']:,} likes | 💬 {len(p.get('comentarios', []))} comentarios")
            
            for c in p.get('comentarios', [])[:2]:
                print(f"   └─ @{c['autor']}: {c['contenido'][:50]}...")
        
        print(f"\n📊 TOTAL: {len(posts)} videos, {total_comments} comentarios")
        
        save_to_database(posts)
    else:
        print("❌ No se obtuvieron posts")
