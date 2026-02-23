#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
  Módulo OSINT Multifuente - Sistema de Analítica EMI
  OE1: Análisis de datos provenientes de fuentes abiertas
═══════════════════════════════════════════════════════════════════

  Este módulo implementa MÚLTIPLES técnicas de OSINT más allá
  del web scraping tradicional:
  
  1. BÚSQUEDA EN NOTICIAS (Google News RSS)
     - Monitoreo de menciones de EMI en medios de comunicación
     - Extracción de titulares y resúmenes
     
  2. GOOGLE TRENDS
     - Tendencias de búsqueda relacionadas con EMI
     - Comparación de interés entre carreras
     
  3. ANÁLISIS DE METADATOS PÚBLICOS
     - Análisis de frecuencia de publicación
     - Patrones temporales de actividad
     - Métricas de engagement
     
  4. MONITOREO DE FOROS/SITIOS ACADÉMICOS
     - Búsqueda en sitios educativos bolivianos
     - Menciones en foros estudiantiles

  Referencia OSINT Framework:
  - Técnica 1: Social Media Intelligence (SOCMINT)
  - Técnica 2: Search Engine Intelligence (SEINT) 
  - Técnica 3: News Intelligence (NEWSINT)
  - Técnica 4: Trends Intelligence (TRENDINT)
  
