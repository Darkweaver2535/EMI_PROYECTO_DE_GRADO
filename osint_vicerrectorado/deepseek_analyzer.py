#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  Analizador con DeepSeek — Sistema OSINT EMI
═══════════════════════════════════════════════════════════════

Segunda capa de análisis que se ejecuta DESPUÉS del análisis BERT
de sentimiento. Toma cada post / comentario ya clasificado por BERT
y lo envía a DeepSeek (API compatible con OpenAI) para obtener una
clasificación estructurada y dinámica:

  - carrera(s) EMI mencionada(s)
  - tema principal y subtemas (institucional / académico)
  - sentimiento refinado + score (-1..1)
  - severidad (baja|media|alta|critica)
  - si es institucional / si es queja
  - keywords y un resumen de una frase

El resultado se guarda en `analisis_deepseek` y un resumen ejecutivo
agregado en `deepseek_resumen_global`. Estas tablas son la ÚNICA
fuente de los dashboards de carreras / reputación / insights.

Uso CLI:
    python deepseek_analyzer.py [--force] [--limit N]
"""

import os
import re
import json
import time
import sqlite3
import logging
import argparse
from pathlib import Path

import requests

from emi_careers import EMI_CAREERS, VALID_CAREER_IDS, careers_catalog_text

logger = logging.getLogger("OSINT.DeepSeek")

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'data' / 'osint_emi.db'
CONFIG_PATH = BASE_DIR / 'config.json'

# Valores por defecto (sobreescribibles por config.json / env)
DEFAULT_BASE_URL = 'https://api.deepseek.com'
DEFAULT_MODEL = 'deepseek-chat'
DEFAULT_BATCH_SIZE = 12
MAX_TEXT_CHARS = 600          # recorte por ítem para controlar tokens
REQUEST_TIMEOUT = 90          # segundos por llamada
MAX_RETRIES = 3


# ═══════════════════════════════════════════════════════════════
#   Configuración
# ═══════════════════════════════════════════════════════════════
def _load_config() -> dict:
    """Lee la sección `deepseek` de config.json, con override por entorno."""
    try:
        from env_loader import load_env
        load_env()
    except Exception:
        pass
    cfg = {}
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f).get('deepseek', {}) or {}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"No se pudo leer config.json: {e}")

    return {
        'api_key': os.getenv('DEEPSEEK_API_KEY') or cfg.get('api_key', ''),
        'model': os.getenv('DEEPSEEK_MODEL') or cfg.get('model', DEFAULT_MODEL),
        'base_url': (os.getenv('DEEPSEEK_BASE_URL')
                     or cfg.get('base_url', DEFAULT_BASE_URL)).rstrip('/'),
        'batch_size': int(os.getenv('DEEPSEEK_BATCH_SIZE',
                                    cfg.get('batch_size', DEFAULT_BATCH_SIZE))),
    }


class DeepSeekUnavailable(RuntimeError):
    """Se lanza cuando no hay clave o la API no responde; el pipeline no debe romperse."""


# ═══════════════════════════════════════════════════════════════
#   Esquema de base de datos
# ═══════════════════════════════════════════════════════════════
def _init_tables(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS analisis_deepseek (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_contenido VARCHAR(20) NOT NULL,   -- 'post' | 'comentario'
            id_contenido INTEGER NOT NULL,         -- id_dato_procesado o id_comentario
            carreras_json TEXT,                    -- JSON array de career IDs
            tema_principal VARCHAR(120),
            subtemas_json TEXT,                    -- JSON array
            sentimiento VARCHAR(20),               -- Positivo|Neutral|Negativo
            sentimiento_score REAL,                -- -1..1
            severidad VARCHAR(20),                 -- baja|media|alta|critica
            es_institucional BOOLEAN DEFAULT 0,
            es_queja BOOLEAN DEFAULT 0,
            keywords_json TEXT,                    -- JSON array
            resumen TEXT,
            raw_json TEXT,
            modelo VARCHAR(40) DEFAULT 'deepseek-chat',
            fecha_analisis TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tipo_contenido, id_contenido)
        )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_ds_tipo ON analisis_deepseek(tipo_contenido)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_ds_severidad ON analisis_deepseek(severidad)')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deepseek_resumen_global (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resumen_ejecutivo TEXT,
            sentimiento_general VARCHAR(20),
            temas_criticos_json TEXT,
            recomendaciones_json TEXT,
            carreras_destacadas_json TEXT,
            total_analizados INTEGER,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


# ═══════════════════════════════════════════════════════════════
#   Cliente HTTP
# ═══════════════════════════════════════════════════════════════
def _call_deepseek(cfg: dict, messages: list, max_tokens: int = 4000) -> dict:
    """Llama al endpoint chat/completions y devuelve el JSON parseado del contenido.

    Lanza DeepSeekUnavailable si no hay clave o falla tras los reintentos.
    """
    if not cfg['api_key']:
        raise DeepSeekUnavailable("No hay DEEPSEEK_API_KEY configurada (env o config.json).")

    url = f"{cfg['base_url']}/chat/completions"
    headers = {
        'Authorization': f"Bearer {cfg['api_key']}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': cfg['model'],
        'messages': messages,
        'response_format': {'type': 'json_object'},
        'temperature': 0,
        'max_tokens': max_tokens,
    }

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                content = r.json()['choices'][0]['message']['content']
                return json.loads(content)
            # 429 / 5xx → reintentar con backoff
            if r.status_code in (429, 500, 502, 503, 504):
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                logger.warning(f"DeepSeek {last_err} (intento {attempt}/{MAX_RETRIES})")
                time.sleep(2 ** attempt)
                continue
            # Errores no recuperables (401, 400, ...)
            raise DeepSeekUnavailable(f"HTTP {r.status_code}: {r.text[:200]}")
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            last_err = str(e)
            logger.warning(f"DeepSeek error: {e} (intento {attempt}/{MAX_RETRIES})")
            time.sleep(2 ** attempt)

    raise DeepSeekUnavailable(f"DeepSeek no disponible tras {MAX_RETRIES} intentos: {last_err}")


# ═══════════════════════════════════════════════════════════════
#   Prompts
# ═══════════════════════════════════════════════════════════════
_SYSTEM_PROMPT = (
    "Eres un analista OSINT de la Escuela Militar de Ingeniería (EMI) de Bolivia. "
    "Clasificas publicaciones y comentarios de redes sociales sobre la EMI. "
    "Respondes SIEMPRE en JSON válido, en español, sin texto adicional."
)


def _build_batch_prompt(items: list) -> str:
    catalogo = careers_catalog_text()
    items_txt = json.dumps(
        [{'id': it['key'], 'tipo': it['tipo'], 'sentimiento_bert': it['sent_bert'],
          'texto': it['texto'][:MAX_TEXT_CHARS]} for it in items],
        ensure_ascii=False
    )
    return (
        "Catálogo de carreras oficiales de la EMI (id: nombre):\n"
        f"{catalogo}\n\n"
        "Analiza CADA ítem del siguiente arreglo. Devuelve un objeto JSON con la clave "
        "\"resultados\" que contenga un arreglo, un objeto por ítem EN EL MISMO ORDEN, "
        "con EXACTAMENTE estos campos:\n"
        "  - id: el id del ítem (string, igual al de entrada)\n"
        "  - carreras: arreglo de ids (string) de carreras del catálogo mencionadas o claramente aludidas; [] si ninguna\n"
        "  - tema_principal: tema institucional/académico en 1-3 palabras (ej. 'infraestructura', 'inscripciones', 'docentes', 'eventos')\n"
        "  - subtemas: arreglo de strings (0-3)\n"
        "  - sentimiento: 'Positivo' | 'Neutral' | 'Negativo'\n"
        "  - sentimiento_score: número entre -1 (muy negativo) y 1 (muy positivo)\n"
        "  - severidad: 'baja' | 'media' | 'alta' | 'critica' (qué tan urgente es para la institución)\n"
        "  - es_institucional: true si trata de la EMI como institución (trámites, infraestructura, docentes, pagos, carreras, eventos); false si es contenido personal/irrelevante\n"
        "  - es_queja: true si expresa una queja o reclamo\n"
        "  - keywords: arreglo de 1-5 palabras clave\n"
        "  - resumen: una frase corta describiendo el ítem\n\n"
        "Solo usa ids de carrera presentes en el catálogo. No inventes carreras.\n\n"
        f"Ítems a analizar:\n{items_txt}"
    )


def _build_summary_prompt(stats: dict, temas: list, carreras: list, ejemplos_negativos: list) -> str:
    return (
        "Con base en el análisis agregado de publicaciones y comentarios sobre la EMI, "
        "genera un resumen ejecutivo para el Vicerrectorado. Devuelve SOLO un objeto JSON con:\n"
        "  - resumen_ejecutivo: párrafo (3-5 frases) sobre el estado de la percepción pública\n"
        "  - sentimiento_general: 'Positivo' | 'Neutral' | 'Negativo'\n"
        "  - temas_criticos: arreglo de objetos { tema, severidad, descripcion } (máx 5)\n"
        "  - recomendaciones: arreglo de strings accionables (máx 5)\n"
        "  - carreras_destacadas: arreglo de objetos { careerId, careerName, observacion } (máx 5)\n\n"
        f"Distribución de sentimiento: {json.dumps(stats, ensure_ascii=False)}\n"
        f"Temas más frecuentes: {json.dumps(temas, ensure_ascii=False)}\n"
        f"Carreras más mencionadas: {json.dumps(carreras, ensure_ascii=False)}\n"
        f"Ejemplos de contenido negativo institucional: {json.dumps(ejemplos_negativos, ensure_ascii=False)}"
    )


# ═══════════════════════════════════════════════════════════════
#   Carga de pendientes
# ═══════════════════════════════════════════════════════════════
def _load_pending(conn: sqlite3.Connection, force: bool, limit) -> list:
    """Devuelve ítems analizados por BERT que faltan por procesar con DeepSeek."""
    cur = conn.cursor()
    items = []

    # Posts (dato_procesado + sentimiento BERT)
    where_post = "" if force else (
        "AND dp.id_dato_procesado NOT IN "
        "(SELECT id_contenido FROM analisis_deepseek WHERE tipo_contenido='post')"
    )
    cur.execute(f'''
        SELECT dp.id_dato_procesado AS id, dp.contenido_limpio AS texto,
               a.sentimiento_predicho AS sent
        FROM dato_procesado dp
        JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE dp.contenido_limpio IS NOT NULL AND LENGTH(dp.contenido_limpio) > 3
        {where_post}
    ''')
    for r in cur.fetchall():
        items.append({'tipo': 'post', 'id': r['id'], 'key': f"post:{r['id']}",
                      'texto': r['texto'] or '', 'sent_bert': r['sent'] or 'Neutral'})

    # Comentarios (comentario + sentimiento BERT)
    where_com = "" if force else (
        "AND c.id_comentario NOT IN "
        "(SELECT id_contenido FROM analisis_deepseek WHERE tipo_contenido='comentario')"
    )
    # LEFT JOIN: DeepSeek analiza TODOS los comentarios no vacíos, incluso los de
    # solo emojis (🥰❤️👏🔥), que BERT descarta por longitud. DeepSeek interpreta
    # bien los emojis, así esas reacciones (normalmente positivas) sí se clasifican.
    cur.execute(f'''
        SELECT c.id_comentario AS id, c.contenido AS texto,
               COALESCE(ac.sentimiento, 'Neutral') AS sent
        FROM comentario c
        LEFT JOIN analisis_comentario ac ON c.id_comentario = ac.id_comentario
        WHERE c.contenido IS NOT NULL AND LENGTH(TRIM(c.contenido)) >= 1
        {where_com}
    ''')
    for r in cur.fetchall():
        items.append({'tipo': 'comentario', 'id': r['id'], 'key': f"com:{r['id']}",
                      'texto': r['texto'] or '', 'sent_bert': r['sent'] or 'Neutral'})

    if limit:
        items = items[:int(limit)]
    return items


# ═══════════════════════════════════════════════════════════════
#   Normalización / persistencia de resultados
# ═══════════════════════════════════════════════════════════════
_SENT_VALID = {'Positivo', 'Neutral', 'Negativo'}
_SEV_VALID = {'baja', 'media', 'alta', 'critica'}


def _clean_careers(value) -> list:
    out = []
    if isinstance(value, list):
        for v in value:
            cid = str(v).strip()
            if cid in VALID_CAREER_IDS and cid not in out:
                out.append(cid)
    return out


def _to_bool(v) -> int:
    return 1 if v in (True, 1, 'true', 'True', 'si', 'sí') else 0


def _persist_item(conn, item, res) -> None:
    sent = res.get('sentimiento', '')
    sent = sent if sent in _SENT_VALID else item['sent_bert']
    sev = str(res.get('severidad', 'baja')).lower()
    sev = sev if sev in _SEV_VALID else 'baja'
    try:
        score = float(res.get('sentimiento_score'))
        score = max(-1.0, min(1.0, score))
    except (TypeError, ValueError):
        score = {'Positivo': 0.6, 'Neutral': 0.0, 'Negativo': -0.6}.get(sent, 0.0)

    conn.execute('''
        INSERT INTO analisis_deepseek
            (tipo_contenido, id_contenido, carreras_json, tema_principal, subtemas_json,
             sentimiento, sentimiento_score, severidad, es_institucional, es_queja,
             keywords_json, resumen, raw_json, modelo, fecha_analisis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(tipo_contenido, id_contenido) DO UPDATE SET
            carreras_json=excluded.carreras_json,
            tema_principal=excluded.tema_principal,
            subtemas_json=excluded.subtemas_json,
            sentimiento=excluded.sentimiento,
            sentimiento_score=excluded.sentimiento_score,
            severidad=excluded.severidad,
            es_institucional=excluded.es_institucional,
            es_queja=excluded.es_queja,
            keywords_json=excluded.keywords_json,
            resumen=excluded.resumen,
            raw_json=excluded.raw_json,
            fecha_analisis=excluded.fecha_analisis
    ''', (
        item['tipo'], item['id'],
        json.dumps(_clean_careers(res.get('carreras')), ensure_ascii=False),
        (res.get('tema_principal') or 'general')[:120],
        json.dumps(res.get('subtemas') or [], ensure_ascii=False),
        sent, score, sev,
        _to_bool(res.get('es_institucional')),
        _to_bool(res.get('es_queja')),
        json.dumps(res.get('keywords') or [], ensure_ascii=False),
        (res.get('resumen') or '')[:500],
        json.dumps(res, ensure_ascii=False),
        'deepseek',
    ))


# ═══════════════════════════════════════════════════════════════
#   Generación de alertas (reemplaza la heurística de keywords)
# ═══════════════════════════════════════════════════════════════
def _generar_alertas(conn) -> int:
    """Crea alertas en la tabla `alerta` desde el análisis DeepSeek.

    Solo contenido institucional con severidad alta/crítica.
    """
    cur = conn.cursor()
    _sev_ok = ('baja', 'media', 'alta', 'critica')

    # Posts institucionales relevantes: severidad alta/crítica O sentimiento negativo
    cur.execute('''
        SELECT ds.id_contenido AS id, ds.severidad, ds.sentimiento, ds.tema_principal,
               ds.resumen, dp.contenido_limpio AS texto, f.tipo_fuente AS fuente
        FROM analisis_deepseek ds
        JOIN dato_procesado dp ON ds.id_contenido = dp.id_dato_procesado
        JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
        JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
        WHERE ds.tipo_contenido='post' AND ds.es_institucional=1
          AND (ds.severidad IN ('alta','critica') OR ds.sentimiento='Negativo')
          AND ds.id_contenido NOT IN (SELECT id_dato_procesado FROM alerta WHERE id_dato_procesado IS NOT NULL)
    ''')
    generadas = 0
    for r in cur.fetchall():
        sev = r['severidad'] if r['severidad'] in _sev_ok else 'media'
        titulo = f"[{r['tema_principal']}] Tema institucional detectado (IA)"
        descripcion = (r['resumen'] or r['texto'] or '')[:500]
        conn.execute('''
            INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado,
                                id_dato_procesado, confianza, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, 'nueva', ?, ?, datetime('now'))
        ''', ('deepseek_institucional', sev, titulo, descripcion,
              r['fuente'], r['id'], 0.9))
        generadas += 1

    # Comentarios institucionales relevantes
    cur.execute('''
        SELECT ds.id_contenido AS id, ds.severidad, ds.sentimiento, ds.tema_principal,
               ds.resumen, c.contenido AS texto, f.tipo_fuente AS fuente
        FROM analisis_deepseek ds
        JOIN comentario c ON ds.id_contenido = c.id_comentario
        JOIN fuente_osint f ON c.id_fuente = f.id_fuente
        WHERE ds.tipo_contenido='comentario' AND ds.es_institucional=1
          AND (ds.severidad IN ('alta','critica') OR ds.sentimiento='Negativo')
    ''')
    for r in cur.fetchall():
        descripcion = (r['resumen'] or r['texto'] or '')[:500]
        cur2 = conn.execute("SELECT 1 FROM alerta WHERE descripcion = ? AND tipo='deepseek_institucional'",
                            (descripcion,))
        if cur2.fetchone():
            continue
        sev = r['severidad'] if r['severidad'] in _sev_ok else 'media'
        titulo = f"[{r['tema_principal']}] Comentario institucional (IA)"
        conn.execute('''
            INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado,
                                confianza, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, 'nueva', ?, datetime('now'))
        ''', ('deepseek_institucional', sev, titulo, descripcion, r['fuente'], 0.85))
        generadas += 1

    conn.commit()
    return generadas


# ═══════════════════════════════════════════════════════════════
#   Resumen ejecutivo agregado
# ═══════════════════════════════════════════════════════════════
def _generar_insights(conn, cfg) -> bool:
    # Los insights del Vicerrectorado se basan SOLO en contenido institucional
    # (es_institucional=1); el contenido personal/no institucional se excluye.
    cur = conn.cursor()
    cur.execute("SELECT sentimiento, COUNT(*) c FROM analisis_deepseek WHERE es_institucional=1 GROUP BY sentimiento")
    stats = {row['sentimiento']: row['c'] for row in cur.fetchall()}
    total = sum(stats.values())
    if total == 0:
        return False

    cur.execute('''SELECT tema_principal, COUNT(*) c FROM analisis_deepseek
                   WHERE tema_principal IS NOT NULL AND es_institucional=1 GROUP BY tema_principal
                   ORDER BY c DESC LIMIT 12''')
    temas = [{'tema': r['tema_principal'], 'menciones': r['c']} for r in cur.fetchall()]

    # Conteo de carreras desde carreras_json (solo institucional)
    career_counts = {}
    cur.execute("SELECT carreras_json FROM analisis_deepseek WHERE carreras_json IS NOT NULL AND es_institucional=1")
    for r in cur.fetchall():
        try:
            for cid in json.loads(r['carreras_json']):
                career_counts[cid] = career_counts.get(cid, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    carreras = sorted(
        ({'careerId': cid, 'careerName': EMI_CAREERS.get(cid, cid), 'menciones': n}
         for cid, n in career_counts.items()),
        key=lambda x: x['menciones'], reverse=True)[:10]

    cur.execute('''SELECT resumen FROM analisis_deepseek
                   WHERE es_institucional=1 AND sentimiento='Negativo'
                   ORDER BY severidad DESC LIMIT 10''')
    ejemplos = [r['resumen'] for r in cur.fetchall() if r['resumen']]

    prompt = _build_summary_prompt(stats, temas, carreras, ejemplos)
    try:
        res = _call_deepseek(cfg, [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ], max_tokens=2000)
    except DeepSeekUnavailable as e:
        logger.warning(f"No se pudo generar insights ejecutivos: {e}")
        return False

    conn.execute('''
        INSERT INTO deepseek_resumen_global
            (resumen_ejecutivo, sentimiento_general, temas_criticos_json,
             recomendaciones_json, carreras_destacadas_json, total_analizados, fecha)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (
        res.get('resumen_ejecutivo', ''),
        res.get('sentimiento_general', 'Neutral'),
        json.dumps(res.get('temas_criticos') or [], ensure_ascii=False),
        json.dumps(res.get('recomendaciones') or [], ensure_ascii=False),
        json.dumps(res.get('carreras_destacadas') or carreras, ensure_ascii=False),
        total,
    ))
    conn.commit()
    return True


# ═══════════════════════════════════════════════════════════════
#   Análisis de NOTICIAS (NEWSINT) con DeepSeek
# ═══════════════════════════════════════════════════════════════
def analizar_noticias(force: bool = False, limit=None) -> dict:
    """Clasifica con IA las noticias de osint_noticias (medios bolivianos).

    Por cada noticia obtiene: sentimiento, tema, si es realmente sobre la EMI
    de Bolivia, tono mediático e impacto reputacional. Actualiza la fila.
    """
    cfg = _load_config()
    stats = {'analizadas': 0, 'error': None}
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # ¿Existe la tabla de noticias?
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='osint_noticias'")
        if not cur.fetchone():
            return stats

        where = "" if force else "WHERE (procesado IS NULL OR procesado = 0)"
        cur.execute(f"SELECT id, titulo, resumen FROM osint_noticias {where} ORDER BY id DESC")
        rows = cur.fetchall()
        if limit:
            rows = rows[:int(limit)]
        if not rows:
            return stats

        bs = max(1, cfg['batch_size'])
        catalogo = careers_catalog_text()
        for i in range(0, len(rows), bs):
            batch = rows[i:i + bs]
            items_txt = json.dumps(
                [{'id': r['id'], 'titular': (r['titulo'] or '')[:200],
                  'resumen': (r['resumen'] or '')[:400]} for r in batch],
                ensure_ascii=False)
            prompt = (
                "Analiza noticias de medios bolivianos sobre la Escuela Militar de "
                "Ingeniería (EMI) de Bolivia. Para CADA ítem devuelve un objeto JSON "
                "en la clave \"resultados\" (arreglo, mismo orden) con:\n"
                "  - id\n"
                "  - es_emi_bolivia: true solo si trata de la EMI de BOLIVIA (no de otro país)\n"
                "  - sentimiento: 'Positivo' | 'Neutral' | 'Negativo'\n"
                "  - tema_principal: 1-3 palabras\n"
                "  - impacto_reputacional: 'alto' | 'medio' | 'bajo'\n"
                "  - carreras: ids del catálogo mencionados, [] si ninguno\n"
                "  - resumen: una frase\n\n"
                f"Catálogo de carreras:\n{catalogo}\n\nNoticias:\n{items_txt}"
            )
            try:
                data = _call_deepseek(cfg, [
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ])
            except DeepSeekUnavailable as e:
                stats['error'] = str(e)
                break

            resultados = data.get('resultados') if isinstance(data, dict) else data
            if not isinstance(resultados, list):
                continue
            by_id = {str(r.get('id')): r for r in resultados if isinstance(r, dict)}
            for r in batch:
                res = by_id.get(str(r['id']))
                if not res:
                    continue
                sent = res.get('sentimiento')
                sent = sent if sent in _SENT_VALID else 'Neutral'
                meta = {
                    'tema_principal': (res.get('tema_principal') or 'general')[:80],
                    'impacto_reputacional': res.get('impacto_reputacional', 'bajo'),
                    'es_emi_bolivia': _to_bool(res.get('es_emi_bolivia')),
                    'carreras': _clean_careers(res.get('carreras')),
                    'resumen_ia': (res.get('resumen') or '')[:300],
                }
                conn.execute('''
                    UPDATE osint_noticias
                    SET sentimiento = ?, temas_json = ?, procesado = 1
                    WHERE id = ?
                ''', (sent, json.dumps(meta, ensure_ascii=False), r['id']))
                stats['analizadas'] += 1
            conn.commit()

        logger.info(f"📰🤖 DeepSeek noticias: {stats['analizadas']} clasificadas")
        return stats
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
#   Orquestador principal
# ═══════════════════════════════════════════════════════════════
def analizar_con_deepseek(force: bool = False, limit=None) -> dict:
    """Ejecuta el análisis DeepSeek sobre los datos ya analizados por BERT.

    No lanza excepción si DeepSeek no está disponible: registra el motivo y
    devuelve stats con `error`, para no romper el pipeline BERT.
    """
    cfg = _load_config()
    stats = {'analizados': 0, 'lotes': 0, 'alertas': 0, 'insights': False, 'error': None}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        _init_tables(conn)
        pendientes = _load_pending(conn, force, limit)
        logger.info(f"🤖 DeepSeek: {len(pendientes)} ítems pendientes de análisis")
        if not pendientes:
            # Aún así (re)generamos insights si hay datos previos
            stats['insights'] = _generar_insights(conn, cfg)
            conn.close()
            try:
                stats['noticias'] = analizar_noticias(force=force)
            except Exception as e:
                stats['noticias'] = {'error': str(e)}
            return stats

        bs = max(1, cfg['batch_size'])
        for i in range(0, len(pendientes), bs):
            batch = pendientes[i:i + bs]
            prompt = _build_batch_prompt(batch)
            try:
                data = _call_deepseek(cfg, [
                    {'role': 'system', 'content': _SYSTEM_PROMPT},
                    {'role': 'user', 'content': prompt},
                ])
            except DeepSeekUnavailable as e:
                logger.error(f"DeepSeek no disponible, abortando lote: {e}")
                stats['error'] = str(e)
                break

            resultados = data.get('resultados') if isinstance(data, dict) else data
            if not isinstance(resultados, list):
                logger.warning("Respuesta DeepSeek sin arreglo 'resultados'; lote omitido")
                continue

            # Mapear por id; si falta, usar orden posicional
            by_id = {str(r.get('id')): r for r in resultados if isinstance(r, dict)}
            for idx, item in enumerate(batch):
                res = by_id.get(item['key']) or (resultados[idx]
                       if idx < len(resultados) and isinstance(resultados[idx], dict) else None)
                if res is None:
                    continue
                _persist_item(conn, item, res)
                stats['analizados'] += 1
            conn.commit()
            stats['lotes'] += 1
            logger.info(f"  Lote {stats['lotes']}: {stats['analizados']}/{len(pendientes)} analizados")

        # Alertas + insights agregados
        try:
            stats['alertas'] = _generar_alertas(conn)
        except Exception as e:
            logger.warning(f"No se pudieron generar alertas DeepSeek: {e}")
        if stats['analizados'] > 0 and not stats['error']:
            stats['insights'] = _generar_insights(conn, cfg)

        logger.info(f"✅ DeepSeek: {stats['analizados']} analizados, "
                    f"{stats['alertas']} alertas, insights={stats['insights']}")
    finally:
        conn.close()

    # Clasificar también las noticias pendientes (NEWSINT)
    try:
        stats['noticias'] = analizar_noticias()
    except Exception as e:
        logger.warning(f"No se pudieron analizar noticias con IA: {e}")
        stats['noticias'] = {'error': str(e)}
    return stats


# ═══════════════════════════════════════════════════════════════
#   CLI
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description='Análisis DeepSeek post-BERT (OSINT EMI)')
    parser.add_argument('--force', action='store_true', help='Re-analiza todo, incluso lo ya procesado')
    parser.add_argument('--limit', type=int, default=None, help='Limita la cantidad de ítems (pruebas)')
    args = parser.parse_args()

    result = analizar_con_deepseek(force=args.force, limit=args.limit)
    print("\n" + "=" * 50)
    print("RESULTADO DEEPSEEK")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
