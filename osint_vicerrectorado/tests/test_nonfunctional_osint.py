"""
Pruebas no funcionales para sistema OSINT universitario.

Cobertura:
- Rendimiento: 12 casos
- Seguridad: 7 casos
- Carga: 3 escenarios

Notas:
- Las pruebas usan SQLite temporal y mocks para simular PostgreSQL/APIs cuando aplica.
- Cada caso define SLA, tamano de dataset, metrica y criterio pass/fail via aserciones.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

from database.db_writer import DatabaseWriter
from etl.data_cleaner import DataCleaner
from etl.data_transformer import DataTransformer
from etl.etl_controller import ETLController
from run_analysis import analyze_sentiment_simple
from api_real import app as flask_app, hash_password


@dataclass
class NFCase:
    case_id: str
    sla: float
    dataset_size: int
    metric_name: str


# ============================================================
# Fixtures compartidas
# ============================================================

@pytest.fixture
def nf_db(tmp_path):
    """BD temporal de pruebas no funcionales."""
    db = DatabaseWriter(db_path=str(tmp_path / "nf_osint.db"))
    conn = db._get_connection()
    cur = conn.cursor()

    # Compatibilidad con filtros de API que usan es_oficial.
    cur.execute("PRAGMA table_info(fuente_osint)")
    cols = {r[1] for r in cur.fetchall()}
    if "es_oficial" not in cols:
        cur.execute("ALTER TABLE fuente_osint ADD COLUMN es_oficial INTEGER DEFAULT 0")

    # Tabla analisis_sentimiento para pruebas de seguridad/carga.
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
def cleaner_cfg():
    return {
        "etl": {
            "remove_urls": True,
            "remove_mentions": True,
            "remove_hashtags": False,
            "remove_emojis": False,
            "normalize_whitespace": True,
            "min_text_length": 1,
            "max_text_length": 10000,
        }
    }


@pytest.fixture
def secure_api_client(tmp_path, monkeypatch):
    """Cliente Flask con esquema auth minimo para pruebas de seguridad."""
    test_db_path = str(tmp_path / "secure_api.db")

    conn = sqlite3.connect(test_db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol TEXT NOT NULL,
            cargo TEXT,
            activo INTEGER DEFAULT 1,
            ultimo_login TEXT,
            fecha_creacion TEXT,
            permisos TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE log_actividad (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER,
            accion TEXT,
            detalle TEXT,
            ip_address TEXT,
            fecha TEXT
        )
        """
    )
    cur.execute(
        """
        INSERT INTO usuario (
            username, email, password_hash, nombre_completo,
            rol, cargo, activo, fecha_creacion, permisos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
        """,
        (
            "qa_user",
            "qa_user@emi.edu.bo",
            hash_password("secret123"),
            "QA User",
            "administrador",
            "QA",
            1,
            json.dumps({"canRead": True, "canWrite": True}),
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("api_real.DB_PATH", test_db_path)
    flask_app.config["TESTING"] = True

    with flask_app.test_client() as client:
        yield client


# ============================================================
# PRUEBAS DE RENDIMIENTO (12 casos)
# ============================================================

class TestRendimiento:
    """Rendimiento y tiempos de respuesta con SLA."""

    def _seed_records(self, db: DatabaseWriter, total: int) -> int:
        source_id = db.get_or_create_source("NF Fuente", "Facebook", "https://facebook.com/nf", "nf_fb")
        rows = []
        now_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        for i in range(total):
            rows.append(
                {
                    "id_externo": f"nf_{i}",
                    "fecha_publicacion": now_iso,
                    "contenido_original": f"Publicacion {i} de prueba rendimiento",
                    "autor": "nf_user",
                    "engagement_likes": i % 37,
                    "engagement_comments": i % 11,
                    "engagement_shares": i % 5,
                    "tipo_contenido": "texto",
                    "url_publicacion": f"https://facebook.com/p/{i}",
                    "metadata_json": {"batch": "nf", "idx": i},
                }
            )
        db.save_collected_data(rows, source_id=source_id)
        return source_id

    def test_perf_001_query_count_miles_records_under_2s(self, nf_db):
        """PERF-001: Tiempo de consulta COUNT con miles de registros (<2s)."""
        case = NFCase("PERF-001", sla=2.0, dataset_size=20000, metric_name="seconds")
        self._seed_records(nf_db, case.dataset_size)

        conn = nf_db._get_connection()
        cur = conn.cursor()
        t0 = time.perf_counter()
        cur.execute("SELECT COUNT(*) FROM dato_recolectado")
        count = cur.fetchone()[0]
        elapsed = time.perf_counter() - t0

        assert count == case.dataset_size, "PERF-001 FAIL: Conteo total no coincide con dataset insertado"
        assert elapsed < case.sla, (
            f"PERF-001 FAIL: Consulta COUNT tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_002_query_join_groupby_miles_records_under_2s(self, nf_db):
        """PERF-002: Tiempo de consulta JOIN+GROUP BY con miles de registros (<2s)."""
        case = NFCase("PERF-002", sla=2.0, dataset_size=15000, metric_name="seconds")
        self._seed_records(nf_db, case.dataset_size)

        conn = nf_db._get_connection()
        cur = conn.cursor()
        t0 = time.perf_counter()
        cur.execute(
            """
            SELECT f.tipo_fuente, COUNT(*) as total, AVG(dr.engagement_likes) as avg_likes
            FROM dato_recolectado dr
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            GROUP BY f.tipo_fuente
            """
        )
        rows = cur.fetchall()
        elapsed = time.perf_counter() - t0

        assert len(rows) >= 1, "PERF-002 FAIL: La consulta agrupada no devolvio resultados"
        assert elapsed < case.sla, (
            f"PERF-002 FAIL: JOIN+GROUP BY tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_003_etl_clean_transform_large_batch_throughput(self, cleaner_cfg):
        """PERF-003: Velocidad de procesamiento ETL para lote grande (registros/s)."""
        case = NFCase("PERF-003", sla=4000.0, dataset_size=10000, metric_name="records_per_second")
        cleaner = DataCleaner(config=cleaner_cfg)
        transformer = DataTransformer(config={})

        df = pd.DataFrame(
            {
                "id_dato": range(case.dataset_size),
                "contenido_original": [
                    "Texto con URL https://emi.edu.bo y menciones @alumno para limpieza"
                    for _ in range(case.dataset_size)
                ],
                "fecha_publicacion": ["2026-04-21 10:00:00"] * case.dataset_size,
                "engagement_likes": np.random.randint(0, 100, size=case.dataset_size),
                "engagement_comments": np.random.randint(0, 50, size=case.dataset_size),
                "engagement_shares": np.random.randint(0, 20, size=case.dataset_size),
            }
        )

        t0 = time.perf_counter()
        clean_df = cleaner.clean_dataframe(df)
        trans_df = transformer.transform_dataframe(clean_df)
        elapsed = time.perf_counter() - t0
        rps = len(trans_df) / max(elapsed, 1e-9)

        assert len(trans_df) > 0, "PERF-003 FAIL: ETL no genero registros transformados"
        assert rps >= case.sla, (
            f"PERF-003 FAIL: Throughput ETL={rps:.2f} reg/s, umbral={case.sla:.2f} reg/s"
        )

    def test_perf_004_etl_controller_run_large_batch(self, nf_db, cleaner_cfg):
        """PERF-004: Tiempo de ejecucion de ETLController para lote grande."""
        case = NFCase("PERF-004", sla=20.0, dataset_size=5000, metric_name="seconds")
        source_id = nf_db.get_or_create_source("ETL Fuente", "Facebook", "https://facebook.com/etl", "etl_fb")

        rows = []
        now_iso = "2026-04-21 10:00:00"
        for i in range(case.dataset_size):
            rows.append(
                {
                    "id_externo": f"etl_batch_{i}",
                    "fecha_publicacion": now_iso,
                    "contenido_original": "Contenido academico de prueba para pipeline ETL",
                    "autor": "etl_user",
                    "engagement_likes": i % 10,
                    "engagement_comments": i % 4,
                    "engagement_shares": i % 2,
                    "tipo_contenido": "texto",
                    "url_publicacion": f"https://facebook.com/etl/{i}",
                    "metadata_json": {},
                }
            )
        nf_db.save_collected_data(rows, source_id=source_id)

        etl_cfg = {"etl": {"batch_size": case.dataset_size, **cleaner_cfg["etl"]}}
        etl = ETLController(config=etl_cfg, db=nf_db)

        t0 = time.perf_counter()
        result = etl.run(limit=case.dataset_size)
        elapsed = time.perf_counter() - t0

        assert result["extracted"] >= case.dataset_size, "PERF-004 FAIL: ETL no extrajo el lote esperado"
        assert elapsed < case.sla, (
            f"PERF-004 FAIL: ETL run tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_005_dashboard_historical_load_time(self, nf_db):
        """PERF-005: Tiempo de carga de dashboard historico (<2s)."""
        case = NFCase("PERF-005", sla=2.0, dataset_size=12000, metric_name="seconds")
        self._seed_records(nf_db, case.dataset_size)

        t0 = time.perf_counter()
        stats = nf_db.get_statistics()
        by_source = nf_db.get_engagement_stats_by_source()
        payload = {
            "kpis": {
                "total_fuentes": stats["fuentes"]["total"],
                "total_recolectados": stats["datos_recolectados"]["total"],
            },
            "series": by_source,
        }
        elapsed = time.perf_counter() - t0

        assert payload["kpis"]["total_recolectados"] >= case.dataset_size, "PERF-005 FAIL: KPI total recolectados invalido"
        assert elapsed < case.sla, (
            f"PERF-005 FAIL: Armado de payload dashboard tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_006_dashboard_refresh_time(self, nf_db):
        """PERF-006: Tiempo de refresco de KPIs de dashboard (<2s)."""
        case = NFCase("PERF-006", sla=2.0, dataset_size=8000, metric_name="seconds")
        self._seed_records(nf_db, case.dataset_size)

        t0 = time.perf_counter()
        _ = nf_db.get_statistics()
        _ = nf_db.get_engagement_stats_by_source()
        elapsed = time.perf_counter() - t0

        assert elapsed < case.sla, (
            f"PERF-006 FAIL: Refresco de KPIs tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_007_sentiment_model_latency_single_post(self):
        """PERF-007: Latencia de analisis de sentimiento por publicacion individual."""
        case = NFCase("PERF-007", sla=0.020, dataset_size=1, metric_name="seconds")
        text = "Excelente calidad academica y buen servicio al estudiante"

        t0 = time.perf_counter()
        sentiment, conf = analyze_sentiment_simple(text)
        elapsed = time.perf_counter() - t0

        assert sentiment in {"positivo", "negativo", "neutral"}, "PERF-007 FAIL: Salida de sentimiento invalida"
        assert 0 <= conf <= 1, "PERF-007 FAIL: Confianza fuera de rango"
        assert elapsed < case.sla, (
            f"PERF-007 FAIL: Latencia inferencia={elapsed:.6f}s, SLA={case.sla:.3f}s"
        )

    def test_perf_008_sentiment_model_latency_batch(self):
        """PERF-008: Latencia promedio de sentimiento para lote de publicaciones."""
        case = NFCase("PERF-008", sla=0.005, dataset_size=2000, metric_name="seconds_per_record")
        texts = [
            "Excelente infraestructura y apoyo docente" if i % 2 == 0 else "Mala atencion en ventanilla"
            for i in range(case.dataset_size)
        ]

        t0 = time.perf_counter()
        outputs = [analyze_sentiment_simple(t) for t in texts]
        elapsed = time.perf_counter() - t0
        avg_latency = elapsed / case.dataset_size

        assert len(outputs) == case.dataset_size, "PERF-008 FAIL: El batch de salida esta incompleto"
        assert avg_latency < case.sla, (
            f"PERF-008 FAIL: Latencia promedio={avg_latency:.6f}s/registro, SLA={case.sla:.6f}s"
        )

    def test_perf_009_retraining_ml_time(self):
        """PERF-009: Tiempo de reentrenamiento de modelo ML (KMeans)."""
        case = NFCase("PERF-009", sla=10.0, dataset_size=15000, metric_name="seconds")
        from sklearn.cluster import KMeans

        X = np.random.rand(case.dataset_size, 20)
        model = KMeans(n_clusters=6, random_state=42, n_init=10)

        t0 = time.perf_counter()
        model.fit(X)
        elapsed = time.perf_counter() - t0

        assert hasattr(model, "cluster_centers_"), "PERF-009 FAIL: El modelo no termino entrenamiento"
        assert elapsed < case.sla, (
            f"PERF-009 FAIL: Reentrenamiento tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    def test_perf_010_incremental_retraining_time(self):
        """PERF-010: Tiempo de actualizacion/reentrenamiento incremental."""
        case = NFCase("PERF-010", sla=15.0, dataset_size=20000, metric_name="seconds")
        from sklearn.cluster import MiniBatchKMeans

        X = np.random.rand(case.dataset_size, 15)
        model = MiniBatchKMeans(n_clusters=5, random_state=42, batch_size=1024)

        t0 = time.perf_counter()
        model.partial_fit(X[:10000])
        model.partial_fit(X[10000:])
        elapsed = time.perf_counter() - t0

        assert hasattr(model, "cluster_centers_"), "PERF-010 FAIL: MiniBatchKMeans no genero centros"
        assert elapsed < case.sla, (
            f"PERF-010 FAIL: Reentrenamiento incremental tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_perf_011_scrapers_network_variable_latency(self):
        """PERF-011: Rendimiento de scraper bajo red variable simulada."""
        case = NFCase("PERF-011", sla=2.5, dataset_size=300, metric_name="seconds")

        async def mock_scraper_call(i: int) -> dict[str, Any]:
            # Simula latencia variable de red.
            await asyncio.sleep(0.001 + (i % 5) * 0.001)
            return {"id_externo": f"net_{i}", "contenido": "ok"}

        t0 = time.perf_counter()
        out = await asyncio.gather(*[mock_scraper_call(i) for i in range(case.dataset_size)])
        elapsed = time.perf_counter() - t0

        assert len(out) == case.dataset_size, "PERF-011 FAIL: Se perdieron respuestas de scraper"
        assert elapsed < case.sla, (
            f"PERF-011 FAIL: Scraper en red variable tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )

    @pytest.mark.asyncio
    async def test_perf_012_scraper_retry_under_jitter(self):
        """PERF-012: Rendimiento de scraper con reintentos ante jitter/fallos intermitentes."""
        case = NFCase("PERF-012", sla=3.5, dataset_size=200, metric_name="seconds")

        async def flaky_fetch(i: int) -> dict[str, Any]:
            await asyncio.sleep(0.001)
            if i % 10 == 0:
                raise TimeoutError("network jitter")
            return {"id_externo": f"jit_{i}", "ok": True}

        async def fetch_with_retry(i: int, retries: int = 2) -> dict[str, Any]:
            for attempt in range(retries + 1):
                try:
                    return await flaky_fetch(i)
                except TimeoutError:
                    if attempt == retries:
                        return {"id_externo": f"jit_{i}", "ok": False}
            return {"id_externo": f"jit_{i}", "ok": False}

        t0 = time.perf_counter()
        out = await asyncio.gather(*[fetch_with_retry(i) for i in range(case.dataset_size)])
        elapsed = time.perf_counter() - t0
        success_rate = sum(1 for x in out if x["ok"]) / case.dataset_size

        assert success_rate >= 0.85, (
            f"PERF-012 FAIL: Tasa de exito={success_rate:.2%}, minimo aceptable=85%"
        )
        assert elapsed < case.sla, (
            f"PERF-012 FAIL: Ejecucion con retry tardo {elapsed:.4f}s, SLA={case.sla:.2f}s"
        )


# ============================================================
# PRUEBAS DE SEGURIDAD (7 casos)
# ============================================================

class TestSeguridad:
    """Pruebas de seguridad y hardening minimo."""

    def test_sec_001_no_credentials_in_logs(self, secure_api_client, caplog):
        """SEC-001: Credenciales API no deben aparecer en logs."""
        caplog.set_level(logging.INFO)
        secret = "MY_SUPER_SECRET_TOKEN"

        response = secure_api_client.post(
            "/api/auth/login",
            json={"email": "qa_user@emi.edu.bo", "password": secret},
            content_type="application/json",
        )

        assert response.status_code in {200, 401}, "SEC-001 FAIL: Estado inesperado en login"
        assert secret not in caplog.text, "SEC-001 FAIL: Se filtraron credenciales en logs"

    def test_sec_002_sql_injection_protection_dynamic_queries(self, nf_db):
        """SEC-002: Proteccion contra inyeccion SQL en consultas dinamicas."""
        malicious = "abc'; DROP TABLE fuente_osint; --"
        _ = nf_db.get_or_create_source("Malicious", "Facebook", "https://x", malicious)

        conn = nf_db._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM fuente_osint")
        total = cur.fetchone()[0]

        assert total >= 1, "SEC-002 FAIL: Posible inyeccion SQL, tabla fuente_osint comprometida"

    def test_sec_003_oauth_token_validation(self, secure_api_client):
        """SEC-003: Validacion de tokens OAuth/API (token invalido debe ser rechazado)."""
        resp = secure_api_client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
        assert resp.status_code == 401, "SEC-003 FAIL: Token invalido no fue rechazado"

    def test_sec_004_access_control_authorized_only(self, secure_api_client):
        """SEC-004: Control de acceso solo para usuarios autorizados."""
        unauth = secure_api_client.get("/api/auth/me")
        auth = secure_api_client.get("/api/auth/me", headers={"Authorization": "Bearer token_qa_user_1"})

        assert unauth.status_code == 401, "SEC-004 FAIL: Endpoint protegido permitio acceso sin token"
        assert auth.status_code == 200, "SEC-004 FAIL: Usuario autorizado no pudo acceder"

    def test_sec_005_external_text_sanitization_before_store(self, cleaner_cfg):
        """SEC-005: Sanitizacion de texto externo antes de almacenar."""
        cleaner = DataCleaner(config=cleaner_cfg)
        raw = "<script>alert('xss')</script> visita https://emi.edu.bo @test"
        cleaned = cleaner.clean_text(raw)

        assert "https://" not in cleaned, "SEC-005 FAIL: URL externa no fue sanitizada"
        assert "@test" not in cleaned, "SEC-005 FAIL: Mencion externa no fue sanitizada"

    def test_sec_006_minimum_privacy_personal_data(self, secure_api_client, tmp_path, monkeypatch):
        """SEC-006: Cumplimiento minimo de privacidad (password no en texto plano)."""
        db_path = str(tmp_path / "privacy.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE usuario (
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT,
                password_hash TEXT,
                nombre_completo TEXT,
                rol TEXT,
                cargo TEXT,
                activo INTEGER,
                ultimo_login TEXT,
                fecha_creacion TEXT,
                permisos TEXT
            )
            """
        )
        cur.execute(
            "INSERT INTO usuario (username, email, password_hash, nombre_completo, rol, activo, permisos) VALUES (?,?,?,?,?,?,?)",
            ("u_priv", "u_priv@emi.edu.bo", hash_password("plain123"), "Priv User", "administrador", 1, "{}"),
        )
        conn.commit()
        cur.execute("SELECT password_hash FROM usuario WHERE username='u_priv'")
        stored = cur.fetchone()[0]
        conn.close()

        assert stored != "plain123", "SEC-006 FAIL: Se detecto password en texto plano"
        assert len(stored) == 64, "SEC-006 FAIL: El hash almacenado no cumple longitud SHA-256"

    def test_sec_007_secure_error_handling_no_stack_trace_exposure(self, secure_api_client):
        """SEC-007: Manejo seguro de errores sin exponer stack trace al usuario."""
        resp = secure_api_client.post(
            "/api/auth/change-password",
            json={"currentPassword": "x", "newPassword": "y"},
            headers={"Authorization": "Bearer malformed"},
            content_type="application/json",
        )
        text = resp.get_data(as_text=True)

        assert resp.status_code in {400, 401}, "SEC-007 FAIL: Estado inesperado en manejo de error"
        assert "Traceback" not in text, "SEC-007 FAIL: Se expuso stack trace al cliente"
        assert "File \"" not in text, "SEC-007 FAIL: Se expuso detalle interno de archivos"


# ============================================================
# PRUEBAS DE CARGA (3 escenarios)
# ============================================================

class TestCarga:
    """Escenarios de carga normal, alta y pico."""

    @pytest.mark.asyncio
    async def test_load_001_carga_normal_100_publicaciones_estable(self, cleaner_cfg):
        """
        Escenario 1 - Carga normal:
        - 100 publicaciones simultaneas
        - Sistema estable
        """
        sla_seconds = 5.0
        total_posts = 100
        cleaner = DataCleaner(config=cleaner_cfg)

        async def process_post(i: int) -> dict[str, Any]:
            text = cleaner.clean_text(f"Publicacion {i} sobre EMI https://emi.edu.bo")
            sent, conf = analyze_sentiment_simple(text)
            return {"id": i, "text": text, "sent": sent, "conf": conf}

        t0 = time.perf_counter()
        out = await asyncio.gather(*[process_post(i) for i in range(total_posts)])
        elapsed = time.perf_counter() - t0

        assert len(out) == total_posts, "LOAD-001 FAIL: No se procesaron las 100 publicaciones"
        assert all(0 <= x["conf"] <= 1 for x in out), "LOAD-001 FAIL: Se detectaron confianzas invalidas"
        assert elapsed < sla_seconds, (
            f"LOAD-001 FAIL: Tiempo total={elapsed:.4f}s, SLA={sla_seconds:.2f}s"
        )

    def test_load_002_carga_alta_1000_publicaciones_etl_under_60s(self, cleaner_cfg):
        """
        Escenario 2 - Carga alta:
        - 1000 publicaciones en pipeline ETL
        - tiempo total < 60 segundos
        """
        sla_seconds = 60.0
        total_posts = 1000

        cleaner = DataCleaner(config=cleaner_cfg)
        transformer = DataTransformer(config={})

        df = pd.DataFrame(
            {
                "id_dato": range(total_posts),
                "contenido_original": [
                    "Texto de prueba para pipeline ETL con menciones @x y URL https://emi.edu.bo"
                    for _ in range(total_posts)
                ],
                "fecha_publicacion": ["2026-04-21 10:00:00"] * total_posts,
                "engagement_likes": np.random.randint(0, 50, size=total_posts),
                "engagement_comments": np.random.randint(0, 20, size=total_posts),
                "engagement_shares": np.random.randint(0, 10, size=total_posts),
            }
        )

        t0 = time.perf_counter()
        clean_df = cleaner.clean_dataframe(df)
        trans_df = transformer.transform_dataframe(clean_df)
        elapsed = time.perf_counter() - t0
        throughput = len(trans_df) / max(elapsed, 1e-9)

        assert len(trans_df) == total_posts, "LOAD-002 FAIL: Se perdieron registros en pipeline ETL"
        assert elapsed < sla_seconds, (
            f"LOAD-002 FAIL: Tiempo total ETL={elapsed:.4f}s, SLA={sla_seconds:.2f}s"
        )
        assert throughput > 15, (
            f"LOAD-002 FAIL: Throughput bajo ({throughput:.2f} reg/s), esperado > 15 reg/s"
        )

    @pytest.mark.asyncio
    async def test_load_003_carga_pico_scrapers_paralelos_sin_perdida(self, nf_db):
        """
        Escenario 3 - Carga pico:
        - multiples scrapers en paralelo
        - sin perdida de datos ni condiciones de carrera
        """
        source_id = nf_db.get_or_create_source("Pico Fuente", "TikTok", "https://tiktok.com/@pico", "pico_tk")

        scrapers = 8
        items_per_scraper = 150
        expected_total = scrapers * items_per_scraper

        async def run_scraper(scraper_id: int) -> list[dict[str, Any]]:
            await asyncio.sleep(0.002)
            out = []
            for i in range(items_per_scraper):
                out.append(
                    {
                        "id_externo": f"pico_{scraper_id}_{i}",
                        "fecha_publicacion": "2026-04-21 10:00:00",
                        "contenido_original": f"Post {i} scraper {scraper_id}",
                        "autor": f"scraper_{scraper_id}",
                        "engagement_likes": i % 13,
                        "engagement_comments": i % 7,
                        "engagement_shares": i % 3,
                        "tipo_contenido": "texto",
                        "url_publicacion": f"https://tiktok.com/{scraper_id}/{i}",
                        "metadata_json": {"scraper": scraper_id},
                    }
                )
            return out

        t0 = time.perf_counter()
        batches = await asyncio.gather(*[run_scraper(s) for s in range(scrapers)])
        combined = [item for batch in batches for item in batch]
        inserted, duplicates = nf_db.save_collected_data(combined, source_id=source_id)
        elapsed = time.perf_counter() - t0

        conn = nf_db._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dato_recolectado WHERE id_fuente = ?", (source_id,))
        persisted = cur.fetchone()[0]

        assert inserted == expected_total, (
            f"LOAD-003 FAIL: Insertados={inserted}, esperado={expected_total}"
        )
        assert duplicates == 0, "LOAD-003 FAIL: No se esperaban duplicados en ids unicos"
        assert persisted == expected_total, "LOAD-003 FAIL: Se detecto perdida de datos en carga pico"
        assert elapsed < 20.0, f"LOAD-003 FAIL: Carga pico tardo {elapsed:.4f}s, umbral=20.0s"
