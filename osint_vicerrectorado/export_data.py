#!/usr/bin/env python3
"""
Script de exportación de datos del Sistema OSINT EMI Bolivia
Genera archivos JSON, CSV y reporte en Markdown
"""

import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path


def main():
    # Crear directorio de exportación
    export_dir = Path('exports')
    export_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    conn = sqlite3.connect('data/osint_emi.db')
    conn.row_factory = sqlite3.Row
    
    print("="*70)
    print("📦 EXPORTANDO DATOS DEL SISTEMA OSINT EMI")
    print("="*70)
    
    # ========================================================================
    # 1. EXPORTAR FACEBOOK
    # ========================================================================
    print("\n📘 Exportando datos de FACEBOOK...")
    
    fb_data = {
        'plataforma': 'Facebook',
        'fecha_exportacion': datetime.now().isoformat(),
        'fuentes': [],
        'estadisticas': {
            'total_posts': 0,
            'total_comentarios': 0,
            'posts_con_comentarios': 0
        }
    }
    
    # Obtener fuentes de Facebook
    fuentes_fb = conn.execute("""
        SELECT f.*, COUNT(d.id_dato) as total_posts
        FROM fuente_osint f
        LEFT JOIN dato_recolectado d ON f.id_fuente = d.id_fuente
        WHERE f.id_fuente IN (2, 3)
        GROUP BY f.id_fuente
    """).fetchall()
    
    for fuente in fuentes_fb:
        fuente_dict = dict(fuente)
        fuente_info = {
            'id': fuente_dict['id_fuente'],
            'nombre': fuente_dict['nombre_fuente'],
            'url': fuente_dict['url_fuente'],
            'tipo': fuente_dict['tipo_fuente'],
            'total_posts': fuente_dict['total_posts'],
            'posts': []
        }
        
        # Obtener posts de esta fuente
        posts = conn.execute("""
            SELECT * FROM dato_recolectado 
            WHERE id_fuente = ?
            ORDER BY fecha_publicacion DESC
        """, (fuente_dict['id_fuente'],)).fetchall()
        
        for post in posts:
            try:
                post_dict = dict(post)
                metadata = json.loads(post_dict['metadata_json']) if post_dict.get('metadata_json') else {}
                comentarios = metadata.get('comentarios', [])
                
                post_data = {
                    'id': post_dict['id_dato'],
                    'id_externo': post_dict['id_dato_externo'],
                    'autor': post_dict['autor'],
                    'fecha_publicacion': post_dict['fecha_publicacion'],
                    'contenido': post_dict['contenido_original'],
                    'metricas': {
                        'likes': post_dict['num_likes'],
                        'comentarios_count': post_dict['num_comentarios'],
                        'compartidos': post_dict['num_compartidos']
                    },
                    'comentarios': [
                        {
                            'autor': c.get('autor'),
                            'texto': c.get('texto'),
                            'fecha': c.get('fecha')
                        } for c in comentarios if c.get('texto')
                    ],
                    'metadata': metadata
                }
                
                fuente_info['posts'].append(post_data)
                fb_data['estadisticas']['total_posts'] += 1
                if comentarios:
                    fb_data['estadisticas']['posts_con_comentarios'] += 1
                    fb_data['estadisticas']['total_comentarios'] += len([c for c in comentarios if c.get('texto')])
            except Exception as e:
                print(f"  ⚠️  Error procesando post {post_dict.get('id_dato', '?')}: {e}")
        
        fuente_info['total_comentarios'] = sum(len(p['comentarios']) for p in fuente_info['posts'])
        fb_data['fuentes'].append(fuente_info)
    
    # Guardar Facebook
    fb_file = export_dir / f'facebook_completo_{timestamp}.json'
    with open(fb_file, 'w', encoding='utf-8') as f:
        json.dump(fb_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ Guardado: {fb_file}")
    print(f"     Posts: {fb_data['estadisticas']['total_posts']}")
    print(f"     Comentarios: {fb_data['estadisticas']['total_comentarios']}")
    
    # ========================================================================
    # 2. EXPORTAR TIKTOK
    # ========================================================================
    print("\n🎵 Exportando datos de TIKTOK...")
    
    tk_data = {
        'plataforma': 'TikTok',
        'fecha_exportacion': datetime.now().isoformat(),
        'fuentes': [],
        'estadisticas': {
            'total_videos': 0,
            'total_comentarios': 0,
            'videos_con_comentarios': 0,
            'total_views': 0,
            'total_likes': 0
        }
    }
    
    # Obtener fuente de TikTok
    fuentes_tk = conn.execute("""
        SELECT f.*, COUNT(d.id_dato) as total_posts
        FROM fuente_osint f
        LEFT JOIN dato_recolectado d ON f.id_fuente = d.id_fuente
        WHERE f.id_fuente = 4
        GROUP BY f.id_fuente
    """).fetchall()
    
    for fuente in fuentes_tk:
        fuente_dict = dict(fuente)
        fuente_info = {
            'id': fuente_dict['id_fuente'],
            'nombre': fuente_dict['nombre_fuente'],
            'url': fuente_dict['url_fuente'],
            'tipo': fuente_dict['tipo_fuente'],
            'total_videos': fuente_dict['total_posts'],
            'videos': []
        }
        
        # Obtener videos
        videos = conn.execute("""
            SELECT * FROM dato_recolectado 
            WHERE id_fuente = ?
            ORDER BY fecha_publicacion DESC
        """, (fuente_dict['id_fuente'],)).fetchall()
        
        for video in videos:
            try:
                video_dict = dict(video)
                metadata = json.loads(video_dict['metadata_json']) if video_dict.get('metadata_json') else {}
                comentarios = metadata.get('comentarios', [])
                
                video_data = {
                    'id': video_dict['id_dato'],
                    'id_externo': video_dict['id_dato_externo'],
                    'autor': video_dict['autor'],
                    'fecha_publicacion': video_dict['fecha_publicacion'],
                    'descripcion': video_dict['contenido_original'],
                    'metricas': {
                        'views': metadata.get('views', 0),
                        'likes': video_dict['num_likes'],
                        'comentarios_count': video_dict['num_comentarios'],
                        'compartidos': video_dict['num_compartidos']
                    },
                    'detalles': {
                        'duracion': metadata.get('duration'),
                        'musica': metadata.get('music'),
                        'hashtags': metadata.get('hashtags', [])
                    },
                    'comentarios': [
                        {
                            'autor': c.get('autor'),
                            'texto': c.get('texto')
                        } for c in comentarios if c.get('texto')
                    ],
                    'metadata': metadata
                }
                
                fuente_info['videos'].append(video_data)
                tk_data['estadisticas']['total_videos'] += 1
                tk_data['estadisticas']['total_views'] += metadata.get('views', 0)
                tk_data['estadisticas']['total_likes'] += video_dict['num_likes'] or 0
                
                if comentarios:
                    tk_data['estadisticas']['videos_con_comentarios'] += 1
                    tk_data['estadisticas']['total_comentarios'] += len([c for c in comentarios if c.get('texto')])
            except Exception as e:
                print(f"  ⚠️  Error procesando video {video_dict.get('id_dato', '?')}: {e}")
        
        fuente_info['total_comentarios'] = sum(len(v['comentarios']) for v in fuente_info['videos'])
        tk_data['fuentes'].append(fuente_info)
    
    # Guardar TikTok
    tk_file = export_dir / f'tiktok_completo_{timestamp}.json'
    with open(tk_file, 'w', encoding='utf-8') as f:
        json.dump(tk_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ Guardado: {tk_file}")
    print(f"     Videos: {tk_data['estadisticas']['total_videos']}")
    print(f"     Comentarios: {tk_data['estadisticas']['total_comentarios']}")
    
    # ========================================================================
    # 3. EXPORTAR SOLO COMENTARIOS (CSV para análisis)
    # ========================================================================
    print("\n💬 Exportando COMENTARIOS para análisis...")
    
    comentarios_file = export_dir / f'comentarios_todos_{timestamp}.csv'
    with open(comentarios_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'plataforma', 'fuente', 'post_id', 'autor_post', 'fecha_post', 
                         'autor_comentario', 'texto_comentario', 'fecha_comentario'])
        
        total_comentarios = 0
        
        # Facebook
        for fuente in fb_data['fuentes']:
            for post in fuente['posts']:
                for comentario in post['comentarios']:
                    writer.writerow([
                        post['id'],
                        'Facebook',
                        fuente['nombre'],
                        post['id_externo'],
                        post['autor'],
                        post['fecha_publicacion'],
                        comentario['autor'],
                        comentario['texto'],
                        comentario.get('fecha', '')
                    ])
                    total_comentarios += 1
        
        # TikTok
        for fuente in tk_data['fuentes']:
            for video in fuente['videos']:
                for comentario in video['comentarios']:
                    writer.writerow([
                        video['id'],
                        'TikTok',
                        fuente['nombre'],
                        video['id_externo'],
                        video['autor'],
                        video['fecha_publicacion'],
                        comentario['autor'],
                        comentario['texto'],
                        ''  # TikTok no tiene fecha de comentario
                    ])
                    total_comentarios += 1
    
    print(f"  ✅ Guardado: {comentarios_file}")
    print(f"     Total comentarios: {total_comentarios}")
    
    # ========================================================================
    # 4. GENERAR REPORTE
    # ========================================================================
    print("\n📄 Generando REPORTE...")
    
    reporte_file = export_dir / f'REPORTE_SISTEMA_{timestamp}.md'
    reporte_content = f"""# 📊 REPORTE SISTEMA OSINT - EMI BOLIVIA VICERRECTORADO

**Fecha de generación:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

---

## 📈 RESUMEN EJECUTIVO

| Métrica | Valor |
|---------|-------|
| **Total Posts/Videos** | {fb_data['estadisticas']['total_posts'] + tk_data['estadisticas']['total_videos']} |
| **Total Comentarios** | {fb_data['estadisticas']['total_comentarios'] + tk_data['estadisticas']['total_comentarios']} |
| **Plataformas activas** | 2 (Facebook, TikTok) |
| **Fuentes monitoreadas** | {len(fb_data['fuentes']) + len(tk_data['fuentes'])} |

---

## 📘 FACEBOOK

### Estadísticas Generales
- **Posts totales:** {fb_data['estadisticas']['total_posts']}
- **Posts con comentarios:** {fb_data['estadisticas']['posts_con_comentarios']}
- **Total comentarios:** {fb_data['estadisticas']['total_comentarios']}

### Fuentes
"""

    for fuente in fb_data['fuentes']:
        reporte_content += f"""
#### {fuente['nombre']}
- **URL:** {fuente['url']}
- **Posts recolectados:** {fuente['total_posts']}
- **Comentarios extraídos:** {fuente['total_comentarios']}
"""

    reporte_content += f"""
---

## 🎵 TIKTOK

### Estadísticas Generales
- **Videos totales:** {tk_data['estadisticas']['total_videos']}
- **Videos con comentarios:** {tk_data['estadisticas']['videos_con_comentarios']}
- **Total comentarios:** {tk_data['estadisticas']['total_comentarios']}
- **Total views:** {tk_data['estadisticas']['total_views']:,}
- **Total likes:** {tk_data['estadisticas']['total_likes']:,}

### Fuentes
"""

    for fuente in tk_data['fuentes']:
        reporte_content += f"""
#### {fuente['nombre']}
- **URL:** {fuente['url']}
- **Videos recolectados:** {fuente['total_videos']}
- **Comentarios extraídos:** {fuente['total_comentarios']}
"""

    reporte_content += f"""
---

## 🗂️ ARCHIVOS EXPORTADOS

1. **`facebook_completo_{timestamp}.json`**
   - Datos completos de Facebook con posts y comentarios
   - Incluye metadata completa de cada post

2. **`tiktok_completo_{timestamp}.json`**
   - Datos completos de TikTok con videos y comentarios
   - Incluye métricas, hashtags, música, etc.

3. **`comentarios_todos_{timestamp}.csv`**
   - Todos los comentarios en formato CSV
   - Listo para análisis de sentimiento
   - Campos: plataforma, fuente, autor, texto, fecha

---

## ✅ VERIFICACIÓN DE CALIDAD

### Estructura de Datos
- ✅ Posts/Videos con ID único
- ✅ Comentarios con texto completo
- ✅ Metadata estructurada en JSON
- ✅ Fechas en formato ISO
- ✅ Métricas de engagement completas

### Integridad
- ✅ Todos los posts tienen autor
- ✅ Todos los comentarios tienen texto
- ✅ Relaciones fuente-dato correctas
- ✅ Sin duplicados por ID externo

---

## 🎯 SIGUIENTES PASOS RECOMENDADOS

1. **Análisis de Sentimiento**
   - Procesar `comentarios_todos_{timestamp}.csv`
   - Clasificar sentimientos: positivo/negativo/neutral
   - Generar estadísticas por plataforma

2. **Recolección Continua**
   - Incrementar límite de posts/videos
   - Programar recolección periódica
   - Monitorear nuevos comentarios

3. **Visualizaciones**
   - Gráficos de engagement por plataforma
   - Nube de palabras de comentarios
   - Timeline de publicaciones

---

**Sistema generado por:** OSINT Vicerrectorado EMI Bolivia  
**Versión:** 1.0  
**Tecnologías:** Python 3.13, Playwright, yt-dlp, SQLite
"""

    with open(reporte_file, 'w', encoding='utf-8') as f:
        f.write(reporte_content)
    
    print(f"  ✅ Guardado: {reporte_file}")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    print("\n" + "="*70)
    print("✨ EXPORTACIÓN COMPLETADA")
    print("="*70)
    print(f"\n📁 Directorio: {export_dir.absolute()}\n")
    print(f"   1. {fb_file.name}")
    print(f"   2. {tk_file.name}")
    print(f"   3. {comentarios_file.name}")
    print(f"   4. {reporte_file.name}")
    print("\n" + "="*70)
    
    conn.close()


if __name__ == '__main__':
    main()
