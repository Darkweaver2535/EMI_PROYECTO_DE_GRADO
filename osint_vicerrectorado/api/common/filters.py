"""
SQL Filters — Shared query fragments for excluding official sources.
"""

# Filtro SQL para excluir posts de fuentes oficiales
EXTERNAL_POSTS_FILTER = """
    JOIN fuente_osint fo_filter ON dr.id_fuente = fo_filter.id_fuente
    AND (fo_filter.es_oficial = 0 OR fo_filter.es_oficial IS NULL)
"""

# Subconsulta para IDs de dato_procesado que vienen de fuentes externas
EXTERNAL_PROCESADOS_SUBQUERY = """
    dp.id_dato_procesado IN (
        SELECT dp2.id_dato_procesado
        FROM dato_procesado dp2
        JOIN dato_recolectado dr2 ON dp2.id_dato_original = dr2.id_dato
        JOIN fuente_osint fo2 ON dr2.id_fuente = fo2.id_fuente
        WHERE fo2.es_oficial = 0 OR fo2.es_oficial IS NULL
    )
"""
