#!/usr/bin/env python3
"""Verificación rápida de todos los endpoints del sistema."""
import urllib.request

endpoints = [
    '/api/ai/sentiments/distribution',
    '/api/ai/sentiments/kpis',
    '/api/ai/sentiments/trend',
    '/api/ai/sentiments/posts',
    '/api/ai/sentiments/top-posts',
    '/api/ai/alerts',
    '/api/ai/alerts/stats',
    '/api/ai/alerts/active',
    '/api/ai/alerts/anomalies',
    '/api/ai/analysis/trends',
    '/api/ai/analysis/correlations',
    '/api/ai/analysis/anomalies',
    '/api/ai/benchmarking/careers',
    '/api/ai/benchmarking/correlations',
    '/api/ai/reputation/wordcloud',
    '/api/ai/reputation/topics',
    '/api/ai/reputation/heatmap',
    '/api/ai/reputation/metrics',
    '/api/ai/reputation/competitors',
    '/api/nlp/resumen',
    '/api/nlp/keywords',
    '/api/nlp/topicos',
    '/api/nlp/clusters',
    '/api/nlp/entidades',
    '/api/nlp/sentimiento-aspecto',
    '/api/osint/noticias',
    '/api/osint/tendencias-busqueda',
    '/api/evaluacion/resumen',
    '/api/careers',
    '/api/posts',
    '/api/comentarios',
]

ok = fail = 0
for ep in endpoints:
    try:
        r = urllib.request.urlopen(f'http://localhost:5001{ep}')
        print(f'  [{r.status}] OK   {ep}')
        ok += 1
    except Exception as e:
        code = getattr(e, 'code', '???')
        print(f'  [{code}] FAIL {ep}')
        fail += 1

print(f'\n=== Resultado: {ok} OK, {fail} FAIL de {len(endpoints)} endpoints ===')
