-- ============================================================
-- Schema de Base de Datos SQLite
-- Sistema OSINT Vicerrectorado EMI
-- ============================================================
-- Este script crea las tablas necesarias para almacenar
-- datos recolectados de redes sociales (Facebook, TikTok)
-- y datos procesados por el pipeline ETL.
--
-- Autor: Sistema OSINT EMI
-- Fecha: Diciembre 2024
-- Base de datos: SQLite 3
-- ============================================================

-- Eliminar tablas existentes si existen (para desarrollo)
DROP TABLE IF EXISTS dato_procesado;
DROP TABLE IF EXISTS dato_recolectado;
DROP TABLE IF EXISTS fuente_osint;
DROP TABLE IF EXISTS log_ejecucion;

-- ============================================================
-- Tabla 1: fuente_osint
-- ============================================================
-- Almacena información sobre las fuentes de datos OSINT
-- (páginas de Facebook, perfiles de TikTok, etc.)

CREATE TABLE fuente_osint (
    id_fuente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_fuente VARCHAR(100) NOT NULL,
    tipo_fuente VARCHAR(50) NOT NULL,  -- 'Facebook', 'TikTok', 'Twitter'
    url_fuente VARCHAR(255) NOT NULL,
    identificador VARCHAR(100),  -- ID de página o username
    puntuacion_confiabilidad DECIMAL(3,2) DEFAULT 0.80,
    activa BOOLEAN DEFAULT 1,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_recoleccion TIMESTAMP,
    total_registros_recolectados INTEGER DEFAULT 0,
    metadata_json TEXT,  -- JSON con configuración adicional
    
    UNIQUE(tipo_fuente, identificador)
);

-- Índices para búsqueda rápida
CREATE INDEX idx_fuente_tipo ON fuente_osint(tipo_fuente);
CREATE INDEX idx_fuente_activa ON fuente_osint(activa);

-- ============================================================
-- Tabla 2: dato_recolectado
-- ============================================================
-- Almacena los datos crudos recolectados de cada fuente.
-- Estos datos NO han sido procesados por el pipeline ETL.

CREATE TABLE dato_recolectado (
    id_dato INTEGER PRIMARY KEY AUTOINCREMENT,
    id_fuente INTEGER NOT NULL,
    id_externo VARCHAR(100) UNIQUE NOT NULL,  -- ID único de la plataforma origen
    fecha_publicacion TIMESTAMP NOT NULL,
    fecha_recoleccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    contenido_original TEXT NOT NULL,  -- Texto del post/video sin modificar
    autor VARCHAR(100),
    engagement_likes INTEGER DEFAULT 0,
    engagement_comments INTEGER DEFAULT 0,
    engagement_shares INTEGER DEFAULT 0,
    engagement_views INTEGER DEFAULT 0,  -- Para TikTok
    tipo_contenido VARCHAR(30),  -- 'texto', 'imagen', 'video'
    url_publicacion VARCHAR(500),
    metadata_json TEXT,  -- JSON con datos adicionales específicos de plataforma
    procesado BOOLEAN DEFAULT 0,  -- 0=No procesado, 1=Procesado por ETL
    fecha_procesamiento TIMESTAMP,
    
    FOREIGN KEY (id_fuente) REFERENCES fuente_osint(id_fuente)
);

-- Índices para optimizar consultas frecuentes
CREATE INDEX idx_dato_fuente ON dato_recolectado(id_fuente);
CREATE INDEX idx_dato_fecha_pub ON dato_recolectado(fecha_publicacion);
CREATE INDEX idx_dato_fecha_rec ON dato_recolectado(fecha_recoleccion);
CREATE INDEX idx_dato_procesado ON dato_recolectado(procesado);
CREATE INDEX idx_dato_tipo ON dato_recolectado(tipo_contenido);

-- ============================================================
-- Tabla 3: dato_procesado
-- ============================================================
-- Almacena los datos después de pasar por el pipeline ETL.
-- Estos datos están limpios, normalizados y listos para análisis.

CREATE TABLE dato_procesado (
    id_dato_procesado INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dato_original INTEGER NOT NULL,  -- Referencia al dato crudo
    contenido_limpio TEXT NOT NULL,  -- Texto procesado y limpio
    longitud_texto INTEGER,  -- Cantidad de caracteres
    cantidad_palabras INTEGER,  -- Cantidad de palabras
    fecha_publicacion_iso TIMESTAMP NOT NULL,  -- Fecha normalizada
    anio INTEGER,  -- Año de publicación
    mes INTEGER,  -- Mes (1-12)
    dia_semana INTEGER,  -- Día de la semana (0=Lunes, 6=Domingo)
    hora INTEGER,  -- Hora del día (0-23)
    semestre VARCHAR(10),  -- '2025-I', '2025-II' (académico)
    es_horario_laboral BOOLEAN,  -- Si fue publicado en horario laboral
    engagement_total INTEGER,  -- likes + comments + shares
    engagement_normalizado DECIMAL(5,2),  -- Normalizado por fuente (0-100)
    ratio_engagement DECIMAL(8,4),  -- Engagement / views (si aplica)
    categoria_preliminar VARCHAR(50),  -- Clasificación básica del contenido
    idioma_detectado VARCHAR(10) DEFAULT 'es',  -- Idioma del texto
    contiene_mencion_emi BOOLEAN DEFAULT 0,  -- Si menciona EMI directamente
    sentimiento_basico VARCHAR(20),  -- 'positivo', 'negativo', 'neutral' (básico)
    fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_etl VARCHAR(20) DEFAULT '1.0.0',  -- Versión del pipeline que procesó
    
    FOREIGN KEY (id_dato_original) REFERENCES dato_recolectado(id_dato)
);

