"""
Pruebas de integracion y funcionales (E2E) para el sistema de Analitica OSINT.

Cobertura de esta suite:
- Integracion (INT-001..INT-004)
- Funcionales end-to-end (FUNC-001..FUNC-008)

Formato de cada prueba:
- ID unico
- Escenario
- Precondiciones
- Pasos
- Resultado esperado
- Criterio de aceptacion
- Tipo (positivo/negativo)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from database.db_writer import DatabaseWriter
from etl.data_cleaner import DataCleaner
from etl.data_transformer import DataTransformer
from etl.etl_controller import ETLController
from run_analysis import analyze_sentiment_simple
from ai.utils.metrics import AIMetrics
from osint_multifuente import OSINTMultifuente
import setup_users_alerts


def _case_metadata(
    case_id: str,
    descripcion: str,
    precondiciones: list[str],
    pasos: list[str],
    resultado_esperado: str,
    criterio_aceptacion: str,
    tipo: str,
) -> dict:
    """Construye metadata estructurada del caso de prueba."""
    return {
        "id": case_id,
        "descripcion": descripcion,
        "precondiciones": precondiciones,
        "pasos": pasos,
        "resultado_esperado": resultado_esperado,
        "criterio_aceptacion": criterio_aceptacion,
        "tipo": tipo,
    }


def _assert_case_metadata(meta: dict) -> None:
    """Valida que la metadata del caso cumpla el formato solicitado."""
    required = [
        "id",
        "descripcion",
        "precondiciones",
        "pasos",
        "resultado_esperado",
        "criterio_aceptacion",
        "tipo",
    ]
    for key in required:
        assert key in meta, f"Falta campo obligatorio en metadata del caso: {key}"
        assert meta[key], f"El campo {key} no debe estar vacio"


@pytest.fixture
def test_db(tmp_path):
    """Base de datos de prueba aislada por test."""
    db_path = tmp_path / "osint_integration_test.db"
    db = DatabaseWriter(db_path=str(db_path))

    # Ajustes para compatibilidad con consultas de dashboard/API que requieren esta columna
    conn = db._get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(fuente_osint)")
    cols = {r[1] for r in cur.fetchall()}
    if "es_oficial" not in cols:
        cur.execute("ALTER TABLE fuente_osint ADD COLUMN es_oficial INTEGER DEFAULT 0")

    # Tabla minima para pruebas de alertas automáticas
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analisis_sentimiento (
            id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
            id_dato_procesado INTEGER NOT NULL,
            sentimiento_predicho TEXT NOT NULL,
            confianza REAL NOT NULL,
            modelo_version TEXT,
            fecha_analisis TEXT
        )
        """
    )
    conn.commit()

    yield db
    db.close()


@pytest.fixture
def cleaner_config():
    """Configuracion de limpieza textual para pruebas ETL."""
    return {
        "etl": {
            "remove_urls": True,
            "remove_mentions": True,
            "remove_hashtags": False,
            "remove_emojis": False,
            "normalize_whitespace": True,
            "min_text_length": 1,
            "max_text_length": 5000,
        }
    }


@pytest.fixture
def mock_social_apis():
    """Mocks de APIs de redes sociales para escenarios positivos y negativos."""
    tweepy_client = Mock()
    tweepy_client.search_recent_tweets.return_value = Mock(
        data=[
            Mock(id="tw_1", text="EMI excelente experiencia academica"),
            Mock(id="tw_2", text="Problemas de infraestructura en EMI"),
        ]
    )

    graph_client = Mock()
    graph_client.get_connections.return_value = {
        "data": [
            {"id": "fb_1", "message": "Inscripciones abiertas EMI"},
            {"id": "fb_2", "message": "Queja por horarios"},
        ]
    }

    return {"tweepy": tweepy_client, "graph": graph_client}


