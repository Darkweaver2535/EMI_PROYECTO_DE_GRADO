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


class NLPPipeline:
    """
    Pipeline completo de NLP para análisis de datos OSINT.
    
    Implementa múltiples técnicas de ML y NLP:
    - TF-IDF keyword extraction
    - Topic modeling (LDA, NMF)
    - K-Means clustering
    - Entity recognition (rule-based NER)
    - Aspect-based sentiment patterns
    - Automatic summarization
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.textos = []
        self.metadatos = []
        self.resultados = {}

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
        except:
            pass

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

    def modelar_topicos(self, n_topicos=6, metodo='lda'):
        """
        Descubre tópicos usando LDA o NMF.
        
        Args:
            n_topicos: Número de tópicos a descubrir
            metodo: 'lda' o 'nmf'
        """
        if not SKLEARN_AVAILABLE or not self.textos:
            return []

        logger.info(f"🔍 Modelando {n_topicos} tópicos con {metodo.upper()}...")

        if metodo == 'lda':
            vectorizer = CountVectorizer(
                max_features=1000,
                min_df=2,
                max_df=0.85,
                stop_words=list(STOPWORDS_ES),
                token_pattern=r'(?u)\b[a-záéíóúüñ]{3,}\b'
            )
        else:
            vectorizer = TfidfVectorizer(
                max_features=1000,
                min_df=2,
                max_df=0.85,
                stop_words=list(STOPWORDS_ES),
                token_pattern=r'(?u)\b[a-záéíóúüñ]{3,}\b'
            )

        try:
            matrix = vectorizer.fit_transform(self.textos)
        except ValueError:
            return []

        feature_names = vectorizer.get_feature_names_out()

        if metodo == 'lda':
            model = LatentDirichletAllocation(
                n_components=n_topicos,
                random_state=42,
                max_iter=20,
                learning_method='online'
            )
        else:
            model = NMF(
                n_components=n_topicos,
                random_state=42,
                max_iter=200
            )

        try:
            doc_topics = model.fit_transform(matrix)
        except Exception as e:
            logger.error(f"Error en modelado de tópicos: {e}")
            return []

        topicos = []
        for topic_idx in range(n_topicos):
            top_word_indices = model.components_[topic_idx].argsort()[::-1][:10]
            top_words = [feature_names[i] for i in top_word_indices]
            weights = [float(model.components_[topic_idx][i]) for i in top_word_indices]

            # Contar documentos asignados a este tópico
            assigned_docs = int(np.sum(np.argmax(doc_topics, axis=1) == topic_idx))

            # Auto-naming del tópico
            nombre = self._auto_name_topic(top_words)

            topicos.append({
                'topico_id': topic_idx,
                'nombre': nombre,
                'palabras_clave': top_words,
                'pesos': weights,
                'num_documentos': assigned_docs,
                'peso_total': float(np.sum(model.components_[topic_idx])),
                'metodo': metodo.upper()
            })

        # Ordenar por relevancia
        topicos.sort(key=lambda x: x['num_documentos'], reverse=True)

        self.resultados['topicos'] = topicos
        logger.info(f"✅ Descubiertos {len(topicos)} tópicos")
        return topicos

    def _auto_name_topic(self, words):
        """Genera nombre automático para un tópico basado en sus palabras."""
        topic_names = {
            'carrera': 'Carreras e Ingeniería',
            'clase': 'Vida Académica',
            'profesor': 'Docentes',
            'examen': 'Evaluaciones',
            'beca': 'Becas y Ayudas',
            'matricula': 'Inscripciones',
            'inscripcion': 'Proceso de Inscripción',
            'laboratorio': 'Laboratorios',
            'militar': 'Formación Militar',
            'emi': 'Institución EMI',
            'estudiante': 'Comunidad Estudiantil',
            'graduacion': 'Graduaciones',
            'titulo': 'Titulación',
            'infraestructura': 'Infraestructura',
            'comedor': 'Servicios Universitarios',
            'transporte': 'Transporte',
            'deporte': 'Deportes',
            'tecnologia': 'Tecnología',
            'convocatoria': 'Convocatorias',
            'evento': 'Eventos',
            'civil': 'Ingeniería Civil',
            'sistemas': 'Ingeniería de Sistemas',
            'industrial': 'Ingeniería Industrial',
        }

        for word in words[:5]:
            if word in topic_names:
                return topic_names[word]

        # Si no se encuentra, usar las primeras 3 palabras
        return ' / '.join(words[:3]).title()

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
                except:
                    pass

            k = best_k
            logger.info(f"   K óptimo encontrado: {k} (silhouette: {best_score:.3f})")

        # Clustering final
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(tfidf_matrix)

        try:
            sil_score = silhouette_score(tfidf_matrix, labels)
        except:
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
            etiqueta = self._auto_name_topic(top_words)

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
    # 5. EXTRACCIÓN DE ENTIDADES (NER basado en reglas)
    # ═══════════════════════════════════════════════════════════

    def extraer_entidades(self):
        """Extrae entidades relevantes para la EMI."""
        if not self.textos:
            return {}

        logger.info("🏷️ Extrayendo entidades...")

        entidades = {
            'carreras_mencionadas': Counter(),
            'sedes_mencionadas': Counter(),
            'temas_academicos': Counter(),
            'servicios_mencionados': Counter(),
            'sentimiento_keywords': {'positivo': Counter(), 'negativo': Counter()},
            'personas': [],
            'total_entidades': 0
        }

        for texto in self.textos:
            texto_lower = texto.lower() if texto else ''

            for carrera in CARRERAS_EMI:
                if carrera in texto_lower:
                    entidades['carreras_mencionadas'][carrera] += 1

            for sede in ENTIDADES_EMI['sedes']:
                if sede in texto_lower:
                    entidades['sedes_mencionadas'][sede] += 1

            for tema in ENTIDADES_EMI['academico']:
                if tema in texto_lower:
                    entidades['temas_academicos'][tema] += 1

            for servicio in ENTIDADES_EMI['servicios']:
                if servicio in texto_lower:
                    entidades['servicios_mencionados'][servicio] += 1

            for word in ENTIDADES_EMI['sentimiento']['positivo']:
                if word in texto_lower:
                    entidades['sentimiento_keywords']['positivo'][word] += 1

            for word in ENTIDADES_EMI['sentimiento']['negativo']:
                if word in texto_lower:
                    entidades['sentimiento_keywords']['negativo'][word] += 1

        # Convertir Counters a listas ordenadas
        entidades['carreras_mencionadas'] = [
            {'entidad': k, 'menciones': v} for k, v in entidades['carreras_mencionadas'].most_common(15)
        ]
        entidades['sedes_mencionadas'] = [
            {'entidad': k, 'menciones': v} for k, v in entidades['sedes_mencionadas'].most_common(10)
        ]
        entidades['temas_academicos'] = [
            {'entidad': k, 'menciones': v} for k, v in entidades['temas_academicos'].most_common(15)
        ]
        entidades['servicios_mencionados'] = [
            {'entidad': k, 'menciones': v} for k, v in entidades['servicios_mencionados'].most_common(10)
        ]
        entidades['sentimiento_keywords'] = {
            'positivo': [{'palabra': k, 'frecuencia': v} for k, v in
                         entidades['sentimiento_keywords']['positivo'].most_common(10)],
            'negativo': [{'palabra': k, 'frecuencia': v} for k, v in
                         entidades['sentimiento_keywords']['negativo'].most_common(10)]
        }

        total = sum(len(v) if isinstance(v, list) else 0 for v in entidades.values())
        entidades['total_entidades'] = total

        self.resultados['entidades'] = entidades
        logger.info(f"✅ Extraídas {total} entidades")
        return entidades

    # ═══════════════════════════════════════════════════════════
    # 6. ANÁLISIS DE SENTIMIENTO POR ASPECTO
    # ═══════════════════════════════════════════════════════════

    def sentimiento_por_aspecto(self):
        """Analiza sentimiento desglosado por aspecto/tema."""
        if not self.textos or not self.metadatos:
            return {}

        logger.info("😊 Analizando sentimiento por aspecto...")

        aspectos = {
            'Calidad Académica': ['clase', 'profesor', 'docente', 'materia', 'nota', 'examen', 'enseñanza'],
            'Infraestructura': ['edificio', 'aula', 'laboratorio', 'wifi', 'instalaciones', 'baño', 'internet'],
            'Servicios': ['comedor', 'transporte', 'beca', 'tramite', 'secretaria', 'biblioteca'],
            'Vida Estudiantil': ['compañero', 'amigo', 'evento', 'deporte', 'actividad', 'club'],
            'Formación Militar': ['militar', 'disciplina', 'formacion', 'valores', 'regimiento'],
            'Procesos Administrativos': ['inscripcion', 'matricula', 'pago', 'certificado', 'titulo'],
            'Empleo y Futuro': ['trabajo', 'empleo', 'egresado', 'empresa', 'practica', 'profesional'],
        }

        resultados_aspecto = {}

        for aspecto, keywords in aspectos.items():
            positivos = 0
            negativos = 0
            neutrales = 0
            total_asp = 0
            textos_ejemplo = []

            for i, texto in enumerate(self.textos):
                texto_lower = texto.lower() if texto else ''
                if any(kw in texto_lower for kw in keywords):
                    total_asp += 1
                    sent = self.metadatos[i]['sentimiento'] if i < len(self.metadatos) else 'Neutral'
                    if sent == 'Positivo':
                        positivos += 1
                    elif sent == 'Negativo':
                        negativos += 1
                    else:
                        neutrales += 1
                    if len(textos_ejemplo) < 3:
                        textos_ejemplo.append(texto[:120])

            if total_asp > 0:
                score = round((positivos - negativos) / total_asp * 100, 1)
                resultados_aspecto[aspecto] = {
                    'total_menciones': total_asp,
                    'positivos': positivos,
                    'negativos': negativos,
                    'neutrales': neutrales,
                    'score': score,
                    'textos_ejemplo': textos_ejemplo,
                    'keywords_activos': keywords
                }

        # Ordenar por menciones
        resultados_aspecto = dict(
            sorted(resultados_aspecto.items(), key=lambda x: x[1]['total_menciones'], reverse=True)
        )

        self.resultados['sentimiento_aspecto'] = resultados_aspecto
        logger.info(f"✅ Analizado sentimiento en {len(resultados_aspecto)} aspectos")
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
                    peso_topico, num_documentos)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (top['metodo'], top['topico_id'], top['nombre'],
                  json.dumps(top['palabras_clave']), top['peso_total'], top['num_documentos']))

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
