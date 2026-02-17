-- Crear tabla de comentarios (lo más importante para el análisis)
CREATE TABLE IF NOT EXISTS comentario (
    id_comentario INTEGER PRIMARY KEY AUTOINCREMENT,
    id_post INTEGER NOT NULL,
    id_fuente INTEGER NOT NULL,
    id_externo VARCHAR(100),
    autor VARCHAR(100),
    contenido TEXT NOT NULL,
    fecha_publicacion TIMESTAMP,
    fecha_recoleccion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    likes INTEGER DEFAULT 0,
    respuestas INTEGER DEFAULT 0,
    es_respuesta BOOLEAN DEFAULT 0,
    id_comentario_padre INTEGER,
    procesado BOOLEAN DEFAULT 0,
    metadata_json TEXT,
    
    FOREIGN KEY (id_post) REFERENCES dato_recolectado(id_dato),
    FOREIGN KEY (id_fuente) REFERENCES fuente_osint(id_fuente),
    FOREIGN KEY (id_comentario_padre) REFERENCES comentario(id_comentario)
);

CREATE INDEX IF NOT EXISTS idx_comentario_post ON comentario(id_post);
CREATE INDEX IF NOT EXISTS idx_comentario_fuente ON comentario(id_fuente);
CREATE INDEX IF NOT EXISTS idx_comentario_fecha ON comentario(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_comentario_procesado ON comentario(procesado);

-- Tabla para análisis de sentimiento de comentarios
CREATE TABLE IF NOT EXISTS analisis_comentario (
    id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
    id_comentario INTEGER NOT NULL,
    sentimiento VARCHAR(20) NOT NULL,
    confianza DECIMAL(5,4) NOT NULL,
    probabilidad_positivo DECIMAL(5,4),
    probabilidad_neutral DECIMAL(5,4),
    probabilidad_negativo DECIMAL(5,4),
    fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (id_comentario) REFERENCES comentario(id_comentario)
);

CREATE INDEX IF NOT EXISTS idx_analisis_comentario ON analisis_comentario(id_comentario);
CREATE INDEX IF NOT EXISTS idx_analisis_sentimiento ON analisis_comentario(sentimiento);

-- Vista para ver posts con conteo de comentarios
CREATE VIEW IF NOT EXISTS v_posts_con_comentarios AS
SELECT 
    dr.id_dato as id_post,
    f.nombre_fuente,
    f.tipo_fuente,
    dr.contenido_original as contenido_post,
    dr.fecha_publicacion,
    dr.engagement_likes as likes,
    dr.engagement_comments as comentarios_count,
    dr.engagement_shares as shares,
    dr.url_publicacion,
    (SELECT COUNT(*) FROM comentario c WHERE c.id_post = dr.id_dato) as comentarios_recolectados
FROM dato_recolectado dr
JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
ORDER BY dr.fecha_publicacion DESC;

-- Vista para resumen de sentimientos por post
CREATE VIEW IF NOT EXISTS v_sentimientos_por_post AS
SELECT 
    c.id_post,
    COUNT(*) as total_comentarios,
    SUM(CASE WHEN ac.sentimiento = 'Positivo' THEN 1 ELSE 0 END) as positivos,
    SUM(CASE WHEN ac.sentimiento = 'Neutral' THEN 1 ELSE 0 END) as neutrales,
    SUM(CASE WHEN ac.sentimiento = 'Negativo' THEN 1 ELSE 0 END) as negativos,
    AVG(ac.confianza) as confianza_promedio
FROM comentario c
LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
WHERE ac.id_analisis IS NOT NULL
GROUP BY c.id_post;
