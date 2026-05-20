#!/usr/bin/env python3
"""
API Flask para Sistema OSINT EMI
=================================

Este archivo es un wrapper de compatibilidad que delega al nuevo
sistema modular basado en Blueprints (api/app.py).

El código fuente de cada módulo está en:
  api/auth/routes.py         — Autenticación
  api/users/routes.py        — CRUD usuarios
  api/sentiment/routes.py    — Análisis de sentimientos
  api/stats/routes.py        — Estadísticas, datos, health, reputación
  api/alerts/routes.py       — Alertas y anomalías
  api/benchmarking/routes.py — Benchmarking académico
  api/sources/routes.py      — Fuentes y recolección (Apify)
  api/posts/routes.py        — Posts, comentarios, jerarquías
  api/osint/routes.py        — OSINT multifuente
  api/nlp/routes.py          — Pipeline NLP
  api/evaluacion/routes.py   — Evaluación del sistema

Infraestructura compartida:
  api/common/database.py     — Conexión a BD
  api/common/filters.py      — Filtros SQL compartidos
  api/common/auth.py         — Utilidades de autenticación
  api/common/state.py        — Estado global compartido
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import create_app

app = create_app()

if __name__ == '__main__':
    print('''
    ╔══════════════════════════════════════════════════════════╗
    ║       OSINT EMI - API Modular (Flask Blueprints)         ║
    ║                                                          ║
    ║  Estructura: Fuentes → Posts → Comentarios               ║
    ║  Puerto: 5001                                            ║
    ║  Base de datos: data/osint_emi.db                        ║
    ║                                                          ║
    ║  ✨ 11 blueprints | Apify data collection                ║
    ╚══════════════════════════════════════════════════════════╝
    ''')

    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    api_routes = [r for r in rules if r.rule.startswith('/api')]
    print(f"  📋 {len(api_routes)} API routes across 11 blueprints\n")

    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False, threaded=True)
