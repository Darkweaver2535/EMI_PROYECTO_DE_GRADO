#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  Catálogo oficial de carreras — Sistema OSINT EMI
═══════════════════════════════════════════════════════════════

Fuente única de verdad de las 14 carreras oficiales de la EMI.

La clasificación de carrera por contenido la realiza DeepSeek
(ver `deepseek_analyzer.py`); este módulo solo provee el catálogo
id → nombre compartido entre el motor de IA y la capa API.
"""

# id (str) → nombre oficial
EMI_CAREERS = {
    '1': 'Ingeniería Civil',
    '2': 'Ingeniería Geográfica',
    '3': 'Ingeniería Ambiental',
    '4': 'Ingeniería de Sistemas',
    '5': 'Ingeniería en Telecomunicaciones',
    '6': 'Ingeniería en Sistemas Electrónicos',
    '7': 'Ingeniería Industrial',
    '8': 'Ingeniería Petrolera',
    '9': 'Ingeniería Mecatrónica',
    '10': 'Ingeniería Comercial',
    '11': 'Ingeniería Financiera',
    '12': 'Derecho',
    '13': 'Ingeniería Agronómica',
    '14': 'Ingeniería Agroindustrial',
}

# Conjunto de IDs válidos para validar la salida de DeepSeek
VALID_CAREER_IDS = set(EMI_CAREERS.keys())


def career_name(career_id) -> str:
    """Devuelve el nombre de la carrera o un placeholder estable."""
    cid = str(career_id)
    return EMI_CAREERS.get(cid, f'Carrera #{cid}')


def careers_catalog_text() -> str:
    """Catálogo en texto plano para inyectar en el prompt de DeepSeek."""
    return "\n".join(f"  {cid}: {name}" for cid, name in EMI_CAREERS.items())
