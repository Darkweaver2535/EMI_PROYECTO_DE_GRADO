import sys, sqlite3, json, traceback, os
sys.path.insert(0, '.')
import logging
logging.disable(logging.CRITICAL)

def log_header(title):
    print(f"\n{'='*70}\n{title}\n{'='*70}")

log_header("1. INSPECCIÓN DE BASE DE DATOS REAL (data/osint_emi.db)")
db_path = "data/osint_emi.db"

if not os.path.exists(db_path):
    print(f"ERROR: No se encontró la BD en {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

for tabla in ["dato_procesado", "dato_recolectado", "comentario"]:
    cursor.execute(f"SELECT COUNT(*) as count FROM {tabla}")
    count = cursor.fetchone()['count']
    print(f"\n[Tabla: {tabla}] -> {count} registros totales")
    
    col = 'contenido_limpio' if tabla == 'dato_procesado' else ('contenido' if tabla == 'comentario' else 'contenido_original')
    
    try:
        cursor.execute(f"SELECT {col} as texto FROM {tabla} WHERE {col} IS NOT NULL AND length(trim({col})) > 5 LIMIT 3")
        rows = cursor.fetchall()
        for i, row in enumerate(rows, 1):
            texto = row['texto'].replace('\n', ' ')
            print(f"  Ejemplo {i}: {texto[:100]}...")
    except Exception as e:
        print(f"  Error leyendo tabla {tabla}: {e}")

log_header("2. PRUEBA DE SENTIMENT ANALYZER (Force Reanalysis)")
try:
    from sentiment_analyzer import ejecutar_analisis_completo
    res_sentiment = ejecutar_analisis_completo(force_reanalysis=True)
    
    print("\nEstadísticas de Procesamiento:")
    print(json.dumps(res_sentiment, indent=2, ensure_ascii=False))
    
    for sent in ['Positivo', 'Neutral', 'Negativo']:
        print(f"\nEjemplos de sentimiento: {sent.upper()}")
        cursor.execute(f"SELECT t1.contenido_limpio, t2.confianza FROM dato_procesado t1 JOIN analisis_sentimiento t2 ON t1.id_dato_procesado = t2.id_dato_procesado WHERE t2.sentimiento_predicho = ? ORDER BY t2.confianza DESC LIMIT 2", (sent,))
        for row in cursor.fetchall():
            print(f"  [{row['confianza']:.2f}] {row['contenido_limpio'][:120]}...")
            
except Exception as e:
    print(f"\n❌ ERROR EN SENTIMENT ANALYZER:")
    traceback.print_exc()

log_header("3. PRUEBA DEL NLP PIPELINE (BERTopic, KMeans, TF-IDF, NER)")
try:
    from nlp_pipeline import NLPPipeline
    pipeline = NLPPipeline()
    
    print("\nCargando textos de la BD...")
    pipeline.cargar_textos()
    res_nlp = pipeline.ejecutar_pipeline_completo()
    
    print("\n📝 TOPICOS DESCUBIERTOS (BERTopic):")
    for t in res_nlp.get('topicos', [])[:5]:
        print(f"  - Tópico {t['topico_id']}: '{t['nombre']}' | Coherencia: {t.get('coherencia', 'N/A'):.4f} | Docs: {t['num_documentos']}")
        
    print("\n🔑 TOP 10 KEYWORDS (TF-IDF):")
    for kw in res_nlp.get('palabras_clave', [])[:10]:
        print(f"  - {kw['palabra']} (Score: {kw['relevancia']:.4f})")
        
    print("\n🧠 CLUSTERS ENCONTRADOS (K-Means):")
    clusters = res_nlp.get('clusters', [])
    print(f"  Total clusters: {len(clusters)}")
    for c in clusters[:3]:
        print(f"  - Cluster {c['cluster_id']}: {', '.join(c['palabras_clave'][:5])} ({c['num_documentos']} docs)")
        
    print("\n🏷️ ENTIDADES MAS MENCIONADAS:")
    entidades = res_nlp.get('entidades', {})
    print("  Carreras: ", [e['entidad'] for e in entidades.get('carreras_mencionadas', [])[:3]])
    print("  Sedes: ", [e['entidad'] for e in entidades.get('sedes_mencionadas', [])[:3]])
    print("  Temas: ", [e['entidad'] for e in entidades.get('temas_academicos', [])[:3]])
    print("  Personas (spaCy): ", [e['entidad'] for e in entidades.get('personas', [])[:3]])
    
except Exception as e:
    print(f"\n❌ ERROR EN NLP PIPELINE:")
    traceback.print_exc()

conn.close()
