#!/usr/bin/env python3
"""
Script para migrar comentarios del metadata_json a la tabla comentario.
Ejecutar una vez para poblar la tabla de comentarios.
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'osint_emi.db')

def migrate_comments():
    """Migra comentarios de metadata_json a la tabla comentario"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔄 Migrando comentarios de metadata_json a tabla comentario...")
    
    # Obtener todos los posts con metadata
    cursor.execute('''
        SELECT id_dato, id_fuente, metadata_json 
        FROM dato_recolectado 
        WHERE metadata_json IS NOT NULL
    ''')
    
    total_comentarios = 0
    posts_con_comentarios = 0
    
    for row in cursor.fetchall():
        post_id = row['id_dato']
        fuente_id = row['id_fuente']
        
        try:
            metadata = json.loads(row['metadata_json'])
        except (json.JSONDecodeError, TypeError):
            continue
        
        comentarios = metadata.get('comentarios', [])
        if not comentarios:
            continue
        
        posts_con_comentarios += 1
        
        for c in comentarios:
            try:
                # Insertar comentario
                cursor.execute('''
                    INSERT OR IGNORE INTO comentario 
                    (id_post, id_fuente, autor, contenido, fecha_publicacion, likes, procesado)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    post_id,
                    fuente_id,
                    c.get('autor', 'Anónimo'),
                    c.get('texto', ''),
                    c.get('fecha', datetime.now().isoformat()),
                    c.get('likes', 0)
                ))
                total_comentarios += 1
            except Exception as e:
                print(f"  ⚠️ Error insertando comentario: {e}")
    
    conn.commit()
    
    # Verificar cuántos comentarios hay ahora
    cursor.execute('SELECT COUNT(*) FROM comentario')
    total_en_tabla = cursor.fetchone()[0]
    
    print(f"\n✅ Migración completada:")
    print(f"   - Posts con comentarios procesados: {posts_con_comentarios}")
    print(f"   - Comentarios migrados: {total_comentarios}")
    print(f"   - Total comentarios en tabla: {total_en_tabla}")
    
    conn.close()
    return total_comentarios

if __name__ == '__main__':
    migrate_comments()