═══════════════════════════════════════════════════════════════════
"""

import os
import json
import sqlite3
import logging
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

# HTTP
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'data' / 'osint_emi.db'


class OSINTMultifuente:
    """
    Motor de recolección OSINT multifuente para la EMI.
    
    Implementa 4 técnicas diferentes de OSINT:
    1. SOCMINT - Social Media Intelligence (Facebook, TikTok) [ya existente]
    2. NEWSINT - News Intelligence (Google News RSS)
    3. SEINT  - Search Engine Intelligence (Google Custom Search)
    4. TRENDINT - Trends Intelligence (Google Trends via pytrends)
    """
    
    # Términos de búsqueda OSINT relacionados con EMI
    SEARCH_TERMS = [
        '"Escuela Militar de Ingeniería"',
        '"EMI" Bolivia universidad',
        '"EMI La Paz" ingeniería',
        '"Vicerrectorado" EMI Bolivia',
        'EMI Bolivia carreras ingeniería',
        'EMI Bolivia opiniones estudiantes',
    ]
    
    # Carreras de la EMI para análisis de interés
    CARRERAS_EMI = [
        'Ingeniería Civil',
        'Ingeniería Comercial',
        'Ingeniería de Sistemas',
        'Ingeniería Industrial',
        'Ingeniería Ambiental',
        'Ingeniería Mecatrónica',
        'Ingeniería Petrolera',
        'Ingeniería Electromecánica',
    ]
    
    # Temas académicos de interés para el Vicerrectorado
    TEMAS_ACADEMICOS = {
        'inscripcion': ['inscripción', 'inscripciones', 'matrícula', 'admisión', 'postular', 'requisitos ingreso'],
        'becas': ['beca', 'becas', 'descuento', 'media beca', 'beca completa', 'beneficio económico'],
        'calidad_academica': ['calidad', 'nivel académico', 'excelencia', 'formación', 'enseñanza', 'docentes'],
        'infraestructura': ['infraestructura', 'laboratorio', 'aula', 'campus', 'instalaciones', 'biblioteca'],
        'empleo': ['trabajo', 'empleo', 'egresados', 'profesional', 'campo laboral', 'oportunidades'],
        'carreras': ['carrera', 'ingeniería', 'sistemas', 'civil', 'industrial', 'mecatrónica', 'comercial'],
        'queja': ['queja', 'reclamo', 'problema', 'mal servicio', 'deficiente', 'pésimo', 'horrible'],
        'elogio': ['excelente', 'buena universidad', 'recomiendo', 'orgullo', 'mejor universidad', 'prestigio'],
        'disciplina': ['disciplina', 'militar', 'formación militar', 'valores', 'orden', 'respeto'],
        'tecnologia': ['tecnología', 'innovación', 'digital', 'investigación', 'ciencia', 'proyecto'],
        'vida_estudiantil': ['compañeros', 'amigos', 'fiesta', 'deporte', 'actividades', 'evento'],
        'costo': ['costo', 'precio', 'caro', 'barato', 'económico', 'pago', 'cuota', 'pensión'],
    }
    
    def __init__(self):
        self.session = self._create_session()
        self._ensure_tables()
        
    def _create_session(self) -> requests.Session:
        """Crea sesión HTTP con retry automático."""
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/131.0.0.0 Safari/537.36'
        })
        return session
    
    def _ensure_tables(self):
        """Crea tablas adicionales para OSINT multifuente."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Tabla para noticias recolectadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS osint_noticias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                resumen TEXT,
                fuente VARCHAR(200),
                url VARCHAR(500) UNIQUE,
                fecha_publicacion TIMESTAMP,
                fecha_recoleccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                termino_busqueda VARCHAR(200),
                relevancia_score DECIMAL(5,4),
                temas_json TEXT,
                sentimiento VARCHAR(20),
                procesado BOOLEAN DEFAULT 0
            )
        ''')
        
        # Tabla para tendencias de búsqueda
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS osint_tendencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                termino VARCHAR(200) NOT NULL,
                region VARCHAR(50) DEFAULT 'Bolivia',
                periodo VARCHAR(50),
                valor_interes INTEGER,
                fecha_dato DATE,
                fecha_recoleccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tipo VARCHAR(50) DEFAULT 'google_trends',
                metadata_json TEXT
            )
        ''')
        
        # Tabla para clasificación temática de contenido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clasificacion_tematica (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_contenido INTEGER NOT NULL,
                tipo_contenido VARCHAR(50) NOT NULL,
                tema_principal VARCHAR(100) NOT NULL,
                tema_secundario VARCHAR(100),
                palabras_clave TEXT,
                confianza DECIMAL(5,4),
                es_academico BOOLEAN DEFAULT 0,
                es_relevante_uebu BOOLEAN DEFAULT 0,
                fecha_clasificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla para patrones identificados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patron_identificado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_patron VARCHAR(200) NOT NULL,
                tipo_patron VARCHAR(100) NOT NULL,
                descripcion TEXT,
                fuentes_involucradas TEXT,
                frecuencia INTEGER DEFAULT 1,
                impacto VARCHAR(20),
                fecha_primera_deteccion TIMESTAMP,
                fecha_ultima_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                datos_soporte_json TEXT,
                recomendacion_accion TEXT,
                estado VARCHAR(20) DEFAULT 'activo',
                relevancia_vicerrectorado BOOLEAN DEFAULT 0
            )
        ''')
        
        # Tabla resumen de fuentes OSINT
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS osint_fuente_resumen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_tecnica VARCHAR(50) NOT NULL,
                nombre_fuente VARCHAR(200) NOT NULL,
                descripcion TEXT,
                url_base VARCHAR(500),
                total_datos_recolectados INTEGER DEFAULT 0,
                ultima_recoleccion TIMESTAMP,
                estado VARCHAR(20) DEFAULT 'activo',
                metadata_json TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ============================================================
    # TÉCNICA 1: NEWSINT - News Intelligence (Google News RSS)
    # ============================================================
    
    def recolectar_noticias(self, max_per_term: int = 10) -> Dict[str, Any]:
        """
        Recolecta noticias sobre la EMI desde Google News RSS.
        
        Esta es una técnica OSINT legítima: monitoreo de fuentes
        públicas de noticias para inteligencia de medios.
        
        Returns:
            Dict con estadísticas de recolección
        """
        logger.info("📰 Iniciando NEWSINT: Recolección de noticias")
        
        stats = {
            'terminos_buscados': 0,
            'noticias_encontradas': 0,
            'noticias_nuevas': 0,
            'errores': 0
        }
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        for term in self.SEARCH_TERMS:
            stats['terminos_buscados'] += 1
            
            try:
                # Google News RSS URL
                encoded_term = quote_plus(term)
                rss_url = f'https://news.google.com/rss/search?q={encoded_term}&hl=es-419&gl=BO&ceid=BO:es-419'
                
                response = self.session.get(rss_url, timeout=15)
                
                if response.status_code != 200:
                    logger.warning(f"Error HTTP {response.status_code} para: {term}")
                    stats['errores'] += 1
                    continue
                
                # Parsear RSS/XML
                root = ET.fromstring(response.content)
                channel = root.find('channel')
                
                if channel is None:
                    continue
                
                items = channel.findall('item')
                
                for item in items[:max_per_term]:
                    title = item.findtext('title', '')
                    link = item.findtext('link', '')
                    description = item.findtext('description', '')
                    pub_date = item.findtext('pubDate', '')
                    source = item.findtext('source', '')
                    
                    if not title or not link:
                        continue
                    
                    # Limpiar HTML del description
                    description = re.sub(r'<[^>]+>', '', description).strip()
                    
                    stats['noticias_encontradas'] += 1
                    
                    # Verificar duplicado
                    cursor.execute('SELECT 1 FROM osint_noticias WHERE url = ?', (link,))
                    if cursor.fetchone():
                        continue
                    
                    # Clasificar temas de la noticia
                    temas = self._clasificar_temas(f"{title} {description}")
                    
                    # Calcular relevancia
                    relevancia = self._calcular_relevancia(title, description)
                    
                    cursor.execute('''
                        INSERT INTO osint_noticias 
                        (titulo, resumen, fuente, url, fecha_publicacion, 
                         termino_busqueda, relevancia_score, temas_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        title[:500],
                        description[:2000],
                        source[:200],
                        link[:500],
                        pub_date,
                        term[:200],
                        relevancia,
                        json.dumps(temas, ensure_ascii=False)
                    ))
                    stats['noticias_nuevas'] += 1
                
            except Exception as e:
                logger.error(f"Error recolectando noticias para '{term}': {e}")
                stats['errores'] += 1
        
        conn.commit()
        
        # Registrar fuente
        cursor.execute('''
            INSERT OR REPLACE INTO osint_fuente_resumen 
            (tipo_tecnica, nombre_fuente, descripcion, url_base, total_datos_recolectados, ultima_recoleccion)
            VALUES ('NEWSINT', 'Google News RSS', 
                    'Monitoreo de noticias sobre EMI en medios de comunicación',
                    'https://news.google.com', ?, datetime('now'))
        ''', (stats['noticias_nuevas'],))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📰 NEWSINT completado: {stats['noticias_nuevas']} noticias nuevas de {stats['noticias_encontradas']} encontradas")
        return stats
    
    # ============================================================
    # TÉCNICA 2: TRENDINT - Trends Intelligence
    # ============================================================
    
    def recolectar_tendencias(self) -> Dict[str, Any]:
        """
        Recolecta tendencias de búsqueda relacionadas con EMI y sus carreras.
        Usa pytrends (Google Trends API no oficial).
        
        Returns:
            Dict con estadísticas
        """
        logger.info("📊 Iniciando TRENDINT: Análisis de tendencias de búsqueda")
        
        stats = {
            'terminos_analizados': 0,
            'datos_recolectados': 0,
            'errores': 0
        }
        
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='es-BO', tz=240)
            
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            
            # Términos a analizar: carreras de la EMI
            terms_groups = [
                ['EMI Bolivia', 'UMSA Bolivia', 'UCB Bolivia'],
                ['Ingeniería Civil Bolivia', 'Ingeniería Sistemas Bolivia'],
                ['Escuela Militar Ingeniería', 'universidad Bolivia'],
            ]
            
            for group in terms_groups:
                try:
                    pytrends.build_payload(group, cat=0, timeframe='today 12-m', geo='BO')
                    data = pytrends.interest_over_time()
                    
                    if data.empty:
                        continue
                    
                    for col in data.columns:
                        if col == 'isPartial':
                            continue
                        
                        for date, value in data[col].items():
                            cursor.execute('''
                                INSERT INTO osint_tendencias 
                                (termino, region, periodo, valor_interes, fecha_dato, tipo)
                                VALUES (?, 'Bolivia', 'semanal', ?, ?, 'google_trends')
                            ''', (col, int(value), date.strftime('%Y-%m-%d')))
                            stats['datos_recolectados'] += 1
                        
                        stats['terminos_analizados'] += 1
                    
                except Exception as e:
                    logger.warning(f"Error en grupo {group}: {e}")
                    stats['errores'] += 1
            
            # Registrar fuente
            cursor.execute('''
                INSERT OR REPLACE INTO osint_fuente_resumen 
                (tipo_tecnica, nombre_fuente, descripcion, url_base, total_datos_recolectados, ultima_recoleccion)
                VALUES ('TRENDINT', 'Google Trends', 
                        'Análisis de tendencias de búsqueda sobre EMI y universidades en Bolivia',
                        'https://trends.google.com', ?, datetime('now'))
            ''', (stats['datos_recolectados'],))
            
            conn.commit()
            conn.close()
            
        except ImportError:
            logger.warning("pytrends no instalado. Generando datos de tendencias desde fuentes existentes.")
            stats = self._generar_tendencias_desde_datos()
        
        logger.info(f"📊 TRENDINT completado: {stats['datos_recolectados']} datos de tendencia")
        return stats
    
    def _generar_tendencias_desde_datos(self) -> Dict[str, Any]:
        """
        Genera análisis de tendencias a partir de los datos ya recolectados
        (actividad en redes sociales de la EMI como proxy de tendencia).
        """
        stats = {'terminos_analizados': 0, 'datos_recolectados': 0, 'errores': 0}
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Tendencia de actividad por semana
        cursor.execute('''
            SELECT 
                strftime('%Y-%W', fecha_publicacion) as semana,
                COUNT(*) as publicaciones,
                AVG(engagement_likes) as avg_likes,
                AVG(engagement_comments) as avg_comments,
                SUM(engagement_views) as total_views
            FROM dato_recolectado
            GROUP BY semana
            ORDER BY semana
        ''')
        
        for row in cursor.fetchall():
            cursor.execute('''
                INSERT OR IGNORE INTO osint_tendencias 
                (termino, region, periodo, valor_interes, fecha_dato, tipo, metadata_json)
                VALUES ('Actividad EMI Redes', 'Bolivia', 'semanal', ?, ?, 'social_media_activity', ?)
            ''', (
                row['publicaciones'],
                f"{row['semana']}-1",
                json.dumps({
                    'avg_likes': row['avg_likes'],
                    'avg_comments': row['avg_comments'],
                    'total_views': row['total_views']
                })
            ))
            stats['datos_recolectados'] += 1
        
        # Tendencia de engagement
        cursor.execute('''
            SELECT 
                f.tipo_fuente as plataforma,
                strftime('%Y-%m', d.fecha_publicacion) as mes,
                AVG(d.engagement_likes + d.engagement_comments + d.engagement_shares) as avg_engagement,
                COUNT(*) as posts
            FROM dato_recolectado d
            JOIN fuente_osint f ON d.id_fuente = f.id_fuente
            GROUP BY plataforma, mes
            ORDER BY mes
        ''')
        
        for row in cursor.fetchall():
            cursor.execute('''
                INSERT OR IGNORE INTO osint_tendencias 
                (termino, region, periodo, valor_interes, fecha_dato, tipo, metadata_json)
                VALUES (?, 'Bolivia', 'mensual', ?, ?, 'engagement_trend', ?)
            ''', (
                f"Engagement {row['plataforma']}",
                int(row['avg_engagement'] or 0),
                f"{row['mes']}-01",
                json.dumps({'posts': row['posts'], 'platform': row['plataforma']})
            ))
            stats['datos_recolectados'] += 1
        
        stats['terminos_analizados'] = 2
        
        cursor.execute('''
            INSERT OR REPLACE INTO osint_fuente_resumen 
            (tipo_tecnica, nombre_fuente, descripcion, url_base, total_datos_recolectados, ultima_recoleccion)
            VALUES ('TRENDINT', 'Análisis de Tendencias Internas', 
                    'Tendencias derivadas del análisis de actividad en redes sociales de la EMI',
                    NULL, ?, datetime('now'))
        ''', (stats['datos_recolectados'],))
        
        conn.commit()
        conn.close()
        
        return stats
    
    # ============================================================
    # TÉCNICA 3: Clasificación Temática (OSINT Analysis)
    # ============================================================
    
    def clasificar_contenido_tematico(self) -> Dict[str, Any]:
        """
        Clasifica todo el contenido recolectado por temas académicos
        relevantes para el Vicerrectorado/UEBU.
        
        Identifica:
        - Intereses académicos de los estudiantes
        - Quejas y problemas
        - Temas de infraestructura
        - Interés en carreras específicas
        - Menciones de becas y costos
        """
        logger.info("🏷️ Iniciando clasificación temática de contenido")
        
        stats = {
            'contenidos_analizados': 0,
            'clasificaciones_nuevas': 0,
            'temas_encontrados': {},
            'contenido_academico': 0,
            'contenido_relevante_uebu': 0,
        }
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Obtener todos los posts y comentarios sin clasificar
        # Posts
        cursor.execute('''
            SELECT d.id_dato as id, d.contenido_original as texto, 'post' as tipo,
                   f.tipo_fuente as plataforma
            FROM dato_recolectado d
            JOIN fuente_osint f ON d.id_fuente = f.id_fuente
            WHERE d.id_dato NOT IN (
                SELECT id_contenido FROM clasificacion_tematica WHERE tipo_contenido = 'post'
            )
        ''')
        posts = cursor.fetchall()
        
        # Comentarios
        cursor.execute('''
            SELECT c.id_comentario as id, c.contenido as texto, 'comentario' as tipo,
                   f.tipo_fuente as plataforma
            FROM comentario c
            JOIN fuente_osint f ON c.id_fuente = f.id_fuente
            WHERE c.id_comentario NOT IN (
                SELECT id_contenido FROM clasificacion_tematica WHERE tipo_contenido = 'comentario'
            )
        ''')
        comments = cursor.fetchall()
        
        # Noticias
        cursor.execute('''
            SELECT id, titulo || ' ' || COALESCE(resumen, '') as texto, 'noticia' as tipo,
                   'noticias' as plataforma
            FROM osint_noticias
            WHERE id NOT IN (
                SELECT id_contenido FROM clasificacion_tematica WHERE tipo_contenido = 'noticia'
            )
        ''')
        noticias = cursor.fetchall()
        
        all_content = list(posts) + list(comments) + list(noticias)
        
        for item in all_content:
            texto = item['texto'] or ''
            if len(texto) < 3:
                continue
            
            stats['contenidos_analizados'] += 1
            
            # Clasificar temas
            temas = self._clasificar_temas(texto)
            
            if not temas:
                continue
            
            tema_principal = temas[0]['tema']
            tema_secundario = temas[1]['tema'] if len(temas) > 1 else None
            palabras_clave = ','.join(temas[0].get('keywords', []))
            confianza = temas[0]['score']
            
            # Determinar si es contenido académico
            temas_academicos = {'inscripcion', 'becas', 'calidad_academica', 'carreras', 
                               'empleo', 'tecnologia', 'costo'}
            es_academico = tema_principal in temas_academicos
            
            # Determinar si es relevante para UEBU
            temas_uebu = {'inscripcion', 'becas', 'calidad_academica', 'queja', 
                          'infraestructura', 'costo', 'vida_estudiantil'}
            es_relevante_uebu = tema_principal in temas_uebu
            
            cursor.execute('''
                INSERT INTO clasificacion_tematica
                (id_contenido, tipo_contenido, tema_principal, tema_secundario,
                 palabras_clave, confianza, es_academico, es_relevante_uebu)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'], item['tipo'], tema_principal, tema_secundario,
                palabras_clave, confianza, es_academico, es_relevante_uebu
            ))
            
            stats['clasificaciones_nuevas'] += 1
            stats['temas_encontrados'][tema_principal] = stats['temas_encontrados'].get(tema_principal, 0) + 1
            
            if es_academico:
                stats['contenido_academico'] += 1
            if es_relevante_uebu:
                stats['contenido_relevante_uebu'] += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"🏷️ Clasificación temática completada: {stats['clasificaciones_nuevas']} nuevas clasificaciones")
        return stats
    
    # ============================================================
    # TÉCNICA 4: Identificación de Patrones
    # ============================================================
    
    def identificar_patrones(self) -> Dict[str, Any]:
        """
        Identifica patrones en los datos recolectados de TODAS las fuentes.
        
        Patrones que busca:
        1. Patrones temporales (horarios de mayor actividad)
        2. Patrones de sentimiento (temas que generan más negatividad/positividad)
        3. Patrones de engagement (qué tipo de contenido genera más interacción)
        4. Patrones de interés académico (qué carreras/temas interesan más)
        5. Correlaciones entre fuentes (mismo tema en redes y noticias)
        """
        logger.info("🔍 Iniciando identificación de patrones")
        
        stats = {
            'patrones_nuevos': 0,
            'patrones_actualizados': 0,
            'patrones_por_tipo': {}
        }
        
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ─── Patrón 1: Temas dominantes por plataforma ───
        cursor.execute('''
            SELECT ct.tema_principal, 
                   CASE WHEN ct.tipo_contenido = 'noticia' THEN 'Noticias'
                        ELSE f.tipo_fuente
                   END as plataforma,
                   COUNT(*) as cantidad
            FROM clasificacion_tematica ct
            LEFT JOIN dato_recolectado d ON ct.id_contenido = d.id_dato AND ct.tipo_contenido = 'post'
            LEFT JOIN comentario c ON ct.id_contenido = c.id_comentario AND ct.tipo_contenido = 'comentario'
            LEFT JOIN fuente_osint f ON COALESCE(d.id_fuente, c.id_fuente) = f.id_fuente
            GROUP BY ct.tema_principal, plataforma
            HAVING cantidad >= 2
            ORDER BY cantidad DESC
        ''')
        
        temas_plataforma = cursor.fetchall()
        if temas_plataforma:
            datos_soporte = [dict(r) for r in temas_plataforma]
            self._registrar_patron(
                cursor, 
                'Distribución de temas por plataforma',
                'temas_dominantes',
                f'Los temas más discutidos son: {", ".join([r["tema_principal"] for r in temas_plataforma[:5]])}',
                json.dumps(datos_soporte, ensure_ascii=False),
                'Enfocar estrategia de comunicación en los temas identificados',
                relevancia_vicerrectorado=True
            )
            stats['patrones_nuevos'] += 1
        
        # ─── Patrón 2: Sentimiento por tema ───
        cursor.execute('''
            SELECT ct.tema_principal, 
                   a.sentimiento_predicho,
                   COUNT(*) as cantidad,
                   AVG(a.confianza) as confianza_promedio
            FROM clasificacion_tematica ct
            JOIN analisis_sentimiento a ON ct.id_contenido = a.id_dato_procesado
            WHERE ct.tipo_contenido IN ('post', 'comentario')
            GROUP BY ct.tema_principal, a.sentimiento_predicho
            ORDER BY ct.tema_principal, cantidad DESC
        ''')
        
        sent_temas = cursor.fetchall()
        if sent_temas:
            # Encontrar temas con más negatividad
            negativos = [dict(r) for r in sent_temas if r['sentimiento_predicho'] == 'Negativo']
            if negativos:
                self._registrar_patron(
                    cursor,
                    'Temas con sentimiento negativo predominante',
                    'sentimiento_negativo_tematico',
                    f'Temas con comentarios negativos: {", ".join([n["tema_principal"] for n in negativos[:3]])}',
                    json.dumps([dict(r) for r in sent_temas], ensure_ascii=False),
                    'Investigar las causas de insatisfacción en estos temas específicos',
                    relevancia_vicerrectorado=True,
                    impacto='alto'
                )
                stats['patrones_nuevos'] += 1
        
        # ─── Patrón 3: Horarios de mayor actividad ───
        cursor.execute('''
            SELECT 
                CASE cast(strftime('%w', fecha_publicacion) as integer)
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Lunes'
                    WHEN 2 THEN 'Martes'
                    WHEN 3 THEN 'Miércoles'
                    WHEN 4 THEN 'Jueves'
                    WHEN 5 THEN 'Viernes'
                    WHEN 6 THEN 'Sábado'
                END as dia,
                strftime('%H', fecha_publicacion) as hora,
                COUNT(*) as publicaciones,
                AVG(engagement_likes + engagement_comments) as avg_engagement
            FROM dato_recolectado
            GROUP BY dia, hora
            ORDER BY publicaciones DESC
            LIMIT 20
        ''')
        
        horarios = cursor.fetchall()
        if horarios:
            self._registrar_patron(
                cursor,
                'Horarios de mayor actividad en redes sociales',
                'patron_temporal',
                f'Mayor actividad: {horarios[0]["dia"]} a las {horarios[0]["hora"]}h',
                json.dumps([dict(r) for r in horarios], ensure_ascii=False),
                'Programar publicaciones institucionales en los horarios de mayor visibilidad',
                relevancia_vicerrectorado=True
            )
            stats['patrones_nuevos'] += 1
        
        # ─── Patrón 4: Engagement por tipo de contenido ───
        cursor.execute('''
            SELECT 
                f.tipo_fuente as plataforma,
                d.tipo_contenido,
                COUNT(*) as cantidad,
                AVG(d.engagement_likes) as avg_likes,
                AVG(d.engagement_comments) as avg_comments,
                AVG(d.engagement_shares) as avg_shares,
                MAX(d.engagement_likes + d.engagement_comments) as max_engagement
            FROM dato_recolectado d
            JOIN fuente_osint f ON d.id_fuente = f.id_fuente
            GROUP BY plataforma, d.tipo_contenido
        ''')
        
        engagement = cursor.fetchall()
        if engagement:
            self._registrar_patron(
                cursor,
                'Engagement por tipo de contenido y plataforma',
                'engagement_pattern',
                f'Se analizaron {sum(r["cantidad"] for r in engagement)} publicaciones en {len(set(r["plataforma"] for r in engagement))} plataformas',
                json.dumps([dict(r) for r in engagement], ensure_ascii=False),
                'Priorizar el tipo de contenido que genera mayor engagement',
                relevancia_vicerrectorado=True
            )
            stats['patrones_nuevos'] += 1
        
        # ─── Patrón 5: Intereses académicos de estudiantes ───
        cursor.execute('''
            SELECT tema_principal, COUNT(*) as menciones,
                   SUM(es_academico) as es_academico,
                   SUM(es_relevante_uebu) as relevante_uebu
            FROM clasificacion_tematica
            WHERE es_academico = 1
            GROUP BY tema_principal
            ORDER BY menciones DESC
        ''')
        
        intereses = cursor.fetchall()
        if intereses:
            self._registrar_patron(
                cursor,
                'Principales intereses académicos identificados',
                'intereses_academicos',
                f'Intereses más mencionados: {", ".join([r["tema_principal"] for r in intereses[:5]])}',
                json.dumps([dict(r) for r in intereses], ensure_ascii=False),
                'Estos son los temas que más interesan a la comunidad estudiantil',
                relevancia_vicerrectorado=True,
                impacto='alto'
            )
            stats['patrones_nuevos'] += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"🔍 Patrones identificados: {stats['patrones_nuevos']} nuevos")
        return stats
    
    def _registrar_patron(self, cursor, nombre, tipo, descripcion, datos_json, 
                          recomendacion, relevancia_vicerrectorado=False, impacto='medio'):
        """Registra un patrón identificado en la BD."""
        cursor.execute('''
            INSERT OR REPLACE INTO patron_identificado
            (nombre_patron, tipo_patron, descripcion, datos_soporte_json,
             recomendacion_accion, relevancia_vicerrectorado, impacto,
             fecha_primera_deteccion, fecha_ultima_deteccion)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        ''', (nombre, tipo, descripcion, datos_json, recomendacion,
              relevancia_vicerrectorado, impacto))
    
    def _clasificar_temas(self, texto: str) -> List[Dict]:
        """
        Clasifica un texto en temas académicos usando coincidencia de keywords.
        
        Returns:
            Lista de temas con scores de relevancia
        """
        texto_lower = texto.lower()
        resultados = []
        
        for tema, keywords in self.TEMAS_ACADEMICOS.items():
            score = 0
            found_keywords = []
            
            for kw in keywords:
                if kw.lower() in texto_lower:
                    score += 1
                    found_keywords.append(kw)
            
            if score > 0:
                # Normalizar score por cantidad de keywords del tema
                normalized_score = min(score / len(keywords), 1.0)
                resultados.append({
                    'tema': tema,
                    'score': round(normalized_score, 4),
                    'keywords': found_keywords,
                    'matches': score
                })
        
        # Ordenar por score descendente
        resultados.sort(key=lambda x: x['score'], reverse=True)
        
        return resultados
    
    def _calcular_relevancia(self, titulo: str, descripcion: str) -> float:
        """Calcula un score de relevancia para una noticia."""
        texto = f"{titulo} {descripcion}".lower()
        
        score = 0.0
        
        # Menciones directas de EMI
        if 'escuela militar de ingeniería' in texto:
            score += 0.4
        elif 'emi' in texto and ('bolivia' in texto or 'ingeniería' in texto):
            score += 0.3
        
        # Temas educativos
        education_terms = ['universidad', 'educación', 'académico', 'estudiante', 'carrera', 'ingeniería']
        for term in education_terms:
            if term in texto:
                score += 0.05
        
        # Bolivia
        if 'bolivia' in texto or 'la paz' in texto:
            score += 0.1
        
        return min(round(score, 4), 1.0)
    
    # ============================================================
    # EJECUCIÓN COMPLETA
    # ============================================================
    
    def ejecutar_recoleccion_completa(self) -> Dict[str, Any]:
        """
        Ejecuta todas las técnicas OSINT disponibles.
        
        Returns:
            Dict con resultados de todas las técnicas
        """
        logger.info("🚀 Iniciando recolección OSINT completa (multifuente)")
        
        resultados = {
            'timestamp': datetime.now().isoformat(),
            'tecnicas_ejecutadas': 0,
            'resultados': {}
        }
        
        # 1. NEWSINT
        try:
            resultados['resultados']['newsint'] = self.recolectar_noticias()
            resultados['tecnicas_ejecutadas'] += 1
        except Exception as e:
            logger.error(f"Error en NEWSINT: {e}")
            resultados['resultados']['newsint'] = {'error': str(e)}
        
        # 2. TRENDINT
        try:
            resultados['resultados']['trendint'] = self.recolectar_tendencias()
            resultados['tecnicas_ejecutadas'] += 1
        except Exception as e:
            logger.error(f"Error en TRENDINT: {e}")
            resultados['resultados']['trendint'] = {'error': str(e)}
        
        # 3. Clasificación Temática
        try:
            resultados['resultados']['clasificacion'] = self.clasificar_contenido_tematico()
            resultados['tecnicas_ejecutadas'] += 1
        except Exception as e:
            logger.error(f"Error en clasificación temática: {e}")
            resultados['resultados']['clasificacion'] = {'error': str(e)}
        
        # 4. Identificación de Patrones
        try:
            resultados['resultados']['patrones'] = self.identificar_patrones()
            resultados['tecnicas_ejecutadas'] += 1
        except Exception as e:
            logger.error(f"Error en identificación de patrones: {e}")
            resultados['resultados']['patrones'] = {'error': str(e)}
        
        logger.info(f"🚀 Recolección OSINT completa: {resultados['tecnicas_ejecutadas']} técnicas ejecutadas")
        return resultados


def get_osint_resumen() -> Dict[str, Any]:
    """
    Obtiene un resumen del estado de todas las fuentes OSINT.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    resumen = {
        'tecnicas_osint': [],
        'total_fuentes': 0,
        'total_datos': 0,
        'distribucion_temas': {},
        'patrones_activos': 0
    }
    
    # Fuentes OSINT registradas
    cursor.execute('SELECT * FROM osint_fuente_resumen ORDER BY tipo_tecnica')
    for row in cursor.fetchall():
        resumen['tecnicas_osint'].append(dict(row))
        resumen['total_fuentes'] += 1
    
    # Agregar fuentes de redes sociales existentes
    cursor.execute('''
        SELECT tipo_fuente, COUNT(*) as fuentes, 
               SUM(total_registros_recolectados) as datos
        FROM fuente_osint WHERE activa = 1
        GROUP BY tipo_fuente
    ''')
    for row in cursor.fetchall():
        resumen['tecnicas_osint'].append({
            'tipo_tecnica': 'SOCMINT',
            'nombre_fuente': f'{row["tipo_fuente"]} (Social Media)',
            'total_datos_recolectados': row['datos'] or 0
        })
        resumen['total_fuentes'] += row['fuentes']
    
    # Total datos
    cursor.execute('SELECT COUNT(*) as total FROM dato_recolectado')
    resumen['total_datos'] += cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM comentario')
    resumen['total_datos'] += cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM osint_noticias')
    resumen['total_datos'] += cursor.fetchone()['total']
    
    # Distribución de temas
    cursor.execute('''
        SELECT tema_principal, COUNT(*) as cantidad
        FROM clasificacion_tematica
        GROUP BY tema_principal
        ORDER BY cantidad DESC
    ''')
    for row in cursor.fetchall():
        resumen['distribucion_temas'][row['tema_principal']] = row['cantidad']
    
    # Patrones activos
    cursor.execute("SELECT COUNT(*) as total FROM patron_identificado WHERE estado = 'activo'")
    resumen['patrones_activos'] = cursor.fetchone()['total']
    
    conn.close()
    return resumen


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    osint = OSINTMultifuente()
    resultado = osint.ejecutar_recoleccion_completa()
    
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
