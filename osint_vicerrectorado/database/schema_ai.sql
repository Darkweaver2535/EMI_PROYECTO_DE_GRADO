-- ============================================================
-- Schema de Tablas de IA - Sistema OSINT EMI
-- Sprint 3: Módulo de Identificación de Patrones
-- ============================================================
-- Este script añade las tablas necesarias para almacenar
-- resultados de análisis de IA: sentimientos, tendencias,
-- clustering y anomalías.
--
-- Autor: Sistema OSINT EMI
-- Fecha: Enero 2025
-- ============================================================

-- ============================================================
-- Tabla: analisis_sentimiento
-- ============================================================
-- Almacena resultados del análisis de sentimientos con BETO

CREATE TABLE IF NOT EXISTS analisis_sentimiento (
    id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dato_procesado INTEGER NOT NULL,
    sentimiento_predicho VARCHAR(20) NOT NULL,  -- 'Positivo', 'Negativo', 'Neutral'
    confianza DECIMAL(5,4) NOT NULL,  -- Probabilidad de la predicción (0-1)
    probabilidad_positivo DECIMAL(5,4),
    probabilidad_neutral DECIMAL(5,4),
    probabilidad_negativo DECIMAL(5,4),
    modelo_version VARCHAR(50) DEFAULT '1.0.0',
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_dato_procesado) REFERENCES dato_procesado(id_dato_procesado)
);

CREATE INDEX IF NOT EXISTS idx_sentimiento_dato ON analisis_sentimiento(id_dato_procesado);
CREATE INDEX IF NOT EXISTS idx_sentimiento_predicho ON analisis_sentimiento(sentimiento_predicho);
CREATE INDEX IF NOT EXISTS idx_sentimiento_fecha ON analisis_sentimiento(fecha_analisis);
CREATE INDEX IF NOT EXISTS idx_sentimiento_confianza ON analisis_sentimiento(confianza);

-- ============================================================
-- Tabla: analisis_tendencia
-- ============================================================
-- Almacena análisis de tendencias temporales

CREATE TABLE IF NOT EXISTS analisis_tendencia (
    id_tendencia INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo VARCHAR(50) NOT NULL,  -- 'diario', 'semanal', 'mensual'
    metrica VARCHAR(100) NOT NULL,  -- 'sentimiento', 'engagement', 'volumen'
    tipo_tendencia VARCHAR(30) NOT NULL,  -- 'creciente', 'decreciente', 'estable'
    valor_slope DECIMAL(10,6),  -- Pendiente de la tendencia
    valor_r_squared DECIMAL(5,4),  -- R² de la regresión
    confianza DECIMAL(5,4),  -- Nivel de confianza
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    datos_puntos INTEGER,  -- Número de puntos de datos
    estacionalidad_detectada BOOLEAN DEFAULT 0,
    forecast_json TEXT,  -- JSON con predicciones futuras
    metadata_json TEXT,  -- JSON con detalles adicionales
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tendencia_periodo ON analisis_tendencia(periodo);
CREATE INDEX IF NOT EXISTS idx_tendencia_metrica ON analisis_tendencia(metrica);
CREATE INDEX IF NOT EXISTS idx_tendencia_tipo ON analisis_tendencia(tipo_tendencia);
CREATE INDEX IF NOT EXISTS idx_tendencia_fechas ON analisis_tendencia(fecha_inicio, fecha_fin);

-- ============================================================
-- Tabla: clustering_resultado
-- ============================================================
-- Almacena resultados del clustering de opiniones

CREATE TABLE IF NOT EXISTS clustering_resultado (
    id_clustering INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dato_procesado INTEGER NOT NULL,
    cluster_id INTEGER NOT NULL,
    distancia_centroide DECIMAL(10,6),
    confianza_asignacion DECIMAL(5,4),  -- Qué tan bien encaja en el cluster
    fecha_clustering TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_dato_procesado) REFERENCES dato_procesado(id_dato_procesado)
);

CREATE INDEX IF NOT EXISTS idx_clustering_dato ON clustering_resultado(id_dato_procesado);
CREATE INDEX IF NOT EXISTS idx_clustering_cluster ON clustering_resultado(cluster_id);

-- ============================================================
-- Tabla: clustering_modelo
-- ============================================================
-- Almacena información de modelos de clustering entrenados

