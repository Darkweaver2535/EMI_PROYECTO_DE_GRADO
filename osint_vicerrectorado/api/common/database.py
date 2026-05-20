"""
Database utilities — Shared across all blueprints
"""
import os
import sqlite3

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'osint_emi.db'
)


def get_db():
    """Obtiene conexión a SQLite con row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
