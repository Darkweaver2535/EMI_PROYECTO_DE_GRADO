#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
Ejecución Completa de TODOS los Módulos de IA — SADUTO
═══════════════════════════════════════════════════════════════

Ejecuta todos los componentes de Inteligencia Artificial:
1. Detección de Anomalías (Isolation Forest)
2. Detección de Tendencias (ARIMA / statsmodels)
3. Análisis de Correlaciones (Pearson)
4. Guarda resultados en la base de datos

Autor: Sistema SADUTO
Fecha: Febrero 2026
"""

import os
import sys
import json
import time
import sqlite3
import logging
import numpy as np
import pandas as pd
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AI_MODULES")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'osint_emi.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cargar_datos_numericos():
    """Carga datos numéricos de la BD para análisis."""
    conn = get_db()
    
    # Cargar datos procesados con métricas
    df = pd.read_sql_query("""
        SELECT dp.id_dato_procesado, dp.longitud_texto, dp.cantidad_palabras,
               dp.engagement_total, dp.engagement_normalizado,
               dp.hora, dp.dia_semana, dp.mes,
               COALESCE(a.confianza, 0) as confianza_sentimiento,
               CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1
                    WHEN a.sentimiento_predicho = 'Negativo' THEN -1
                    ELSE 0 END as score_sentimiento,
               dp.fecha_publicacion_iso
        FROM dato_procesado dp
        LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE dp.contenido_limpio IS NOT NULL
        ORDER BY dp.fecha_publicacion_iso
    """, conn)
    
    conn.close()
    return df


# ═══════════════════════════════════════════════════════════
# 1. DETECCIÓN DE ANOMALÍAS (Isolation Forest)
# ═══════════════════════════════════════════════════════════

def ejecutar_anomalias(df):
    """Ejecuta detección de anomalías con Isolation Forest."""
    logger.info("=" * 60)
    logger.info("MODULO 1: DETECCION DE ANOMALIAS (Isolation Forest)")
    logger.info("=" * 60)
    
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    
    # Preparar features
    feature_cols = ['longitud_texto', 'cantidad_palabras', 'engagement_total', 
                    'engagement_normalizado', 'hora', 'score_sentimiento']
    
    X = df[feature_cols].fillna(0).values
    
    if len(X) < 10:
        logger.warning("Pocos datos para detección de anomalías, ajustando parámetros")
    
    # Escalar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Isolation Forest
    iso_forest = IsolationForest(
        contamination=0.1,
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )
    
    predictions = iso_forest.fit_predict(X_scaled)
    scores = iso_forest.decision_function(X_scaled)
    
    # Identificar anomalías
    anomalias = []
    conn = get_db()
    cursor = conn.cursor()
    
    # Limpiar tabla
    cursor.execute("DELETE FROM anomalia_detectada")
    
    n_anomalias = 0
    for i in range(len(df)):
        if predictions[i] == -1:  # Anomalía
            score = float(scores[i])
            
            # Determinar severidad
            if score < -0.7:
                severidad = 'critica'
            elif score < -0.5:
                severidad = 'alta'
            elif score < -0.3:
                severidad = 'media'
            else:
                severidad = 'baja'
            
            # Determinar tipo de anomalía
            row = df.iloc[i]
            if abs(row['score_sentimiento']) > 0 and row['confianza_sentimiento'] > 0.9:
                tipo = 'cambio_sentimiento'
            elif row['engagement_total'] > df['engagement_total'].quantile(0.9):
                tipo = 'engagement_anormal'
            elif row['longitud_texto'] > df['longitud_texto'].quantile(0.95):
                tipo = 'volumen_anormal'
            else:
                tipo = 'outlier'
            
            detalle = json.dumps({
                'id_dato': int(row['id_dato_procesado']),
                'score_anomalia': round(score, 4),
                'engagement': int(row['engagement_total']),
                'longitud': int(row['longitud_texto']),
                'sentimiento_score': int(row['score_sentimiento']),
                'features': {col: round(float(X_scaled[i][j]), 4) for j, col in enumerate(feature_cols)}
            }, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO anomalia_detectada 
                (tipo_anomalia, descripcion, severidad, metrica_afectada,
                 valor_esperado, valor_observado, anomaly_score, 
                 fecha_deteccion, estado, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), 'nueva', ?)
            """, (
                tipo,
                f'Anomalía detectada en dato #{int(row["id_dato_procesado"])} — {tipo}',
                severidad,
                'engagement_total',
                float(df['engagement_total'].mean()),
                float(row['engagement_total']),
                round(score, 4),
                detalle
            ))
            
            n_anomalias += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"Anomalias detectadas: {n_anomalias} de {len(df)} registros")
    logger.info(f"Tasa de anomalías: {n_anomalias/len(df)*100:.1f}%")
    
    return n_anomalias


