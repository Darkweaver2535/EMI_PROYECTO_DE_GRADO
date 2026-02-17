#!/usr/bin/env python3
"""
🎵 EXTRACTOR INTERACTIVO DE COMENTARIOS TIKTOK
===============================================
Este script abre un navegador donde puedes:
1. Iniciar sesión en TikTok (si es necesario)
2. Resolver CAPTCHA manualmente UNA VEZ
3. Luego el script extrae automáticamente todos los comentarios

Uso:
    python tiktok_interactive_extractor.py
"""

import asyncio
import sqlite3
import json
import random
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Configuración
DB_PATH = Path(__file__).parent / 'data' / 'osint_emi.db'
COOKIES_FILE = Path(__file__).parent / 'data' / 'tiktok_cookies.json'
BROWSER_PROFILE = Path(__file__).parent / 'data' / 'tiktok_browser_profile'

# Delays
DELAYS = {
    'between_videos': (5, 10),
    'between_scroll': (0.8, 1.5),
    'after_page_load': (3, 5),
}


async def extract_comments_interactive():
    """Extracción interactiva de comentarios."""
    
    print(f"\n{'='*70}")
    print(f"  🎵 EXTRACTOR INTERACTIVO DE COMENTARIOS TIKTOK")
    print(f"  📁 Perfil del navegador: {BROWSER_PROFILE}")
    print(f"  🍪 Cookies: {'✅' if COOKIES_FILE.exists() else '❌'}")
    print(f"{'='*70}\n")
    
    # Obtener videos de la BD
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id_dato, url_publicacion, contenido_original, engagement_comments,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_post = d.id_dato) as extracted
        FROM dato_recolectado d
        WHERE id_fuente = 5
        ORDER BY id_dato
    ''')
    
    videos = cursor.fetchall()
    conn.close()
    
    if not videos:
        print("❌ No hay videos de TikTok en la BD")
        return
    
    # Mostrar estado
    print("📊 Videos en la base de datos:")
    for v in videos:
        status = "✅" if v['extracted'] >= v['engagement_comments'] else "⚠️" if v['extracted'] > 0 else "❌"
        desc = (v['contenido_original'] or '')[:40]
        print(f"   {status} [{v['id_dato']}] {desc}... ({v['extracted']}/{v['engagement_comments']})")
    
    # Filtrar videos que necesitan comentarios
    videos_to_process = [v for v in videos if v['extracted'] < v['engagement_comments']]
    
    if not videos_to_process:
        print("\n✅ Todos los videos ya tienen sus comentarios!")
        return
    
    print(f"\n📋 {len(videos_to_process)} videos necesitan extracción de comentarios")
    
    # Iniciar navegador con perfil persistente
    print("\n🌐 Iniciando navegador...")
    print("   ⚠️  Si aparece CAPTCHA, resuélvelo manualmente")
    print("   ⚠️  Si no estás logueado, inicia sesión")
    print("   ✅ Luego presiona ENTER para continuar\n")
    
    async with async_playwright() as p:
        # Crear directorio para perfil
        BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)
        
        # Lanzar navegador con perfil persistente
        context = await p.chromium.launch_persistent_context(
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
        
        page = await context.new_page()
        
        # Cargar cookies si existen
        if COOKIES_FILE.exists():
            try:
                with open(COOKIES_FILE, 'r') as f:
                    raw_cookies = json.load(f)
                
                playwright_cookies = []
                for cookie in raw_cookies:
                    same_site = cookie.get('sameSite', 'Lax')
                    # Normalizar sameSite a valores válidos de Playwright
                    if same_site in ['unspecified', '', None]:
                        same_site = 'Lax'
                    elif same_site == 'no_restriction':
                        same_site = 'None'
                    elif same_site == 'lax':
                        same_site = 'Lax'
                    elif same_site == 'strict':
                        same_site = 'Strict'
                    elif same_site not in ['Strict', 'Lax', 'None']:
                        same_site = 'Lax'  # Default seguro
                    
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
                
                await context.add_cookies(playwright_cookies)
                print(f"   🍪 Cargadas {len(playwright_cookies)} cookies")
            except Exception as e:
                print(f"   ⚠️ Error cargando cookies: {e}")
        
        # Ir a TikTok homepage
        print("\n📍 Navegando a TikTok...")
        await page.goto('https://www.tiktok.com/', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Esperar input del usuario
        input("\n🔔 Presiona ENTER cuando estés listo para comenzar la extracción...")
        
        total_comments = 0
        
        # Procesar cada video
        for i, video in enumerate(videos_to_process):
            print(f"\n{'─'*60}")
            print(f"  📹 [{i+1}/{len(videos_to_process)}] Video ID: {video['id_dato']}")
            print(f"  🔗 {video['url_publicacion']}")
            print(f"  📊 Comentarios: {video['extracted']}/{video['engagement_comments']}")
            
            try:
                # Navegar al video
                await page.goto(video['url_publicacion'], wait_until='domcontentloaded')
                
                # Delay
                delay = random.uniform(*DELAYS['after_page_load'])
                print(f"  ⏱️  Esperando {delay:.1f}s...")
                await page.wait_for_timeout(int(delay * 1000))
                
                # Verificar CAPTCHA
                content = await page.content()
                if 'captcha' in content.lower() or 'verify' in content.lower():
                    print(f"  ⚠️  CAPTCHA detectado - resuélvelo manualmente")
                    input("  🔔 Presiona ENTER cuando lo hayas resuelto...")
                
                # Scroll para cargar comentarios
                print(f"  📜 Cargando comentarios...")
                for _ in range(8):
                    scroll = random.randint(300, 500)
                    await page.evaluate(f'window.scrollBy(0, {scroll})')
                    await page.wait_for_timeout(int(random.uniform(*DELAYS['between_scroll']) * 1000))
                
                # Buscar comentarios
                selectors = [
                    '[class*="DivCommentItemContainer"]',
                    '[data-e2e="comment-item"]',
                    '[class*="CommentItem"]',
                ]
                
                comment_elements = []
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            comment_elements = elements
                            print(f"  ✓ Encontrados {len(elements)} elementos con {selector}")
                            break
                    except:
                        continue
                
                if not comment_elements:
                    print(f"  ⚠️ No se encontraron comentarios")
                    continue
                
                # Extraer comentarios
                comments = []
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
                                'día', 'day', 'week', 'semana'
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
                
                print(f"  💬 Extraídos {len(comments)} comentarios")
                
                # Guardar en BD
                if comments:
                    conn = sqlite3.connect(str(DB_PATH))
                    cursor = conn.cursor()
                    
                    saved = 0
                    for c in comments:
                        # Verificar duplicado
                        cursor.execute(
                            'SELECT 1 FROM comentario WHERE id_post = ? AND contenido = ?',
                            (video['id_dato'], c['contenido'][:500])
                        )
                        if cursor.fetchone():
                            continue
                        
                        cursor.execute('''
                            INSERT INTO comentario 
                            (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                            VALUES (?, 5, ?, ?, ?, 0, 0)
                        ''', (
                            video['id_dato'],
                            c['autor'],
                            c['contenido'],
                            c['fecha']
                        ))
                        saved += 1
                    
                    conn.commit()
                    conn.close()
                    
                    total_comments += saved
                    print(f"  💾 Guardados {saved} nuevos comentarios")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            # Delay entre videos
            if i < len(videos_to_process) - 1:
                delay = random.uniform(*DELAYS['between_videos'])
                print(f"\n  ⏱️  Esperando {delay:.1f}s antes del siguiente...")
                await page.wait_for_timeout(int(delay * 1000))
        
        # Cerrar
        await context.close()
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"  🎉 EXTRACCIÓN COMPLETADA")
    print(f"  💬 Total comentarios nuevos: {total_comments}")
    print(f"{'='*70}")
    
    # Estado final
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id_dato, engagement_comments,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_post = d.id_dato) as extracted
        FROM dato_recolectado d
        WHERE id_fuente = 5
    ''')
    
    print("\n📊 Estado final:")
    for v in cursor.fetchall():
        pct = (v['extracted'] / v['engagement_comments'] * 100) if v['engagement_comments'] > 0 else 0
        status = "✅" if pct >= 80 else "⚠️" if pct > 0 else "❌"
        print(f"   {status} Video {v['id_dato']}: {v['extracted']}/{v['engagement_comments']} ({pct:.0f}%)")
    
    conn.close()


if __name__ == '__main__':
    asyncio.run(extract_comments_interactive())
