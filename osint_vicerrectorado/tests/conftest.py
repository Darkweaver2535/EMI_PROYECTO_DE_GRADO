"""
Configuración de pytest para el proyecto OSINT EMI.

Este archivo configura fixtures globales y opciones de pytest.
"""

import pytest
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def project_root():
    """Retorna el directorio raíz del proyecto."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope='session')
def base_config():
    """Configuración base compartida entre todos los tests."""
    return {
        'database': {
            'path': ':memory:',
            'type': 'sqlite'
        },
        'sources': {
            'facebook': {
                'enabled': True,
                'pages': [
                    {'name': 'Test Page', 'url': 'https://facebook.com/testpage'}
                ]
            },
            'tiktok': {
                'enabled': True,
                'accounts': [
                    {'name': 'Test Account', 'username': 'testaccount',
                     'url': 'https://tiktok.com/@testaccount'}
                ]
            }
        },
        'scraping': {
            'min_delay_seconds': 0.01,
            'max_delay_seconds': 0.02,
            'max_retries': 1,
            'timeout_seconds': 5
        },
        'rate_limits': {
            'facebook': {'requests_per_hour': 1000},
            'tiktok': {'requests_per_hour': 1000}
        },
        'scheduler': {
            'collection_interval_hours': 12,
            'etl_interval_hours': 6,
            'timezone': 'UTC'
        },
        'etl': {
            'batch_size': 100,
            'clean': {
                'remove_emojis': False,
                'remove_urls': True,
                'remove_mentions': False,
                'remove_hashtags': False,
                'lowercase': False
            },
            'transform': {
                'extract_temporal': True,
                'normalize_engagement': True,
                'classify_content': True,
                'sentiment_analysis': True
            }
        }
    }


def pytest_configure(config):
    """Configuración inicial de pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modifica la colección de tests según configuración."""
    # Si no se especifica -m slow, excluir tests lentos por defecto
    if config.option.markexpr == '':
        skip_slow = pytest.mark.skip(reason="need -m slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
