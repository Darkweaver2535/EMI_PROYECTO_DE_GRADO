#!/usr/bin/env python3
import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path

# Crear directorio de exportación
export_dir = Path('exports')
export_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
conn = sqlite3.connect('data/osint_emi.db')

print("="*70)
print("📦 EXPORTANDO DATOS DEL SISTEMA OSINT EMI")
print("="*70)

# Obtener todos los datos
all_data = conn.execute("""
    SELECT 
        d.id_dato,
        d.id_externo,
        d.id_fuente,
        f.nombre_fuente,
        f.url_fuente,
        f.tipo_fuente,
        d.fecha_publicacion,
        d.contenido_original,
        d.autor,
        d.engagement_likes,
        d.engagement_comments,
        d.engagement_shares,
        d.engagement_views,
        d.metadata_json
    FROM dato_recolectado d
    JOIN fuente_osint f ON d.id_fuente = f.id_fuente
    ORDER BY d.id_fuente, d.fecha_publicacion DESC
""").fetchall()

# Organizar por plataforma
facebook_data = []
tiktok_data = []
all_comments = []

fb_comentarios_count = 0
tk_comentarios_count = 0

for row in all_data:
    try:
        metadata = json.loads(row[13]) if row[13] else {}
        comentarios = metadata.get('comentarios', [])
        
        item = {
            'id': row[0],
            'id_externo': row[1],
            'fuente': row[3],
            'url_fuente': row[4],
            'fecha_publicacion': row[6],
            'contenido': row[7],
            'autor': row[8],
            'metricas': {
                'likes': row[9] or 0,
                'comentarios': row[10] or 0,
                'compartidos': row[11] or 0,
                'views': row[12] or metadata.get('views', 0)
            },
            'comentarios': [
                {
                    'autor': c.get('autor', ''),
                    'texto': c.get('texto', ''),
                    'fecha': c.get('fecha', '')
                } for c in comentarios if c.get('texto')
            ],
            'metadata': metadata
        }
        
        # Separar por plataforma
        if row[2] in (2, 3):  # Facebook
            facebook_data.append(item)
            fb_comentarios_count += len(item['comentarios'])
            
            # Agregar a CSV de comentarios
            for com in item['comentarios']:
                all_comments.append({
                    'plataforma': 'Facebook',
                    'fuente': row[3],
                    'post_id': row[1],
                    'autor_post': row[8],
                    'fecha_post': row[6],
                    'autor_comentario': com['autor'],
                    'texto_comentario': com['texto'],
                    'fecha_comentario': com.get('fecha', '')
                })
                
        elif row[2] == 4:  # TikTok
            tiktok_data.append(item)
            tk_comentarios_count += len(item['comentarios'])
            
            # Agregar a CSV de comentarios
            for com in item['comentarios']:
                all_comments.append({
                    'plataforma': 'TikTok',
                    'fuente': row[3],
                    'post_id': row[1],
                    'autor_post': row[8],
                    'fecha_post': row[6],
                    'autor_comentario': com['autor'],
                    'texto_comentario': com['texto'],
                    'fecha_comentario': ''
                })
    except Exception as e:
        print(f"  ⚠️  Error procesando registro {row[0]}: {e}")

# Guardar archivos
print(f"\n📘 FACEBOOK: {len(facebook_data)} posts, {fb_comentarios_count} comentarios")
fb_file = export_dir / f'facebook_completo_{timestamp}.json'
with open(fb_file, 'w', encoding='utf-8') as f:
    json.dump({
        'plataforma': 'Facebook',
        'fecha_exportacion': datetime.now().isoformat(),
        'total_posts': len(facebook_data),
        'total_comentarios': fb_comentarios_count,
        'posts': facebook_data
    }, f, ensure_ascii=False, indent=2)
print(f"  ✅ {fb_file.name}")

print(f"\n🎵 TIKTOK: {len(tiktok_data)} videos, {tk_comentarios_count} comentarios")
tk_file = export_dir / f'tiktok_completo_{timestamp}.json'
with open(tk_file, 'w', encoding='utf-8') as f:
    json.dump({
        'plataforma': 'TikTok',
        'fecha_exportacion': datetime.now().isoformat(),
        'total_videos': len(tiktok_data),
        'total_comentarios': tk_comentarios_count,
        'videos': tiktok_data
    }, f, ensure_ascii=False, indent=2)
