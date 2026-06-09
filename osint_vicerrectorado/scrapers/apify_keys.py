"""
Apify API Key Manager - Gestión inteligente de múltiples API keys
Sistema de Analítica EMI

Asigna API keys por plataforma y hace fallback automático
si una key se queda sin créditos/memoria.

Configuración en config.json:
{
    "apify": {
        "api_keys": {
            "facebook": "apify_api_xxx...",
            "tiktok": "apify_api_yyy...",
            "fallback": "apify_api_yyy..."
        }
    }
}
"""

import os
import sys
import logging

logger = logging.getLogger('OSINT.ApifyKeys')

# Cargar variables de entorno (.env) de forma defensiva
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from env_loader import load_env
    load_env()
except Exception:  # noqa: BLE001 — si no existe, se sigue con config.json
    pass


def _env_key(platform: str) -> str:
    """Lee la API key de Apify desde variables de entorno (prioridad sobre config)."""
    plat = (platform or '').upper()
    return (
        os.getenv(f'APIFY_API_KEY_{plat}')
        or os.getenv('APIFY_API_KEY')
        or ''
    )


# Errores que indican agotamiento de créditos/memoria
QUOTA_ERROR_PATTERNS = [
    'memory',
    'limit',
    'exceeded',
    'quota',
    'insufficient',
    'billing',
    'credit',
    'usage limit',
    'out of',
    'Actor run exceeded',
    'not enough',
]


def get_api_key(config: dict, platform: str = 'default') -> str:
    """
    Obtiene la API key de Apify para la plataforma indicada.
    
    Prioridad:
      1. Key específica de la plataforma (config.apify.api_keys.facebook)
      2. Key genérica (config.apify.api_key)
    
    Args:
        config: Diccionario de configuración del sistema
        platform: 'facebook', 'tiktok', o 'default'
    
    Returns:
        API key string
    """
    # 1) Variables de entorno (.env) — fuente recomendada, no se sube a git
    env_key = _env_key(platform)
    if env_key:
        return env_key

    # 2) config.json (compatibilidad; normalmente vacío en el repo)
    apify_config = config.get('apify', {})
    platform_keys = apify_config.get('api_keys', {})
    platform_key = platform_keys.get(platform.lower())
    if platform_key:
        return platform_key

    return apify_config.get('api_key', '')


def get_fallback_key(config: dict, platform: str) -> str:
    """
    Obtiene la API key alternativa para cuando la principal falla.
    
    Si Facebook falla → usa la key de TikTok (o fallback)
    Si TikTok falla → usa la key de Facebook (o fallback)
    
    Args:
        config: Diccionario de configuración
        platform: Plataforma que falló
    
    Returns:
        API key alternativa, o '' si no hay
    """
    apify_config = config.get('apify', {})
    platform_keys = apify_config.get('api_keys', {})

    # Key de fallback explícita (entorno tiene prioridad)
    fallback = os.getenv('APIFY_API_KEY_FALLBACK', '') or platform_keys.get('fallback', '')
    
    # Si no hay fallback explícito, usar la key de la otra plataforma
    if not fallback:
        if platform.lower() == 'facebook':
            fallback = platform_keys.get('tiktok', '')
        elif platform.lower() == 'tiktok':
            fallback = platform_keys.get('facebook', '')
    
    # No devolver la misma key que ya falló
    primary = get_api_key(config, platform)
    if fallback == primary:
        # Buscar cualquier otra key diferente
        for key_name, key_value in platform_keys.items():
            if key_value and key_value != primary:
                return key_value
        return ''
    
    return fallback


def is_quota_error(error: Exception) -> bool:
    """
    Detecta si un error de Apify es por agotamiento de créditos/memoria.
    
    Args:
        error: Excepción capturada
    
    Returns:
        True si parece un error de cuota/memoria
    """
    error_msg = str(error).lower()
    return any(pattern in error_msg for pattern in QUOTA_ERROR_PATTERNS)


def create_client_with_fallback(config: dict, platform: str):
    """
    Crea un ApifyClient con la key correcta.
    Devuelve (client, api_key) para que el caller pueda hacer retry.
    
    Args:
        config: Configuración del sistema
        platform: 'facebook' o 'tiktok'
    
    Returns:
        Tuple (ApifyClient, api_key_used)
    """
    from apify_client import ApifyClient
    
    api_key = get_api_key(config, platform)
    if not api_key:
        raise ValueError(
            f"No hay API key configurada para {platform}. "
            f"Agregar en config.json: apify.api_keys.{platform}"
        )
    
    logger.info(
        f"Usando API key para {platform}: ...{api_key[-8:]}"
    )
    
    return ApifyClient(api_key), api_key


def create_fallback_client(config: dict, platform: str):
    """
    Crea un ApifyClient con la key alternativa (fallback).
    
    Args:
        config: Configuración del sistema
        platform: Plataforma que falló
    
    Returns:
        Tuple (ApifyClient, api_key_used) o None si no hay fallback
    """
    from apify_client import ApifyClient
    
    fallback_key = get_fallback_key(config, platform)
    if not fallback_key:
        return None
    
    logger.warning(
        f"⚠️ Usando API key de FALLBACK para {platform}: "
        f"...{fallback_key[-8:]}"
    )
    
    return ApifyClient(fallback_key), fallback_key
