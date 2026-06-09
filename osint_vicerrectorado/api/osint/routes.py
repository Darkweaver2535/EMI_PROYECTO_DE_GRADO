"""
OSINT multi-source routes
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
from api.common.state import _osint_set_status, OSINT_EXECUTION_STATUS, OSINT_STATUS_LOCK

bp = Blueprint('osint', __name__)

# Estado del job de análisis IA de noticias
_news_ai_job = {'running': False}


@bp.route('/api/osint/fuentes-bolivia')
def osint_fuentes_bolivia():
    """Catálogo de fuentes de noticias gratuitas de Bolivia + estadísticas reales."""
    try:
        from news_sources_bolivia import listar_fuentes
        fuentes = listar_fuentes()
    except Exception:
        fuentes = []

    conn = get_db()
    cursor = conn.cursor()
    # Conteo real de noticias por fuente
    por_fuente = {}
    try:
        cursor.execute("SELECT fuente, COUNT(*) c FROM osint_noticias GROUP BY fuente")
        por_fuente = {(r['fuente'] or 'Desconocida'): r['c'] for r in cursor.fetchall()}
    except Exception:
        pass
    # Cuántas noticias ya clasificó la IA
    analizadas = 0
    total = 0
    try:
        cursor.execute("SELECT COUNT(*) c FROM osint_noticias")
        total = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) c FROM osint_noticias WHERE procesado = 1")
        analizadas = cursor.fetchone()['c']
    except Exception:
        pass
    conn.close()

    return jsonify({
        'fuentes': fuentes,
        'totalFuentes': len(fuentes),
        'noticiasPorFuente': por_fuente,
        'totalNoticias': total,
        'noticiasAnalizadasIA': analizadas,
    })


@bp.route('/api/osint/noticias/analizar', methods=['POST'])
def osint_analizar_noticias():
    """Dispara la clasificación IA (DeepSeek) de las noticias pendientes."""
    if _news_ai_job['running']:
        return jsonify({'status': 'en_progreso'}), 409

    def run_job():
        _news_ai_job['running'] = True
        try:
            from deepseek_analyzer import analizar_noticias
            analizar_noticias()
        except Exception as e:
            logging.getLogger('OSINT.API').warning(f"Error IA noticias: {e}")
        finally:
            _news_ai_job['running'] = False

    threading.Thread(target=run_job, daemon=True).start()
    return jsonify({'status': 'iniciado', 'mensaje': 'Clasificación IA de noticias iniciada.'})


# ============== OSINT MULTIFUENTE Y PATRONES ==============

@bp.route('/api/osint/ejecutar', methods=['POST'])
def ejecutar_osint_completo():
    """Ejecuta todas las técnicas OSINT: noticias, tendencias, clasificación, patrones."""
    with OSINT_STATUS_LOCK:
        if OSINT_EXECUTION_STATUS.get('running'):
            return jsonify({
                'success': False,
                'message': 'Ya existe una ejecución OSINT en curso'
            }), 409

    started_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _osint_set_status(
        running=True,
        status='running',
        progress=5,
        current_step='Inicializando proceso OSINT',
        started_at=started_at,
        finished_at=None,
        message='OSINT iniciado en segundo plano',
        steps=[{'timestamp': started_at, 'message': 'Inicio de ejecución OSINT'}],
        step_message='Inicializando motores de recolección'
    )

    def run_osint():
        try:
            _osint_set_status(progress=10, current_step='Importando módulo OSINT', step_message='Preparando componentes')
            from osint_multifuente import OSINTMultifuente

            osint = OSINTMultifuente()
            resultados = {'tecnicas_ejecutadas': 0, 'resultados': {}}

            # 1. NEWSINT
            _osint_set_status(progress=15, current_step='📰 NEWSINT: Recolectando noticias de Google News', step_message='Buscando noticias sobre EMI en medios bolivianos...')
            try:
                resultados['resultados']['newsint'] = osint.recolectar_noticias()
                resultados['tecnicas_ejecutadas'] += 1
            except Exception as e:
                print(f"Error NEWSINT: {e}")

            # 2. SEINT
            _osint_set_status(progress=35, current_step='🔍 SEINT: Search Engine Intelligence', step_message='Buscando menciones de EMI en motores de búsqueda...')
            try:
                resultados['resultados']['seint'] = osint.recolectar_busquedas()
                resultados['tecnicas_ejecutadas'] += 1
            except Exception as e:
                print(f"Error SEINT: {e}")

            # 3. TRENDINT
            _osint_set_status(progress=55, current_step='📊 TRENDINT: Analizando tendencias de búsqueda', step_message='Analizando tendencias de actividad...')
            try:
                resultados['resultados']['trendint'] = osint.recolectar_tendencias()
                resultados['tecnicas_ejecutadas'] += 1
            except Exception as e:
                print(f"Error TRENDINT: {e}")
                
            # 3.5 SENTIMIENTOS
            _osint_set_status(progress=65, current_step='🎭 Analizando Sentimientos', step_message='Clasificando sentimientos (BETO/Lexicón)...')
            try:
                import sentiment_analyzer
                resultados['resultados']['sentimientos'] = sentiment_analyzer.ejecutar_analisis_completo()
                # No sumamos técnica ejecutada porque es interna
            except Exception as e:
                print(f"Error Sentimientos: {e}")

            # 4. Clasificación temática
            _osint_set_status(progress=70, current_step='🏷️ Clasificando contenido por temas', step_message='Analizando posts, comentarios y noticias...')
            try:
                resultados['resultados']['clasificacion'] = osint.clasificar_contenido_tematico()
                resultados['tecnicas_ejecutadas'] += 1
            except Exception as e:
                print(f"Error clasificación: {e}")

            # 5. Patrones
            _osint_set_status(progress=85, current_step='🔍 Identificando patrones', step_message='Cruzando datos de múltiples fuentes...')
            try:
                resultados['resultados']['patrones'] = osint.identificar_patrones()
                resultados['tecnicas_ejecutadas'] += 1
            except Exception as e:
                print(f"Error patrones: {e}")

            tecnicas = resultados['tecnicas_ejecutadas']
            newsint = resultados['resultados'].get('newsint', {})
            seint = resultados['resultados'].get('seint', {})
            news_new = newsint.get('noticias_nuevas', 0) + seint.get('resultados_nuevos', 0)
            
            summary_msg = f'OSINT completo: {tecnicas} técnica(s) ejecutada(s), {news_new} noticias nuevas'
            finished_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            _osint_set_status(
                running=False,
                status='success',
                progress=100,
                current_step='Ejecución completada',
                finished_at=finished_at,
                message=summary_msg,
                step_message='Proceso OSINT finalizado correctamente'
            )
            print(f"✅ {summary_msg}")
        except Exception as e:
            finished_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _osint_set_status(
                running=False,
                status='error',
                progress=100,
                current_step='Ejecución finalizada con error',
                finished_at=finished_at,
                message=f'Error OSINT: {str(e)}',
                step_message=f'Error detectado: {str(e)}'
            )
            print(f"❌ Error OSINT: {e}")
    
    thread = threading.Thread(target=run_osint, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Recolección OSINT iniciada en segundo plano'})


@bp.route('/api/osint/estado')
def osint_estado():
    """Estado de ejecución OSINT para barra de progreso en frontend."""
    with OSINT_STATUS_LOCK:
        return jsonify(dict(OSINT_EXECUTION_STATUS))


@bp.route('/api/osint/resumen')
def osint_resumen():
    """Resumen de todas las fuentes y técnicas OSINT utilizadas."""
    try:
        from osint_multifuente import get_osint_resumen
        resumen = get_osint_resumen()
        return jsonify(resumen)
    except Exception as e:
        # Fallback: construir resumen desde BD directamente
        conn = get_db()
        cursor = conn.cursor()
        
        tecnicas = []
        
        # SOCMINT
        cursor.execute('''
            SELECT tipo_fuente, COUNT(*) as fuentes,
                   (SELECT COUNT(*) FROM dato_recolectado dr WHERE dr.id_fuente = f.id_fuente) as datos
            FROM fuente_osint f WHERE activa = 1 GROUP BY tipo_fuente
        ''')
        for row in cursor.fetchall():
            tecnicas.append({
                'tipo_tecnica': 'SOCMINT',
                'nombre_fuente': f'{row["tipo_fuente"]} (Redes Sociales)',
                'descripcion': f'Web scraping de {row["tipo_fuente"]}',
                'total_datos_recolectados': row['datos'] or 0
            })
        
        # Contar datos
        cursor.execute('SELECT COUNT(*) as t FROM dato_recolectado')
        total_posts = cursor.fetchone()['t']
        cursor.execute('SELECT COUNT(*) as t FROM comentario')
        total_comments = cursor.fetchone()['t']
        
        # Noticias
        try:
            cursor.execute('SELECT COUNT(*) as t FROM osint_noticias')
            total_noticias = cursor.fetchone()['t']
            if total_noticias > 0:
                tecnicas.append({
                    'tipo_tecnica': 'NEWSINT',
                    'nombre_fuente': 'Google News RSS',
                    'descripcion': 'Monitoreo de noticias sobre EMI en medios',
                    'total_datos_recolectados': total_noticias
                })
        except:
            total_noticias = 0
        
        conn.close()
        
        return jsonify({
            'tecnicas_osint': tecnicas,
            'total_fuentes': len(tecnicas),
            'total_datos': total_posts + total_comments + total_noticias,
            'distribucion_temas': {},
            'patrones_activos': 0
        })


@bp.route('/api/osint/noticias')
def osint_noticias():
    """Retorna noticias recolectadas sobre la EMI con filtros opcionales."""
    conn = get_db()
    cursor = conn.cursor()

    fuente = (request.args.get('fuente') or '').strip().lower()
    search = (request.args.get('search') or '').strip().lower()
    fecha_desde = (request.args.get('fecha_desde') or '').strip()
    fecha_hasta = (request.args.get('fecha_hasta') or '').strip()
    sort_by = (request.args.get('sort_by') or 'fecha_recoleccion').strip().lower()

    try:
        min_relevancia = float(request.args.get('min_relevancia', 0) or 0)
    except ValueError:
        min_relevancia = 0

    try:
        limit = int(request.args.get('limit', 50) or 50)
    except ValueError:
        limit = 50

    limit = max(1, min(200, limit))

    sort_columns = {
        'fecha_publicacion': 'fecha_publicacion',
        'fecha_recoleccion': 'fecha_recoleccion',
        'relevancia': 'relevancia_score'
    }
    order_column = sort_columns.get(sort_by, 'fecha_recoleccion')
    
    try:
        where_clauses = []
        params = []

        if fuente:
            where_clauses.append('LOWER(COALESCE(fuente, "")) LIKE ?')
            params.append(f'%{fuente}%')

        if search:
            where_clauses.append('(' 
                                 'LOWER(COALESCE(titulo, "")) LIKE ? '
                                 'OR LOWER(COALESCE(resumen, "")) LIKE ?'
                                 ')')
            params.extend([f'%{search}%', f'%{search}%'])

        if fecha_desde:
            where_clauses.append('DATE(COALESCE(fecha_publicacion, fecha_recoleccion)) >= DATE(?)')
            params.append(fecha_desde)

        if fecha_hasta:
            where_clauses.append('DATE(COALESCE(fecha_publicacion, fecha_recoleccion)) <= DATE(?)')
            params.append(fecha_hasta)

        if min_relevancia > 0:
            where_clauses.append('COALESCE(relevancia_score, 0) >= ?')
            params.append(min_relevancia)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

        query = f'''
            SELECT * FROM osint_noticias
            {where_sql}
            ORDER BY {order_column} DESC
            LIMIT ?
        '''
        params.append(limit)
        cursor.execute(query, params)
        noticias = [dict(row) for row in cursor.fetchall()]
    except:
        noticias = []
    
    conn.close()
    return jsonify(noticias)


@bp.route('/api/osint/patrones')
def osint_patrones():
    """Retorna patrones identificados por el sistema."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT * FROM patron_identificado 
            WHERE estado = 'activo'
            ORDER BY relevancia_vicerrectorado DESC, fecha_ultima_deteccion DESC
        ''')
        patrones = []
        for row in cursor.fetchall():
            p = dict(row)
            if p.get('datos_soporte_json'):
                try:
                    p['datos_soporte'] = json.loads(p['datos_soporte_json'])
                except:
                    p['datos_soporte'] = None
            patrones.append(p)
    except:
        patrones = []
    
    conn.close()
    return jsonify(patrones)


@bp.route('/api/osint/temas')
def osint_temas():
    """Distribución de temas académicos identificados en el contenido."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Distribución general
        cursor.execute('''
            SELECT tema_principal, COUNT(*) as cantidad,
                   SUM(es_academico) as academicos,
                   SUM(es_relevante_uebu) as relevantes_uebu
            FROM clasificacion_tematica
            GROUP BY tema_principal
            ORDER BY cantidad DESC
        ''')
        distribucion = [dict(row) for row in cursor.fetchall()]
        
        # Temas por tipo de contenido
        cursor.execute('''
            SELECT tipo_contenido, tema_principal, COUNT(*) as cantidad
            FROM clasificacion_tematica
            GROUP BY tipo_contenido, tema_principal
            ORDER BY tipo_contenido, cantidad DESC
        ''')
        por_tipo = [dict(row) for row in cursor.fetchall()]
        
        # Contenido relevante para UEBU
        cursor.execute('''
            SELECT ct.tema_principal, ct.tipo_contenido, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN d.contenido_original
                       WHEN ct.tipo_contenido = 'comentario' THEN c.contenido
                       WHEN ct.tipo_contenido = 'noticia' THEN n.titulo
                   END as texto
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            LEFT JOIN osint_noticias n ON ct.id_contenido = n.id AND ct.tipo_contenido = 'noticia'
            WHERE ct.es_relevante_uebu = 1
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 30
        ''')
        relevante_uebu = [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        distribucion = []
        por_tipo = []
        relevante_uebu = []
    
    conn.close()
    
    return jsonify({
        'distribucion': distribucion,
        'por_tipo': por_tipo,
        'relevante_uebu': relevante_uebu,
        'total_clasificados': sum(d['cantidad'] for d in distribucion) if distribucion else 0
    })


@bp.route('/api/osint/tendencias-busqueda')
def osint_tendencias_busqueda():
    """Tendencias de búsqueda/actividad."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT termino, periodo, fecha_dato, valor_interes, tipo, metadata_json
            FROM osint_tendencias
            ORDER BY fecha_dato DESC
            LIMIT 200
        ''')
        tendencias = []
        for row in cursor.fetchall():
            t = dict(row)
            if t.get('metadata_json'):
                try:
                    t['metadata'] = json.loads(t['metadata_json'])
                except:
                    pass
            tendencias.append(t)
    except:
        tendencias = []
    
    conn.close()
    return jsonify(tendencias)