CREATE TABLE IF NOT EXISTS clustering_modelo (
    id_modelo INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_modelo VARCHAR(100) NOT NULL,
    n_clusters INTEGER NOT NULL,
    silhouette_score DECIMAL(5,4),
    calinski_score DECIMAL(10,2),
    davies_bouldin_score DECIMAL(10,4),
    total_documentos INTEGER,
    cluster_keywords_json TEXT,  -- JSON con keywords por cluster
    configuracion_json TEXT,  -- JSON con parámetros del modelo
    modelo_path VARCHAR(500),  -- Ruta al modelo serializado
    activo BOOLEAN DEFAULT 1,
    fecha_entrenamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_modelo_activo ON clustering_modelo(activo);

-- ============================================================
-- Tabla: anomalia_detectada
-- ============================================================
-- Almacena anomalías detectadas en las métricas

CREATE TABLE IF NOT EXISTS anomalia_detectada (
    id_anomalia INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_anomalia VARCHAR(50) NOT NULL,  -- 'pico', 'caida', 'cambio_sentimiento', etc.
    descripcion TEXT NOT NULL,
    severidad VARCHAR(20) NOT NULL,  -- 'baja', 'media', 'alta', 'critica'
    metrica_afectada VARCHAR(100),
    valor_esperado DECIMAL(15,4),
    valor_observado DECIMAL(15,4),
    anomaly_score DECIMAL(10,6),
    fecha_deteccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ocurrencia TIMESTAMP,
    estado VARCHAR(20) DEFAULT 'nueva',  -- 'nueva', 'revisada', 'resuelta', 'falso_positivo'
    notas TEXT,
    metadata_json TEXT  -- JSON con detalles adicionales
);

CREATE INDEX IF NOT EXISTS idx_anomalia_tipo ON anomalia_detectada(tipo_anomalia);
CREATE INDEX IF NOT EXISTS idx_anomalia_severidad ON anomalia_detectada(severidad);
CREATE INDEX IF NOT EXISTS idx_anomalia_fecha ON anomalia_detectada(fecha_deteccion);
CREATE INDEX IF NOT EXISTS idx_anomalia_estado ON anomalia_detectada(estado);

-- ============================================================
-- Tabla: correlacion_resultado
-- ============================================================
-- Almacena resultados de análisis de correlaciones

CREATE TABLE IF NOT EXISTS correlacion_resultado (
    id_correlacion INTEGER PRIMARY KEY AUTOINCREMENT,
    variable_1 VARCHAR(100) NOT NULL,
    variable_2 VARCHAR(100) NOT NULL,
    coeficiente_correlacion DECIMAL(6,4) NOT NULL,  -- -1 a 1
    p_value DECIMAL(10,8) NOT NULL,
    es_significativa BOOLEAN NOT NULL,
    fuerza VARCHAR(30),  -- 'muy_fuerte', 'fuerte', 'moderada', 'debil'
    direccion VARCHAR(20),  -- 'positiva', 'negativa'
    n_muestras INTEGER,
    metodo VARCHAR(30) DEFAULT 'pearson',  -- 'pearson', 'spearman', 'kendall'
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_correlacion_vars ON correlacion_resultado(variable_1, variable_2);
CREATE INDEX IF NOT EXISTS idx_correlacion_significativa ON correlacion_resultado(es_significativa);

-- ============================================================
-- Tabla: modelo_entrenamiento
-- ============================================================
-- Registro de entrenamientos de modelos de IA

CREATE TABLE IF NOT EXISTS modelo_entrenamiento (
    id_entrenamiento INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_modelo VARCHAR(50) NOT NULL,  -- 'sentimiento', 'clustering', 'anomalias'
    nombre_modelo VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    metricas_json TEXT NOT NULL,  -- JSON con métricas de evaluación
    parametros_json TEXT,  -- JSON con hiperparámetros
    datos_entrenamiento INTEGER,  -- Número de muestras de entrenamiento
    datos_validacion INTEGER,
    modelo_path VARCHAR(500),  -- Ruta al modelo guardado
    estado VARCHAR(20) DEFAULT 'entrenado',  -- 'entrenado', 'activo', 'deprecado'
    fecha_entrenamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_activacion TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_modelo_tipo ON modelo_entrenamiento(tipo_modelo);
CREATE INDEX IF NOT EXISTS idx_modelo_estado ON modelo_entrenamiento(estado);

-- ============================================================
-- Tabla: alerta_ia
-- ============================================================
-- Sistema de alertas generadas por los módulos de IA

CREATE TABLE IF NOT EXISTS alerta_ia (
    id_alerta INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_alerta VARCHAR(50) NOT NULL,  -- 'anomalia', 'tendencia', 'sentimiento_negativo'
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    severidad VARCHAR(20) NOT NULL,  -- 'baja', 'media', 'alta', 'critica'
    modulo_origen VARCHAR(50),  -- 'anomaly_detector', 'trend_detector', etc.
    referencia_id INTEGER,  -- ID del registro relacionado
    referencia_tipo VARCHAR(50),  -- 'anomalia', 'tendencia', etc.
    requiere_accion BOOLEAN DEFAULT 0,
    estado VARCHAR(20) DEFAULT 'nueva',  -- 'nueva', 'leida', 'atendida', 'descartada'
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_lectura TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    usuario_asignado VARCHAR(100),
    notas_resolucion TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerta_tipo ON alerta_ia(tipo_alerta);
CREATE INDEX IF NOT EXISTS idx_alerta_severidad ON alerta_ia(severidad);
CREATE INDEX IF NOT EXISTS idx_alerta_estado ON alerta_ia(estado);
CREATE INDEX IF NOT EXISTS idx_alerta_fecha ON alerta_ia(fecha_creacion);

-- ============================================================
-- Tabla: anotacion_manual
-- ============================================================
-- Datos anotados manualmente para entrenamiento

CREATE TABLE IF NOT EXISTS anotacion_manual (
    id_anotacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_dato_procesado INTEGER NOT NULL,
    texto_original TEXT NOT NULL,
    sentimiento_anotado VARCHAR(20) NOT NULL,  -- 'Positivo', 'Negativo', 'Neutral'
    confianza_anotacion VARCHAR(20),  -- 'alta', 'media', 'baja'
    anotador VARCHAR(100),
    fecha_anotacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notas TEXT,
    usado_entrenamiento BOOLEAN DEFAULT 0,
    
    FOREIGN KEY (id_dato_procesado) REFERENCES dato_procesado(id_dato_procesado)
);

CREATE INDEX IF NOT EXISTS idx_anotacion_dato ON anotacion_manual(id_dato_procesado);
CREATE INDEX IF NOT EXISTS idx_anotacion_sentimiento ON anotacion_manual(sentimiento_anotado);
CREATE INDEX IF NOT EXISTS idx_anotacion_usado ON anotacion_manual(usado_entrenamiento);

-- ============================================================
-- Vistas para consultas frecuentes de IA
-- ============================================================

-- Vista: Resumen de sentimientos por período
CREATE VIEW IF NOT EXISTS v_sentimientos_periodo AS
SELECT 
    strftime('%Y-%m', dp.fecha_publicacion_iso) as periodo,
    COUNT(*) as total_analisis,
    SUM(CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1 ELSE 0 END) as positivos,
    SUM(CASE WHEN a.sentimiento_predicho = 'Neutral' THEN 1 ELSE 0 END) as neutrales,
    SUM(CASE WHEN a.sentimiento_predicho = 'Negativo' THEN 1 ELSE 0 END) as negativos,
    AVG(a.confianza) as confianza_promedio
FROM analisis_sentimiento a
JOIN dato_procesado dp ON a.id_dato_procesado = dp.id_dato_procesado
GROUP BY strftime('%Y-%m', dp.fecha_publicacion_iso)
ORDER BY periodo DESC;

-- Vista: Alertas activas
CREATE VIEW IF NOT EXISTS v_alertas_activas AS
SELECT 
    id_alerta,
    tipo_alerta,
    titulo,
    severidad,
    modulo_origen,
    fecha_creacion,
    CASE 
        WHEN severidad = 'critica' THEN 1
        WHEN severidad = 'alta' THEN 2
        WHEN severidad = 'media' THEN 3
        ELSE 4
    END as prioridad_orden
FROM alerta_ia
WHERE estado IN ('nueva', 'leida')
ORDER BY prioridad_orden, fecha_creacion DESC;

-- Vista: Estadísticas de clusters
CREATE VIEW IF NOT EXISTS v_estadisticas_clusters AS
SELECT 
    cr.cluster_id,
    COUNT(*) as total_documentos,
    AVG(cr.distancia_centroide) as distancia_promedio,
    MIN(cr.fecha_clustering) as primer_documento,
    MAX(cr.fecha_clustering) as ultimo_documento
FROM clustering_resultado cr
GROUP BY cr.cluster_id
ORDER BY total_documentos DESC;

-- ============================================================
-- Fin del schema de IA
-- ============================================================
