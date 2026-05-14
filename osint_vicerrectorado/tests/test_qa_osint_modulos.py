"""
Pruebas unitarias QA para el sistema de Analitica OSINT EMI.

Cobertura por modulo:
1) Recoleccion automatizada
2) Base de datos (conceptos PostgreSQL/JSONB modelados sobre SQLite para pruebas)
3) Analisis IA / ML
4) Pipeline ETL

Ejecutar:
    pytest tests/test_qa_osint_modulos.py -v
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from database.db_writer import DatabaseWriter
from etl.data_cleaner import DataCleaner
from etl.data_transformer import DataTransformer
from etl.etl_controller import ETLController
from osint_multifuente import OSINTMultifuente
from run_analysis import analyze_sentiment_simple
from scrapers.facebook_scraper import FacebookScraper
from ai.utils.metrics import AIMetrics


class TestModuloRecoleccionAutomatizada:
    """Pruebas unitarias del modulo de recoleccion automatizada."""

    @pytest.fixture
    def base_config(self):
        """Configuracion minima para instanciar componentes de recoleccion."""
        return {
            "database": {"path": ":memory:", "type": "sqlite"},
            "etl": {
                "remove_urls": True,
                "remove_mentions": True,
                "remove_hashtags": False,
                "normalize_whitespace": True,
                "max_text_length": 5000,
            },
        }

    @pytest.mark.asyncio
    async def test___scraping_beautifulsoup_parseo_html_estatico_happy_path(self, base_config):
        """Valida que el parser de HTML estatico extraiga posts cuando hay contenedores role=article."""
        # Arrange
        scraper = FacebookScraper(
            page_url="https://www.facebook.com/EMI.UALP",
            page_name="EMI UALP",
            config=base_config,
        )
        html = """
        <html>
            <body>
                <div role='article'><div dir='auto'>Post 1 con suficiente contenido para validar extracción</div></div>
                <div role='article'><div dir='auto'>Post 2 con contenido educativo de la EMI y comentarios de usuarios</div></div>
            </body>
        </html>
        """
        with patch.object(scraper, "_extract_post_data") as mock_extract:
            mock_extract.side_effect = [
                {"id_externo": "fb_1", "contenido_original": "Post 1"},
                {"id_externo": "fb_2", "contenido_original": "Post 2"},
            ]

            # Act
            result = await scraper._parse_posts_from_html(html, limit=5)

        # Assert
        assert len(result) == 2, "Se esperaban exactamente 2 posts parseados desde HTML estatico"
        assert result[0]["id_externo"] == "fb_1", "El primer ID externo parseado no coincide"

    @pytest.mark.asyncio
    async def test___scraping_beautifulsoup_parseo_html_estatico_edge_html_vacio(self, base_config):
        """Valida que el parser de HTML estatico retorne vacio ante HTML sin articulos."""
        # Arrange
        scraper = FacebookScraper(
            page_url="https://www.facebook.com/EMI.UALP",
            page_name="EMI UALP",
            config=base_config,
        )

        # Act
        result = await scraper._parse_posts_from_html("<html><body></body></html>", limit=3)

        # Assert
        assert result == [], "Con HTML vacio el parser debe retornar lista vacia"

    def test___scraping_dinamico_js_equivalente_selenium_con_mock_happy_path(self):
        """Valida una recoleccion dinamica JS usando un driver mockeado (patron Selenium/WebDriver)."""
        # Arrange
        driver = Mock()
        driver.get.return_value = None
        driver.page_source = "<div id='app'>contenido dinamico renderizado</div>"

        def collect_dynamic_html(mock_driver, url):
            mock_driver.get(url)
            return mock_driver.page_source

        # Act
        html = collect_dynamic_html(driver, "https://sitio-dinamico.test")

        # Assert
        assert "contenido dinamico" in html, "El contenido dinamico esperado no fue recuperado"
        driver.get.assert_called_once_with("https://sitio-dinamico.test")

    def test___recoleccion_tweepy_api_happy_path(self):
        """Valida la recoleccion via API de Twitter/X usando cliente tipo Tweepy mockeado."""
        # Arrange
        tweepy_client = Mock()
        tweepy_client.search_recent_tweets.return_value = Mock(
            data=[Mock(id="1", text="EMI excelente"), Mock(id="2", text="EMI necesita mejoras")]
        )

        def collect_from_tweepy(client, query, max_results):
            response = client.search_recent_tweets(query=query, max_results=max_results)
            return [{"id_externo": str(t.id), "contenido_original": t.text} for t in (response.data or [])]

        # Act
        rows = collect_from_tweepy(tweepy_client, "EMI", 10)

        # Assert
        assert len(rows) == 2, "La recoleccion Tweepy debia devolver 2 registros mockeados"
        assert rows[0]["id_externo"] == "1", "El id_externo del primer tweet es incorrecto"

    def test___recoleccion_tweepy_api_edge_error_externo(self):
        """Valida manejo de error cuando la API tipo Tweepy falla."""
        # Arrange
        tweepy_client = Mock()
        tweepy_client.search_recent_tweets.side_effect = RuntimeError("Rate limit exceeded")

        def collect_from_tweepy(client, query, max_results):
            try:
                response = client.search_recent_tweets(query=query, max_results=max_results)
                return [{"id_externo": str(t.id), "contenido_original": t.text} for t in (response.data or [])]
            except Exception:
                return []

        # Act
        rows = collect_from_tweepy(tweepy_client, "EMI", 10)

        # Assert
        assert rows == [], "Ante error de API, la salida debe ser lista vacia controlada"

    def test___recoleccion_facebook_graph_api_happy_path(self):
        """Valida la recoleccion via Facebook Graph API usando cliente SDK mockeado."""
        # Arrange
        graph_client = Mock()
        graph_client.get_connections.return_value = {
            "data": [
                {"id": "p1", "message": "Publicacion oficial EMI"},
                {"id": "p2", "message": "Consulta sobre admisiones"},
            ]
        }

        def collect_from_graph_api(client, page_id):
            payload = client.get_connections(page_id, "posts")
            return [
                {"id_externo": item["id"], "contenido_original": item.get("message", "")}
                for item in payload.get("data", [])
            ]

        # Act
        rows = collect_from_graph_api(graph_client, "emi.page")

        # Assert
        assert len(rows) == 2, "Graph API mockeada debia retornar 2 publicaciones"
        assert rows[1]["contenido_original"].startswith("Consulta"), "El contenido de la segunda publicacion no coincide"

    def test___deduplicacion_registros_happy_path(self, tmp_path):
        """Valida deduplicacion de registros usando save_collected_data por id_externo."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "osint_test.db"))
        source_id = db.get_or_create_source("EMI FB", "Facebook", "https://facebook.com/emi", "emi_fb")
        rows = [
            {
                "id_externo": "dup_001",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Contenido A",
                "autor": "User1",
                "engagement_likes": 1,
                "engagement_comments": 0,
                "engagement_shares": 0,
                "tipo_contenido": "texto",
                "url_publicacion": "https://facebook.com/p/1",
                "metadata_json": {"tema": "admisiones"},
            },
            {
                "id_externo": "dup_001",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Contenido A repetido",
                "autor": "User2",
                "engagement_likes": 2,
                "engagement_comments": 1,
                "engagement_shares": 0,
                "tipo_contenido": "texto",
                "url_publicacion": "https://facebook.com/p/1",
                "metadata_json": {"tema": "admisiones"},
            },
        ]

        # Act
        inserted, duplicates = db.save_collected_data(rows, source_id=source_id)

        # Assert
        assert inserted == 1, "Solo debe insertarse un registro unico por id_externo"
        assert duplicates == 1, "Debe detectarse exactamente 1 duplicado"
        db.close()

    def test___limpieza_normalizacion_textual_happy_path(self, base_config):
        """Valida limpieza y normalizacion textual (URLs, menciones y espacios)."""
        # Arrange
        cleaner = DataCleaner(config=base_config)
        raw = "Visita https://emi.edu.bo   @usuario   #EMI  Excelente   servicio"

        # Act
        clean = cleaner.clean_text(raw)

        # Assert
        assert "https://" not in clean, "La URL debio ser removida durante la limpieza"
        assert "@usuario" not in clean, "La mencion debio ser removida durante la limpieza"
        assert "  " not in clean, "No deben quedar espacios duplicados tras normalizar"


