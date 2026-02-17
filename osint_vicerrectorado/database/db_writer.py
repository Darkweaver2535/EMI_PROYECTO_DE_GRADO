"""
DatabaseWriter - Gestor de escritura/lectura en SQLite
Sistema de Analítica EMI

Proporciona una interfaz para interactuar con la base de datos SQLite:
- Conexión y gestión de transacciones
- Inserción de datos recolectados con detección de duplicados
- Consultas para el pipeline ETL
- Estadísticas y reportes

Autor: Sistema OSINT EMI
Fecha: Diciembre 2024
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging


class DatabaseWriter:
    """
    Gestor de base de datos SQLite para el sistema OSINT.
    
    Maneja todas las operaciones de lectura/escritura con la base de datos,
    incluyendo transacciones atómicas y detección de duplicados.
    
    Attributes:
        db_path (str): Ruta al archivo de base de datos SQLite
        logger (logging.Logger): Logger para registrar operaciones
        connection (sqlite3.Connection): Conexión activa a la BD
    """
    
    def __init__(self, db_path: str = None, config: dict = None):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_path: Ruta al archivo SQLite. Si es None, usa config.
            config: Diccionario de configuración con ruta de BD.
        """
        self.logger = logging.getLogger("OSINT.DatabaseWriter")
        
        # Determinar ruta de la base de datos
        if db_path:
            self.db_path = db_path
        elif config and 'database' in config:
            self.db_path = config['database'].get('path', 'data/osint_emi.db')
        else:
            self.db_path = 'data/osint_emi.db'
        
        # Asegurar que existe el directorio
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            self.logger.info(f"Directorio de BD creado: {db_dir}")
        
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()
        
        self.logger.info(f"DatabaseWriter inicializado: {self.db_path}")
    
    def _initialize_database(self) -> None:
        """
        Inicializa la base de datos creando las tablas si no existen.
        """
        # Verificar si la BD ya existe
        db_exists = os.path.exists(self.db_path)
        
        if not db_exists:
            self.logger.info("Base de datos no existe, creando schema...")
            self._create_schema()
        else:
            # Verificar si tiene las tablas necesarias
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='fuente_osint'
            """)
            if not cursor.fetchone():
                self.logger.info("Tablas no encontradas, creando schema...")
                self._create_schema()
    
    def _create_schema(self) -> None:
        """
        Crea el schema de la base de datos desde el archivo SQL.
        """
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            conn = self._get_connection()
            conn.executescript(schema_sql)
            conn.commit()
            self.logger.info("Schema de base de datos creado exitosamente")
        else:
            # Crear schema inline si no existe el archivo
            self._create_schema_inline()
    
    def _create_schema_inline(self) -> None:
        """
        Crea el schema de forma inline (sin archivo SQL).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla fuente_osint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fuente_osint (
                id_fuente INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_fuente VARCHAR(100) NOT NULL,
                tipo_fuente VARCHAR(50) NOT NULL,
                url_fuente VARCHAR(255) NOT NULL,
                identificador VARCHAR(100),
                puntuacion_confiabilidad DECIMAL(3,2) DEFAULT 0.80,
                activa BOOLEAN DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_ultima_recoleccion TIMESTAMP,
                total_registros_recolectados INTEGER DEFAULT 0,
                metadata_json TEXT,
                UNIQUE(tipo_fuente, identificador)
            )
        """)
        
        # Tabla dato_recolectado
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dato_recolectado (
                id_dato INTEGER PRIMARY KEY AUTOINCREMENT,
                id_fuente INTEGER NOT NULL,
                id_externo VARCHAR(100) UNIQUE NOT NULL,
                fecha_publicacion TIMESTAMP NOT NULL,
                fecha_recoleccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                contenido_original TEXT NOT NULL,
                autor VARCHAR(100),
                engagement_likes INTEGER DEFAULT 0,
                engagement_comments INTEGER DEFAULT 0,
                engagement_shares INTEGER DEFAULT 0,
                engagement_views INTEGER DEFAULT 0,
                tipo_contenido VARCHAR(30),
                url_publicacion VARCHAR(500),
                metadata_json TEXT,
                procesado BOOLEAN DEFAULT 0,
                fecha_procesamiento TIMESTAMP,
                FOREIGN KEY (id_fuente) REFERENCES fuente_osint(id_fuente)
            )
        """)
        
        # Tabla dato_procesado
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dato_procesado (
                id_dato_procesado INTEGER PRIMARY KEY AUTOINCREMENT,
                id_dato_original INTEGER NOT NULL,
                contenido_limpio TEXT NOT NULL,
                longitud_texto INTEGER,
                cantidad_palabras INTEGER,
                fecha_publicacion_iso TIMESTAMP NOT NULL,
                anio INTEGER,
                mes INTEGER,
                dia_semana INTEGER,
                hora INTEGER,
                semestre VARCHAR(10),
                es_horario_laboral BOOLEAN,
                engagement_total INTEGER,
                engagement_normalizado DECIMAL(5,2),
                ratio_engagement DECIMAL(8,4),
                categoria_preliminar VARCHAR(50),
                idioma_detectado VARCHAR(10) DEFAULT 'es',
                contiene_mencion_emi BOOLEAN DEFAULT 0,
                sentimiento_basico VARCHAR(20),
                fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version_etl VARCHAR(20) DEFAULT '1.0.0',
                FOREIGN KEY (id_dato_original) REFERENCES dato_recolectado(id_dato)
            )
        """)
        
        # Tabla log_ejecucion
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_ejecucion (
                id_log INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_operacion VARCHAR(50) NOT NULL,
                fuente VARCHAR(100),
                fecha_inicio TIMESTAMP NOT NULL,
                fecha_fin TIMESTAMP,
                duracion_segundos DECIMAL(10,2),
                registros_procesados INTEGER DEFAULT 0,
                registros_exitosos INTEGER DEFAULT 0,
                registros_fallidos INTEGER DEFAULT 0,
                estado VARCHAR(20) DEFAULT 'en_progreso',
                mensaje_error TEXT,
                detalles_json TEXT
            )
        """)
        
        # Insertar fuentes por defecto
        cursor.execute("""
            INSERT OR IGNORE INTO fuente_osint 
            (nombre_fuente, tipo_fuente, url_fuente, identificador, puntuacion_confiabilidad)
            VALUES 
            ('EMI Oficial Facebook', 'Facebook', 'https://www.facebook.com/profile.php?id=61574626396439', '61574626396439', 0.95),
            ('EMI UALP Facebook', 'Facebook', 'https://www.facebook.com/EMI.UALP', 'EMI.UALP', 0.90),
            ('EMI La Paz TikTok', 'TikTok', 'https://www.tiktok.com/@emilapazoficial', 'emilapazoficial', 0.85)
        """)
        
        conn.commit()
        self.logger.info("Schema inline creado exitosamente")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Obtiene o crea una conexión a la base de datos.
        
        Returns:
            sqlite3.Connection: Conexión activa
        """
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            # Habilitar claves foráneas
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Configurar row factory para diccionarios
            self.connection.row_factory = sqlite3.Row
        
        return self.connection
    
    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Conexión a BD cerrada")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # =========================================================
    # Métodos de escritura de datos
    # =========================================================
    
    def get_or_create_source(self, nombre: str, tipo: str, url: str, 
                              identificador: str, confiabilidad: float = 0.80) -> int:
        """
        Obtiene o crea una fuente OSINT.
        
        Args:
            nombre: Nombre descriptivo de la fuente
            tipo: Tipo de fuente ('Facebook', 'TikTok')
            url: URL de la fuente
            identificador: ID único de la fuente
            confiabilidad: Puntuación de confiabilidad (0-1)
            
        Returns:
            int: ID de la fuente
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Buscar si ya existe
        cursor.execute("""
            SELECT id_fuente FROM fuente_osint 
            WHERE tipo_fuente = ? AND identificador = ?
        """, (tipo, identificador))
        
        result = cursor.fetchone()
        
        if result:
            return result['id_fuente']
        
        # Crear nueva fuente
        cursor.execute("""
            INSERT INTO fuente_osint 
            (nombre_fuente, tipo_fuente, url_fuente, identificador, puntuacion_confiabilidad)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, tipo, url, identificador, confiabilidad))
        
        conn.commit()
        self.logger.info(f"Nueva fuente creada: {nombre} (ID: {cursor.lastrowid})")
        
        return cursor.lastrowid
    
    def save_collected_data(self, data: List[Dict[str, Any]], 
                            source_id: int) -> Tuple[int, int]:
        """
        Guarda datos recolectados en la base de datos.
        
        Detecta duplicados por id_externo y solo inserta registros nuevos.
        
        Args:
            data: Lista de diccionarios con datos recolectados
            source_id: ID de la fuente OSINT
            
        Returns:
            Tuple[int, int]: (registros_insertados, duplicados_omitidos)
        """
        if not data:
            return 0, 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        inserted = 0
        duplicates = 0
        
        for item in data:
            try:
                # Verificar si ya existe
                cursor.execute(
                    "SELECT id_dato, metadata_json FROM dato_recolectado WHERE id_externo = ?",
                    (item['id_externo'],)
                )
                
                existing = cursor.fetchone()
                if existing:
                    # Si el item tiene comentarios, actualizar el registro existente
                    item_metadata = item.get('metadata_json', {})
                    if isinstance(item_metadata, str):
                        item_metadata = json.loads(item_metadata)
                    
                    if item_metadata.get('comentarios') or item_metadata.get('num_comentarios_extraidos'):
                        # Fusionar metadata
                        old_metadata = {}
                        if existing['metadata_json']:
                            try:
                                old_metadata = json.loads(existing['metadata_json'])
                            except:
                                old_metadata = {}
                        
                        old_metadata.update(item_metadata)
                        new_metadata = json.dumps(old_metadata, ensure_ascii=False)
                        
                        cursor.execute("""
                            UPDATE dato_recolectado 
                            SET metadata_json = ?,
                                engagement_comments = ?
                            WHERE id_dato = ?
                        """, (
                            new_metadata,
                            item.get('engagement_comments', len(item_metadata.get('comentarios', []))),
                            existing['id_dato']
                        ))
                        self.logger.debug(f"Actualizado registro {existing['id_dato']} con comentarios")
                    
                    duplicates += 1
                    continue
                
                # Preparar metadata
                metadata = item.get('metadata_json', {})
                if isinstance(metadata, dict):
                    metadata = json.dumps(metadata, ensure_ascii=False)
                
                # Insertar nuevo registro
                cursor.execute("""
                    INSERT INTO dato_recolectado 
                    (id_fuente, id_externo, fecha_publicacion, contenido_original,
                     autor, engagement_likes, engagement_comments, engagement_shares,
                     engagement_views, tipo_contenido, url_publicacion, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    source_id,
                    item['id_externo'],
                    item.get('fecha_publicacion', datetime.now()),
                    item['contenido_original'],
                    item.get('autor', 'Desconocido'),
                    item.get('engagement_likes', 0),
                    item.get('engagement_comments', 0),
                    item.get('engagement_shares', 0),
                    item.get('metadata_json', {}).get('views', 0),
                    item.get('tipo_contenido', 'texto'),
                    item.get('url_publicacion', ''),
                    metadata
                ))
                
                inserted += 1
                
            except Exception as e:
                self.logger.error(f"Error insertando registro: {e}")
                continue
        
        conn.commit()
        
        # Actualizar estadísticas de la fuente
        self._update_source_stats(source_id, inserted)
        
        self.logger.info(f"Datos guardados: {inserted} nuevos, {duplicates} duplicados")
        return inserted, duplicates
    
    def _update_source_stats(self, source_id: int, new_records: int) -> None:
        """
        Actualiza las estadísticas de una fuente OSINT.
        
        Args:
            source_id: ID de la fuente
            new_records: Cantidad de nuevos registros insertados
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE fuente_osint 
            SET fecha_ultima_recoleccion = CURRENT_TIMESTAMP,
                total_registros_recolectados = total_registros_recolectados + ?
            WHERE id_fuente = ?
        """, (new_records, source_id))
        
        conn.commit()
    
    def save_processed_data(self, data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Guarda datos procesados por el pipeline ETL.
        
        Args:
            data: Lista de diccionarios con datos procesados
            
        Returns:
            Tuple[int, int]: (registros_insertados, errores)
        """
        if not data:
            return 0, 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        inserted = 0
        errors = 0
        
        for item in data:
            try:
                cursor.execute("""
                    INSERT INTO dato_procesado 
                    (id_dato_original, contenido_limpio, longitud_texto, cantidad_palabras,
                     fecha_publicacion_iso, anio, mes, dia_semana, hora, semestre,
                     es_horario_laboral, engagement_total, engagement_normalizado,
                     ratio_engagement, categoria_preliminar, idioma_detectado,
                     contiene_mencion_emi, sentimiento_basico)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['id_dato_original'],
                    item['contenido_limpio'],
                    item.get('longitud_texto', 0),
                    item.get('cantidad_palabras', 0),
                    item['fecha_publicacion_iso'],
                    item.get('anio'),
                    item.get('mes'),
                    item.get('dia_semana'),
                    item.get('hora'),
                    item.get('semestre'),
                    item.get('es_horario_laboral', False),
                    item.get('engagement_total', 0),
                    item.get('engagement_normalizado', 0),
                    item.get('ratio_engagement', 0),
                    item.get('categoria_preliminar', 'General'),
                    item.get('idioma_detectado', 'es'),
                    item.get('contiene_mencion_emi', False),
                    item.get('sentimiento_basico', 'neutral')
                ))
                
                # Marcar registro original como procesado
                cursor.execute("""
                    UPDATE dato_recolectado 
                    SET procesado = 1, fecha_procesamiento = CURRENT_TIMESTAMP
                    WHERE id_dato = ?
                """, (item['id_dato_original'],))
                
                inserted += 1
                
            except Exception as e:
                self.logger.error(f"Error guardando dato procesado: {e}")
                errors += 1
                continue
        
        conn.commit()
        self.logger.info(f"Datos procesados guardados: {inserted} exitosos, {errors} errores")
        
        return inserted, errors
    
    # =========================================================
    # Métodos de lectura de datos
    # =========================================================
    
    def get_unprocessed_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene datos que no han sido procesados por ETL.
        
        Args:
            limit: Número máximo de registros a obtener
            
        Returns:
            List[Dict]: Lista de datos sin procesar
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                dr.id_dato,
                dr.id_fuente,
                dr.id_externo,
                dr.fecha_publicacion,
                dr.contenido_original,
                dr.autor,
                dr.engagement_likes,
                dr.engagement_comments,
                dr.engagement_shares,
                dr.engagement_views,
                dr.tipo_contenido,
                dr.url_publicacion,
                dr.metadata_json,
                f.nombre_fuente,
                f.tipo_fuente,
                f.puntuacion_confiabilidad
            FROM dato_recolectado dr
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            WHERE dr.procesado = 0
            ORDER BY dr.fecha_recoleccion DESC
            LIMIT ?
        """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            item = dict(row)
            # Parsear JSON
            if item.get('metadata_json'):
                try:
                    item['metadata_json'] = json.loads(item['metadata_json'])
                except:
                    item['metadata_json'] = {}
            results.append(item)
        
        return results
    
    def get_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene las fuentes OSINT configuradas.
        
        Args:
            active_only: Si True, solo retorna fuentes activas
            
        Returns:
            List[Dict]: Lista de fuentes
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM fuente_osint"
        if active_only:
            query += " WHERE activa = 1"
        
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de la base de datos.
        
        Returns:
            Dict: Estadísticas del sistema
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {
            'fuentes': {},
            'datos_recolectados': {},
            'datos_procesados': {},
            'general': {}
        }
        
        # Estadísticas de fuentes
        cursor.execute("SELECT COUNT(*) as total, SUM(activa) as activas FROM fuente_osint")
        row = cursor.fetchone()
        stats['fuentes'] = {'total': row['total'], 'activas': row['activas']}
        
        # Estadísticas de datos recolectados
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN procesado = 1 THEN 1 ELSE 0 END) as procesados,
                SUM(CASE WHEN procesado = 0 THEN 1 ELSE 0 END) as pendientes,
                AVG(engagement_likes) as promedio_likes,
                MAX(fecha_recoleccion) as ultima_recoleccion
            FROM dato_recolectado
        """)
        row = cursor.fetchone()
        stats['datos_recolectados'] = dict(row)
        
        # Estadísticas de datos procesados
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                AVG(engagement_normalizado) as engagement_promedio,
                AVG(cantidad_palabras) as palabras_promedio
            FROM dato_procesado
        """)
        row = cursor.fetchone()
        stats['datos_procesados'] = dict(row)
        
        # Por tipo de fuente
        cursor.execute("""
            SELECT 
                f.tipo_fuente,
                COUNT(dr.id_dato) as total_registros
            FROM fuente_osint f
            LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
            GROUP BY f.tipo_fuente
        """)
        stats['por_tipo'] = {row['tipo_fuente']: row['total_registros'] for row in cursor.fetchall()}
        
        return stats
    
    def get_engagement_stats_by_source(self) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas de engagement agrupadas por fuente.
        
        Returns:
            List[Dict]: Estadísticas por fuente
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                f.nombre_fuente,
                f.tipo_fuente,
                COUNT(dr.id_dato) as total_posts,
                ROUND(AVG(dr.engagement_likes), 2) as promedio_likes,
                ROUND(AVG(dr.engagement_comments), 2) as promedio_comments,
                MAX(dr.engagement_likes) as max_likes,
                SUM(dr.engagement_likes + dr.engagement_comments + dr.engagement_shares) as engagement_total
            FROM fuente_osint f
            LEFT JOIN dato_recolectado dr ON f.id_fuente = dr.id_fuente
            GROUP BY f.id_fuente, f.nombre_fuente, f.tipo_fuente
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================
    # Métodos de logging
    # =========================================================
    
    def log_execution(self, tipo: str, fuente: str = None) -> int:
        """
        Inicia un log de ejecución.
        
        Args:
            tipo: Tipo de operación ('recoleccion', 'etl', 'scheduler')
            fuente: Fuente afectada
            
        Returns:
            int: ID del log creado
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO log_ejecucion (tipo_operacion, fuente, fecha_inicio, estado)
            VALUES (?, ?, CURRENT_TIMESTAMP, 'en_progreso')
        """, (tipo, fuente or 'all'))
        
        conn.commit()
        return cursor.lastrowid
    
    def complete_execution_log(self, log_id: int, success: bool,
                                processed: int = 0, successful: int = 0,
                                failed: int = 0, error_msg: str = None,
                                details: dict = None) -> None:
        """
        Completa un log de ejecución.
        
        Args:
            log_id: ID del log a completar
            success: Si la ejecución fue exitosa
            processed: Registros procesados
            successful: Registros exitosos
            failed: Registros fallidos
            error_msg: Mensaje de error si hubo
            details: Detalles adicionales como dict
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        estado = 'completado' if success else 'error'
        details_json = json.dumps(details) if details else None
        
        cursor.execute("""
            UPDATE log_ejecucion 
            SET fecha_fin = CURRENT_TIMESTAMP,
                duracion_segundos = ROUND((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(fecha_inicio)) * 86400, 2),
                registros_procesados = ?,
                registros_exitosos = ?,
                registros_fallidos = ?,
                estado = ?,
                mensaje_error = ?,
                detalles_json = ?
            WHERE id_log = ?
        """, (processed, successful, failed, estado, error_msg, details_json, log_id))
        
        conn.commit()


    def get_all_processed_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los datos procesados para exportación.
        
        Returns:
            Lista de diccionarios con datos procesados y raw combinados
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                dp.id_dato_procesado as id_procesado,
                dr.id_dato as id_raw,
                dr.id_externo,
                f.nombre_fuente as fuente,
                f.tipo_fuente as plataforma,
                dr.autor,
                dr.contenido_original,
                dp.contenido_limpio,
                dr.fecha_publicacion,
                dr.engagement_likes as likes,
                dr.engagement_comments as comentarios,
                dr.engagement_shares as compartidos,
                dr.engagement_views as views,
                dp.sentimiento_basico as sentimiento,
                dp.categoria_preliminar as categoria,
                dp.engagement_normalizado as engagement_score,
                dp.semestre,
                dp.fecha_procesamiento,
                dr.metadata_json
            FROM dato_procesado dp
            JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            ORDER BY dp.fecha_procesamiento DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Parsear JSON fields
            if record.get('metadata_json'):
                try:
                    record['metadata'] = json.loads(record['metadata_json'])
                except:
                    record['metadata'] = {}
            results.append(record)
        
        return results


# =========================================================
# Función de conveniencia para uso rápido
# =========================================================

def get_database(config: dict = None) -> DatabaseWriter:
    """
    Factory function para obtener una instancia de DatabaseWriter.
    
    Args:
        config: Configuración opcional
        
    Returns:
        DatabaseWriter: Instancia del gestor de BD
    """
    return DatabaseWriter(config=config)


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseWriter(db_path="data/test_osint.db")
    
    # Obtener fuentes
    sources = db.get_sources()
    print(f"Fuentes configuradas: {len(sources)}")
    for source in sources:
        print(f"  - {source['nombre_fuente']} ({source['tipo_fuente']})")
    
    # Estadísticas
    stats = db.get_statistics()
    print(f"\nEstadísticas:")
    print(f"  Total recolectados: {stats['datos_recolectados'].get('total', 0)}")
    print(f"  Total procesados: {stats['datos_procesados'].get('total', 0)}")
    
    db.close()
