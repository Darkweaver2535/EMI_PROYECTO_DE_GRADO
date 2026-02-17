#!/usr/bin/env python3
"""
Test script para scraping de TikTok con extracción de comentarios
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import subprocess
import json
import asyncio
from datetime import datetime

# Configuración
TIKTOK_URL = "https://www.tiktok.com/@emilapazoficial"
MAX_VIDEOS = 5
MAX_COMMENTS_PER_VIDEO = 30


async def extract_tiktok_comments_playwright(video_url: str, max_comments: int = 30) -> list:
    """
    Extrae comentarios REALES de un video de TikTok usando Playwright.
    """
    from playwright.async_api import async_playwright
    import random
    
    comments = []
    
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(
                headless=True,
                args=['--no-sandbox']
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='es-ES'
            )
            
            page = await context.new_page()
            
            print(f"    🔍 Navegando a: {video_url}")
            
            await page.goto(video_url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # Esperar comentarios
            try:
                await page.wait_for_selector('[class*="CommentItem"], [class*="comment-item"], [data-e2e="comment-item"]', timeout=15000)
            except:
                print(f"    ⚠️ No se encontró contenedor de comentarios, intentando scroll...")
            
            # Scroll para cargar más
            for _ in range(3):
                await page.evaluate('window.scrollBy(0, 500)')
                await page.wait_for_timeout(1500)
            
            # Buscar comentarios con múltiples selectores
            selectors = [
                '[data-e2e="comment-item"]',
                '[class*="DivCommentItemContainer"]',
                '[class*="CommentItem"]',
                'div[class*="comment-item"]'
            ]
            
            comment_elements = []
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    comment_elements = elements
                    print(f"    ✓ Encontrados {len(elements)} comentarios con selector: {selector}")
                    break
            
            if not comment_elements:
                print(f"    ⚠️ No se encontraron elementos de comentarios")
                await browser.close()
                return comments
            
            # Procesar comentarios
            for i, element in enumerate(comment_elements[:max_comments]):
                try:
                    # Autor
                    autor = "Usuario TikTok"
                    autor_selectors = ['[data-e2e="comment-username"]', '[class*="UserName"]', 'a[href*="/@"]']
                    for sel in autor_selectors:
                        autor_el = await element.query_selector(sel)
                        if autor_el:
                            autor = await autor_el.inner_text()
                            break
                    
                    # Texto
                    texto = ""
                    texto_selectors = ['[data-e2e="comment-level-1"] > span', '[class*="CommentText"]', 'span[class*="text"]', 'p']
                    for sel in texto_selectors:
                        texto_el = await element.query_selector(sel)
                        if texto_el:
                            texto = await texto_el.inner_text()
                            if texto.strip():
                                break
                    
                    if not texto:
                        texto = await element.inner_text()
                        texto = texto.replace(autor, '').strip()
                    
                    # Likes
                    likes = 0
                    like_selectors = ['[data-e2e="comment-like-count"]', '[class*="LikeCount"]']
                    for sel in like_selectors:
                        like_el = await element.query_selector(sel)
                        if like_el:
                            like_text = await like_el.inner_text()
                            like_text = like_text.strip().upper()
                            if 'K' in like_text:
                                likes = int(float(like_text.replace('K', '')) * 1000)
                            elif 'M' in like_text:
                                likes = int(float(like_text.replace('M', '')) * 1000000)
                            elif like_text.isdigit():
                                likes = int(like_text)
                            break
                    
                    if texto.strip():
                        comments.append({
                            'autor': autor.strip()[:100],
                            'contenido': texto.strip()[:2000],
                            'likes': likes,
                            'fecha': datetime.now().isoformat(),
                            'plataforma': 'tiktok'
                        })
                        
                except Exception as e:
                    continue
            
            await browser.close()
            print(f"    ✓ Extraídos {len(comments)} comentarios de TikTok")
            
    except Exception as e:
        print(f"    ❌ Error extrayendo comentarios: {e}")
        import traceback
        traceback.print_exc()
    
    return comments


def scrape_tiktok_complete(profile_url: str, max_videos: int = 5):
    """
    Scraping completo de TikTok: videos + comentarios
    """
    venv_path = os.path.join(os.path.dirname(__file__), 'venv', 'bin', 'yt-dlp')
    ytdlp_cmd = venv_path if os.path.exists(venv_path) else 'yt-dlp'
    
    posts = []
    
    print(f"\n{'='*60}")
    print(f"🎵 SCRAPING TIKTOK: {profile_url}")
    print(f"{'='*60}\n")
    
    # PASO 1: Obtener lista de videos
    print(f"📹 PASO 1: Extrayendo metadatos de {max_videos} videos...")
    
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
        print(f"❌ Error yt-dlp: {result.stderr[:500] if result.stderr else 'desconocido'}")
        return []
    
    video_data = []
    for line in result.stdout.strip().split('\n'):
        if line:
            try:
                video_data.append(json.loads(line))
            except:
                pass
    
    print(f"   ✓ {len(video_data)} videos encontrados\n")
    
    # PASO 2: Para cada video, obtener detalles y comentarios
    print(f"💬 PASO 2: Extrayendo descripciones y comentarios...")
    
    for i, data in enumerate(video_data):
        video_id = data.get('id', '')
        video_url = data.get('url') or f"https://www.tiktok.com/@{data.get('uploader', 'user')}/video/{video_id}"
        
        print(f"\n  [{i+1}/{len(video_data)}] Video: {video_id}")
        
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
        
        print(f"    📝 Descripción: {descripcion[:80]}...")
        print(f"    📊 Métricas: {likes} likes, {comments_count} comments, {views} views")
        
        # Extraer hashtags
        import re
        hashtags = re.findall(r'#(\w+)', descripcion)
        
        # Extraer comentarios reales
        comentarios = []
        if comments_count > 0:
            print(f"    💬 Extrayendo comentarios ({comments_count} disponibles)...")
            try:
                comentarios = asyncio.run(extract_tiktok_comments_playwright(video_url, MAX_COMMENTS_PER_VIDEO))
            except Exception as e:
                print(f"    ⚠️ Error en comentarios: {e}")
        
        post = {
            'id_externo': f"tt_{video_id}",
            'texto': descripcion[:2000],
            'contenido': descripcion[:2000],
            'fecha': fecha,
            'autor': data.get('uploader', data.get('channel', 'TikTok User')),
            'likes': int(likes),
            'comentarios_count': int(comments_count),
            'shares': int(shares),
            'views': int(views),
            'url': video_url,
            'tipo': 'video',
            'metadata': {
                'platform': 'tiktok',
                'video_id': video_id,
                'duration': data.get('duration', 0),
                'music': data.get('track', ''),
                'artist': data.get('artist', ''),
                'hashtags': hashtags,
            },
            'comentarios': comentarios
        }
        
        posts.append(post)
        print(f"    ✅ Video procesado con {len(comentarios)} comentarios extraídos")
    
    return posts


def save_to_database(posts, source_id=5):
    """Guardar posts y comentarios en la base de datos"""
    import sqlite3
    
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'osint_emi.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    posts_added = 0
    comments_added = 0
    
    for post in posts:
        try:
            external_id = post['id_externo']
            
            # Verificar si ya existe
            cursor.execute('SELECT id_dato FROM dato_recolectado WHERE id_externo = ?', (external_id,))
            existing = cursor.fetchone()
            
            if existing:
                post_id = existing[0]
                print(f"  Post {external_id} ya existe (id={post_id}), actualizando...")
                cursor.execute('''
                    UPDATE dato_recolectado SET
                    engagement_likes = ?,
                    engagement_comments = ?,
                    engagement_shares = ?,
                    engagement_views = ?,
                    metadata_json = ?
                    WHERE id_dato = ?
                ''', (
                    post['likes'], post['comentarios_count'], post['shares'], post['views'],
                    json.dumps(post['metadata']), post_id
                ))
            else:
                # Insertar nuevo post
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
                    'video', post['url'], json.dumps(post['metadata'])
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
                    ''', (
                        post_id, source_id, c['autor'], c['contenido'],
                        c.get('fecha', datetime.now().isoformat()), c.get('likes', 0)
                    ))
                    comments_added += 1
                except sqlite3.IntegrityError:
                    continue
            
        except Exception as e:
            print(f"  Error guardando post: {e}")
            continue
    
    # Actualizar última recolección
    cursor.execute('''
        UPDATE fuente_osint SET ultima_recoleccion = datetime('now')
        WHERE id_fuente = ?
    ''', (source_id,))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Guardado en BD: {posts_added} posts nuevos, {comments_added} comentarios")
    return posts_added, comments_added


if __name__ == '__main__':
    print("\n" + "="*60)
    print("   TEST DE SCRAPING TIKTOK CON COMENTARIOS")
    print("="*60)
    
    # Ejecutar scraping
    posts = scrape_tiktok_complete(TIKTOK_URL, MAX_VIDEOS)
    
    if posts:
        print(f"\n{'='*60}")
        print(f"📊 RESUMEN: {len(posts)} videos extraídos")
        print(f"{'='*60}")
        
        total_comments = 0
        for i, post in enumerate(posts, 1):
            num_comments = len(post.get('comentarios', []))
            total_comments += num_comments
            print(f"\n  {i}. {post['contenido'][:60]}...")
            print(f"     👁️ {post['views']:,} views | ❤️ {post['likes']:,} likes | 💬 {num_comments} comentarios extraídos")
            
            # Mostrar algunos comentarios
            for j, c in enumerate(post.get('comentarios', [])[:3], 1):
                print(f"        └─ @{c['autor']}: {c['contenido'][:50]}...")
        
        print(f"\n📊 TOTAL COMENTARIOS EXTRAÍDOS: {total_comments}")
        
        # Guardar en BD
        print(f"\n💾 Guardando en base de datos...")
        save_to_database(posts)
        
    else:
        print("❌ No se pudieron extraer posts")