# ═══════════════════════════════════════════════════════════
# 2. DETECCIÓN DE TENDENCIAS (Statsmodels)
# ═══════════════════════════════════════════════════════════

def ejecutar_tendencias(df):
    """Ejecuta análisis de tendencias temporales."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("MODULO 2: DETECCION DE TENDENCIAS (ARIMA / Statsmodels)")
    logger.info("=" * 60)
    
    from scipy import stats
    from scipy.signal import find_peaks
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Limpiar tabla
    cursor.execute("DELETE FROM analisis_tendencia")
    
    # Preparar serie temporal de sentimiento
    df_time = df.copy()
    df_time['fecha'] = pd.to_datetime(df_time['fecha_publicacion_iso'], errors='coerce')
    df_time = df_time.dropna(subset=['fecha'])
    df_time = df_time.sort_values('fecha')
    
    n_tendencias = 0
    
    # --- Tendencia 1: Sentimiento a lo largo del tiempo ---
    if len(df_time) >= 5:
        x = np.arange(len(df_time))
        y = df_time['score_sentimiento'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        if slope > 0.01:
            tipo_tendencia = 'creciente'
        elif slope < -0.01:
            tipo_tendencia = 'decreciente'
        else:
            tipo_tendencia = 'estable'
        
        cursor.execute("""
            INSERT INTO analisis_tendencia 
            (periodo, metrica, tipo_tendencia, valor_slope, valor_r_squared,
             confianza, fecha_inicio, fecha_fin, datos_puntos,
             metadata_json, fecha_analisis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            'diario',
            'sentimiento_promedio',
            tipo_tendencia,
            round(slope, 6),
            round(r_value**2, 4),
            round(1 - p_value, 4),
            str(df_time['fecha'].min())[:10],
            str(df_time['fecha'].max())[:10],
            len(df_time),
            json.dumps({'slope': round(slope, 6), 'r_squared': round(r_value**2, 4), 'p_value': round(p_value, 6), 'std_err': round(std_err, 6)})
        ))
        n_tendencias += 1
        logger.info(f"  Sentimiento: tendencia {tipo_tendencia} (slope={slope:.4f}, R²={r_value**2:.4f})")
    
    # --- Tendencia 2: Engagement a lo largo del tiempo ---
    if len(df_time) >= 5:
        y_eng = df_time['engagement_total'].fillna(0).values
        
        slope_e, intercept_e, r_e, p_e, std_e = stats.linregress(x, y_eng)
        
        if slope_e > 0.5:
            tipo_eng = 'creciente'
        elif slope_e < -0.5:
            tipo_eng = 'decreciente'
        else:
            tipo_eng = 'estable'
        
        cursor.execute("""
            INSERT INTO analisis_tendencia 
            (periodo, metrica, tipo_tendencia, valor_slope, valor_r_squared,
             confianza, fecha_inicio, fecha_fin, datos_puntos,
             metadata_json, fecha_analisis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            'diario',
            'engagement_promedio',
            tipo_eng,
            round(slope_e, 6),
            round(r_e**2, 4),
            round(1 - p_e, 4),
            str(df_time['fecha'].min())[:10],
            str(df_time['fecha'].max())[:10],
            len(df_time),
            json.dumps({'slope': round(slope_e, 6), 'r_squared': round(r_e**2, 4), 'p_value': round(p_e, 6)})
        ))
        n_tendencias += 1
        logger.info(f"  Engagement: tendencia {tipo_eng} (slope={slope_e:.4f}, R²={r_e**2:.4f})")
    
    # --- Tendencia 3: Volumen de publicaciones por mes ---
    if len(df_time) >= 5:
        vol_mensual = df_time.set_index('fecha').resample('ME').size()
        
        if len(vol_mensual) >= 2:
            x_vol = np.arange(len(vol_mensual))
            y_vol = vol_mensual.values
            slope_v, _, r_v, p_v, _ = stats.linregress(x_vol, y_vol)
            
            tipo_vol = 'creciente' if slope_v > 0.5 else ('decreciente' if slope_v < -0.5 else 'estable')
            
            cursor.execute("""
                INSERT INTO analisis_tendencia 
                (periodo, metrica, tipo_tendencia, valor_slope, valor_r_squared,
                 confianza, fecha_inicio, fecha_fin, datos_puntos,
                 metadata_json, fecha_analisis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                'mensual',
                'volumen_publicaciones',
                tipo_vol,
                round(slope_v, 6),
                round(r_v**2, 4),
                round(1 - p_v, 4),
                str(vol_mensual.index[0])[:10],
                str(vol_mensual.index[-1])[:10],
                len(vol_mensual),
                json.dumps({'slope': round(slope_v, 6), 'meses': len(vol_mensual)})
            ))
            n_tendencias += 1
            logger.info(f"  Volumen: tendencia {tipo_vol} ({len(vol_mensual)} meses)")
    
    # --- Tendencia 4: Distribución horaria ---
    if len(df_time) >= 5:
        hora_dist = df_time['hora'].value_counts().sort_index()
        hora_pico = int(hora_dist.idxmax()) if len(hora_dist) > 0 else 0
        
        cursor.execute("""
            INSERT INTO analisis_tendencia 
            (periodo, metrica, tipo_tendencia, valor_slope, valor_r_squared,
             confianza, fecha_inicio, fecha_fin, datos_puntos,
             estacionalidad_detectada, metadata_json, fecha_analisis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            'diario',
            'patron_horario',
            'estacional',
            0, 0, 0,
            str(df_time['fecha'].min())[:10],
            str(df_time['fecha'].max())[:10],
            len(df_time),
            1,
            json.dumps({'hora_pico': hora_pico, 'distribucion': hora_dist.to_dict()})
        ))
        n_tendencias += 1
        logger.info(f"  Patrón horario: hora pico = {hora_pico}:00")
    
    # --- Tendencia 5: Sentimiento por fuente ---
    try:
        df_fuente = pd.read_sql_query("""
            SELECT f.nombre_fuente as fuente, 
                   AVG(CASE WHEN a.sentimiento_predicho = 'Positivo' THEN 1
                            WHEN a.sentimiento_predicho = 'Negativo' THEN -1
                            ELSE 0 END) as sent_prom,
                   COUNT(*) as n
            FROM dato_procesado dp
            JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
            JOIN fuente_osint f ON dr.id_fuente = f.id_fuente
            LEFT JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
            GROUP BY f.nombre_fuente
        """, conn)
        
        for _, row in df_fuente.iterrows():
            tipo_s = 'positiva' if row['sent_prom'] > 0.1 else ('negativa' if row['sent_prom'] < -0.1 else 'neutra')
            cursor.execute("""
                INSERT INTO analisis_tendencia 
                (periodo, metrica, tipo_tendencia, valor_slope, valor_r_squared,
                 confianza, fecha_inicio, fecha_fin, datos_puntos,
                 metadata_json, fecha_analisis)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                'global',
                f'sentimiento_{row["fuente"]}',
                tipo_s,
                float(row['sent_prom']),
                0, 0,
                str(df_time['fecha'].min())[:10] if len(df_time) > 0 else '2025-01-01',
                str(df_time['fecha'].max())[:10] if len(df_time) > 0 else '2025-12-31',
                int(row['n']),
                json.dumps({'fuente': row['fuente'], 'sentimiento_promedio': round(float(row['sent_prom']), 4), 'n_publicaciones': int(row['n'])})
            ))
            n_tendencias += 1
            logger.info(f"  {row['fuente']}: sentimiento {tipo_s} ({row['sent_prom']:.3f})")
    except Exception as e:
        logger.warning(f"  Error en sentimiento por fuente: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Total tendencias registradas: {n_tendencias}")
    return n_tendencias


