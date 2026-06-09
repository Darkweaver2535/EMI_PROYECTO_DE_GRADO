"""
SQL Filters — Shared query fragments for excluding official sources.

NOTA: Para el sistema OSINT de Vicerrectorado, TODAS las fuentes son
relevantes para el análisis de sentimiento (tanto páginas oficiales
como páginas de confesiones/estudiantes). El filtro es_oficial se
desactiva para no perder datos valiosos.
"""

# Filtro SQL para posts (incluye todas las fuentes)
EXTERNAL_POSTS_FILTER = """
    JOIN fuente_osint fo_filter ON dr.id_fuente = fo_filter.id_fuente
"""

# Subconsulta para IDs de dato_procesado (incluye todos)
EXTERNAL_PROCESADOS_SUBQUERY = """
    dp.id_dato_procesado IN (
        SELECT dp2.id_dato_procesado
        FROM dato_procesado dp2
        JOIN dato_recolectado dr2 ON dp2.id_dato_original = dr2.id_dato
        JOIN fuente_osint fo2 ON dr2.id_fuente = fo2.id_fuente
    )
"""

# Restringe a POSTS clasificados por DeepSeek como INSTITUCIONALES.
# El sistema es netamente académico de la EMI: el contenido personal
# (confesiones, chismes, declaraciones románticas) se excluye de TODO el
# análisis y los dashboards aunque mencione la universidad o una carrera.
# Si DeepSeek aún no analizó un post, queda fuera (no se muestra dato sin
# clasificar). `dp` debe ser el alias de dato_procesado en la consulta.
INSTITUTIONAL_POSTS_SUBQUERY = """
    dp.id_dato_procesado IN (
        SELECT id_contenido FROM analisis_deepseek
        WHERE tipo_contenido = 'post' AND es_institucional = 1
    )
"""

# Equivalente para comentarios (alias `c` = comentario).
INSTITUTIONAL_COMMENTS_SUBQUERY = """
    c.id_comentario IN (
        SELECT id_contenido FROM analisis_deepseek
        WHERE tipo_contenido = 'comentario' AND es_institucional = 1
    )
"""
