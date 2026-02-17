#!/usr/bin/env python3
"""
Script para obtener cookies de Facebook de forma interactiva.
Abre un navegador donde puedes iniciar sesión y guarda las cookies automáticamente.

USO:
    python utils/get_facebook_cookies.py

IMPORTANTE: Usa una cuenta secundaria, NO tu cuenta principal.
"""

import asyncio
import json
import os
from datetime import datetime

async def get_facebook_cookies():
    """Abre un navegador para login y extrae las cookies."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           EXTRACTOR DE COOKIES DE FACEBOOK                            ║
║                                                                        ║
║  ⚠️  IMPORTANTE: Usa una cuenta SECUNDARIA, no tu cuenta principal    ║
║  ⚠️  Facebook puede detectar actividad automatizada                   ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Error: Playwright no está instalado")
        print("Ejecuta: pip install playwright && playwright install chromium")
        return
    
    print("\n[1/3] Abriendo navegador...")
    print("      Inicia sesión en Facebook cuando se abra el navegador.\n")
    
    async with async_playwright() as p:
        # Abrir navegador visible (no headless)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='es-ES'
        )
        page = await context.new_page()
        
        # Ir a Facebook
        await page.goto('https://www.facebook.com/login')
        
        print("="*60)
        print("  📱 INSTRUCCIONES:")
        print("  1. Inicia sesión en Facebook en el navegador que se abrió")
        print("  2. Espera a que cargue tu feed de noticias")
        print("  3. Vuelve aquí y presiona ENTER")
        print("="*60)
        
        input("\n  >>> Presiona ENTER cuando hayas iniciado sesión... ")
        
        print("\n[2/3] Extrayendo cookies...")
        
        # Obtener todas las cookies
        cookies = await context.cookies()
        
        # Filtrar las cookies importantes de Facebook
        fb_cookies = []
        important_cookies = ['c_user', 'xs', 'datr', 'fr', 'sb']
        
        for cookie in cookies:
            if cookie['name'] in important_cookies and 'facebook.com' in cookie['domain']:
                fb_cookies.append({
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie['domain']
                })
                print(f"    ✓ Cookie encontrada: {cookie['name']}")
        
        await browser.close()
        
        if len(fb_cookies) < 2:
            print("\n  ❌ No se encontraron suficientes cookies.")
            print("     Asegúrate de haber iniciado sesión correctamente.")
            return
        
        print(f"\n[3/3] Guardando {len(fb_cookies)} cookies...")
        
        # Cargar configuración existente
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'facebook_cookies.json')
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except:
            config = {}
        
        # Actualizar cookies
        config['cookies'] = fb_cookies
        config['enabled'] = True
        config['last_updated'] = datetime.now().isoformat()
        config['safety_settings'] = {
            'min_delay_seconds': 8,
            'max_delay_seconds': 15,
            'max_posts_per_session': 20,
            'max_comments_per_post': 10,
            'session_cooldown_minutes': 30
        }
        
        # Guardar
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\n  ✅ Cookies guardadas en: {config_path}")
        print("\n" + "="*60)
        print("  🎉 ¡LISTO! Ahora puedes ejecutar:")
        print("     python main.py --collect --source facebook")
        print("  ")
        print("  El scraper usará las cookies para extraer comentarios.")
        print("="*60 + "\n")

if __name__ == '__main__':
    asyncio.run(get_facebook_cookies())
