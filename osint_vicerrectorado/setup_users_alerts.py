#!/usr/bin/env python3
"""
Script para crear tablas de usuario, alerta, configuracion_alerta y log_actividad.
Inserta datos semilla.
"""
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'osint_emi.db')

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # ==================== TABLA USUARIO ====================
    c.execute("DROP TABLE IF EXISTS usuario")
    c.execute("""
        CREATE TABLE usuario (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre_completo TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('administrador','vicerrector','uebu')),
            cargo TEXT,
            activo INTEGER DEFAULT 1,
            ultimo_login TEXT,
            fecha_creacion TEXT DEFAULT (datetime('now'))
        )
    """)
    print("[OK] Tabla usuario creada")

    # Insertar usuarios semilla
    users = [
        ('admin', 'admin@emi.edu.bo', sha256('admin123'), 'Administrador del Sistema', 'administrador', 'Administrador TI'),
        ('vicerrector', 'vicerrector@emi.edu.bo', sha256('vice2024'), 'Dr. Juan Pérez', 'vicerrector', 'Vicerrector de Grado'),
        ('jefe_uebu', 'jefe.uebu@emi.edu.bo', sha256('uebu2024'), 'Lic. María García', 'uebu', 'Jefa UEBU'),
        ('analista_uebu', 'analista@emi.edu.bo', sha256('analista123'), 'Ing. Carlos López', 'uebu', 'Analista UEBU'),
    ]
    c.executemany("""
        INSERT INTO usuario (username, email, password_hash, nombre_completo, rol, cargo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, users)
    print(f"[OK] {len(users)} usuarios insertados")

    # ==================== TABLA ALERTA ====================
    c.execute("DROP TABLE IF EXISTS alerta")
    c.execute("""
        CREATE TABLE alerta (
            id_alerta INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            severidad TEXT NOT NULL CHECK(severidad IN ('critica','alta','media','baja')),
            titulo TEXT NOT NULL,
            descripcion TEXT,
            fuente TEXT DEFAULT 'facebook',
            estado TEXT NOT NULL DEFAULT 'nueva' CHECK(estado IN ('nueva','en_proceso','resuelta','descartada')),
            id_dato_procesado INTEGER,
            confianza REAL,
            engagement INTEGER,
            asignado_a INTEGER REFERENCES usuario(id_usuario),
            resolucion TEXT,
            resuelto_por INTEGER REFERENCES usuario(id_usuario),
            fecha_creacion TEXT DEFAULT (datetime('now')),
            fecha_resolucion TEXT
        )
    """)
    print("[OK] Tabla alerta creada")

    # Generar alertas a partir de sentimientos negativos reales
    c.execute("""
        SELECT dp.id_dato_procesado, dp.contenido_limpio, a.confianza, dp.engagement_total, dp.fecha_publicacion_iso
        FROM dato_procesado dp
        JOIN analisis_sentimiento a ON dp.id_dato_procesado = a.id_dato_procesado
        WHERE a.sentimiento_predicho = 'Negativo'
        ORDER BY a.confianza DESC
        LIMIT 30
    """)
    neg_rows = c.fetchall()

    alert_count = 0
    now = datetime.now()
    for i, row in enumerate(neg_rows):
        conf = row['confianza'] or 0
        eng = row['engagement_total'] or 0
        text = (row['contenido_limpio'] or '')[:200]

        if conf > 0.85:
            sev = 'critica'
        elif conf > 0.7:
            sev = 'alta'
        elif conf > 0.5:
            sev = 'media'
        else:
            sev = 'baja'

        # Some resolved, most new
        if i < 3:
            estado = 'resuelta'
            resolucion = 'Revisado y gestionado por el equipo UEBU'
            resuelto_por = 3
            fecha_res = (now - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S')
        elif i < 5:
            estado = 'en_proceso'
            resolucion = None
            resuelto_por = None
            fecha_res = None
        else:
            estado = 'nueva'
            resolucion = None
            resuelto_por = None
            fecha_res = None

        fecha_creacion = row['fecha_publicacion_iso'] or (now - timedelta(hours=i*2)).strftime('%Y-%m-%d %H:%M:%S')

        c.execute("""
            INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado, id_dato_procesado, confianza, engagement, asignado_a, resolucion, resuelto_por, fecha_creacion, fecha_resolucion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'sentiment_negative', sev,
            f'Sentimiento negativo detectado (confianza {conf:.0%})',
            text, 'facebook', estado,
            row['id_dato_procesado'], conf, eng,
            3 if estado != 'nueva' else None,
            resolucion, resuelto_por, fecha_creacion, fecha_res
        ))
        alert_count += 1

    # Add some engagement-spike alerts
    c.execute("""
        SELECT dp.id_dato_procesado, dp.contenido_limpio, dp.engagement_total, dp.fecha_publicacion_iso
        FROM dato_procesado dp
        WHERE dp.engagement_total > 50
        ORDER BY dp.engagement_total DESC
        LIMIT 5
    """)
    for row in c.fetchall():
        c.execute("""
            INSERT INTO alerta (tipo, severidad, titulo, descripcion, fuente, estado, id_dato_procesado, engagement, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'engagement_spike', 'media',
            f'Pico de engagement detectado ({row["engagement_total"]} interacciones)',
            (row['contenido_limpio'] or '')[:200],
            'facebook', 'nueva',
            row['id_dato_procesado'], row['engagement_total'],
            row['fecha_publicacion_iso'] or now.strftime('%Y-%m-%d %H:%M:%S')
        ))
        alert_count += 1

    print(f"[OK] {alert_count} alertas insertadas")

    # ==================== TABLA CONFIGURACION_ALERTA ====================
    c.execute("DROP TABLE IF EXISTS configuracion_alerta")
    c.execute("""
        CREATE TABLE configuracion_alerta (
            id_config INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo_alerta TEXT NOT NULL,
            umbral_valor REAL DEFAULT 0.7,
            umbral_confianza REAL DEFAULT 0.5,
            severidad_minima TEXT DEFAULT 'media',
            activa INTEGER DEFAULT 1,
            notificar_email INTEGER DEFAULT 0,
            creado_por INTEGER REFERENCES usuario(id_usuario),
            fecha_creacion TEXT DEFAULT (datetime('now'))
        )
    """)
    configs = [
        ('Alerta Sentimiento Negativo', 'sentiment_negative', 0.7, 0.6, 'media', 1, 0, 1),
        ('Alerta Pico Engagement', 'engagement_spike', 50, 0.5, 'media', 1, 0, 1),
        ('Alerta Crítica Reputación', 'reputation_critical', 0.9, 0.8, 'critica', 1, 1, 1),
        ('Alerta Volumen Anomalía', 'volume_anomaly', 2.0, 0.5, 'alta', 1, 0, 1),
    ]
    c.executemany("""
        INSERT INTO configuracion_alerta (nombre, tipo_alerta, umbral_valor, umbral_confianza, severidad_minima, activa, notificar_email, creado_por)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, configs)
    print(f"[OK] {len(configs)} configuraciones de alerta insertadas")

    # ==================== TABLA LOG_ACTIVIDAD ====================
    c.execute("DROP TABLE IF EXISTS log_actividad")
    c.execute("""
        CREATE TABLE log_actividad (
            id_log INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER REFERENCES usuario(id_usuario),
            accion TEXT NOT NULL,
            detalle TEXT,
            ip_address TEXT,
            fecha TEXT DEFAULT (datetime('now'))
        )
    """)
    # Insert a few sample logs
    logs = [
        (1, 'login', 'Inicio de sesión exitoso', '127.0.0.1'),
        (1, 'crear_usuario', 'Creó usuario vicerrector', '127.0.0.1'),
        (3, 'resolver_alerta', 'Resolvió alerta #1', '127.0.0.1'),
    ]
    c.executemany("""
        INSERT INTO log_actividad (id_usuario, accion, detalle, ip_address)
        VALUES (?, ?, ?, ?)
    """, logs)
    print(f"[OK] {len(logs)} logs de actividad insertados")

    conn.commit()
    conn.close()
    print("\n=== Setup completado exitosamente ===")

if __name__ == '__main__':
    main()