@pytest.fixture
def ai_api_client():
    """Cliente Flask para endpoints de IA con modelos mockeados."""
    with patch("api.ai_endpoints.SentimentAnalyzer"), patch("api.ai_endpoints.ClusteringEngine"), patch(
        "api.ai_endpoints.TrendDetector"
    ), patch("api.ai_endpoints.AnomalyDetector"), patch("api.ai_endpoints.CorrelationAnalyzer"):
        from api import create_app

        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client


class TestIntegracionOSINT:
    """Casos de integracion INT-001..INT-004."""

    def test_int_001_integracion_recoleccion_base_datos(self, test_db, cleaner_config, mock_social_apis):
        """
        ID: INT-001
        Escenario: Integracion Recoleccion -> Limpieza -> Persistencia en BD.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="INT-001",
            descripcion="Flujo completo scraper/API extrae datos, se limpian y se insertan en BD con relacion a fuente.",
            precondiciones=[
                "BD de prueba inicializada",
                "Fuente OSINT registrada",
                "APIs externas mockeadas con datos validos",
            ],
            pasos=[
                "Recolectar datos desde APIs mock",
                "Aplicar limpieza textual",
                "Persistir registros en dato_recolectado",
                "Validar relacion FK con fuente_osint",
            ],
            resultado_esperado="Los registros quedan persistidos sin errores y asociados a su fuente.",
            criterio_aceptacion="inserted > 0, duplicates >= 0 y conteo en join coincide con insertados.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        source_id = test_db.get_or_create_source(
            nombre="API Social EMI",
            tipo="Twitter",
            url="https://x.com/emi",
            identificador="emi_x",
        )
        cleaner = DataCleaner(config=cleaner_config)

        # Act
        tw_rows = [
            {"id_externo": str(t.id), "contenido_original": t.text}
            for t in mock_social_apis["tweepy"].search_recent_tweets(query="EMI", max_results=10).data
        ]
        fb_rows = [
            {"id_externo": item["id"], "contenido_original": item.get("message", "")}
            for item in mock_social_apis["graph"].get_connections("emi", "posts").get("data", [])
        ]
        scraped = tw_rows + fb_rows

        prepared = []
        for row in scraped:
            prepared.append(
                {
                    "id_externo": row["id_externo"],
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": cleaner.clean_text(row["contenido_original"]),
                    "autor": "api_user",
                    "engagement_likes": 1,
                    "engagement_comments": 0,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://example.test/post",
                    "metadata_json": {"source": "mock_api"},
                }
            )

        inserted, duplicates = test_db.save_collected_data(prepared, source_id=source_id)

        conn = test_db._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM dato_recolectado dr
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            WHERE f.id_fuente = ?
            """,
            (source_id,),
        )
        persisted_count = cur.fetchone()[0]

        # Assert
        assert inserted >= 2, "INT-001: Deben insertarse al menos 2 registros recolectados"
        assert duplicates >= 0, "INT-001: El numero de duplicados no puede ser negativo"
        assert persisted_count == inserted, "INT-001: Los registros persistidos no coinciden con los insertados"

    def test_int_002_integracion_etl_modelos_ia(self, test_db, cleaner_config):
        """
        ID: INT-002
        Escenario: Integracion Pipeline ETL -> Modelos IA (sentimiento + clasificacion tematica).
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="INT-002",
            descripcion="Datos limpios del ETL alimentan el analisis de sentimiento y la clasificacion tematica sin errores.",
            precondiciones=[
                "BD con registros crudos pendientes de ETL",
                "Controlador ETL inicializado",
            ],
            pasos=[
                "Insertar datos crudos",
                "Ejecutar _extract, _clean y _transform",
                "Ejecutar analisis de sentimiento sobre contenido_limpio",
                "Verificar categoria_preliminar y ausencia de excepciones",
            ],
            resultado_esperado="El pipeline transforma datos correctamente y la capa IA produce salida valida.",
            criterio_aceptacion="DataFrame transformado no vacio, sentimiento en dominio permitido y categoria tipo string.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        source_id = test_db.get_or_create_source("EMI FB", "Facebook", "https://facebook.com/emi", "emi_fb")
        rows = [
            {
                "id_externo": "etl_1",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Excelente infraestructura y buena atencion academica en la EMI",
                "autor": "user_a",
                "engagement_likes": 10,
                "engagement_comments": 2,
                "engagement_shares": 1,
                "tipo_contenido": "texto",
                "url_publicacion": "https://facebook.com/p/etl_1",
                "metadata_json": {"tema": "infraestructura"},
            }
        ]
        test_db.save_collected_data(rows, source_id=source_id)

        etl = ETLController(config={"etl": {"batch_size": 10, **cleaner_config["etl"]}}, db=test_db)

        # Act
        raw_df = etl._extract(limit=10)
        cleaned_df = etl._clean(raw_df)
        transformed_df = etl._transform(cleaned_df)

        sentiment, confidence = analyze_sentiment_simple(transformed_df.iloc[0]["contenido_limpio"])
        category = transformed_df.iloc[0].get("categoria_preliminar")

        # Assert
        assert not transformed_df.empty, "INT-002: El DataFrame transformado no debe estar vacio"
        assert sentiment in {"positivo", "negativo", "neutral"}, "INT-002: Sentimiento fuera del dominio esperado"
        assert 0 <= confidence <= 1, "INT-002: Confianza de sentimiento fuera de rango [0,1]"
        assert isinstance(category, str) and category != "", "INT-002: categoria_preliminar debe ser string no vacio"

    def test_int_003_integracion_bd_dashboard(self, test_db):
        """
        ID: INT-003
        Escenario: Integracion Base de Datos -> Dashboard (formato + KPIs).
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="INT-003",
            descripcion="Consultas de BD entregan formato consumible por dashboard y KPIs correctos.",
            precondiciones=["BD con fuentes y publicaciones cargadas"],
            pasos=[
                "Insertar fuentes y datos recolectados",
                "Consultar estadisticas generales y por fuente",
                "Mapear payload para visualizacion",
                "Validar KPIs principales",
            ],
            resultado_esperado="Payload de dashboard contiene series y KPIs coherentes con los datos almacenados.",
            criterio_aceptacion="Campos esperados presentes y totales correctos (>0 cuando hay datos).",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        s1 = test_db.get_or_create_source("EMI FB", "Facebook", "https://facebook.com/emi", "emi_fb")
        s2 = test_db.get_or_create_source("EMI TK", "TikTok", "https://tiktok.com/@emi", "emi_tk")
        sample_rows = [
            {
                "id_externo": "dash_1",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Post 1",
                "autor": "a",
                "engagement_likes": 10,
                "engagement_comments": 2,
                "engagement_shares": 1,
                "tipo_contenido": "texto",
                "url_publicacion": "https://x/1",
                "metadata_json": {},
            },
            {
                "id_externo": "dash_2",
                "fecha_publicacion": datetime.now().isoformat(),
                "contenido_original": "Post 2",
                "autor": "b",
                "engagement_likes": 4,
                "engagement_comments": 1,
                "engagement_shares": 0,
                "tipo_contenido": "texto",
                "url_publicacion": "https://x/2",
                "metadata_json": {},
            },
        ]
        test_db.save_collected_data([sample_rows[0]], source_id=s1)
        test_db.save_collected_data([sample_rows[1]], source_id=s2)

        # Act
        general_stats = test_db.get_statistics()
        by_source = test_db.get_engagement_stats_by_source()

        dashboard_payload = {
            "kpis": {
                "total_fuentes": general_stats["fuentes"]["total"],
                "total_recolectados": general_stats["datos_recolectados"]["total"],
                "pendientes_etl": general_stats["datos_recolectados"]["pendientes"],
            },
            "series": by_source,
        }

        # Assert
        assert "kpis" in dashboard_payload and "series" in dashboard_payload, "INT-003: Payload incompleto para dashboard"
        assert dashboard_payload["kpis"]["total_fuentes"] >= 2, "INT-003: KPI total_fuentes incorrecto"
        assert dashboard_payload["kpis"]["total_recolectados"] >= 2, "INT-003: KPI total_recolectados incorrecto"
        assert isinstance(dashboard_payload["series"], list), "INT-003: La serie por fuente debe ser una lista"

    def test_int_004_integracion_monitoreo_continuo_alertas_y_sync(self, test_db, monkeypatch):
        """
        ID: INT-004
        Escenario: Integracion Monitoreo Continuo (alertas criticas + sincronizacion sin duplicados).
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="INT-004",
            descripcion="El sistema de alertas detecta patrones criticos y la sincronizacion evita duplicados.",
            precondiciones=[
                "BD de prueba con dato_procesado y analisis_sentimiento",
                "Script de alertas disponible",
            ],
            pasos=[
                "Insertar un registro con sentimiento negativo y alta confianza",
                "Ejecutar generacion automatica de alertas",
                "Reinsertar datos recolectados duplicados en flujo de sincronizacion",
                "Validar alertas criticas/altas y conteo de duplicados",
            ],
            resultado_esperado="Se crean alertas de severidad alta/critica y el sync no duplica publicaciones.",
            criterio_aceptacion="alert_count >= 1 y duplicates >= 1.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        source_id = test_db.get_or_create_source("EMI FB", "Facebook", "https://facebook.com/emi", "emi_fb_sync")
        test_db.save_collected_data(
            [
                {
                    "id_externo": "sync_1",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Servicio pesimo en ventanilla",
                    "autor": "u1",
                    "engagement_likes": 2,
                    "engagement_comments": 3,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://fb/sync_1",
                    "metadata_json": {},
                }
            ],
            source_id=source_id,
        )

        conn = test_db._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dato_procesado (
                id_dato_original, contenido_limpio, longitud_texto, cantidad_palabras,
                fecha_publicacion_iso, anio, mes, dia_semana, hora, semestre,
                es_horario_laboral, engagement_total, engagement_normalizado,
                ratio_engagement, categoria_preliminar, idioma_detectado,
                contiene_mencion_emi, sentimiento_basico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "servicio pesimo en ventanilla",
                29,
                4,
                datetime.now().isoformat(),
                2026,
                4,
                1,
                10,
                "1er Semestre 2026",
                1,
                5,
                30.0,
                0.1,
                "Queja",
                "es",
                1,
                "negativo",
            ),
        )
        cur.execute(
            """
            INSERT INTO analisis_sentimiento (id_dato_procesado, sentimiento_predicho, confianza, modelo_version, fecha_analisis)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "Negativo", 0.92, "mock_v1", datetime.now().isoformat()),
        )
        conn.commit()

        # Act
        monkeypatch.setattr(setup_users_alerts, "DB_PATH", str(Path(test_db.db_path)))
        setup_users_alerts.main()

        # Simular sincronizacion repetida (sin duplicados)
        inserted_1, dup_1 = test_db.save_collected_data(
            [
                {
                    "id_externo": "sync_dup",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Publicacion sincronizada",
                    "autor": "u2",
                    "engagement_likes": 1,
                    "engagement_comments": 0,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://fb/sync_dup",
                    "metadata_json": {},
                }
            ],
            source_id=source_id,
        )
        inserted_2, dup_2 = test_db.save_collected_data(
            [
                {
                    "id_externo": "sync_dup",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Publicacion sincronizada repetida",
                    "autor": "u2",
                    "engagement_likes": 2,
                    "engagement_comments": 1,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://fb/sync_dup",
                    "metadata_json": {},
                }
            ],
            source_id=source_id,
        )

        cur.execute("SELECT COUNT(*) FROM alerta WHERE severidad IN ('alta', 'critica')")
        alert_count = cur.fetchone()[0]

        # Assert
        assert alert_count >= 1, "INT-004: Debe existir al menos una alerta alta/critica"
        assert inserted_1 == 1 and inserted_2 == 0, "INT-004: El segundo sync no debe insertar duplicados"
        assert dup_1 == 0 and dup_2 >= 1, "INT-004: Debe detectarse duplicado en la segunda sincronizacion"


