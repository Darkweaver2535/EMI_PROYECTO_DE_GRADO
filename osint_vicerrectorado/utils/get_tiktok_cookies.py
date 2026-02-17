#!/usr/bin/env python3
"""
Utilidad para extraer cookies de TikTok desde una sesión de navegador.

Este script abre un navegador donde puedes navegar a TikTok,
resolver el CAPTCHA manualmente, y luego guarda las cookies
para usar en el scraper.

Uso:
    python utils/get_tiktok_cookies.py
"""

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright


async def get_tiktok_cookies():
    """
    Abre un navegador para que el usuario navegue a TikTok,
    resuelva CAPTCHAs, y luego extrae las cookies.
    """
    print("="*60)
    print("🎵 EXTRACTOR DE COOKIES DE TIKTOK")
    print("="*60)
    print()
    print("Este script te ayudará a obtener cookies de TikTok")
    print("para evitar CAPTCHAs durante el scraping.")
    print()
    print("INSTRUCCIONES:")
    print("1. Se abrirá un navegador con TikTok")
    print("2. Si aparece un CAPTCHA, resuélvelo manualmente")
    print("3. Navega a un video cualquiera para verificar que funciona")
    print("4. Vuelve aquí y presiona ENTER para guardar las cookies")
    print()
    
    input("Presiona ENTER para abrir el navegador...")
    
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = await browser.new_context(
        viewport={'width': 1400, 'height': 900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        locale='es-ES'
    )
    
    # Anti-detección
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    """)
    
    page = await context.new_page()
    
    print("\n📱 Navegando a TikTok...")
    await page.goto('https://www.tiktok.com/@emilapazoficial', wait_until='domcontentloaded')
    
    print("\n⏳ Navegador abierto.")
    print("   - Resuelve el CAPTCHA si aparece")
    print("   - Navega a un video para verificar que carga bien")
    print("   - Los comentarios deben ser visibles")
    print()
    input("Cuando hayas terminado, presiona ENTER para guardar cookies...")
    
    # Extraer cookies
    cookies = await context.cookies()
    
    # Filtrar cookies importantes de TikTok
    important_cookies = {}
    for cookie in cookies:
        if 'tiktok' in cookie.get('domain', ''):
            important_cookies[cookie['name']] = {
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie.get('path', '/'),
                'secure': cookie.get('secure', True),
                'httpOnly': cookie.get('httpOnly', False)
            }
    
    print(f"\n✅ {len(important_cookies)} cookies extraídas de TikTok")
    
    # Guardar configuración
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'tiktok_cookies.json')
    
    config = {
        "enabled": True,
        "cookies": important_cookies,
        "extracted_at": datetime.now().isoformat(),
        "note": "Cookies extraídas para evitar CAPTCHA en scraping de TikTok",
        "safety_settings": {
            "min_delay_seconds": 5,
            "max_delay_seconds": 10,
            "max_videos_per_session": 20,
            "max_comments_per_video": 50
        }
    }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Cookies guardadas en: {config_path}")
    
    # Mostrar cookies importantes
    print("\n🍪 Cookies guardadas:")
    for name in list(important_cookies.keys())[:10]:
        print(f"   - {name}")
    
    await browser.close()
    await playwright.stop()
    
    print("\n" + "="*60)
    print("✅ ¡Listo! Ahora el scraper de TikTok usará estas cookies")
    print("   para evitar CAPTCHAs y extraer comentarios.")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(get_tiktok_cookies())
