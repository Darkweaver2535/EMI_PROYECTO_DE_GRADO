# 📘 Manual de Operaciones - Sistema OSINT EMI Bolivia

## Sprint 6: Hardening y Automatización del Módulo de Recolección

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Componentes de Resiliencia](#componentes-de-resiliencia)
4. [Monitoreo y Métricas](#monitoreo-y-métricas)
5. [Operaciones Comunes](#operaciones-comunes)
6. [Gestión de Scrapers](#gestión-de-scrapers)
7. [Alertas y Notificaciones](#alertas-y-notificaciones)
8. [Backup y Recuperación](#backup-y-recuperación)
9. [Procedimientos de Emergencia](#procedimientos-de-emergencia)

---

## 🎯 Descripción General

El Sistema OSINT EMI Bolivia es una plataforma de recolección y análisis de datos de fuentes abiertas diseñada para el monitoreo de redes sociales y noticias en Bolivia.

### Objetivos del Sprint 6

| Métrica | Objetivo | Estado Actual |
|---------|----------|---------------|
| Uptime | ≥99% | - |
| Error Rate | <1% | - |
| Mejora de Rendimiento | ≥30% | - |
| Tiempo de Deploy | ≤5 minutos | - |

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      API Gateway (Flask)                        │
│                     ┌──────────────────┐                        │
│                     │ Metrics Endpoint │──────► Prometheus      │
│                     │     :9090        │                        │
│                     └──────────────────┘                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                    Scraper Orchestrator                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Facebook │  │  TikTok  │  │ Noticias │  │ Gobierno │        │
│  │ Scraper  │  │ Scraper  │  │ Scraper  │  │ Scraper  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │             │             │             │               │
│  ┌────┴─────────────┴─────────────┴─────────────┴────┐         │
│  │              Resilience Layer                      │         │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────────┐   │         │
│  │  │ Circuit   │ │   Rate    │ │    Retry      │   │         │
│  │  │ Breaker   │ │  Limiter  │ │   Manager     │   │         │
│  │  └───────────┘ └───────────┘ └───────────────┘   │         │
│  └───────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │PostgreSQL│  │  Redis   │  │  Celery  │                      │
│  │    DB    │  │  Cache   │  │  Queue   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Componentes de Resiliencia

### Circuit Breaker

El Circuit Breaker previene fallas en cascada cuando un servicio no responde.

#### Estados

| Estado | Descripción | Comportamiento |
|--------|-------------|----------------|
| **CLOSED** | Normal | Todas las requests pasan |
| **OPEN** | Falla activa | Requests rechazadas inmediatamente |
| **HALF-OPEN** | Probando recuperación | Permite requests de prueba |

#### Configuración

```yaml
# scrapers/config/sources.yaml
failure_threshold: 5      # Fallas antes de abrir
circuit_timeout_seconds: 300  # Tiempo en OPEN antes de HALF-OPEN
```

#### Monitoreo

```promql
# Estado del circuit breaker (0=closed, 1=open, 2=half-open)
circuit_breaker_state{scraper_name="facebook"}

# Cambios de estado
rate(circuit_breaker_state_changes_total[1h])
```

### Rate Limiter Adaptativo

Ajusta automáticamente la tasa de requests basándose en respuestas 429.

#### Comportamiento

| Evento | Acción |
|--------|--------|
| Respuesta 429 | Reducir RPM en 50% |
| 5 min sin 429 | Incrementar RPM en 10% |
| Header Retry-After | Respetar tiempo indicado |

#### Configuración

```yaml
requests_per_minute: 60   # RPM base
adaptive_rate_limiting: true
min_rpm: 10               # Mínimo permitido
max_rpm: 120              # Máximo permitido
```

### Retry Manager

Reintentos con exponential backoff + jitter.

#### Fórmula de Backoff

```
delay = initial_delay * (2 ^ attempt) + random(0, 1)
```

#### Excepciones Reintentables

- `TimeoutError`
- `ConnectionError`
- HTTP 5xx
- HTTP 429

#### Excepciones NO Reintentables

- `ValueError`
- `TypeError`
- HTTP 4xx (excepto 429)

---

## 📊 Monitoreo y Métricas

### URLs de Acceso

| Servicio | URL | Credenciales |
|----------|-----|--------------|
| API | http://localhost:5000 | - |
| Prometheus | http://localhost:9091 | - |
| Grafana | http://localhost:3000 | admin / osint2024 |
| AlertManager | http://localhost:9093 | - |
| Flower (Celery) | http://localhost:5555 | admin / emi2024 |

### Métricas Principales

| Métrica | Descripción | Tipo |
|---------|-------------|------|
| `scraper_requests_total` | Total de requests | Counter |
| `scraper_request_duration_seconds` | Latencia | Histogram |
| `scraper_errors_total` | Total de errores | Counter |
| `scraper_items_scraped_total` | Items extraídos | Counter |
| `circuit_breaker_state` | Estado del CB | Gauge |
| `rate_limiter_current_rate_rpm` | RPM actual | Gauge |

### Dashboard de Grafana

El dashboard "OSINT Scraper Health" incluye:

1. **Overview**: Success rate, items scraped, active scrapers
2. **Request Metrics**: Rate y latencia por scraper
3. **Errors & Resilience**: Errores por tipo, estado de circuit breakers
4. **Rate Limiting**: RPM actual, throttled requests
5. **Scraper Details**: Tabla de estado de todos los scrapers

---

## ⚙️ Operaciones Comunes

### Despliegue

```bash
# Deploy completo
./deployment/deploy.sh production

# Deploy sin backup
./deployment/deploy.sh production --no-backup

# Deploy forzado (ignora errores)
./deployment/deploy.sh production --force

# Dry run (solo muestra comandos)
./deployment/deploy.sh production --dry-run
```

### Verificación de Salud

```bash
# Check completo
./deployment/health_check.sh

# Solo errores
./deployment/health_check.sh --quiet

# Output JSON
./deployment/health_check.sh --json

# Servicio específico
./deployment/health_check.sh --service postgresql
```

### Backup

```bash
# Backup completo
./deployment/backup.sh full

# Solo base de datos
./deployment/backup.sh database

# Solo Redis
./deployment/backup.sh redis

# Solo configuración
./deployment/backup.sh config
```

### Reinicio de Servicios

```bash
# Reiniciar todo
docker-compose restart

# Reiniciar scraper específico
docker-compose restart api

# Reiniciar workers
docker-compose restart celery-worker

# Ver logs
docker-compose logs -f api
```

---

## 🕷️ Gestión de Scrapers

### Listar Scrapers

```bash
curl http://localhost:5000/api/v1/scrapers/status
```

### Pausar Scraper

```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/pause
```

### Reanudar Scraper

```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/resume
```

### Ejecutar Scraper Manual

```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/run
```

### Resetear Circuit Breaker

```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/circuit-breaker/reset
```

---

## 🔔 Alertas y Notificaciones

### Alertas Configuradas

| Alerta | Severidad | Condición |
|--------|-----------|-----------|
| ScraperDown | Critical | Servicio caído >2min |
| ScraperHighErrorRate | Warning | Error rate >10% por 5min |
| CircuitBreakerOpen | Warning | CB abierto >1min |
| HighRateLimiting | Warning | Muchos throttles |
| NoItemsScraped | Warning | Sin items por 1 hora |

### Silenciar Alertas

```bash
# Via AlertManager UI
http://localhost:9093/#/silences/new

# Via API
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [{"name": "alertname", "value": "ScraperHighErrorRate"}],
    "startsAt": "2024-01-01T00:00:00Z",
    "endsAt": "2024-01-01T01:00:00Z",
    "createdBy": "admin",
    "comment": "Mantenimiento programado"
  }'
```

---

## 💾 Backup y Recuperación

### Política de Backups

| Tipo | Frecuencia | Retención |
|------|------------|-----------|
| Database | Cada 6 horas | 7 días |
| Redis | Cada 12 horas | 3 días |
| Config | Cada deploy | 30 días |
| Full | Semanal | 4 semanas |

### Restaurar Backup

```bash
# Restaurar PostgreSQL
gunzip -c backups/postgres_20240101_120000.sql.gz | \
  docker exec -i osint-postgres psql -U osint osint_db

# Restaurar Redis
docker cp backups/redis_20240101_120000.rdb osint-redis:/data/dump.rdb
docker restart osint-redis
```

---

## 🚨 Procedimientos de Emergencia

### Scraper en Falla Continua

1. Verificar estado del circuit breaker
2. Revisar logs: `docker-compose logs -f api | grep "scraper_name"`
3. Verificar rate limiting en Grafana
4. Si es necesario, pausar scraper temporalmente
5. Investigar causa raíz (cambio de HTML, bloqueo IP, etc.)
6. Aplicar fix y reanudar

### Todos los Scrapers Fallan

1. Verificar conectividad de red
2. Verificar estado de Redis y PostgreSQL
3. Verificar recursos del sistema (CPU, memoria, disco)
4. Reiniciar servicios: `docker-compose restart`
5. Si persiste, realizar rollback al último deploy estable

### Base de Datos Corrupta

1. Detener todos los servicios: `docker-compose down`
2. Restaurar último backup válido
3. Verificar integridad
4. Reiniciar servicios

### Alta Carga / DoS

1. Verificar métricas de rate limiting
2. Reducir `max_concurrent_scrapers` en configuración
3. Aumentar intervalos de scraping temporalmente
4. Monitorear recuperación

---

## 📞 Contactos de Soporte

| Rol | Contacto | Horario |
|-----|----------|---------|
| Administrador Sistema | admin@emi.edu.bo | 8:00-18:00 |
| Soporte 24/7 | soporte@emi.edu.bo | 24/7 |
| Emergencias | +591 XXXXXXXX | 24/7 |

---

*Última actualización: Sprint 6 - Diciembre 2024*
