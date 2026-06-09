import sqlite3
import sys

academic_keywords = [
    'clase', 'examen', 'profesor', 'docente', 'materia', 'carrera', 
    'estudiar', 'tarea', 'semestre', 'inscripcion', 'inscripción', 
    'pago', 'mensualidad', 'tramite', 'trámite', 'laboratorio', 'biblioteca', 
    'wifi', 'internet', 'instalaciones', 'matricula', 'matrícula', 
    'mensualidades', 'rector', 'vicerrector', 'administrativo', 'seguridad', 
    'infraestructura', 'baño', 'cobro', 'universidad', 'emi', 'plataforma',
    'credencial', 'horario', 'parcial'
]

personal_drama_keywords = [
    'cawai', 'novio', 'novia', 'beso', 'pareja', 'enamorados', 'linda', 
    'feo', 'feito', 'rotada', 'borracho', 'peda', 'cortejo', 'corteja'
]

conn = sqlite3.connect('data/osint_emi.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

query = """
    SELECT dp.contenido_limpio, as2.confianza,
           dr.engagement_likes as likes, dr.engagement_comments as comments, 
           dr.engagement_shares as shares, dp.engagement_total
    FROM dato_procesado dp
    JOIN analisis_sentimiento as2 ON dp.id_dato_procesado = as2.id_dato_procesado
    JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
    WHERE as2.sentimiento_predicho = 'Negativo'
    ORDER BY as2.confianza DESC
    LIMIT 10
"""
cursor.execute(query)
posts = cursor.fetchall()

print("=== DIAGNÓSTICO DE ALERTAS: POSTS NEGATIVOS ===\n")
for i, p in enumerate(posts, 1):
    texto = (p['contenido_limpio'] or '').lower()
    conf = p['confianza']
    
    # Evaluar condiciones
    pasa_confianza = conf > 0.60
    
    acad_found = [kw for kw in academic_keywords if kw in texto]
    drama_found = [kw for kw in personal_drama_keywords if kw in texto]
    
    pasa_keywords = bool(acad_found) and not bool(drama_found)
    
    print(f"Post {i}: {p['contenido_limpio'][:100]}...")
    print(f"  - Confianza: {conf:.4f} (> 0.60? {'✅' if pasa_confianza else '❌'})")
    print(f"  - Engagement Total: {p['engagement_total']}")
    
    if acad_found:
        print(f"  - Keywords Académicas: ✅ Encontradas: {acad_found}")
    else:
        print(f"  - Keywords Académicas: ❌ Ninguna encontrada")
        
    if drama_found:
        print(f"  - Keywords Drama: ❌ Encontradas (Bloquea alerta): {drama_found}")
    else:
        print(f"  - Keywords Drama: ✅ Ninguna")
        
    print(f"  => STATUS ALERTA: {'✅ GENERADA' if (pasa_confianza and pasa_keywords) else '❌ RECHAZADA'}\n")
    
conn.close()
