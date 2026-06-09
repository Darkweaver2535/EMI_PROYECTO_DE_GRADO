#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
  Fuentes de noticias GRATUITAS de Bolivia — Sistema OSINT EMI
═══════════════════════════════════════════════════════════════

Catálogo de fuentes abiertas (sin API key de pago) para monitorear
noticias sobre la Escuela Militar de Ingeniería (EMI) **de Bolivia**.

Todas las fuentes fueron verificadas (HTTP 200, feed RSS válido). Se
priorizan portales nacionales bolivianos para evitar confundir la EMI
de Bolivia con instituciones homónimas de otros países.

Tipos de fuente:
  - 'google_news' : Google News RSS (búsqueda por términos, gl=BO). Gratis,
                    sin key. Es la más efectiva para encontrar artículos de
                    la EMI porque busca en TODOS los medios.
  - 'rss_portal'  : Feed RSS directo de un diario boliviano. Gratis, sin key.
                    Se escanea y se filtra por relevancia a la EMI.

NOTA sobre otras APIs evaluadas:
  - GDELT 2.0 DOC API: gratuita y sin key, pero limita a 1 req/5s y su
    cobertura del término "EMI" en español es escasa → descartada por
    inestabilidad.
  - NewsData.io / GNews / Mediastack: tienen plan gratuito pero REQUIEREN
    registro y API key (cuota diaria). Se documentan abajo por si se desea
    activarlas con una key propia (variable de entorno).
"""

# ---------------------------------------------------------------
# Portales bolivianos con RSS abierto y verificado (HTTP 200)
# ---------------------------------------------------------------
BOLIVIA_RSS_PORTALS = [
    {
        'nombre': 'Los Tiempos',
        'ciudad': 'Cochabamba',
        'rss': 'https://www.lostiempos.com/rss.xml',
        'sitio': 'lostiempos.com',
    },
    {
        'nombre': 'El Deber',
        'ciudad': 'Santa Cruz',
        'rss': 'https://eldeber.com.bo/rss/',
        'sitio': 'eldeber.com.bo',
    },
    {
        'nombre': 'Opinión',
        'ciudad': 'Cochabamba',
        'rss': 'https://www.opinion.com.bo/rss/',
        'sitio': 'opinion.com.bo',
    },
    {
        'nombre': 'Brújula Digital',
        'ciudad': 'La Paz',
        'rss': 'https://www.brujuladigital.net/rss',
        'sitio': 'brujuladigital.net',
    },
    {
        'nombre': 'Ahora El Pueblo',
        'ciudad': 'La Paz',
        'rss': 'https://www.ahoradigital.net/feed/',
        'sitio': 'ahoradigital.net',
    },
    {
        'nombre': 'EJU TV',
        'ciudad': 'Santa Cruz',
        'rss': 'https://eju.tv/feed/',
        'sitio': 'eju.tv',
    },
    {
        'nombre': 'ANF (Agencia de Noticias Fides)',
        'ciudad': 'La Paz',
        'rss': 'https://www.noticiasfides.com/rss',
        'sitio': 'noticiasfides.com',
    },
]

# ---------------------------------------------------------------
# Términos de búsqueda para Google News RSS (es-419, gl=BO)
# Orientados EXCLUSIVAMENTE a la EMI de Bolivia.
# ---------------------------------------------------------------
GOOGLE_NEWS_TERMS = [
    '"Escuela Militar de Ingeniería" Bolivia',
    '"Escuela Militar de Ingeniería" La Paz',
    '"Escuela Militar de Ingeniería" Cochabamba',
    '"Escuela Militar de Ingeniería" Santa Cruz',
    'EMI Bolivia ingeniería militar universidad',
    '"Escuela Militar de Ingeniería" carreras admisión',
    '"Escuela Militar de Ingeniería" egresados titulación',
    '"Escuela Militar de Ingeniería" vicerrectorado',
    '"EMI" Bolivia ingeniería estudiantes',
]


def google_news_url(term: str) -> str:
    """Construye la URL de Google News RSS para Bolivia (es-419, gl=BO)."""
    from urllib.parse import quote_plus
    return (
        f'https://news.google.com/rss/search?q={quote_plus(term)}'
        '&hl=es-419&gl=BO&ceid=BO:es-419'
    )


def listar_fuentes() -> list:
    """Devuelve el catálogo de fuentes para mostrar en el dashboard."""
    fuentes = [{
        'nombre': 'Google News (Bolivia)',
        'tipo': 'google_news',
        'ciudad': 'Nacional',
        'sitio': 'news.google.com',
        'gratuita': True,
        'requiere_key': False,
    }]
    for p in BOLIVIA_RSS_PORTALS:
        fuentes.append({
            'nombre': p['nombre'],
            'tipo': 'rss_portal',
            'ciudad': p['ciudad'],
            'sitio': p['sitio'],
            'gratuita': True,
            'requiere_key': False,
        })
    return fuentes
