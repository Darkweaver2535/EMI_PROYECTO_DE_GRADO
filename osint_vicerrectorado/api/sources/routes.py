"""
Data sources CRUD and collection routes
Auto-extracted from api_real.py during modularization.
"""
import os
import json
import hashlib
import sqlite3
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Blueprint, jsonify, request

from api.common.database import get_db
from api.common.filters import EXTERNAL_POSTS_FILTER, EXTERNAL_PROCESADOS_SUBQUERY
from api.common.auth import hash_password, get_active_tokens, get_current_user

bp = Blueprint('sources', __name__)

# ============== FUENTES (SOURCES) ==============
@bp.route('/api/sources')
def get_sources():
    """Lista todas las fuentes de datos (Facebook, TikTok)"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            f.id_fuente,
            f.nombre_fuente,
            f.tipo_fuente,
            f.url_fuente,
            f.activa,
            f.fecha_ultima_recoleccion,
            COUNT(DISTINCT dr.id_dato) as total_posts,
            COUNT(DISTINCT c.id_comentario) as total_comentarios
        FROM fuente_osint f
        LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
        LEFT JOIN comentario c ON dr.id_dato = c.id_post
        GROUP BY f.id_fuente
        ORDER BY f.tipo_fuente, f.nombre_fuente
    ''')
    
    sources = []
    for row in cursor.fetchall():
        sources.append({
            'id': row['id_fuente'],
            'name': row['nombre_fuente'],
            'platform': row['tipo_fuente'],
            'url': row['url_fuente'],
            'active': bool(row['activa']),
            'lastCollection': row['fecha_ultima_recoleccion'],
            'postsCount': row['total_posts'],
            'commentsCount': row['total_comentarios']
        })
    
    conn.close()
    return jsonify(sources)

@bp.route('/api/sources/<int:source_id>', methods=['GET', 'PUT', 'DELETE'])
def source_detail(source_id):
    """GET: Detalle de fuente, PUT: Actualizar, DELETE: Eliminar"""
    conn = get_db()
    cursor = conn.cursor()
    
    # ===== GET: Obtener detalle =====
    if request.method == 'GET':
        cursor.execute('''
            SELECT * FROM fuente_osint WHERE id_fuente = ?
        ''', (source_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        conn.close()
        return jsonify({
            'id': row['id_fuente'],
            'name': row['nombre_fuente'],
            'platform': row['tipo_fuente'],
            'url': row['url_fuente'],
            'active': bool(row['activa']),
            'lastCollection': row['fecha_ultima_recoleccion'],
            'totalRecords': row['total_registros_recolectados']
        })
    
    # ===== PUT: Actualizar fuente =====
    elif request.method == 'PUT':
        data = request.json
        
        # Verificar que existe
        cursor.execute('SELECT * FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        # Campos actualizables
        updates = []
        params = []
        
        if 'name' in data:
            updates.append('nombre_fuente = ?')
            params.append(data['name'])
        if 'url' in data:
            updates.append('url_fuente = ?')
            params.append(data['url'])
        if 'active' in data:
            updates.append('activa = ?')
            params.append(1 if data['active'] else 0)
        
        if not updates:
            conn.close()
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        params.append(source_id)
        cursor.execute(f'''
            UPDATE fuente_osint SET {', '.join(updates)} WHERE id_fuente = ?
        ''', params)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Fuente actualizada'})
    
    # ===== DELETE: Eliminar fuente =====
    elif request.method == 'DELETE':
        # Verificar que existe
        cursor.execute('SELECT nombre_fuente FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Fuente no encontrada'}), 404
        
        source_name = row['nombre_fuente']
        
        # Eliminar en cascada
        cursor.execute('DELETE FROM comentario WHERE id_fuente = ?', (source_id,))
        cursor.execute('''
            DELETE FROM dato_procesado WHERE id_dato_original IN 
            (SELECT id_dato FROM dato_recolectado WHERE id_fuente = ?)
        ''', (source_id,))
        cursor.execute('DELETE FROM dato_recolectado WHERE id_fuente = ?', (source_id,))
        cursor.execute('DELETE FROM fuente_osint WHERE id_fuente = ?', (source_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Fuente "{source_name}" eliminada con todos sus datos'
        })

# ============== CRUD FUENTES ==============
@bp.route('/api/sources', methods=['POST'])
def create_source():
    """Crear nueva fuente de web scraping"""
    data = request.json
    
    name = data.get('name', '').strip()
    platform = data.get('platform', '').strip()
    url = data.get('url', '').strip()
    
    if not name or not platform or not url:
        return jsonify({'error': 'Nombre, plataforma y URL son requeridos'}), 400
    
    # Validar plataforma
    if platform.lower() not in ['facebook', 'tiktok']:
        return jsonify({'error': 'Plataforma debe ser Facebook o TikTok'}), 400
    
    # Extraer identificador de la URL
    identifier = ''
    if 'facebook.com' in url.lower():
        if 'profile.php?id=' in url:
            identifier = url.split('id=')[-1].split('&')[0]
        else:
            identifier = url.rstrip('/').split('/')[-1]
        platform = 'Facebook'
    elif 'tiktok.com' in url.lower():
        identifier = url.rstrip('/').split('/')[-1].replace('@', '')
        platform = 'TikTok'
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Determinar si la fuente es oficial de la EMI o externa
    es_oficial = data.get('es_oficial', 0)
    name_lower = name.lower()
    url_lower = url.lower()
    # Auto-detectar fuentes oficiales por nombre o URL
    if any(kw in name_lower for kw in ['emi oficial', 'emi ualp', 'emilapaz', 'emi la paz']):
        es_oficial = 1
    if any(kw in url_lower for kw in ['emi.ualp', 'emilapazoficial', 'emi_oficial']):
        es_oficial = 1
    
    try:
        cursor.execute('''
            INSERT INTO fuente_osint (nombre_fuente, tipo_fuente, url_fuente, identificador, activa, es_oficial)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (name, platform, url, identifier, es_oficial))
        
        source_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Fuente creada exitosamente',
            'source': {
                'id': source_id,
                'name': name,
                'platform': platform,
                'url': url,
                'identifier': identifier,
                'active': True
            }
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Ya existe una fuente con esta URL'}), 409
    finally:
        conn.close()

# ============== RECOLECCIÓN DE DATOS (Apify) ==============
# Las funciones de scraping con Playwright/yt-dlp fueron removidas.
# La recolección ahora se realiza a través de Apify (ver scrapers/facebook_collector.py
# y scrapers/tiktok_collector.py). Los endpoints de abajo mantienen la misma interfaz
# pero delegan al nuevo sistema de collectors.

def _collect_with_apify(source_id, platform, url, source_name, log_id=None):
    """
    Ejecuta recolección usando los collectors de Apify.
    Función interna usada por el endpoint /api/sources/<id>/scrape.
    
    Lógica de límites:
    - Primera recolección (0 posts existentes): extrae hasta 100 posts
    - Recolecciones posteriores: extrae hasta 50 (dedup descarta los repetidos)
    
    La deduplicación se hace via id_externo en _save_collected_data.
    """
    import json as json_lib
    
    # Load config with Apify key
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json_lib.load(f)
    except FileNotFoundError:
        config = {}
    
    # Determinar cuántos posts extraer: más la primera vez, menos las siguientes
    conn_check = get_db()
    cursor_check = conn_check.cursor()
    cursor_check.execute(
        'SELECT COUNT(*) as cnt FROM dato_recolectado WHERE id_fuente = ?', 
        (source_id,)
    )
    existing_count = cursor_check.fetchone()['cnt']
    conn_check.close()
    
    # Primera vez: 100 posts para llenar la BD
    # Subsecuentes: 50 posts (Apify devuelve los más recientes,
    # la deduplicación ignora los que ya están)
    scrape_limit = 100 if existing_count == 0 else 50
    
    print(f"[SCRAPING] {source_name}: {existing_count} posts existentes → extrayendo hasta {scrape_limit}")
    
    try:
        # Crear collector según plataforma
        if platform == 'facebook':
            from scrapers.facebook_collector import FacebookCollector
            collector = FacebookCollector(
                page_url=url,
                page_name=source_name,
                config=config
            )
        elif platform == 'tiktok':
            from scrapers.tiktok_collector import TikTokCollector
            collector = TikTokCollector(
                profile_url=url,
                account_name=source_name,
                config=config
            )
        else:
            print(f"Plataforma no soportada: {platform}")
            return
        
        # Ejecutar recolección (síncrona — Apify maneja todo en la nube)
        posts = collector.collect_data(limit=scrape_limit)
        
        if posts:
            _save_collected_data(source_id, posts, platform, log_id)
        else:
            print(f"[INFO] No se obtuvieron datos de {source_name}.")

            # Abrir conexión propia para este camino (antes usaba cursor sin definir)
            conn = get_db()
            cursor = conn.cursor()
            if log_id:
                cursor.execute('''
                    UPDATE log_ejecucion 
                    SET fecha_fin = datetime('now'), estado = 'completado', 
                        detalles_json = ?
                    WHERE id_log = ?
                ''', (
                    json_lib.dumps({
                        'message': 'No se obtuvieron datos',
                        'platform': platform
                    }), log_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO log_ejecucion 
                    (tipo_operacion, fuente, fecha_inicio, fecha_fin, 
                     registros_procesados, registros_exitosos, estado, detalles_json)
                    VALUES ('scraping', ?, datetime('now'), datetime('now'), 0, 0, 'completado', ?)
                ''', (
                    source_name,
                    json_lib.dumps({
                        'message': 'No se obtuvieron datos',
                        'platform': platform
                    })
                ))
            conn.commit()
            conn.close()
            
    except Exception as e:
        print(f"Error en recolección Apify: {e}")
        import traceback
        traceback.print_exc()
        
        conn = get_db()
        cursor = conn.cursor()
        if log_id:
            cursor.execute('''
                UPDATE log_ejecucion 
                SET fecha_fin = datetime('now'), estado = 'error', mensaje_error = ?
                WHERE id_log = ?
            ''', (str(e), log_id))
        else:
            cursor.execute('''
                INSERT INTO log_ejecucion 
                (tipo_operacion, fuente, fecha_inicio, fecha_fin, estado, mensaje_error)
                VALUES ('scraping', ?, datetime('now'), datetime('now'), 'error', ?)
            ''', (source_name, str(e)))
        conn.commit()
        conn.close()


def _save_collected_data(source_id, posts, platform, log_id=None):
    """
    Guarda los datos recolectados en la BD.
    Deduplicación por id_externo: si un post ya existe, se ignora.
    """
    import json as json_lib
    
    conn = get_db()
    cursor = conn.cursor()
    
    posts_added = 0
    posts_skipped = 0
    comments_added = 0
    
    for post in posts:
        try:
            external_id = post.get('id_externo', '')
            if not external_id:
                continue
            
            # Deduplicación: verificar si ya existe por id_externo
            cursor.execute(
                'SELECT id_dato FROM dato_recolectado WHERE id_externo = ?', 
                (external_id,)
            )
            existing = cursor.fetchone()
            if existing:
                existing_post_id = existing['id_dato']
                
                # Post ya existe — pero ¿tiene comentarios?
                # Si no tiene, guardar los comentarios nuevos
                cursor.execute(
                    'SELECT COUNT(*) as cnt FROM comentario WHERE id_post = ?',
                    (existing_post_id,)
                )
                existing_comments = cursor.fetchone()['cnt']
                
                metadata = post.get('metadata_json', {})
                new_comments = metadata.get('comentarios', [])
                
                if existing_comments == 0 and new_comments:
                    # Guardar comentarios para post existente
                    for c in new_comments:
                        texto = (c.get('texto', '') or '').strip()
                        if not texto:
                            continue
                        autor = c.get('autor', 'Anónimo') or 'Anónimo'
                        fecha_c = c.get('fecha', '') or datetime.now().isoformat()
                        likes_c = c.get('likes', 0) or 0
                        
                        cursor.execute('''
                            INSERT INTO comentario 
                            (id_post, id_fuente, autor, contenido,
                             fecha_publicacion, likes, procesado)
                            VALUES (?, ?, ?, ?, ?, ?, 0)
                        ''', (
                            existing_post_id, source_id,
                            autor, texto, fecha_c, likes_c
                        ))
                        comments_added += 1
                    
                    # Actualizar engagement_comments si era 0
                    cursor.execute('''
                        UPDATE dato_recolectado 
                        SET engagement_comments = ?
                        WHERE id_dato = ? AND engagement_comments = 0
                    ''', (
                        post.get('engagement_comments', 0),
                        existing_post_id
                    ))
                
                posts_skipped += 1
                continue
            
            # Extraer fecha
            fecha = post.get('fecha_publicacion')
            if hasattr(fecha, 'isoformat'):
                fecha = fecha.isoformat()
            elif not fecha:
                fecha = datetime.now().isoformat()
            
            # Insertar post
            metadata = post.get('metadata_json', {})
            cursor.execute('''
                INSERT INTO dato_recolectado 
                (id_fuente, id_externo, fecha_publicacion, fecha_recoleccion, 
                 contenido_original, autor, engagement_likes, engagement_comments,
                 engagement_shares, engagement_views, tipo_contenido, url_publicacion,
                 metadata_json, procesado)
                VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                source_id,
                external_id,
                fecha,
                post.get('contenido_original', ''),
                post.get('autor', 'Desconocido'),
                post.get('engagement_likes', 0),
                post.get('engagement_comments', 0),
                post.get('engagement_shares', 0),
                post.get('engagement_views', 0),
                post.get('tipo_contenido', 'texto'),
                post.get('url_publicacion', ''),
                json_lib.dumps(metadata)
            ))
            
            post_db_id = cursor.lastrowid
            posts_added += 1
            
            # Guardar comentarios extraídos por Apify
            comentarios = metadata.get('comentarios', [])
            for c in comentarios:
                texto = (c.get('texto', '') or '').strip()
                if not texto:
                    continue  # Saltar comentarios vacíos
                
                autor = c.get('autor', 'Anónimo') or 'Anónimo'
                fecha_c = c.get('fecha', '') or datetime.now().isoformat()
                likes_c = c.get('likes', 0) or 0
                
                # Dedup: verificar si el mismo comentario ya existe
                cursor.execute('''
                    SELECT id_comentario FROM comentario 
                    WHERE id_post = ? AND contenido = ? AND autor = ?
                ''', (post_db_id, texto, autor))
                if cursor.fetchone():
                    continue
                
                cursor.execute('''
                    INSERT INTO comentario 
                    (id_post, id_fuente, autor, contenido, 
                     fecha_publicacion, likes, procesado)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                ''', (
                    post_db_id,
                    source_id,
                    autor,
                    texto,
                    fecha_c,
                    likes_c
                ))
                comments_added += 1
                
        except Exception as e:
            print(f"Error guardando post: {e}")
            continue
    
    total_from_apify = posts_added + posts_skipped
    
    # Actualizar fuente
    cursor.execute('''
        UPDATE fuente_osint 
        SET fecha_ultima_recoleccion = datetime('now'),
            total_registros_recolectados = total_registros_recolectados + ?
        WHERE id_fuente = ?
    ''', (posts_added, source_id))
    
    # Registrar log con info de deduplicación
    if log_id:
        cursor.execute('''
            UPDATE log_ejecucion 
            SET fecha_fin = datetime('now'),
                registros_procesados = ?,
                registros_exitosos = ?,
                estado = 'completado',
                detalles_json = ?
            WHERE id_log = ?
        ''', (
            posts_added + comments_added,
            posts_added,
            json_lib.dumps({
                'posts_nuevos': posts_added,
                'posts_duplicados_ignorados': posts_skipped,
                'posts_de_apify': total_from_apify, 
                'comments': comments_added,
                'method': 'apify'
            }), log_id
        ))
    else:
        cursor.execute('''
            INSERT INTO log_ejecucion 
            (tipo_operacion, fuente, fecha_inicio, fecha_fin, 
             registros_procesados, registros_exitosos, estado, detalles_json)
            VALUES ('scraping', ?, datetime('now'), datetime('now'), ?, ?, 'completado', ?)
        ''', (
            str(source_id),
            posts_added + comments_added,
            posts_added,
            json_lib.dumps({
                'posts_nuevos': posts_added,
                'posts_duplicados_ignorados': posts_skipped,
                'posts_de_apify': total_from_apify, 
                'comments': comments_added,
                'method': 'apify'
            })
        ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ Recolección completada: {posts_added} nuevos, {posts_skipped} duplicados ignorados, {comments_added} comentarios")
    
    # === ANALIZAR SENTIMIENTOS AUTOMÁTICAMENTE ===
    try:
        import sentiment_analyzer
        print("Iniciando análisis de sentimientos post-scraping...")
        sentiment_analyzer.ejecutar_analisis_completo()
    except Exception as e:
        print(f"Error al ejecutar análisis de sentimiento post-scraping: {e}")


@bp.route('/api/sources/<int:source_id>/scrape', methods=['POST'])
def run_scraping(source_id):
    """Ejecutar recolección de datos para una fuente (vía Apify)"""
    import threading
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM fuente_osint WHERE id_fuente = ?', (source_id,))
    source = cursor.fetchone()
    
    if not source:
        conn.close()
        return jsonify({'error': 'Fuente no encontrada'}), 404
    
    platform = source['tipo_fuente'].lower()
    url = source['url_fuente']
    source_name = source['nombre_fuente']
    
    # Registrar estado 'en_progreso' inicial
    cursor.execute('''
        INSERT INTO log_ejecucion 
        (tipo_operacion, fuente, fecha_inicio, estado)
        VALUES ('scraping', ?, datetime('now'), 'en_progreso')
    ''', (str(source_id),))
    log_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    # Ejecutar en background
    thread = threading.Thread(
        target=_collect_with_apify,
        args=(source_id, platform, url, source_name, log_id)
    )
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Recolección iniciada para {source_name} (Apify)',
        'status': 'running',
        'source_id': source_id
    })


@bp.route('/api/sources/<int:source_id>/extract-comments', methods=['POST'])
def extract_tiktok_comments(source_id):
    """
    Endpoint para extraer comentarios de TikTok.
    Con Apify, los comentarios se extraen junto con los videos.
    Este endpoint se mantiene por compatibilidad con el frontend.
    """
    return jsonify({
        'success': True,
        'message': 'Con Apify los comentarios se extraen automáticamente junto con los videos. '
                   'Use el endpoint /api/sources/<id>/scrape para recolectar todo.',
        'status': 'completed'
    })


@bp.route('/api/sources/<int:source_id>/scrape/status')
def scraping_status(source_id):
    """Ver estado del último scraping de una fuente"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get source name for matching
    cursor.execute('SELECT nombre_fuente FROM fuente_osint WHERE id_fuente = ?', (source_id,))
    source_row = cursor.fetchone()
    source_name = source_row['nombre_fuente'] if source_row else ''
    
    # Search by both source_id and source_name (different code paths log differently)
    cursor.execute('''
        SELECT * FROM log_ejecucion 
        WHERE (fuente = ? OR fuente = ?) AND tipo_operacion = 'scraping'
        ORDER BY fecha_inicio DESC LIMIT 1
    ''', (str(source_id), source_name))
    
    log = cursor.fetchone()
    conn.close()
    
    if not log:
        return jsonify({'status': 'never_run', 'message': 'Nunca se ha ejecutado scraping'})
    
    # Parse details JSON for dedup info
    details = {}
    try:
        import json as json_lib
        if log['detalles_json']:
            details = json_lib.loads(log['detalles_json'])
    except Exception:
        pass
    
    return jsonify({
        'status': log['estado'],
        'startTime': log['fecha_inicio'],
        'endTime': log['fecha_fin'],
        'recordsProcessed': log['registros_procesados'],
        'recordsSuccess': log['registros_exitosos'],
        'error': log['mensaje_error'],
        'details': details
    })

