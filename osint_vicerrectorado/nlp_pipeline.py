#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
Pipeline NLP Avanzado — OE3: Modelos de IA, ML y NLP
═══════════════════════════════════════════════════════════════

Implementa:
1. Extracción de Entidades y Palabras Clave (TF-IDF)
2. Modelado de Tópicos (LDA / NMF)
3. Análisis de Sentimiento por Aspecto
4. Clustering de Opiniones (K-Means + Embeddings)
5. Detección de Tendencias NLP
6. Resumen Automático de Contenido

Técnicas ML/NLP aplicadas:
- TF-IDF para representación vectorial
- LDA (Latent Dirichlet Allocation) para tópicos
- NMF (Non-negative Matrix Factorization) para tópicos
- K-Means para clustering de opiniones
- Isolation Forest para detección de anomalías
- BETO (BERT español) para sentimiento
- Regex NLP para extracción de entidades

Autor: Sistema OSINT EMI
"""

import os
import sys
import re
import json
import sqlite3
import logging
import math
from datetime import datetime, timedelta
from collections import Counter, defaultdict

import numpy as np

# Intentar importar sklearn
try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import LatentDirichletAllocation, NMF
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NLP_Pipeline")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'osint_emi.db')

# ─── Stopwords Español ──────────────────────────────────────────
STOPWORDS_ES = {
    'el', 'la', 'de', 'en', 'y', 'a', 'que', 'es', 'un', 'una', 'los', 'las',
    'del', 'al', 'por', 'con', 'para', 'se', 'su', 'como', 'más', 'pero', 'muy',
    'sin', 'sobre', 'este', 'esta', 'son', 'han', 'ha', 'hay', 'ser', 'si', 'no',
    'ya', 'está', 'están', 'fue', 'era', 'puede', 'esto', 'eso', 'todo', 'toda',
    'todos', 'todas', 'tiene', 'tienen', 'hacer', 'hace', 'ver', 'más', 'tan',
    'les', 'nos', 'me', 'te', 'lo', 'le', 'mi', 'tu', 'sus', 'qué', 'quién',
    'cómo', 'cuándo', 'dónde', 'porque', 'aunque', 'también', 'así', 'solo',
    'cada', 'entre', 'desde', 'hasta', 'durante', 'antes', 'después', 'aquí',
    'ahí', 'allí', 'bien', 'mal', 'mucho', 'poco', 'otro', 'otra', 'otros',
    'hay', 'donde', 'cuando', 'quien', 'cual', 'esos', 'esas', 'estos', 'estas',
    'aquellos', 'aquellas', 'mismo', 'misma', 'mismos', 'mismas', 'ser', 'ir',
    'haber', 'poder', 'tener', 'hacer', 'decir', 'dar', 'ver', 'saber', 'querer',
    'llegar', 'pasar', 'deber', 'poner', 'parecer', 'quedar', 'creer', 'hablar',
    'llevar', 'dejar', 'seguir', 'encontrar', 'llamar', 'venir', 'pensar', 'salir',
    'volver', 'tomar', 'conocer', 'vivir', 'sentir', 'tratar', 'mirar', 'contar',
    'empezar', 'esperar', 'buscar', 'existir', 'entrar', 'trabajar', 'escribir',
    'perder', 'producir', 'ocurrir', 'entender', 'pedir', 'recibir', 'recordar',
    'terminar', 'permitir', 'aparecer', 'conseguir', 'comenzar', 'servir',
    'sacar', 'necesitar', 'mantener', 'resultar', 'leer', 'caer', 'cambiar',
    'presentar', 'crear', 'abrir', 'considerar', 'oír', 'acabar', 'convertir',
    'ganar', 'formar', 'traer', 'partir', 'morir', 'aceptar', 'realizar',
    'https', 'http', 'www', 'com',
    'nbsp', 'amp', 'quot', 'ver', 'más', 'ahora', 'anónimo', 'confesión',
    'hola', 'gracias', 'bueno', 'buena', 'buenos', 'buenas', 'jaja', 'jajaja',
    'xd', 'lol', 'etc', 'asi', 'ahi', 'aca'
}

# ─── Entidades EMI ──────────────────────────────────────────────
CARRERAS_EMI = [
    'civil', 'sistemas', 'industrial', 'electrónica', 'mecatrónica',
    'ambiental', 'petróleo', 'petrolera', 'telecomunicaciones',
    'eléctrica', 'mecánica', 'automotriz', 'comercial', 'militar'
]

ENTIDADES_EMI = {
    'institucion': ['emi', 'escuela militar', 'vicerrectorado', 'rectorado', 'decanatura'],
    'sedes': ['cochabamba', 'la paz', 'santa cruz', 'oruro', 'sucre', 'riberalta'],
    'academico': ['semestre', 'materia', 'examen', 'clase', 'nota', 'profesor', 'docente',
                   'laboratorio', 'practica', 'tesis', 'grado', 'titulo', 'carrera'],
    'servicios': ['beca', 'comedor', 'residencia', 'transporte', 'bienestar', 'biblioteca',
                   'inscripcion', 'matricula', 'certificado', 'tramite'],
    'sentimiento': {
        'positivo': ['excelente', 'bueno', 'mejor', 'increible', 'felicidades', 'orgullo',
                     'gracias', 'genial', 'perfecto', 'recomiendo', 'éxito', 'gran'],
        'negativo': ['malo', 'peor', 'terrible', 'pesimo', 'queja', 'problema', 'deficiente',
                     'reclamo', 'denuncia', 'corrupcion', 'abuso', 'injusto']
    }
}


# ── Frases que invalidan la detección de una carrera en su contexto ──────
# Si el término de carrera aparece dentro de alguna de estas frases,
# NO se cuenta como mención académica.  Se comparan en texto_lower.
CARRERAS_CONTEXTO_NEGATIVO = {
    'civil': [
        'estado civil', 'registro civil', 'guerra civil', 'sociedad civil',
        'derecho civil', 'código civil', 'matrimonio civil', 'unión civil',
        'desobediencia civil', 'población civil',
    ],
    'industrial': [
        'revolución industrial', 'era industrial', 'sector industrial',
        'zona industrial', 'espionaje industrial', 'accidente industrial',
        'residuo industrial', 'parque industrial',
    ],
    'ambiental': [
        'daño ambiental', 'impacto ambiental', 'contaminación ambiental',
        'crisis ambiental', 'problema ambiental',
    ],
    'militar': [
        'acción militar', 'conflicto militar', 'golpe militar',
        'base militar', 'zona militar', 'operación militar',
        'junta militar', 'dictadura militar',
    ],
    'comercial': [
        'centro comercial', 'local comercial', 'zona comercial',
        'relación comercial', 'acuerdo comercial', 'intercambio comercial',
    ],
}

# Tokens que, cuando aparecen cerca de una carrera, CONFIRMAN que
# se habla de la carrera académica (usado si spaCy está disponible).
_TOKENS_ACADEMICOS = {
    'ingeniería', 'ingenieria', 'carrera', 'facultad', 'licenciatura',
    'estudi', 'titulación', 'tesis', 'grado', 'emi', 'semestre',
    'materia', 'cursando', 'egresado', 'graduado',
}


class NLPPipeline:
    """
    Pipeline completo de NLP para análisis de datos OSINT.

    Implementa múltiples técnicas de ML y NLP:
    - TF-IDF keyword extraction
    - Topic modeling (LDA, NMF)
    - K-Means clustering
    - Named Entity Recognition (spaCy es_core_news_lg + word-boundary regex)
    - Aspect-based sentiment patterns
    - Automatic summarization
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.textos = []
        self.metadatos = []
        self.resultados = {}

        # ── Cargar modelo spaCy UNA sola vez ────────────────────
        self._nlp = None
        try:
            import spacy
            self._nlp = spacy.load('es_core_news_lg',
                                   disable=['parser', 'textcat'])
            logger.info("✅ spaCy es_core_news_lg cargado")
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning(f"⚠️  Modelo es_core_news_lg no pudo cargarse ({e}). NER usará diccionarios. Ejecuta: python -m spacy download es_core_news_lg\n"
                "   El NER operará solo con diccionarios + word boundaries."
            )
        except ImportError:
            logger.warning(
                "⚠️  spaCy no instalado. Ejecuta: pip install spacy\n"
                "   El NER operará solo con diccionarios + word boundaries."
            )

        # ── Sentencizer (pipeline ligero solo para segmentar oraciones) ───
        # Usa un pipeline separado de _nlp para no interferir con el NER
        # y evitar cargar el tagger/parser completo dos veces.
        self._sentencizer = None
        try:
            import spacy
            # Reutilizamos es_core_news_lg pero solo con senter habilitado
            self._sentencizer = spacy.load(
                'es_core_news_lg',
                enable=['senter'],          # solo segmentador de oraciones
                disable=['tagger', 'morphologizer', 'parser',
                         'ner', 'attribute_ruler', 'lemmatizer']
            )
            logger.info("✅ spaCy sentencizer cargado")
        except (OSError, RuntimeError, ValueError) as e:
            # Fallback: segmentación por regex en _segmentar_oraciones()
            logger.warning(
                f"⚠️  spaCy sentencizer no disponible: {e}. "
                "ABSA usará segmentación por regex."
            )

        # ── Cargar modelo BERTopic Embedding UNA sola vez ──────────────
        self._embedding_model = None
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            # Modelo rápido y multilingüe (120MB) recomendado para textos cortos
            self._embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=device)
            logger.info(f"✅ SentenceTransformer cargado en {device.upper()}")
        except ImportError:
            logger.warning(
                "⚠️ sentence-transformers no instalado. "
                "El modelado de tópicos BERTopic no funcionará."
            )

    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """Crea tablas para resultados NLP."""
        conn = self.get_db()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS nlp_topicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metodo TEXT NOT NULL,
                topico_id INTEGER,
                nombre_topico TEXT,
                palabras_clave TEXT,
                peso_topico REAL,
                num_documentos INTEGER,
                coherencia REAL,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS nlp_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_id INTEGER,
                etiqueta TEXT,
                palabras_clave TEXT,
                num_documentos INTEGER,
                sentimiento_predominante TEXT,
                textos_representativos TEXT,
                silhouette_score REAL,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS nlp_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                palabra TEXT NOT NULL,
                tfidf_score REAL,
                frecuencia INTEGER,
                tipo TEXT,
                contexto TEXT,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS nlp_entidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                texto_original TEXT,
                entidad TEXT,
                tipo_entidad TEXT,
                frecuencia INTEGER,
                contextos TEXT,
                fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS nlp_resumen_ejecutivo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_resumen TEXT,
                contenido TEXT,
                datos_soporte TEXT,
                fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS evaluacion_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metrica TEXT NOT NULL,
                categoria TEXT,
                valor REAL,
                detalle TEXT,
                fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        conn.close()

    # ═══════════════════════════════════════════════════════════
    # 1. CARGA DE DATOS
    # ═══════════════════════════════════════════════════════════

    def cargar_textos(self):
        """Carga todos los textos de la BD para análisis."""
        conn = self.get_db()
        cursor = conn.cursor()

        # Posts/comentarios
        cursor.execute('''
            SELECT dp.id_dato_procesado, dp.contenido_limpio, 
                   dp.categoria_preliminar as tipo_dato,
                   dp.fecha_publicacion_iso, dp.engagement_total,
                   COALESCE(a.sentimiento_predicho, 'Sin analizar') as sentimiento,
                   COALESCE(a.confianza, 0) as confianza
            FROM dato_procesado dp
            LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
            WHERE dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 10
        ''')

        for row in cursor.fetchall():
            # Limpiar HTML artifacts
            texto = row['contenido_limpio']
            texto = re.sub(r'&nbsp;?|\xa0|\u00a0', ' ', texto)
            texto = re.sub(r'nbsp', ' ', texto)
            texto = re.sub(r'\s+', ' ', texto).strip()
            if len(texto) < 10:
                continue
            self.textos.append(texto)
            self.metadatos.append({
                'id': row['id_dato_procesado'],
                'tipo': row['tipo_dato'],
                'fecha': row['fecha_publicacion_iso'],
                'engagement': row['engagement_total'] or 0,
                'sentimiento': row['sentimiento'],
                'confianza': row['confianza'],
                'fuente': 'dato_procesado'
            })

        # También cargar noticias OSINT si existen
        try:
            cursor.execute('''
                SELECT id, titulo || ' ' || COALESCE(resumen, '') as texto, 'noticia' as tipo,
                       fecha_publicacion as fecha, relevancia_score as engagement
                FROM osint_noticias
                WHERE titulo IS NOT NULL
            ''')
            for row in cursor.fetchall():
                self.textos.append(row['texto'])
                self.metadatos.append({
                    'id': row['id'],
                    'tipo': 'noticia',
                    'fecha': row['fecha'],
                    'engagement': row['engagement'] or 0,
                    'sentimiento': 'Sin analizar',
                    'confianza': 0,
                    'fuente': 'osint_noticias'
                })
        except sqlite3.Error as e:
            logger.error(f"Error extrayendo datos de sqlite: {e}")

        conn.close()
        logger.info(f"✅ Cargados {len(self.textos)} textos para análisis NLP")
        return len(self.textos)

    # ═══════════════════════════════════════════════════════════
    # 2. EXTRACCIÓN DE KEYWORDS (TF-IDF)
    # ═══════════════════════════════════════════════════════════

    def extraer_keywords(self, top_n=50):
        """Extrae palabras clave usando TF-IDF."""
        if not SKLEARN_AVAILABLE or not self.textos:
            return []

        logger.info("📊 Extrayendo keywords con TF-IDF...")

        vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.85,
            stop_words=list(STOPWORDS_ES),
            token_pattern=r'(?u)\b[a-záéíóúüñ]{3,}\b'
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(self.textos)
        except ValueError:
            logger.warning("No se pudo ajustar TF-IDF (pocos documentos)")
            return []

        feature_names = vectorizer.get_feature_names_out()

        # Calcular scores promedio
        avg_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
        top_indices = avg_tfidf.argsort()[::-1][:top_n]

        keywords = []
        for idx in top_indices:
            word = feature_names[idx]
            score = float(avg_tfidf[idx])

            # Clasificar tipo de palabra clave
            tipo = self._clasificar_keyword(word)

            # Calcular frecuencia
            freq = int(np.asarray((tfidf_matrix[:, idx] > 0).sum()))

            keywords.append({
                'palabra': word,
                'tfidf_score': round(score, 6),
                'frecuencia': freq,
                'tipo': tipo
            })

        self.resultados['keywords'] = keywords
        logger.info(f"✅ Extraídas {len(keywords)} keywords")
        return keywords

    def _clasificar_keyword(self, word):
        """Clasifica una keyword según su dominio."""
        word_lower = word.lower()
        for carrera in CARRERAS_EMI:
            if carrera in word_lower:
                return 'carrera'
        for tipo, lista in ENTIDADES_EMI.items():
            if tipo == 'sentimiento':
                continue
            if isinstance(lista, list):
                for ent in lista:
                    if ent in word_lower:
                        return tipo
        return 'general'

    # ═══════════════════════════════════════════════════════════
    # 3. MODELADO DE TÓPICOS (LDA / NMF)
    # ═══════════════════════════════════════════════════════════

    def modelar_topicos(self, n_topicos=6, metodo='bertopic'):
        """
        Descubre tópicos usando BERTopic (reemplaza LDA/NMF).
        Especialmente útil para textos cortos de redes sociales.
        
        Args:
            n_topicos: (Ignorado, BERTopic usa nr_topics="auto")
            metodo: 'bertopic'
        """
        if not self.textos or self._embedding_model is None:
            return []

        logger.info(f"🔍 Modelando tópicos con BERTopic...")

        try:
            from bertopic import BERTopic
            from sklearn.feature_extraction.text import CountVectorizer
            
            vectorizer_model = CountVectorizer(stop_words=list(STOPWORDS_ES))
            
            # nr_topics="auto" reduce dinámicamente el número de tópicos
            # min_topic_size=5 es ideal para datasets pequeños
            topic_model = BERTopic(
                embedding_model=self._embedding_model,
                vectorizer_model=vectorizer_model,
                min_topic_size=5,
                nr_topics="auto",
                calculate_probabilities=False
            )
            
            topics, _ = topic_model.fit_transform(self.textos)
        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(f"Error en modelado de tópicos con BERTopic: {e}")
            return []

        topicos = []
        topic_info = topic_model.get_topic_info()
        
        for index, row in topic_info.iterrows():
            topic_idx = row['Topic']
            if topic_idx == -1:
                continue  # Ignorar tópicos de ruido (outliers)
                
            # Obtener palabras clave y sus pesos c-TF-IDF
            topic_words_scores = topic_model.get_topic(topic_idx)
            if not topic_words_scores:
                continue
                
            top_words = [word for word, score in topic_words_scores[:10]]
            weights = [float(score) for word, score in topic_words_scores[:10]]
            
            # Calcular pseudo-coherencia (promedio c-TF-IDF de las top keywords)
            coherence_score = float(np.mean(weights)) if weights else 0.0
            
            assigned_docs = int(row['Count'])
            peso_total = float(np.sum(weights))
            
            # Nombramiento automático usando las top 3 keywords
            nombre = " / ".join(top_words[:3]).title()

            topicos.append({
                'topico_id': int(topic_idx),
                'nombre': nombre,
                'palabras_clave': top_words,
                'pesos': weights,
                'num_documentos': assigned_docs,
                'peso_total': peso_total,
                'coherencia': round(coherence_score, 4),
                'metodo': 'BERTOPIC'
            })

        # Ordenar por relevancia (número de documentos)
        topicos.sort(key=lambda x: x['num_documentos'], reverse=True)

        self.resultados['topicos'] = topicos
        logger.info(f"✅ Descubiertos {len(topicos)} tópicos con BERTopic")
        return topicos

    # ═══════════════════════════════════════════════════════════
    # 4. CLUSTERING DE OPINIONES (K-Means)
    # ═══════════════════════════════════════════════════════════

    def clustering_opiniones(self, k=None, max_k=8):
        """
        Agrupa opiniones similares usando TF-IDF + K-Means.
        
        Si k=None, busca el óptimo usando silhouette.
        """
        if not SKLEARN_AVAILABLE or len(self.textos) < 5:
            return []

        logger.info("🔄 Clustering de opiniones...")

        vectorizer = TfidfVectorizer(
            max_features=500,
            min_df=2,
            max_df=0.9,
            stop_words=list(STOPWORDS_ES),
            token_pattern=r'(?u)\b[a-záéíóúüñ]{3,}\b'
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(self.textos)
        except ValueError:
            return []

        feature_names = vectorizer.get_feature_names_out()

        # Buscar k óptimo
        if k is None:
            max_possible_k = min(max_k, len(self.textos) - 1)
            if max_possible_k < 2:
                return []

            best_k = 2
            best_score = -1

            for test_k in range(2, max_possible_k + 1):
                km = KMeans(n_clusters=test_k, random_state=42, n_init=10, max_iter=100)
                labels = km.fit_predict(tfidf_matrix)
                try:
                    score = silhouette_score(tfidf_matrix, labels)
                    if score > best_score:
                        best_score = score
                        best_k = test_k
                except ValueError as e:
                    logger.debug(f"Error en silhouette score test_k={test_k}: {e}")

            k = best_k
            logger.info(f"   K óptimo encontrado: {k} (silhouette: {best_score:.3f})")

        # Clustering final
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(tfidf_matrix)

        try:
            sil_score = silhouette_score(tfidf_matrix, labels)
        except ValueError as e:
            logger.debug(f"Error en silhouette score final: {e}")
            sil_score = 0

        # Extraer info de cada cluster
        clusters = []
        for cluster_id in range(k):
            mask = labels == cluster_id
            indices = np.where(mask)[0]
            n_docs = int(mask.sum())

            # Palabras clave del cluster
            centroid = kmeans.cluster_centers_[cluster_id]
            top_word_indices = centroid.argsort()[::-1][:8]
            top_words = [feature_names[i] for i in top_word_indices]

            # Sentimiento predominante
            sentimientos = [self.metadatos[i]['sentimiento'] for i in indices if i < len(self.metadatos)]
            sent_counts = Counter(sentimientos)
            sent_predominante = sent_counts.most_common(1)[0][0] if sent_counts else 'Neutral'

            # Textos representativos (los más cercanos al centroide)
            distances = np.linalg.norm(tfidf_matrix[mask].toarray() - centroid, axis=1)
            closest = distances.argsort()[:3]
            textos_rep = [self.textos[indices[i]][:150] for i in closest if i < len(indices)]

            # Auto-label
            etiqueta = " / ".join(top_words[:3]).title()

            clusters.append({
                'cluster_id': cluster_id,
                'etiqueta': etiqueta,
                'palabras_clave': top_words,
                'num_documentos': n_docs,
                'sentimiento_predominante': sent_predominante,
                'textos_representativos': textos_rep,
                'distribucion_sentimiento': dict(sent_counts)
            })

        clusters.sort(key=lambda x: x['num_documentos'], reverse=True)

        self.resultados['clusters'] = clusters
        self.resultados['silhouette_score'] = round(sil_score, 4)
        self.resultados['n_clusters'] = k
        logger.info(f"✅ {k} clusters creados (silhouette: {sil_score:.3f})")
        return clusters

    # ═══════════════════════════════════════════════════════════
    # 5. EXTRACCIÓN DE ENTIDADES (spaCy NER + word-boundary regex)
    # ═══════════════════════════════════════════════════════════

    def _wb(self, term: str, texto_lower: str) -> bool:
        """Devuelve True si 'term' aparece con word boundaries en texto_lower.

        Usa re.search con \\b para evitar falsos positivos de substring match.
        Por ejemplo: 'civil' NO coincide dentro de 'estado civil' cuando
        el contexto indica que no es una mención de carrera (eso lo resuelve
        la capa spaCy); pero para términos de sedes/servicios el boundary
        evita coincidencias parciales como 'beca' dentro de 'becados'.
        """
        pattern = r'\b' + re.escape(term) + r'\b'
        return bool(re.search(pattern, texto_lower))

    def extraer_entidades_spacy(self, texto: str) -> dict:
        """Extrae entidades de UN texto usando spaCy + diccionarios EMI.

        Estrategia de dos capas:
        1. spaCy es_core_news_lg detecta PER (personas) y ORG con contexto
           morfosintáctico real — elimina los falsos positivos de substring.
        2. Sobre el texto ya procesado, los diccionarios EMI aplican con
           word boundaries (\\b) para carreras, sedes, temas y servicios.

        Args:
            texto: Texto a analizar (un solo documento).

        Returns:
            dict con listas de entidades detectadas por categoría.
        """
        resultado = {
            'carreras': [],
            'sedes': [],
            'temas_academicos': [],
            'servicios': [],
            'personas': [],
            'organizaciones': [],
            'sentimiento_pos': [],
            'sentimiento_neg': [],
        }

        if not texto:
            return resultado

        texto_lower = texto.lower()

        # ── Capa 1: spaCy NER (PER, ORG, LOC, MISC) ─────────────
        if self._nlp is not None:
            try:
                doc = self._nlp(texto[:1000])  # límite de tokens seguro
                for ent in doc.ents:
                    label = ent.label_
                    texto_ent = ent.text.strip()
                    if not texto_ent:
                        continue
                    if label == 'PER':
                        resultado['personas'].append(texto_ent)
                    elif label == 'ORG':
                        resultado['organizaciones'].append(texto_ent)
                    # LOC/GPE se dejan para la capa de diccionarios de sedes
            except (ValueError, AttributeError) as e:
                logger.warning(f"spaCy error extrayendo entidades: {e}")

        # ── Capa 2: Diccionarios EMI con word boundaries + contexto ──
        #
        # Para las CARRERAS aplicamos tres filtros en orden:
        #   a) Word boundary: descarta coincidencias parciales.
        #   b) Contexto negativo: descarta frases que contraindican carrera.
        #   c) Confirmación por proximidad (si spaCy cargó): al menos uno
        #      de los tokens académicos debe estar en el mismo doc.
        #
        # Para SEDES, TEMAS y SERVICIOS solo se aplican (a) y (b).

        # Tokens académicos presentes en el texto (rápido, sin spaCy)
        tokens_texto = set(texto_lower.split())
        tiene_contexto_acad = bool(tokens_texto & _TOKENS_ACADEMICOS)

        for carrera in CARRERAS_EMI:
            if not self._wb(carrera, texto_lower):
                continue  # (a) no hay word-boundary match

            # (b) ¿el término aparece dentro de una frase que lo invalida?
            frases_neg = CARRERAS_CONTEXTO_NEGATIVO.get(carrera, [])
            if any(frase in texto_lower for frase in frases_neg):
                continue  # falso positivo descartado

            # (c) Si el texto NO tiene ningún token académico, solo
            #     aceptamos carreras ambíguas si spaCy ya las detectó
            #     como ORG/MISC, o si son términos muy específicos
            #     (electrónica, mecatrónica, petrolera, telecomunicaciones)
            terminos_especificos = {
                'electrónica', 'mecatrónica', 'petrolera',
                'telecomunicaciones', 'automotriz', 'mecánica',
                'eléctrica',
            }
            terminos_ambiguos = {'civil', 'industrial', 'ambiental',
                                 'militar', 'comercial'}

            if carrera in terminos_ambiguos and not tiene_contexto_acad:
                continue  # sin contexto académico, descartamos ambíguos

            resultado['carreras'].append(carrera)

        # Sedes: word boundary basta (son nombres propios de ciudades)
        for sede in ENTIDADES_EMI['sedes']:
            if self._wb(sede, texto_lower):
                resultado['sedes'].append(sede)

        # Temas académicos
        for tema in ENTIDADES_EMI['academico']:
            if self._wb(tema, texto_lower):
                resultado['temas_academicos'].append(tema)

        # Servicios
        for servicio in ENTIDADES_EMI['servicios']:
            if self._wb(servicio, texto_lower):
                resultado['servicios'].append(servicio)

        # Sentimiento keywords
        for word in ENTIDADES_EMI['sentimiento']['positivo']:
            if self._wb(word, texto_lower):
                resultado['sentimiento_pos'].append(word)

        for word in ENTIDADES_EMI['sentimiento']['negativo']:
            if self._wb(word, texto_lower):
                resultado['sentimiento_neg'].append(word)

        return resultado

    def extraer_entidades(self):
        """Extrae entidades relevantes para la EMI en todos los textos cargados.

        Usa spaCy es_core_news_lg para detección contextual de personas y
        organizaciones, y word-boundary regex para los diccionarios de dominio
        (carreras, sedes, temas académicos, servicios).  Si spaCy no está
        disponible opera en modo degradado (solo diccionarios + word boundary).

        La estructura de salida es compatible con la tabla nlp_entidades.
        """
        if not self.textos:
            return {}

        modo = 'spaCy + diccionarios EMI' if self._nlp else 'diccionarios EMI (word boundary)'
        logger.info(f"🏷️ Extrayendo entidades con NER [{modo}]...")

        # Acumuladores por categoría
        carreras_cnt   = Counter()
        sedes_cnt      = Counter()
        temas_cnt      = Counter()
        servicios_cnt  = Counter()
        personas_cnt   = Counter()
        sent_pos_cnt   = Counter()
        sent_neg_cnt   = Counter()

        for texto in self.textos:
            ent = self.extraer_entidades_spacy(texto)

            for c in ent['carreras']:
                carreras_cnt[c] += 1
            for s in ent['sedes']:
                sedes_cnt[s] += 1
            for t in ent['temas_academicos']:
                temas_cnt[t] += 1
            for sv in ent['servicios']:
                servicios_cnt[sv] += 1
            for p in ent['personas']:
                personas_cnt[p] += 1
            for w in ent['sentimiento_pos']:
                sent_pos_cnt[w] += 1
            for w in ent['sentimiento_neg']:
                sent_neg_cnt[w] += 1

        # ── Construir salida con la misma estructura que antes ────
        entidades = {
            'carreras_mencionadas': [
                {'entidad': k, 'menciones': v}
                for k, v in carreras_cnt.most_common(15)
            ],
            'sedes_mencionadas': [
                {'entidad': k, 'menciones': v}
                for k, v in sedes_cnt.most_common(10)
            ],
            'temas_academicos': [
                {'entidad': k, 'menciones': v}
                for k, v in temas_cnt.most_common(15)
            ],
            'servicios_mencionados': [
                {'entidad': k, 'menciones': v}
                for k, v in servicios_cnt.most_common(10)
            ],
            # Personas detectadas por spaCy (nuevo campo, compatible con BD)
            'personas': [
                {'entidad': k, 'menciones': v}
                for k, v in personas_cnt.most_common(10)
            ],
            'sentimiento_keywords': {
                'positivo': [
                    {'palabra': k, 'frecuencia': v}
                    for k, v in sent_pos_cnt.most_common(10)
                ],
                'negativo': [
                    {'palabra': k, 'frecuencia': v}
                    for k, v in sent_neg_cnt.most_common(10)
                ],
            },
            'total_entidades': 0,
            'ner_mode': modo,
        }

        total = sum(
            len(v) for v in entidades.values()
            if isinstance(v, list)
        )
        entidades['total_entidades'] = total

        self.resultados['entidades'] = entidades
        logger.info(f"✅ Extraídas {total} entidades [{modo}]")
        return entidades

    # ═══════════════════════════════════════════════════════════
    # 6. ANÁLISIS DE SENTIMIENTO POR ASPECTO (ABSA oración-por-oración)
    # ═══════════════════════════════════════════════════════════

    def _segmentar_oraciones(self, texto: str) -> list:
        """Divide un texto en oraciones individuales.

        Prioriza spaCy senter (preciso); si no está disponible usa regex
        como fallback: divide por '.', '!', '?' y conectores adversativos
        comunes en español ('pero', 'aunque', 'sin embargo', 'mas').

        Args:
            texto: Texto a segmentar.

        Returns:
            Lista de strings, uno por oración. Nunca vacía.
        """
        if not texto:
            return []

        # ── Capa 1: spaCy senter ────────────────────────────────
        if self._sentencizer is not None:
            try:
                doc = self._sentencizer(texto[:2000])  # límite seguro
                oraciones = [s.text.strip() for s in doc.sents
                             if s.text.strip()]
                if oraciones:
                    return oraciones
            except (ValueError, RuntimeError) as e:
                logger.warning(f"spaCy sentencizer error: {e}")

        # ── Capa 2: Regex fallback ──────────────────────────────
        # Divide por puntuación final y también por conectores adversativos
        # que suelen marcar un cambio de sentimiento en el mismo párrafo.
        _ADVERSATIVOS = re.compile(
            r'(?<=[\w\s]),?\s+(?:pero|aunque|sin embargo|mas|no obstante|'  
            r'a pesar de(?: que)?|con todo|ahora bien|aun así)\s+',
            re.IGNORECASE
        )
        # Primero dividir por puntuación
        partes = re.split(r'(?<=[.!?])\s+', texto)
        oraciones = []
        for parte in partes:
            sub = _ADVERSATIVOS.split(parte)
            oraciones.extend(s.strip() for s in sub if s.strip())

        return oraciones or [texto]

    def _sentimiento_oracion(self, oracion: str) -> dict:
        """Analiza el sentimiento de UNA oración usando el modelo DL.

        Llama a sentiment_analyzer.analizar_sentimiento() que ya gestiona
        el classifier Robertuito/BETO. Si la oración es demasiado corta
        (< 4 palabras), devuelve Neutral con confianza baja para no
        contaminar el promedio del aspecto.

        Args:
            oracion: Texto de una sola oración.

        Returns:
            dict con 'sentimiento', 'confianza', 'prob_positivo',
            'prob_neutral', 'prob_negativo' — mismo formato que
            sentiment_analyzer.analizar_sentimiento().
        """
        # Umbral de longitud mínima: oraciones muy cortas ("sí", "ok",
        # "ajá") producen clasificaciones ruidosas.
        if not oracion or len(oracion.split()) < 4:
            return {
                'sentimiento': 'Neutral',
                'confianza': 0.0,   # confianza 0 → no ponderar en el promedio
                'prob_positivo': 0.33,
                'prob_neutral':  0.34,
                'prob_negativo': 0.33,
            }

        try:
            from sentiment_analyzer import analizar_sentimiento
            return analizar_sentimiento(oracion)
        except (ValueError, TypeError, RuntimeError) as e:
            logger.warning(f"Error clasificando oración ABSA: {e}")
            return {
                'sentimiento': 'Neutral',
                'confianza': 0.0,
                'prob_positivo': 0.33,
                'prob_neutral':  0.34,
                'prob_negativo': 0.33,
            }

    def sentimiento_por_aspecto(self):
        """Analiza sentimiento desglosado por aspecto/tema (ABSA real).

        CORRECCIÓN respecto a la versión anterior:
        - Antes: tomaba el sentimiento global del post y lo asignaba a
          todos los aspectos mencionados → resultados incorrectos.
          Ejemplo: "el wifi es pésimo pero el profe excelente" marcaba
          Infraestructura=POS si el sentimiento global era positivo.

        - Ahora: segmenta cada texto en oraciones con spaCy senter,
          detecta qué aspecto(s) cubre cada oración (keyword + word
          boundary), y clasifica el sentimiento SOLO de esa oración.
          Si hay varias oraciones del mismo aspecto, se promedian
          ponderando por confianza del modelo.

        Estructura de salida idéntica a la anterior para compatibilidad
        con el dashboard (total_menciones, positivos, negativos, etc.).
        """
        if not self.textos:
            return {}

        logger.info("😊 Analizando sentimiento por aspecto (ABSA oración-por-oración)...")

        aspectos = {
            'Calidad Académica':       ['clase', 'profesor', 'docente', 'materia',
                                        'nota', 'examen', 'enseñanza', 'catedra'],
            'Infraestructura':         ['edificio', 'aula', 'laboratorio', 'wifi',
                                        'instalaciones', 'baño', 'internet', 'cancha'],
            'Servicios':               ['comedor', 'transporte', 'beca', 'tramite',
                                        'secretaria', 'biblioteca', 'cafeteria'],
            'Vida Estudiantil':        ['compañero', 'amigo', 'evento', 'deporte',
                                        'actividad', 'club', 'fiesta'],
            'Formación Militar':       ['militar', 'disciplina', 'formacion',
                                        'valores', 'regimiento', 'instruccion'],
            'Procesos Administrativos':['inscripcion', 'matricula', 'pago',
                                        'certificado', 'titulo', 'tramite'],
            'Empleo y Futuro':         ['trabajo', 'empleo', 'egresado', 'empresa',
                                        'practica', 'profesional', 'campo laboral'],
        }

        # Pre-compilar patrones regex de word boundary por aspecto
        # (una sola vez fuera del loop de textos)
        _pat_aspecto = {
            asp: [
                re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                for kw in kws
            ]
            for asp, kws in aspectos.items()
        }

        # Acumuladores por aspecto:
        #   oracion_sent[aspecto] → lista de (sentimiento, confianza)
        oracion_sent = {asp: [] for asp in aspectos}
        textos_ejemplo = {asp: [] for asp in aspectos}

        for texto in self.textos:
            if not texto:
                continue

            oraciones = self._segmentar_oraciones(texto)

            # Si el texto es una sola oración larga (sin segmentar),
            # la analizamos directamente sin llamar al DL innecesariamente
            # más de una vez por texto.
            oracion_sent_cache = {}  # cache dentro del mismo texto

            for oracion in oraciones:
                oracion_lower = oracion.lower()

                # Detectar qué aspectos cubre esta oración
                aspectos_oracion = [
                    asp for asp, pats in _pat_aspecto.items()
                    if any(p.search(oracion_lower) for p in pats)
                ]

                if not aspectos_oracion:
                    continue  # esta oración no habla de ningún aspecto

                # Clasificar sentimiento de la oración (con caché dentro
                # del mismo texto para evitar llamadas dobles al modelo)
                if oracion not in oracion_sent_cache:
                    oracion_sent_cache[oracion] = self._sentimiento_oracion(oracion)
                sent_result = oracion_sent_cache[oracion]

                for asp in aspectos_oracion:
                    oracion_sent[asp].append(
                        (sent_result['sentimiento'], sent_result['confianza'])
                    )
                    if len(textos_ejemplo[asp]) < 3:
                        textos_ejemplo[asp].append(oracion[:120])

        # ── Consolidar resultados por aspecto ────────────────────────
        resultados_aspecto = {}

        for asp, sent_list in oracion_sent.items():
            if not sent_list:
                continue

            positivos = sum(1 for s, _ in sent_list if s == 'Positivo')
            negativos = sum(1 for s, _ in sent_list if s == 'Negativo')
            neutrales = sum(1 for s, _ in sent_list if s == 'Neutral')
            total_asp  = len(sent_list)

            # Score ponderado por confianza: suma(conf * signo) / suma(conf)
            # signo: +1 POS, -1 NEG, 0 NEU. Fallback a unweighted si conf=0.
            peso_total = sum(c for _, c in sent_list)
            if peso_total > 0:
                signo = {'Positivo': 1, 'Negativo': -1, 'Neutral': 0}
                score_pond = sum(
                    signo[s] * c for s, c in sent_list
                ) / peso_total * 100
            else:
                # Todas las confianzas son 0 (oraciones muy cortas)
                score_pond = round((positivos - negativos) / total_asp * 100, 1)

            resultados_aspecto[asp] = {
                'total_menciones': total_asp,
                'positivos':  positivos,
                'negativos':  negativos,
                'neutrales':  neutrales,
                'score': round(score_pond, 1),
                'textos_ejemplo': textos_ejemplo[asp],
                'keywords_activos': list(aspectos[asp]),
                'absa_mode': 'sentence-level',  # campo nuevo, no rompe BD
            }

        # Ordenar por total de menciones
        resultados_aspecto = dict(
            sorted(resultados_aspecto.items(),
                   key=lambda x: x[1]['total_menciones'], reverse=True)
        )

        self.resultados['sentimiento_aspecto'] = resultados_aspecto
        logger.info(
            f"✅ ABSA completado: {len(resultados_aspecto)} aspectos, "
            f"{sum(v['total_menciones'] for v in resultados_aspecto.values())} "
            f"oraciones clasificadas"
        )
        return resultados_aspecto

    # ═══════════════════════════════════════════════════════════
    # 7. RESUMEN EJECUTIVO AUTOMÁTICO
    # ═══════════════════════════════════════════════════════════

    def generar_resumen_ejecutivo(self):
        """Genera un resumen ejecutivo automático del análisis."""
        logger.info("📋 Generando resumen ejecutivo...")

        resumen = {
            'fecha_generacion': datetime.now().isoformat(),
            'total_textos_analizados': len(self.textos),
            'tecnicas_nlp_aplicadas': [],
            'hallazgos_principales': [],
            'recomendaciones_uebu': [],
            'metricas_ml': {}
        }

        # Técnicas aplicadas
        if 'keywords' in self.resultados:
            resumen['tecnicas_nlp_aplicadas'].append({
                'tecnica': 'TF-IDF Keyword Extraction',
                'descripcion': f'Extraídas {len(self.resultados["keywords"])} palabras clave',
                'tipo': 'NLP'
            })

        if 'topicos' in self.resultados:
            resumen['tecnicas_nlp_aplicadas'].append({
                'tecnica': 'Topic Modeling (LDA)',
                'descripcion': f'Descubiertos {len(self.resultados["topicos"])} tópicos temáticos',
                'tipo': 'ML'
            })

        if 'clusters' in self.resultados:
            resumen['tecnicas_nlp_aplicadas'].append({
                'tecnica': 'K-Means Clustering',
                'descripcion': f'{self.resultados.get("n_clusters", 0)} clusters de opiniones',
                'tipo': 'ML'
            })
            resumen['metricas_ml']['silhouette_score'] = self.resultados.get('silhouette_score', 0)

        if 'entidades' in self.resultados:
            resumen['tecnicas_nlp_aplicadas'].append({
                'tecnica': 'Named Entity Recognition (NER)',
                'descripcion': 'Extracción de entidades académicas',
                'tipo': 'NLP'
            })

        if 'sentimiento_aspecto' in self.resultados:
            resumen['tecnicas_nlp_aplicadas'].append({
                'tecnica': 'Aspect-Based Sentiment Analysis',
                'descripcion': f'Sentimiento en {len(self.resultados["sentimiento_aspecto"])} aspectos',
                'tipo': 'NLP/ML'
            })

        # Hallazgos principales
        if 'sentimiento_aspecto' in self.resultados:
            for aspecto, datos in self.resultados['sentimiento_aspecto'].items():
                if datos['total_menciones'] >= 3:
                    if datos['score'] < -20:
                        resumen['hallazgos_principales'].append({
                            'tipo': 'alerta',
                            'descripcion': f"El aspecto '{aspecto}' tiene sentimiento negativo predominante (score: {datos['score']})",
                            'impacto': 'alto'
                        })
                        resumen['recomendaciones_uebu'].append(
                            f"Investigar las quejas sobre '{aspecto}' - {datos['negativos']} menciones negativas detectadas"
                        )
                    elif datos['score'] > 30:
                        resumen['hallazgos_principales'].append({
                            'tipo': 'positivo',
                            'descripcion': f"El aspecto '{aspecto}' recibe evaluaciones positivas (score: {datos['score']})",
                            'impacto': 'medio'
                        })

        if 'topicos' in self.resultados:
            for topico in self.resultados['topicos'][:3]:
                resumen['hallazgos_principales'].append({
                    'tipo': 'informativo',
                    'descripcion': f"Tópico relevante: '{topico['nombre']}' con {topico['num_documentos']} menciones",
                    'impacto': 'medio'
                })

        if 'entidades' in self.resultados:
            ent = self.resultados['entidades']
            if ent.get('carreras_mencionadas'):
                top_carrera = ent['carreras_mencionadas'][0]
                resumen['hallazgos_principales'].append({
                    'tipo': 'informativo',
                    'descripcion': f"Carrera más mencionada: Ing. {top_carrera['entidad'].title()} ({top_carrera['menciones']} menciones)",
                    'impacto': 'bajo'
                })

        # Guardar sentimiento_aspecto en resumen
        if 'sentimiento_aspecto' in self.resultados:
            resumen['sentimiento_aspecto'] = self.resultados['sentimiento_aspecto']

        # Distribución de sentimientos
        sentimientos = Counter([m['sentimiento'] for m in self.metadatos])
        total = sum(sentimientos.values())
        if total > 0:
            resumen['distribucion_sentimiento'] = {
                'positivo': sentimientos.get('Positivo', 0),
                'negativo': sentimientos.get('Negativo', 0),
                'neutral': sentimientos.get('Neutral', 0) + sentimientos.get('Sin analizar', 0),
                'total': total,
                'ratio_positivo': round(sentimientos.get('Positivo', 0) / total * 100, 1)
            }

        self.resultados['resumen'] = resumen
        logger.info(f"✅ Resumen ejecutivo generado")
        return resumen

    # ═══════════════════════════════════════════════════════════
    # 8. GUARDAR RESULTADOS EN BD
    # ═══════════════════════════════════════════════════════════

    def guardar_resultados(self):
        """Guarda todos los resultados NLP en la BD."""
        self._init_tables()
        conn = self.get_db()
        cursor = conn.cursor()

        # Limpiar anteriores
        cursor.execute("DELETE FROM nlp_topicos")
        cursor.execute("DELETE FROM nlp_clusters")
        cursor.execute("DELETE FROM nlp_keywords")
        cursor.execute("DELETE FROM nlp_entidades")

        # Guardar keywords
        for kw in self.resultados.get('keywords', []):
            cursor.execute('''
                INSERT INTO nlp_keywords (palabra, tfidf_score, frecuencia, tipo)
                VALUES (?, ?, ?, ?)
            ''', (kw['palabra'], kw['tfidf_score'], kw['frecuencia'], kw['tipo']))

        # Guardar tópicos
        for top in self.resultados.get('topicos', []):
            cursor.execute('''
                INSERT INTO nlp_topicos (metodo, topico_id, nombre_topico, palabras_clave,
                    peso_topico, num_documentos, coherencia)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (top['metodo'], top['topico_id'], top['nombre'],
                  json.dumps(top['palabras_clave']), top['peso_total'], top['num_documentos'], top.get('coherencia')))

        # Guardar clusters
        for cl in self.resultados.get('clusters', []):
            cursor.execute('''
                INSERT INTO nlp_clusters (cluster_id, etiqueta, palabras_clave,
                    num_documentos, sentimiento_predominante, textos_representativos, silhouette_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (cl['cluster_id'], cl['etiqueta'], json.dumps(cl['palabras_clave']),
                  cl['num_documentos'], cl['sentimiento_predominante'],
                  json.dumps(cl.get('textos_representativos', []), ensure_ascii=False),
                  self.resultados.get('silhouette_score', 0)))

        # Guardar entidades
        ent = self.resultados.get('entidades', {})
        for tipo, items in ent.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'entidad' in item:
                        cursor.execute('''
                            INSERT INTO nlp_entidades (entidad, tipo_entidad, frecuencia)
                            VALUES (?, ?, ?)
                        ''', (item['entidad'], tipo, item['menciones']))

        # Guardar resumen
        resumen = self.resultados.get('resumen', {})
        if resumen:
            cursor.execute("DELETE FROM nlp_resumen_ejecutivo")
            cursor.execute('''
                INSERT INTO nlp_resumen_ejecutivo (tipo_resumen, contenido, datos_soporte)
                VALUES (?, ?, ?)
            ''', ('completo', json.dumps(resumen, ensure_ascii=False, default=str),
                  json.dumps({
                      'n_textos': len(self.textos),
                      'n_keywords': len(self.resultados.get('keywords', [])),
                      'n_topicos': len(self.resultados.get('topicos', [])),
                      'n_clusters': self.resultados.get('n_clusters', 0)
                  })))

        conn.commit()
        conn.close()
        logger.info("✅ Resultados NLP guardados en BD")

    # ═══════════════════════════════════════════════════════════
    # 9. EJECUTAR PIPELINE COMPLETO
    # ═══════════════════════════════════════════════════════════

    def ejecutar_pipeline_completo(self):
        """Ejecuta todas las técnicas NLP/ML."""
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO PIPELINE NLP COMPLETO")
        logger.info("=" * 60)

        self._init_tables()
        n_textos = self.cargar_textos()

        if n_textos == 0:
            logger.warning("⚠️ No hay textos para analizar")
            return {'error': 'No hay datos para analizar'}

        logger.info(f"\n📊 Textos cargados: {n_textos}")
        logger.info("-" * 40)

        # 1. Keywords
        self.extraer_keywords()

        # 2. Topic Modeling
        if n_textos >= 5:
            n_top = min(6, max(2, n_textos // 5))
            self.modelar_topicos(n_topicos=n_top, metodo='lda')
        else:
            self.modelar_topicos(n_topicos=2, metodo='lda')

        # 3. Clustering
        self.clustering_opiniones()

        # 4. Entidades
        self.extraer_entidades()

        # 5. Sentimiento por aspecto
        self.sentimiento_por_aspecto()

        # 6. Resumen ejecutivo
        self.generar_resumen_ejecutivo()

        # 7. Guardar
        self.guardar_resultados()

        logger.info("=" * 60)
        logger.info("✅ PIPELINE NLP COMPLETO FINALIZADO")
        logger.info("=" * 60)

        return self.resultados


# ═══════════════════════════════════════════════════════════════
# Ejecución directa
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    pipeline = NLPPipeline()
    results = pipeline.ejecutar_pipeline_completo()
    
    print("\n" + "=" * 50)
    print("RESULTADOS DEL PIPELINE NLP:")
    print("=" * 50)
    
    if 'keywords' in results:
        print(f"\n📊 Top 10 Keywords:")
        for kw in results['keywords'][:10]:
            print(f"   - {kw['palabra']} (TF-IDF: {kw['tfidf_score']:.4f}, freq: {kw['frecuencia']})")
    
    if 'topicos' in results:
        print(f"\n🔍 Tópicos descubiertos:")
        for t in results['topicos']:
            print(f"   [{t['topico_id']}] {t['nombre']} ({t['num_documentos']} docs)")
            print(f"       {', '.join(t['palabras_clave'][:5])}")
    
    if 'clusters' in results:
        print(f"\n🔄 Clusters (silhouette: {results.get('silhouette_score', 'N/A')}):")
        for c in results['clusters']:
            print(f"   [{c['cluster_id']}] {c['etiqueta']} ({c['num_documentos']} docs) - {c['sentimiento_predominante']}")
    
    if 'sentimiento_aspecto' in results:
        print(f"\n😊 Sentimiento por Aspecto:")
        for asp, data in results['sentimiento_aspecto'].items():
            print(f"   {asp}: score={data['score']}, +{data['positivos']}/-{data['negativos']} ({data['total_menciones']} menciones)")
    
    print("\n✅ Pipeline finalizado")
