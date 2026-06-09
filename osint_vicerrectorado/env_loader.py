#!/usr/bin/env python3
"""
Cargador de variables de entorno desde .env — sin dependencias externas.

El proyecto guarda las credenciales (Apify, DeepSeek, SMTP, etc.) en un
archivo `.env` que NO se sube a git. Este módulo lo lee y las inyecta en
`os.environ` sin requerir python-dotenv.

Uso:
    from env_loader import load_env
    load_env()  # idempotente: solo carga una vez

No sobreescribe variables que ya existan en el entorno (precedencia del
entorno real sobre el archivo).
"""

import os
from pathlib import Path

_LOADED = False
_ENV_PATH = Path(__file__).parent / '.env'


def load_env(path: str | None = None, override: bool = False) -> None:
    """Carga las variables de `.env` en os.environ (una sola vez)."""
    global _LOADED
    if _LOADED and path is None:
        return

    env_file = Path(path) if path else _ENV_PATH
    if not env_file.exists():
        _LOADED = True
        return

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue
                if override or key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass
    finally:
        if path is None:
            _LOADED = True