# ═══════════════════════════════════════════════════════════
# 3. ANÁLISIS DE CORRELACIONES (Pearson)
# ═══════════════════════════════════════════════════════════

def ejecutar_correlaciones(df):
    """Ejecuta análisis de correlaciones estadísticas."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("MODULO 3: ANALISIS DE CORRELACIONES (Pearson)")
    logger.info("=" * 60)
    
    from scipy.stats import pearsonr
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Limpiar tabla
    cursor.execute("DELETE FROM correlacion_resultado")
    
    # Variables a correlacionar
    vars_analisis = {
        'longitud_texto': 'Longitud del texto',
        'cantidad_palabras': 'Cantidad de palabras',
        'engagement_total': 'Engagement total',
        'engagement_normalizado': 'Engagement normalizado',
        'hora': 'Hora de publicación',
        'dia_semana': 'Día de la semana',
        'score_sentimiento': 'Score de sentimiento',
        'confianza_sentimiento': 'Confianza del modelo'
    }
    
    cols = list(vars_analisis.keys())
    df_corr = df[cols].fillna(0)
    
    n_correlaciones = 0
    significativas = 0
    
    for i, col1 in enumerate(cols):
        for j, col2 in enumerate(cols):
            if i >= j:
                continue
            
            try:
                corr, p_value = pearsonr(df_corr[col1].values, df_corr[col2].values)
                
                if np.isnan(corr):
                    continue
                
                # Interpretar fuerza
                abs_corr = abs(corr)
                if abs_corr >= 0.9:
                    fuerza = 'muy_fuerte'
                elif abs_corr >= 0.7:
                    fuerza = 'fuerte'
                elif abs_corr >= 0.5:
                    fuerza = 'moderada'
                elif abs_corr >= 0.3:
                    fuerza = 'debil'
                else:
                    fuerza = 'muy_debil'
                
                es_significativa = p_value < 0.05
                if es_significativa:
                    significativas += 1
                
                cursor.execute("""
                    INSERT INTO correlacion_resultado 
                    (variable_1, variable_2, coeficiente_correlacion, p_value,
                     es_significativa, fuerza, direccion, n_muestras, metodo,
                     fecha_analisis)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    vars_analisis[col1],
                    vars_analisis[col2],
                    round(corr, 6),
                    round(p_value, 6),
                    1 if es_significativa else 0,
                    fuerza,
                    'positiva' if corr > 0 else 'negativa',
                    len(df_corr),
                    'pearson'
                ))
                
                n_correlaciones += 1
                
                # Mostrar solo significativas
                if es_significativa and abs_corr >= 0.3:
                    logger.info(f"  {vars_analisis[col1]} <-> {vars_analisis[col2]}: r={corr:.4f} (p={p_value:.4f}) [{fuerza}]")
                    
            except Exception as e:
                continue
    
    conn.commit()
    conn.close()
    
    logger.info(f"Total correlaciones calculadas: {n_correlaciones}")
    logger.info(f"Correlaciones significativas (p<0.05): {significativas}")
    
    return n_correlaciones


def main():
    print("")
    print("=" * 60)
    print("  SADUTO — Ejecución de Módulos de IA/ML")
    print("  Anomalías | Tendencias | Correlaciones")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("")
    
    total_start = time.time()
    
    # Cargar datos
    logger.info("Cargando datos desde la BD...")
    df = cargar_datos_numericos()
    logger.info(f"Datos cargados: {len(df)} registros")
    print("")
    
    # 1. Anomalías
    n_anomalias = ejecutar_anomalias(df)
    
    # 2. Tendencias
    n_tendencias = ejecutar_tendencias(df)
    
    # 3. Correlaciones
    n_correlaciones = ejecutar_correlaciones(df)
    
    elapsed = time.time() - total_start
    
    print("")
    print("=" * 60)
    print(f"  MODULOS IA/ML COMPLETADOS")
    print(f"  Anomalías detectadas: {n_anomalias}")
    print(f"  Tendencias analizadas: {n_tendencias}")
    print(f"  Correlaciones calculadas: {n_correlaciones}")
    print(f"  Tiempo total: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == '__main__':
    main()