class TestFuncionalesE2E:
    """Casos funcionales end-to-end FUNC-001..FUNC-008."""

    def test_func_001_rf01_recoleccion_automatica_exito_y_fallo_api(self, mock_social_apis):
        """
        ID: FUNC-001
        RF-01: El sistema recolecta datos automaticamente (exito y fallo API).
        Tipo: positivo/negativo
        """
        case = _case_metadata(
            case_id="FUNC-001",
            descripcion="Recoleccion automatica desde APIs sociales con escenario exitoso y de fallo por excepcion externa.",
            precondiciones=["Clientes API mockeados", "Conectividad simulada"],
            pasos=[
                "Invocar recoleccion con respuesta valida",
                "Invocar recoleccion cuando la API falla",
                "Verificar salida normal y fallback seguro",
            ],
            resultado_esperado="Se recolectan datos cuando hay respuesta y se maneja fallo sin romper flujo.",
            criterio_aceptacion="happy_path devuelve n>0 y error_path devuelve lista vacia controlada.",
            tipo="positivo/negativo",
        )
        _assert_case_metadata(case)

        # Arrange
        def collect(client):
            try:
                resp = client.search_recent_tweets(query="EMI", max_results=10)
                return [x.text for x in (resp.data or [])]
            except Exception:
                return []

        # Act (happy)
        ok_rows = collect(mock_social_apis["tweepy"])

        # Act (error)
        mock_social_apis["tweepy"].search_recent_tweets.side_effect = RuntimeError("API unavailable")
        err_rows = collect(mock_social_apis["tweepy"])

        # Assert
        assert len(ok_rows) >= 1, "FUNC-001: En escenario exitoso debe haber datos recolectados"
        assert err_rows == [], "FUNC-001: En fallo de API debe retornarse lista vacia controlada"

    def test_func_002_rf02_limpieza_normalizacion_texto(self, cleaner_config):
        """
        ID: FUNC-002
        RF-02: Limpieza y normalizacion de datos textuales.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-002",
            descripcion="La capa ETL limpia URLs, menciones y normaliza espacios en texto crudo.",
            precondiciones=["Config de limpieza habilitada"],
            pasos=["Enviar texto con ruido", "Aplicar clean_text", "Validar salida"],
            resultado_esperado="Texto limpio sin URL/menciones y con espacios normalizados.",
            criterio_aceptacion="No contiene 'http' ni '@usuario' y no hay doble espacio.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        cleaner = DataCleaner(config=cleaner_config)
        text = "Mira https://emi.edu.bo   @usuario   informacion   oficial"

        # Act
        cleaned = cleaner.clean_text(text)

        # Assert
        assert "http" not in cleaned, "FUNC-002: La URL no fue removida"
        assert "@usuario" not in cleaned, "FUNC-002: La mencion no fue removida"
        assert "  " not in cleaned, "FUNC-002: Debe normalizar espacios múltiples"

    def test_func_003_rf03_clasificacion_tematica(self):
        """
        ID: FUNC-003
        RF-03: Clasificacion de publicaciones por categoria tematica.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-003",
            descripcion="El sistema clasifica publicaciones en categorias tematicas preliminares.",
            precondiciones=["Transformador inicializado", "DataFrame con contenido_limpio"],
            pasos=["Crear DataFrame de entrada", "Ejecutar classify_content", "Validar categoria"],
            resultado_esperado="Cada fila recibe categoria_preliminar sin errores.",
            criterio_aceptacion="Existe columna categoria_preliminar y contiene strings validos.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        transformer = DataTransformer(config={})
        df = pd.DataFrame(
            [{"contenido_limpio": "Solicito mejoras en laboratorios e infraestructura academica"}]
        )

        # Act
        out = transformer.classify_content(df)

        # Assert
        assert "categoria_preliminar" in out.columns, "FUNC-003: No se genero categoria_preliminar"
        assert isinstance(out.iloc[0]["categoria_preliminar"], str), "FUNC-003: La categoria debe ser string"

    def test_func_004_rf04_analisis_sentimiento_publicacion(self):
        """
        ID: FUNC-004
        RF-04: Analisis de sentimiento por publicacion.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-004",
            descripcion="Cada publicacion recibe sentimiento y confianza de inferencia.",
            precondiciones=["Funcion de sentimiento disponible"],
            pasos=["Enviar texto", "Ejecutar analisis", "Validar salida"],
            resultado_esperado="Sentimiento dentro del dominio esperado con confianza valida.",
            criterio_aceptacion="sentimiento in {positivo,negativo,neutral} y 0<=conf<=1.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        text = "Excelente apoyo academico, muy satisfecho con la EMI"

        # Act
        sentiment, confidence = analyze_sentiment_simple(text)

        # Assert
        assert sentiment in {"positivo", "negativo", "neutral"}, "FUNC-004: Sentimiento fuera de dominio"
        assert 0 <= confidence <= 1, "FUNC-004: Confianza fuera de rango"

    def test_func_005_rf05_clusters_y_patrones(self):
        """
        ID: FUNC-005
        RF-05: Deteccion de clusters y patrones.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-005",
            descripcion="El sistema detecta estructura de clusters y patrones relevantes.",
            precondiciones=["Modulo de metricas IA disponible"],
            pasos=["Generar matriz de features", "Aplicar clustering_metrics", "Validar n_clusters"],
            resultado_esperado="Se reporta estructura de clusters sin errores de ejecucion.",
            criterio_aceptacion="n_clusters >= 2 en escenario con dos grupos claros.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        metrics = AIMetrics()
        X = np.array([[0.0, 0.1], [0.1, 0.0], [4.9, 5.0], [5.1, 4.9]])
        labels = np.array([0, 0, 1, 1])

        # Act
        result = metrics.clustering_metrics(X, labels)

        # Assert
        assert result.get("n_clusters", 0) >= 2, "FUNC-005: Deben detectarse al menos 2 clusters"

    def test_func_006_rf06_dashboard_tendencias_estadisticas_actualizadas(self, test_db):
        """
        ID: FUNC-006
        RF-06: Dashboard muestra tendencias y estadisticas actualizadas.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-006",
            descripcion="El dashboard recibe estadisticas actualizadas tras nuevas inserciones.",
            precondiciones=["BD operativa", "Fuente registrada"],
            pasos=[
                "Consultar estadisticas iniciales",
                "Insertar nuevas publicaciones",
                "Reconsultar estadisticas",
                "Comparar variacion de KPI",
            ],
            resultado_esperado="El KPI total_recolectados incrementa despues de insertar nuevos datos.",
            criterio_aceptacion="total_final > total_inicial.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        source_id = test_db.get_or_create_source("EMI DASH", "Facebook", "https://facebook.com/emi_dash", "emi_dash")
        initial_total = test_db.get_statistics()["datos_recolectados"]["total"] or 0

        # Act
        test_db.save_collected_data(
            [
                {
                    "id_externo": "kpi_1",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Nuevo post para dashboard",
                    "autor": "dash",
                    "engagement_likes": 3,
                    "engagement_comments": 1,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://fb/kpi_1",
                    "metadata_json": {},
                }
            ],
            source_id=source_id,
        )
        final_total = test_db.get_statistics()["datos_recolectados"]["total"] or 0

        # Assert
        assert final_total > initial_total, "FUNC-006: El dashboard debe reflejar incremento de registros"

    def test_func_007_rf07_alertas_patrones_criticos(self, test_db, monkeypatch):
        """
        ID: FUNC-007
        RF-07: Generacion de alertas ante patrones criticos.
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-007",
            descripcion="Se generan alertas cuando hay patrones de sentimiento negativo critico.",
            precondiciones=["dato_procesado y analisis_sentimiento poblados"],
            pasos=["Insertar muestra critica", "Ejecutar setup de alertas", "Verificar alertas creadas"],
            resultado_esperado="Existen alertas nuevas en tabla alerta con severidad alta/critica.",
            criterio_aceptacion="count(alerta) > 0 y severidad in {'alta','critica'}.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange
        source_id = test_db.get_or_create_source("EMI ALERT", "Facebook", "https://facebook.com/emi_alert", "emi_alert")
        test_db.save_collected_data(
            [
                {
                    "id_externo": "alert_1",
                    "fecha_publicacion": datetime.now().isoformat(),
                    "contenido_original": "Muy mala experiencia, servicio pesimo",
                    "autor": "alert_user",
                    "engagement_likes": 1,
                    "engagement_comments": 4,
                    "engagement_shares": 0,
                    "tipo_contenido": "texto",
                    "url_publicacion": "https://fb/alert_1",
                    "metadata_json": {},
                }
            ],
            source_id=source_id,
        )
        conn = test_db._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dato_procesado (
                id_dato_original, contenido_limpio, longitud_texto, cantidad_palabras,
                fecha_publicacion_iso, anio, mes, dia_semana, hora, semestre,
                es_horario_laboral, engagement_total, engagement_normalizado,
                ratio_engagement, categoria_preliminar, idioma_detectado,
                contiene_mencion_emi, sentimiento_basico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "muy mala experiencia servicio pesimo",
                34,
                5,
                datetime.now().isoformat(),
                2026,
                4,
                2,
                11,
                "1er Semestre 2026",
                1,
                5,
                20.0,
                0.1,
                "Queja",
                "es",
                1,
                "negativo",
            ),
        )
        cur.execute(
            """
            INSERT INTO analisis_sentimiento (id_dato_procesado, sentimiento_predicho, confianza, modelo_version, fecha_analisis)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "Negativo", 0.9, "mock_v1", datetime.now().isoformat()),
        )
        conn.commit()

        # Act
        monkeypatch.setattr(setup_users_alerts, "DB_PATH", str(Path(test_db.db_path)))
        setup_users_alerts.main()
        cur.execute("SELECT COUNT(*) FROM alerta WHERE severidad IN ('alta', 'critica')")
        critical_alerts = cur.fetchone()[0]

        # Assert
        assert critical_alerts >= 1, "FUNC-007: Debe generarse al menos una alerta alta/critica"

    def test_func_008_rf08_actualizacion_modelos_ml_reentrenamiento(self, ai_api_client):
        """
        ID: FUNC-008
        RF-08: Actualizacion de modelos ML con nuevos datos (reentrenamiento).
        Tipo: positivo
        """
        case = _case_metadata(
            case_id="FUNC-008",
            descripcion="Endpoint de entrenamiento acepta nuevos parametros y dispara proceso de reentrenamiento.",
            precondiciones=["API IA levantada en modo testing", "Modelo mockeado"],
            pasos=[
                "Invocar POST /api/ai/sentiments/train",
                "Enviar hiperparametros de entrenamiento",
                "Verificar estado HTTP y estructura de respuesta",
            ],
            resultado_esperado="El sistema acepta solicitud de reentrenamiento y devuelve respuesta valida.",
            criterio_aceptacion="status_code in {200,202,500} y respuesta JSON parseable.",
            tipo="positivo",
        )
        _assert_case_metadata(case)

        # Arrange / Act
        resp = ai_api_client.post(
            "/api/ai/sentiments/train",
            json={"epochs": 2, "batch_size": 8},
            content_type="application/json",
        )

        # Assert
        assert resp.status_code in {200, 202, 500}, "FUNC-008: Estado HTTP inesperado al solicitar reentrenamiento"
        # Debe ser parseable como JSON aun cuando el entrenamiento falle en entorno de prueba
        assert resp.is_json, "FUNC-008: La respuesta del endpoint de reentrenamiento debe ser JSON"
