import sqlite3

conn = sqlite3.connect('data/osint_emi.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

query = """
SELECT dp.contenido_limpio, as2.confianza, 
       as2.probabilidad_positivo, as2.probabilidad_neutral, as2.probabilidad_negativo
FROM dato_procesado dp
JOIN analisis_sentimiento as2 ON dp.id_dato_procesado = as2.id_dato_procesado  
WHERE as2.sentimiento_predicho = 'Neutral'
AND as2.confianza BETWEEN 0.50 AND 0.75
LIMIT 5
"""

cursor.execute(query)
rows = cursor.fetchall()

print("=== 5 TEXTOS NEUTRALES CON BAJA/MEDIA CONFIANZA ===\n")
for i, row in enumerate(rows, 1):
    print(f"Texto {i}: {row['contenido_limpio']}")
    print(f"Probabilidades -> POS: {row['probabilidad_positivo']:.4f} | NEU: {row['probabilidad_neutral']:.4f} | NEG: {row['probabilidad_negativo']:.4f}")
    print("-" * 50)

conn.close()