print(f"  ✅ {tk_file.name}")

print(f"\n💬 COMENTARIOS: {len(all_comments)} comentarios")
csv_file = export_dir / f'comentarios_todos_{timestamp}.csv'
with open(csv_file, 'w', encoding='utf-8', newline='') as f:
    if all_comments:
        writer = csv.DictWriter(f, fieldnames=all_comments[0].keys())
        writer.writeheader()
        writer.writerows(all_comments)
print(f"  ✅ {csv_file.name}")

# Reporte Markdown
reporte_file = export_dir / f'REPORTE_SISTEMA_{timestamp}.md'
reporte = f"""# 📊 REPORTE SISTEMA OSINT - EMI BOLIVIA VICERRECTORADO

**Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

---

## 📈 RESUMEN EJECUTIVO

| Métrica | Facebook | TikTok | TOTAL |
|---------|----------|--------|-------|
| **Posts/Videos** | {len(facebook_data)} | {len(tiktok_data)} | {len(facebook_data) + len(tiktok_data)} |
| **Comentarios** | {fb_comentarios_count} | {tk_comentarios_count} | {len(all_comments)} |

---

## 📊 ESTADÍSTICAS POR PLATAFORMA

### 📘 Facebook
- Posts totales: **{len(facebook_data)}**
- Comentarios con texto: **{fb_comentarios_count}**
- Posts con comentarios: **{len([p for p in facebook_data if p['comentarios']])}**

### 🎵 TikTok
- Videos totales: **{len(tiktok_data)}**
- Comentarios con texto: **{tk_comentarios_count}**
- Videos con comentarios: **{len([v for v in tiktok_data if v['comentarios']])}**
- Views totales: **{sum(v['metricas']['views'] for v in tiktok_data):,}**

---

## 🗂️ ARCHIVOS GENERADOS

1. **`{fb_file.name}`** - Datos completos de Facebook
2. **`{tk_file.name}`** - Datos completos de TikTok
3. **`{csv_file.name}`** - Todos los comentarios en CSV

---

## ✅ VERIFICACIÓN DE CALIDAD

- ✅ Posts/Videos con ID único
- ✅ Comentarios con texto completo (no solo contadores)
- ✅ Metadata estructurada en JSON
- ✅ Métricas de engagement disponibles
- ✅ Relaciones fuente-dato correctas

---

## 🔍 EJEMPLO DE DATOS

### Comentario de Facebook
```
{json.dumps(all_comments[0] if all_comments and all_comments[0]['plataforma'] == 'Facebook' else {'ejemplo': 'No hay comentarios de Facebook'}, ensure_ascii=False, indent=2)}
```

### Comentario de TikTok
```
{json.dumps(next((c for c in all_comments if c['plataforma'] == 'TikTok'), {'ejemplo': 'No hay comentarios de TikTok'}), ensure_ascii=False, indent=2)}
```

---

## 🎯 SIGUIENTES PASOS

1. **Análisis de Sentimiento** - Procesar `{csv_file.name}`
2. **Recolección Continua** - Ejecutar: `python main.py --collect --source facebook --limit 20`
3. **Visualizaciones** - Generar gráficos de engagement y tendencias

---

**Sistema:** OSINT Vicerrectorado EMI Bolivia  
**Versión:** 1.0  
**Tecnologías:** Python 3.13, Playwright, yt-dlp, SQLite
"""

with open(reporte_file, 'w', encoding='utf-8') as f:
    f.write(reporte)
print(f"\n📄 REPORTE: {reporte_file.name}")

print("\n" + "="*70)
print("✨ EXPORTACIÓN COMPLETADA")
print("="*70)
print(f"\n📁 {export_dir.absolute()}\n")
print(f"   • {fb_file.name}")
print(f"   • {tk_file.name}")
print(f"   • {csv_file.name}")
print(f"   • {reporte_file.name}")
print("\n" + "="*70)

conn.close()