@bp.route('/api/osint/intereses-academicos')
def osint_intereses_academicos():
    """Intereses académicos identificados en la comunidad estudiantil."""
    conn = get_db()
    cursor = conn.cursor()
    
    resultado = {
        'intereses_por_tema': [],
        'intereses_por_carrera': [],
        'problemas_detectados': [],
        'elogios_detectados': [],
        'total_contenido_academico': 0
    }
    
    try:
        # Intereses generales
        cursor.execute('''
            SELECT tema_principal, COUNT(*) as menciones,
                   SUM(es_academico) as academico,
                   SUM(es_relevante_uebu) as uebu
            FROM clasificacion_tematica
            WHERE es_academico = 1
            GROUP BY tema_principal
            ORDER BY menciones DESC
        ''')
        resultado['intereses_por_tema'] = [dict(r) for r in cursor.fetchall()]
        resultado['total_contenido_academico'] = sum(r['menciones'] for r in resultado['intereses_por_tema'])
        
        # Menciones de carreras específicas
        cursor.execute('''
            SELECT ct.palabras_clave, ct.tipo_contenido, 
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto,
                   ct.fecha_clasificacion as fecha
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'carreras'
            LIMIT 20
        ''')
        resultado['intereses_por_carrera'] = [dict(r) for r in cursor.fetchall()]
        
        # Problemas/quejas detectadas
        cursor.execute('''
            SELECT ct.tema_principal, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto,
                   ct.fecha_clasificacion as fecha
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'queja'
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 15
        ''')
        resultado['problemas_detectados'] = [dict(r) for r in cursor.fetchall()]
        
        # Elogios
        cursor.execute('''
            SELECT ct.tema_principal, ct.palabras_clave,
                   CASE 
                       WHEN ct.tipo_contenido = 'post' THEN SUBSTR(d.contenido_original, 1, 200)
                       WHEN ct.tipo_contenido = 'comentario' THEN SUBSTR(c.contenido, 1, 200)
                   END as texto,
                   ct.fecha_clasificacion as fecha
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            WHERE ct.tema_principal = 'elogio'
            ORDER BY ct.fecha_clasificacion DESC
            LIMIT 15
        ''')
        resultado['elogios_detectados'] = [dict(r) for r in cursor.fetchall()]
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error en intereses académicos: {e}")
    
    conn.close()
    return jsonify(resultado)



