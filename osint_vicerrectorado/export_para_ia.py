#!/usr/bin/env python3
"""
Exportación optimizada para análisis con IA
Mantiene relación clara entre posts y comentarios
"""

import sqlite3
import json
import csv
from datetime import datetime
from pathlib import Path

def main():
    export_dir = Path('exports')
    export_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    conn = sqlite3.connect('data/osint_emi.db')
    
    print("="*70)
    print("📦 EXPORTACIÓN OPTIMIZADA PARA IA")
    print("="*70)
    
    # =========================================================================
    # 1. ESTRUCTURA JERÁRQUICA COMPLETA (JSON)
    # =========================================================================
    
    all_data = conn.execute("""
        SELECT 
            d.id_dato,
            d.id_externo,
            d.id_fuente,
            f.nombre_fuente,
            f.tipo_fuente,
            f.url_fuente,
            d.fecha_publicacion,
            d.contenido_original,
            d.autor,
            d.engagement_likes,
            d.engagement_comments,
            d.engagement_shares,
            d.engagement_views,
            d.url_publicacion,
            d.metadata_json
        FROM dato_recolectado d
        JOIN fuente_osint f ON d.id_fuente = f.id_fuente
        ORDER BY d.id_fuente, d.fecha_publicacion DESC
    """).fetchall()
    
    # Estructura optimizada para IA
    datos_ia = {
        'meta': {
            'sistema': 'OSINT Vicerrectorado EMI Bolivia',
            'fecha_exportacion': datetime.now().isoformat(),
            'version': '2.0',
            'descripcion': 'Datos estructurados para análisis con IA. Cada comentario está vinculado a su post original.',
            'estructura': {
                'posts': 'Lista de posts/videos con sus comentarios anidados',
                'comentarios_flat': 'Lista plana de comentarios con referencia al post',
                'estadisticas': 'Métricas agregadas por plataforma'
            }
        },
        'posts': [],
        'comentarios_flat': [],  # Para fácil procesamiento
        'estadisticas': {
            'facebook': {'posts': 0, 'comentarios': 0},
            'tiktok': {'videos': 0, 'comentarios': 0, 'views': 0}
        }
    }
    
    comment_id = 1  # ID único para cada comentario
    
    for row in all_data:
        try:
            metadata = json.loads(row[14]) if row[14] else {}
            comentarios_raw = metadata.get('comentarios', [])
            
            # Determinar plataforma
            plataforma = 'tiktok' if row[2] == 4 else 'facebook'
            
            # Estructura del post
            post = {
                'post_id': row[0],
                'post_id_externo': row[1],
                'plataforma': plataforma,
                'fuente': {
                    'nombre': row[3],
                    'tipo': row[4],
                    'url': row[5]
                },
                'contenido': {
                    'texto': row[7],
                    'autor': row[8],
                    'fecha_publicacion': row[6],
                    'url': row[13]
                },
                'engagement': {
                    'likes': row[9] or 0,
                    'comentarios_count': row[10] or 0,
                    'compartidos': row[11] or 0,
                    'views': row[12] or metadata.get('views', 0)
                },
                'metadata': {
                    'hashtags': metadata.get('hashtags', []),
                    'musica': metadata.get('music'),
                    'duracion': metadata.get('duration')
                },
                'comentarios': [],
                'num_comentarios_extraidos': 0
            }
            
            # Procesar comentarios
            for c in comentarios_raw:
                if c.get('texto'):
                    comentario = {
                        'comentario_id': comment_id,
                        'post_id': row[0],  # Referencia al post
                        'post_id_externo': row[1],
                        'plataforma': plataforma,
                        'autor': c.get('autor', 'Anónimo'),
                        'texto': c.get('texto', ''),
                        'fecha': c.get('fecha', ''),
                        # Contexto del post para la IA
                        'contexto_post': {
                            'autor_post': row[8],
                            'texto_post': row[7][:200] if row[7] else '',
                            'fecha_post': row[6]
                        }
                    }
                    
                    post['comentarios'].append(comentario)
                    datos_ia['comentarios_flat'].append(comentario)
                    comment_id += 1
            
            post['num_comentarios_extraidos'] = len(post['comentarios'])
            datos_ia['posts'].append(post)
            
            # Actualizar estadísticas
            if plataforma == 'facebook':
                datos_ia['estadisticas']['facebook']['posts'] += 1
                datos_ia['estadisticas']['facebook']['comentarios'] += len(post['comentarios'])
            else:
                datos_ia['estadisticas']['tiktok']['videos'] += 1
                datos_ia['estadisticas']['tiktok']['comentarios'] += len(post['comentarios'])
                datos_ia['estadisticas']['tiktok']['views'] += post['engagement']['views']
                
        except Exception as e:
            print(f"  ⚠️  Error procesando registro {row[0]}: {e}")
    
    # Guardar JSON estructurado
    json_file = export_dir / f'datos_para_ia_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(datos_ia, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON estructurado: {json_file.name}")
    
    # =========================================================================
    # 2. CSV OPTIMIZADO CON CONTEXTO (para análisis tabular)
    # =========================================================================
    
    csv_file = export_dir / f'comentarios_con_contexto_{timestamp}.csv'
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        fieldnames = [
            'comentario_id',
            'post_id',
            'post_id_externo',
            'plataforma',
            'fuente',
            # Contexto del post
            'post_autor',
            'post_texto',
            'post_fecha',
            'post_likes',
            'post_views',
            # Datos del comentario
            'comentario_autor',
            'comentario_texto',
            'comentario_fecha',
            # Campo para IA (texto limpio)
            'texto_para_analisis'
        ]
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for c in datos_ia['comentarios_flat']:
            # Limpiar texto para análisis
            texto_limpio = c['texto'].replace('\n', ' ').strip()
            
            writer.writerow({
                'comentario_id': c['comentario_id'],
                'post_id': c['post_id'],
                'post_id_externo': c['post_id_externo'],
                'plataforma': c['plataforma'],
                'fuente': next((p['fuente']['nombre'] for p in datos_ia['posts'] if p['post_id'] == c['post_id']), ''),
                'post_autor': c['contexto_post']['autor_post'],
                'post_texto': c['contexto_post']['texto_post'][:100],
                'post_fecha': c['contexto_post']['fecha_post'],
                'post_likes': next((p['engagement']['likes'] for p in datos_ia['posts'] if p['post_id'] == c['post_id']), 0),
                'post_views': next((p['engagement']['views'] for p in datos_ia['posts'] if p['post_id'] == c['post_id']), 0),
                'comentario_autor': c['autor'],
                'comentario_texto': c['texto'],
                'comentario_fecha': c['fecha'],
                'texto_para_analisis': texto_limpio
            })
    
    print(f"✅ CSV con contexto: {csv_file.name}")
    
    # =========================================================================
    # 3. FORMATO PARA FINE-TUNING / PROMPTS (JSONL)
    # =========================================================================
    
    jsonl_file = export_dir / f'datos_prompt_ia_{timestamp}.jsonl'
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for post in datos_ia['posts']:
            if post['comentarios']:
                # Formato para cada post con sus comentarios
                prompt_data = {
                    'id': post['post_id'],
                    'plataforma': post['plataforma'],
                    'post': {
                        'autor': post['contenido']['autor'],
                        'texto': post['contenido']['texto'],
                        'fecha': post['contenido']['fecha_publicacion'],
                        'engagement': post['engagement']
                    },
                    'comentarios': [
                        {
                            'id': c['comentario_id'],
                            'autor': c['autor'],
                            'texto': c['texto']
                        } for c in post['comentarios']
                    ],
                    'num_comentarios': len(post['comentarios'])
                }
                f.write(json.dumps(prompt_data, ensure_ascii=False) + '\n')
    
    print(f"✅ JSONL para prompts: {jsonl_file.name}")
    
    # =========================================================================
    # 4. RESUMEN
    # =========================================================================
    
    total_posts = len(datos_ia['posts'])
    posts_con_comentarios = len([p for p in datos_ia['posts'] if p['comentarios']])
    total_comentarios = len(datos_ia['comentarios_flat'])
    
    print("\n" + "="*70)
    print("📊 RESUMEN DE EXPORTACIÓN PARA IA")
    print("="*70)
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║  RELACIÓN POST → COMENTARIOS                                       ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  Posts/Videos totales:        {total_posts:>3}                                     ║
║  Posts con comentarios:       {posts_con_comentarios:>3}                                     ║
║  Total comentarios:           {total_comentarios:>3}                                     ║
║                                                                     ║
╠════════════════════════════════════════════════════════════════════╣
║  ARCHIVOS GENERADOS                                                 ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  1. {json_file.name:<50}     ║
║     → Estructura jerárquica completa (posts → comentarios)          ║
║     → Ideal para GPT/Claude con contexto completo                   ║
║                                                                     ║
║  2. {csv_file.name:<50}     ║
║     → Cada comentario con contexto del post                         ║
║     → Ideal para Pandas, análisis tabular, ML                       ║
║                                                                     ║
║  3. {jsonl_file.name:<50}     ║
║     → Formato JSONL para fine-tuning / batch processing             ║
║     → Un post por línea con todos sus comentarios                   ║
║                                                                     ║
╚════════════════════════════════════════════════════════════════════╝
""")

    # Mostrar ejemplo de estructura
    print("📝 EJEMPLO DE ESTRUCTURA:")
    print("-"*70)
    
    if datos_ia['comentarios_flat']:
        c = datos_ia['comentarios_flat'][0]
        print(json.dumps({
            'comentario_id': c['comentario_id'],
            'post_id': c['post_id'],
            'plataforma': c['plataforma'],
            'autor': c['autor'],
            'texto': c['texto'][:50] + '...',
            'contexto_post': {
                'autor_post': c['contexto_post']['autor_post'],
                'texto_post': c['contexto_post']['texto_post'][:50] + '...'
            }
        }, ensure_ascii=False, indent=2))
    
    print("\n" + "="*70)
    conn.close()


if __name__ == '__main__':
    main()