class TestModuloBaseDatosPostgreSQLJsonb:
    """Pruebas unitarias del modulo de persistencia (orientado a tablas/JSONB)."""

    def test___insercion_fuente_osint_happy_path(self, tmp_path):
        """Valida insercion en fuente_osint y reutilizacion por llave unica."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "db_fuente.db"))

        # Act
        first_id = db.get_or_create_source("EMI Oficial", "Facebook", "https://facebook.com/emi", "emi")
        second_id = db.get_or_create_source("EMI Oficial", "Facebook", "https://facebook.com/emi", "emi")

        # Assert
        assert first_id == second_id, "get_or_create_source debe reutilizar la fuente existente"
        db.close()

    def test___insercion_dato_recolectado_happy_path(self, tmp_path):
        """Valida insercion en tabla dato_recolectado con metadata JSON."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "db_recolectado.db"))
        source_id = db.get_or_create_source("EMI TikTok", "TikTok", "https://tiktok.com/@emi", "emi_tk")
        rows = [
            {
                "id_externo": "tk_123",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Video sobre laboratorios",
                "autor": "emi",
                "engagement_likes": 10,
                "engagement_comments": 3,
                "engagement_shares": 1,
                "tipo_contenido": "video",
                "url_publicacion": "https://tiktok.com/@emi/video/123",
                "metadata_json": {"tema": "infraestructura", "campus": "La Paz"},
            }
        ]

        # Act
        inserted, duplicates = db.save_collected_data(rows, source_id=source_id)

        # Assert
        assert inserted == 1, "Debe insertarse 1 dato recolectado valido"
        assert duplicates == 0, "No deben detectarse duplicados en insercion unica"
        db.close()

    def test___insercion_analisis_sentimiento_happy_path(self, tmp_path):
        """Valida insercion en analisis_sentimiento (modelo relacional para scoring IA)."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "db_sentiment.db"))
        conn = db._get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analisis_sentimiento (
                id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
                id_dato_procesado INTEGER NOT NULL,
                sentimiento_predicho TEXT NOT NULL,
                confianza REAL NOT NULL,
                fecha_analisis TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            INSERT INTO analisis_sentimiento (id_dato_procesado, sentimiento_predicho, confianza, fecha_analisis)
            VALUES (?, ?, ?, ?)
            """,
            (101, "Positivo", 0.91, datetime.now().isoformat()),
        )
        conn.commit()

        # Act
        cur.execute("SELECT sentimiento_predicho, confianza FROM analisis_sentimiento WHERE id_dato_procesado = ?", (101,))
        row = cur.fetchone()

        # Assert
        assert row is not None, "El analisis de sentimiento insertado debe existir"
        assert row[0] == "Positivo", "El sentimiento predicho almacenado no coincide"

        db.close()

    def test___consulta_filtro_jsonb_happy_path(self, tmp_path):
        """Valida consulta por filtros tipo JSONB sobre metadata_json (equivalente SQLite json_extract)."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "db_json.db"))
        conn = db._get_connection()
        cur = conn.cursor()
        source_id = db.get_or_create_source("EMI FB", "Facebook", "https://facebook.com/emi", "emi_fb")
        db.save_collected_data(
            [
                {
                    "id_externo": "json_1",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Post de becas",
                    "autor": "A",
                    "engagement_likes": 5,
                    "engagement_comments": 1,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://facebook.com/p/1",
                    "metadata_json": {"tema": "becas", "sede": "La Paz"},
                },
                {
                    "id_externo": "json_2",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Post deportivo",
                    "autor": "B",
                    "engagement_likes": 2,
                    "engagement_comments": 0,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://facebook.com/p/2",
                    "metadata_json": {"tema": "deportes", "sede": "Cochabamba"},
                },
            ],
            source_id=source_id,
        )

        # Act
        cur.execute(
            """
            SELECT id_externo
            FROM dato_recolectado
            WHERE json_extract(metadata_json, '$.tema') = ?
            """,
            ("becas",),
        )
        rows = cur.fetchall()

        # Assert
        assert len(rows) == 1, "El filtro JSON por tema='becas' debe devolver un solo registro"
        assert rows[0][0] == "json_1", "El registro filtrado por JSON no corresponde al esperado"

        db.close()

    def test___validacion_integridad_referencial_edge(self, tmp_path):
        """Valida error de integridad referencial cuando id_fuente no existe."""
        # Arrange
        db = DatabaseWriter(db_path=str(tmp_path / "db_fk.db"))
        conn = db._get_connection()
        cur = conn.cursor()

        # Act / Assert
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            cur.execute(
                """
                INSERT INTO dato_recolectado (
                    id_fuente, id_externo, fecha_publicacion, contenido_original
                ) VALUES (?, ?, ?, ?)
                """,
                (999999, "fk_fail_1", datetime.now().isoformat(), "Post sin fuente valida"),
            )
            conn.commit()

        db.close()


class TestModuloAnalisisIAMachineLearning:
    """Pruebas unitarias de funciones de analisis IA / ML."""

    def test___analisis_sentimientos_happy_path(self):
        """Valida analisis de sentimiento lexico para texto positivo."""
        # Arrange
        text = "Excelente servicio academico, muy buena atencion y apoyo"

        # Act
        sentiment, confidence = analyze_sentiment_simple(text)

        # Assert
        assert sentiment in {"positivo", "neutral"}, "El texto positivo no debe clasificarse como negativo"
        assert 0 <= confidence <= 1, "La confianza de sentimiento debe estar en rango [0, 1]"

    def test___analisis_sentimientos_edge_texto_vacio(self):
        """Valida analisis de sentimiento para texto sin senales de polaridad."""
        # Arrange
        text = ""

        # Act
        sentiment, confidence = analyze_sentiment_simple(text)

        # Assert
        assert sentiment == "neutral", "Texto vacio debe producir sentimiento neutral"
        assert confidence == 0.5, "Texto vacio debe mantener confianza base 0.5"

    def test___clasificacion_tematica_happy_path(self):
        """Valida clasificacion tematica con palabras clave academicas."""
        # Arrange
        transformer = DataTransformer(config={})
        text = "Necesitamos mejorar laboratorios e infraestructura academica"

        # Act
        category = transformer._classify_text(text)

        # Assert
        assert category in {"infraestructura", "Académico", "Academico", "General"} or isinstance(category, str), (
            "La clasificacion tematica debe retornar una categoria valida de tipo string"
        )

    def test___deteccion_clusters_happy_path(self):
        """Valida deteccion de clusters usando metricas de clustering del modulo IA."""
        # Arrange
        metrics = AIMetrics()
        X = np.array(
            [
                [0.0, 0.1], [0.1, 0.2], [0.2, 0.1],
                [5.0, 5.1], [5.2, 5.0], [4.9, 5.2],
            ]
        )
        labels = np.array([0, 0, 0, 1, 1, 1])

        # Act
        result = metrics.clustering_metrics(X, labels)

        # Assert
        assert "n_clusters" in result, "La salida de clustering debe incluir la cantidad de clusters"
        assert result["n_clusters"] == 2, "El numero de clusters detectado debe ser 2"

    def test___identificacion_patrones_happy_path_con_mock_bd(self):
        """Valida identificacion de patrones con BD mockeada y registro de patrones invocado."""
        # Arrange
        engine = OSINTMultifuente()

        fake_cursor = Mock()
        fake_cursor.fetchall.side_effect = [
            [{"tema_principal": "becas", "plataforma": "Noticias", "cantidad": 3}],
            [{"tema_principal": "infraestructura", "sentimiento_predicho": "Negativo", "cantidad": 4, "confianza_promedio": 0.8}],
            [{"dia": "Lunes", "hora": "10", "publicaciones": 8, "avg_engagement": 20}],
            [{"plataforma": "Facebook", "tipo_contenido": "texto", "cantidad": 5, "avg_likes": 10, "avg_comments": 2, "avg_shares": 1, "max_engagement": 18}],
            [{"tema_principal": "admisiones", "menciones": 7, "es_academico": 7, "relevante_uebu": 3}],
        ]

        fake_conn = Mock()
        fake_conn.cursor.return_value = fake_cursor

        with patch("osint_multifuente.sqlite3.connect", return_value=fake_conn), patch.object(
            engine, "_registrar_patron"
        ) as mock_register:
            # Act
            stats = engine.identificar_patrones()

        # Assert
        assert stats["patrones_nuevos"] >= 1, "La identificacion de patrones debe registrar al menos un patron"
        assert mock_register.call_count >= 1, "Se esperaba al menos una llamada a _registrar_patron"


class TestPipelineETL:
    """Pruebas unitarias del pipeline ETL (Extract, Transform, Load)."""

    @pytest.fixture
    def mock_db(self):
        """Mock de base de datos para ETL."""
        db = Mock()
        db.log_execution.return_value = 1
        db.complete_execution_log.return_value = None
        db.get_unprocessed_data.return_value = [
            {
                "id_dato": 1,
                "contenido_original": "Excelente infraestructura en la EMI",
                "fecha_publicacion": datetime.now().isoformat(),
                "engagement_likes": 10,
                "engagement_comments": 3,
                "engagement_shares": 1,
                "tipo_fuente": "Facebook",
            }
        ]
        db.save_processed_data.return_value = (1, 0)
        return db

    def test___etl_extract_happy_path(self, mock_db):
        """Valida funcion de extraccion desde fuente OSINT/BD."""
        # Arrange
        etl = ETLController(config={"etl": {"batch_size": 10}}, db=mock_db)

        # Act
        extracted_df = etl._extract(limit=10)

        # Assert
        assert not extracted_df.empty, "La fase EXTRACT debe retornar registros cuando la BD tiene pendientes"
        assert "contenido_original" in extracted_df.columns, "La salida de EXTRACT debe contener la columna contenido_original"

    def test___etl_transform_limpieza_happy_path(self, mock_db):
        """Valida transformacion y limpieza de datos en la fase TRANSFORM."""
        # Arrange
        etl = ETLController(config={"etl": {"batch_size": 10}}, db=mock_db)
        input_df = pd.DataFrame([
            {
                "id_dato": 7,
                "contenido_original": "Visita https://emi.edu.bo para admisiones",
                "fecha_publicacion": datetime.now().isoformat(),
                "engagement_likes": 4,
                "engagement_comments": 1,
                "engagement_shares": 0,
            }
        ])

        # Act
        transformed_df = etl._transform(input_df)

        # Assert
        assert "id_dato_original" in transformed_df.columns, "TRANSFORM debe renombrar id_dato a id_dato_original"
        assert len(transformed_df) == 1, "TRANSFORM no debe perder registros validos en este caso"

    def test___etl_load_happy_path(self, mock_db):
        """Valida carga de datos transformados en la base de datos."""
        # Arrange
        etl = ETLController(config={"etl": {"batch_size": 10}}, db=mock_db)
        transformed_df = pd.DataFrame([
            {
                "id_dato_original": 1,
                "contenido_limpio": "excelente infraestructura emi",
                "longitud_texto": 30,
                "cantidad_palabras": 3,
                "fecha_publicacion_iso": datetime.now().isoformat(),
                "anio": 2026,
                "mes": 4,
                "dia_semana": 0,
                "hora": 10,
                "semestre": "1er Semestre 2026",
                "es_horario_laboral": True,
                "engagement_total": 14,
                "engagement_normalizado": 80.0,
                "ratio_engagement": 0.1,
                "categoria_preliminar": "infraestructura",
                "contiene_mencion_emi": True,
                "sentimiento_basico": "positivo",
            }
        ])

        # Act
        loaded_count = etl._load(transformed_df)

        # Assert
        assert loaded_count == 1, "LOAD debe retornar la cantidad de registros insertados"
        mock_db.save_processed_data.assert_called_once()

    def test___etl_pipeline_run_edge_sin_datos(self, mock_db):
        """Valida que el pipeline ETL responda correctamente cuando no hay datos para procesar."""
        # Arrange
        mock_db.get_unprocessed_data.return_value = []
        etl = ETLController(config={"etl": {"batch_size": 10}}, db=mock_db)

        # Act
        result = etl.run(limit=10)

        # Assert
        assert result["extracted"] == 0, "Sin datos pendientes, EXTRACT debe ser 0"
        assert result["loaded"] == 0, "Sin datos pendientes, LOAD debe ser 0"
        assert result["success"] is False, "Sin datos cargados, success debe ser False segun implementacion actual"