# ============== TIKTOK SCRAPING INTERACTIVO (SSE) ==============

from flask import Response, stream_with_context

@bp.route('/api/tiktok/scraping/start/<int:source_id>', methods=['POST'])
def start_tiktok_interactive_scraping(source_id):
    """
    Inicia una sesión de scraping interactivo de TikTok.
    Retorna un session_id para conectarse al stream de eventos.
    """
    try:
        from tiktok_scraping_service import start_tiktok_scraping
        
        session = start_tiktok_scraping(source_id)
        
        return jsonify({
            'success': True,
            'session_id': session.session_id,
            'message': 'Sesión de scraping iniciada'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/tiktok/scraping/events/<session_id>')
def tiktok_scraping_events(session_id):
    """
    Stream de eventos SSE para una sesión de scraping.
    El frontend se conecta aquí para recibir actualizaciones en tiempo real.
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    def generate():
        for event in session.get_events():
            yield event
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@bp.route('/api/tiktok/scraping/continue/<session_id>', methods=['POST'])
def tiktok_scraping_continue(session_id):
    """
    El usuario confirma que puede continuar (ej: resolvió CAPTCHA).
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    session.user_continue()
    return jsonify({'success': True, 'message': 'Continuando scraping'})


@bp.route('/api/tiktok/scraping/cancel/<session_id>', methods=['POST'])
def tiktok_scraping_cancel(session_id):
    """
    Cancela una sesión de scraping.
    """
    from tiktok_scraping_service import get_session, cleanup_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    session.cancel()
    cleanup_session(session_id)
    return jsonify({'success': True, 'message': 'Scraping cancelado'})


@bp.route('/api/tiktok/scraping/status/<session_id>')
def tiktok_scraping_status(session_id):
    """
    Obtiene el estado actual de una sesión de scraping.
    """
    from tiktok_scraping_service import get_session
    
    session = get_session(session_id)
    if not session:
        return jsonify({'error': 'Sesión no encontrada'}), 404
    
    return jsonify({
        'session_id': session_id,
        'running': session.running,
        'waiting_for_user': session.waiting_for_user,
        'cancelled': session.cancelled,
        'stats': session.stats
    })



