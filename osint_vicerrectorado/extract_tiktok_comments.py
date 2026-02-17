#!/usr/bin/env python3
"""
Extrae comentarios de videos TikTok ya guardados en la BD.
Usa el scraper robusto con anti-detección y cookies de sesión.
"""

import asyncio
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Importar el scraper robusto
from tiktok_scraper_robust import TikTokRobustScraper, COOKIES_FILE

DB_PATH = Path(__file__).parent / 'data' / 'osint_emi.db'


async def extract_comments_for_saved_videos(source_id: int = 5, cookies: str = None):
    """
    Extrae comentarios de videos TikTok ya guardados en la BD.
    """
    # Obtener videos de la BD
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id_dato, url_publicacion, engagement_comments,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_post = d.id_dato) as extracted
        FROM dato_recolectado d
        WHERE id_fuente = ?
        ORDER BY id_dato
    ''', (source_id,))
    
    videos = cursor.fetchall()
    conn.close()
    
    if not videos:
        print("❌ No hay videos de TikTok en la BD")
        return
    
    print(f"\n{'='*70}")
    print(f"  💬 EXTRACCIÓN DE COMENTARIOS DE TIKTOK")
    print(f"  📹 Videos en BD: {len(videos)}")
    print(f"  🍪 Cookies: {'✅ Configuradas' if COOKIES_FILE.exists() else '❌ No configuradas'}")
    print(f"{'='*70}\n")
    
    # Mostrar estado actual
    print("📊 Estado actual de videos:")
    for v in videos:
        status = "✅" if v['extracted'] > 0 else "❌"
        print(f"   {status} Video {v['id_dato']}: {v['extracted']}/{v['engagement_comments']} comentarios extraídos")
    
    # Filtrar videos que necesitan comentarios
    videos_to_process = [v for v in videos if v['extracted'] < v['engagement_comments']]
    
    if not videos_to_process:
        print("\n✅ Todos los videos ya tienen sus comentarios extraídos!")
        return
    
    print(f"\n📋 Procesando {len(videos_to_process)} videos que faltan comentarios...\n")
    
    # Iniciar scraper
    scraper = TikTokRobustScraper(cookies=cookies, headless=False)
    await scraper._setup_browser()
    
    # Inicializar sesión visitando homepage primero
    await scraper._initialize_session()
    
    total_comments = 0
    
    for i, video in enumerate(videos_to_process):
        print(f"\n{'─'*50}")
        print(f"  [{i+1}/{len(videos_to_process)}] Video ID: {video['id_dato']}")
        print(f"  🔗 {video['url_publicacion'][:60]}...")
        print(f"  📊 Faltan: {video['engagement_comments'] - video['extracted']} comentarios")
        
        # Extraer comentarios
        comments = await scraper.extract_comments_from_video(
            video['url_publicacion'],
            max_comments=50
        )
        
        if comments:
            # Guardar en BD
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
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    video['id_dato'],
                    source_id,
                    c['autor'],
                    c['contenido'],
                    c['fecha'],
                    c['likes']
                ))
                saved += 1
            
            conn.commit()
            conn.close()
            
            total_comments += saved
            print(f"  💾 Guardados {saved} nuevos comentarios")
        
        # Delay entre videos
        if i < len(videos_to_process) - 1:
            import random
            delay = random.uniform(8, 15)
            print(f"\n  ⏱️  Esperando {delay:.1f}s antes del siguiente video...")
            await asyncio.sleep(delay)
    
    # Limpiar
    await scraper._cleanup()
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"  🎉 EXTRACCIÓN COMPLETADA")
    print(f"  💬 Total comentarios nuevos: {total_comments}")
    print(f"{'='*70}\n")
    
    # Mostrar estado final
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id_dato, engagement_comments,
               (SELECT COUNT(*) FROM comentario c WHERE c.id_post = d.id_dato) as extracted
        FROM dato_recolectado d
        WHERE id_fuente = ?
    ''', (source_id,))
    
    print("📊 Estado final:")
    for v in cursor.fetchall():
        pct = (v['extracted'] / v['engagement_comments'] * 100) if v['engagement_comments'] > 0 else 0
        status = "✅" if pct >= 80 else "⚠️" if pct > 0 else "❌"
        print(f"   {status} Video {v['id_dato']}: {v['extracted']}/{v['engagement_comments']} ({pct:.0f}%)")
    
    conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extraer comentarios de videos TikTok guardados')
    parser.add_argument('--source-id', '-s', type=int, default=5,
                       help='ID de la fuente TikTok')
    parser.add_argument('--cookies', '-c', type=str, default=None,
                       help='String de cookies de sesión')
    
    args = parser.parse_args()
    
    asyncio.run(extract_comments_for_saved_videos(
        source_id=args.source_id,
        cookies=args.cookies
    ))


if __name__ == '__main__':
    main()