-- Índices para análisis
CREATE INDEX idx_procesado_original ON dato_procesado(id_dato_original);
CREATE INDEX idx_procesado_fecha ON dato_procesado(fecha_publicacion_iso);
CREATE INDEX idx_procesado_mes ON dato_procesado(mes);
CREATE INDEX idx_procesado_semestre ON dato_procesado(semestre);
CREATE INDEX idx_procesado_categoria ON dato_procesado(categoria_preliminar);
CREATE INDEX idx_procesado_engagement ON dato_procesado(engagement_normalizado);

-- ============================================================
-- Tabla 4: log_ejecucion
-- ============================================================
-- Almacena logs de ejecución del sistema para auditoría
-- y monitoreo del funcionamiento.

CREATE TABLE log_ejecucion (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_operacion VARCHAR(50) NOT NULL,  -- 'recoleccion', 'etl', 'scheduler'
    fuente VARCHAR(100),  -- Fuente afectada o 'all'
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_fin TIMESTAMP,
    duracion_segundos DECIMAL(10,2),
    registros_procesados INTEGER DEFAULT 0,
    registros_exitosos INTEGER DEFAULT 0,
    registros_fallidos INTEGER DEFAULT 0,
    estado VARCHAR(20) DEFAULT 'en_progreso',  -- 'en_progreso', 'completado', 'error'
    mensaje_error TEXT,
    detalles_json TEXT  -- JSON con estadísticas adicionales
);

CREATE INDEX idx_log_tipo ON log_ejecucion(tipo_operacion);
CREATE INDEX idx_log_fecha ON log_ejecucion(fecha_inicio);
CREATE INDEX idx_log_estado ON log_ejecucion(estado);

-- ============================================================
-- Datos iniciales: Fuentes OSINT configuradas
-- ============================================================

INSERT INTO fuente_osint (nombre_fuente, tipo_fuente, url_fuente, identificador, puntuacion_confiabilidad, activa)
VALUES 
    ('EMI Oficial Facebook', 'Facebook', 'https://www.facebook.com/profile.php?id=61574626396439', '61574626396439', 0.95, 1),
    ('EMI UALP Facebook', 'Facebook', 'https://www.facebook.com/EMI.UALP', 'EMI.UALP', 0.90, 1),
    ('EMI La Paz TikTok', 'TikTok', 'https://www.tiktok.com/@emilapazoficial', 'emilapazoficial', 0.85, 1);

-- ============================================================
-- Vistas útiles para consultas frecuentes
-- ============================================================

-- Vista: Resumen de datos por fuente
CREATE VIEW v_resumen_por_fuente AS
SELECT 
    f.id_fuente,
    f.nombre_fuente,
    f.tipo_fuente,
    COUNT(d.id_dato) as total_recolectados,
    SUM(CASE WHEN d.procesado = 1 THEN 1 ELSE 0 END) as total_procesados,
    AVG(d.engagement_likes) as promedio_likes,
    MAX(d.fecha_recoleccion) as ultima_recoleccion
FROM fuente_osint f
LEFT JOIN dato_recolectado d ON f.id_fuente = d.id_fuente
GROUP BY f.id_fuente, f.nombre_fuente, f.tipo_fuente;

-- Vista: Datos procesados con información completa
CREATE VIEW v_datos_completos AS
SELECT 
    dp.id_dato_procesado,
    f.nombre_fuente,
    f.tipo_fuente,
    dr.contenido_original,
    dp.contenido_limpio,
    dp.fecha_publicacion_iso,
    dp.semestre,
    dp.engagement_total,
    dp.engagement_normalizado,
    dp.categoria_preliminar,
    dr.url_publicacion
FROM dato_procesado dp
JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
JOIN fuente_osint f ON dr.id_fuente = f.id_fuente;

-- Vista: Estadísticas por semestre
CREATE VIEW v_estadisticas_semestre AS
SELECT 
    semestre,
    COUNT(*) as total_publicaciones,
    AVG(engagement_normalizado) as engagement_promedio,
    SUM(engagement_total) as engagement_total,
    AVG(cantidad_palabras) as palabras_promedio
FROM dato_procesado
GROUP BY semestre
ORDER BY semestre DESC;

-- ============================================================
-- Fin del schema
-- ============================================================
