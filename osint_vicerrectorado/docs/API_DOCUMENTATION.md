# 📡 API Documentation - Sistema OSINT EMI Bolivia

## Sprint 6: Hardening y Automatización del Módulo de Recolección

---

## 📋 Tabla de Contenidos

1. [Información General](#información-general)
2. [Autenticación](#autenticación)
3. [Endpoints de Scrapers](#endpoints-de-scrapers)
4. [Endpoints de Métricas](#endpoints-de-métricas)
5. [Endpoints de Alertas](#endpoints-de-alertas)
6. [Modelos de Datos](#modelos-de-datos)
7. [Códigos de Error](#códigos-de-error)

---

## 🌐 Información General

### Base URL

```
http://localhost:5000/api/v1
```

### Headers Requeridos

```http
Content-Type: application/json
Accept: application/json
```

### Formato de Respuesta

Todas las respuestas siguen el formato:

```json
{
  "success": true,
  "data": { ... },
  "message": "Operación exitosa",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

En caso de error:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Descripción del error",
    "details": { ... }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 🔐 Autenticación

*(Para endpoints protegidos en versiones futuras)*

```http
Authorization: Bearer <token>
```

---

## 🕷️ Endpoints de Scrapers

### Listar Todos los Scrapers

```http
GET /api/v1/scrapers
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "scrapers": [
      {
        "name": "facebook",
        "source": "facebook.com",
        "enabled": true,
        "state": "idle",
        "last_run": "2024-01-01T12:00:00Z",
        "last_success": "2024-01-01T12:00:00Z"
      }
    ],
    "total": 5
  }
}
```

---

### Obtener Estado de un Scraper

```http
GET /api/v1/scrapers/{scraper_name}/status
```

**Parámetros:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| scraper_name | string | Nombre del scraper (ej: "facebook") |

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "name": "facebook",
    "source": "facebook.com",
    "state": "idle",
    "enabled": true,
    "last_run": "2024-01-01T12:00:00Z",
    "last_success": "2024-01-01T12:00:00Z",
    "consecutive_failures": 0,
    "total_runs": 150,
    "total_items": 5430,
    "circuit_breaker": {
      "state": "closed",
      "failure_count": 0,
      "success_count": 150
    },
    "rate_limiter": {
      "current_rpm": 60,
      "base_rpm": 60,
      "throttled_requests": 5
    },
    "stats": {
      "requests_made": 450,
      "items_collected": 5430,
      "errors": 12,
      "retries": 25
    }
  }
}
```

---

### Ejecutar Scraper Manualmente

```http
POST /api/v1/scrapers/{scraper_name}/run
```

**Body (opcional):**

```json
{
  "limit": 50,
  "async": true
}
```

**Parámetros:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| limit | integer | 100 | Máximo de items a recolectar |
| async | boolean | true | Ejecutar en background |

**Respuesta (async=true):**

```json
{
  "success": true,
  "data": {
    "task_id": "abc123",
    "status": "queued",
    "message": "Scrape task enqueued"
  }
}
```

**Respuesta (async=false):**

```json
{
  "success": true,
  "data": {
    "scraper_name": "facebook",
    "items_count": 50,
    "duration_seconds": 45.2,
    "success": true
  }
}
```

---

### Pausar Scraper

```http
POST /api/v1/scrapers/{scraper_name}/pause
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "scraper_name": "facebook",
    "previous_state": "idle",
    "new_state": "paused"
  }
}
```

---

### Reanudar Scraper

```http
POST /api/v1/scrapers/{scraper_name}/resume
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "scraper_name": "facebook",
    "previous_state": "paused",
    "new_state": "idle"
  }
}
```

---

### Obtener Estadísticas del Circuit Breaker

```http
GET /api/v1/scrapers/{scraper_name}/circuit-breaker/stats
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "state": "closed",
    "failure_count": 2,
    "success_count": 148,
    "failure_threshold": 5,
    "timeout_duration": 300,
    "last_failure_time": "2024-01-01T11:55:00Z",
    "stats": {
      "total_calls": 150,
      "successful_calls": 148,
      "failed_calls": 2,
      "rejected_calls": 0
    }
  }
}
```

---

### Resetear Circuit Breaker

```http
POST /api/v1/scrapers/{scraper_name}/circuit-breaker/reset
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "scraper_name": "facebook",
    "previous_state": "open",
    "new_state": "closed",
    "message": "Circuit breaker reset successfully"
  }
}
```

---

### Obtener Estadísticas del Rate Limiter

```http
GET /api/v1/scrapers/{scraper_name}/rate-limiter/stats
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "current_rpm": 45,
    "base_rpm": 60,
    "min_rpm": 10,
    "max_rpm": 120,
    "adaptive_enabled": true,
    "tokens_available": 0.75,
    "throttled_requests": 15,
    "rate_limit_429_hits": 3,
    "last_adaptation": "2024-01-01T11:30:00Z"
  }
}
```

---

### Resetear Rate Limiter

```http
POST /api/v1/scrapers/{scraper_name}/rate-limiter/reset
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "scraper_name": "facebook",
    "previous_rpm": 30,
    "new_rpm": 60,
    "message": "Rate limiter reset to base rate"
  }
}
```

---

## 📊 Endpoints de Métricas

### Métricas Prometheus

```http
GET /metrics
```

**Respuesta:** Texto en formato Prometheus

```
# HELP scraper_requests_total Total de requests realizados
# TYPE scraper_requests_total counter
scraper_requests_total{scraper_name="facebook",source="facebook.com",method="GET",status_code="200"} 450

# HELP scraper_items_scraped_total Total de items extraídos
# TYPE scraper_items_scraped_total counter
scraper_items_scraped_total{scraper_name="facebook",source="facebook.com",item_type="post"} 5430
```

---

### Health Check

```http
GET /health
```

**Respuesta:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "scrapers": "ok"
  }
}
```

---

### Readiness Check

```http
GET /ready
```

**Respuesta:**

```json
{
  "status": "ready",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### Dashboard de Estado

```http
GET /api/v1/dashboard/status
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "orchestrator": {
      "running": true,
      "max_concurrent": 5,
      "stats": {
        "total_runs": 1500,
        "successful_runs": 1485,
        "failed_runs": 15,
        "success_rate": 99.0,
        "total_items": 54300,
        "uptime_seconds": 86400
      }
    },
    "scrapers": [
      {
        "name": "facebook",
        "state": "idle",
        "health": "healthy"
      },
      {
        "name": "tiktok",
        "state": "running",
        "health": "healthy"
      }
    ],
    "alerts": {
      "active": 0,
      "silenced": 1
    }
  }
}
```

---

## 🔔 Endpoints de Alertas

### Webhook de Alertas (para AlertManager)

```http
POST /api/v1/alerts/webhook
```

**Body (AlertManager format):**

```json
{
  "version": "4",
  "groupKey": "{}:{alertname=\"ScraperDown\"}",
  "status": "firing",
  "receiver": "osint-team",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "ScraperDown",
        "scraper_name": "facebook",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Scraper facebook is down",
        "description": "The scraper has been down for more than 2 minutes"
      },
      "startsAt": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**Respuesta:**

```json
{
  "success": true,
  "message": "Alerts processed"
}
```

---

### Listar Alertas Activas

```http
GET /api/v1/alerts
```

**Query Parameters:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| status | string | all | "firing", "resolved", "all" |
| severity | string | all | "critical", "warning", "all" |

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "alerts": [
      {
        "id": "alert_123",
        "name": "ScraperHighErrorRate",
        "status": "firing",
        "severity": "warning",
        "scraper_name": "facebook",
        "started_at": "2024-01-01T12:00:00Z",
        "annotations": {
          "summary": "High error rate for facebook",
          "description": "Error rate is 15%"
        }
      }
    ],
    "total": 1
  }
}
```

---

## 📦 Modelos de Datos

### ScraperState (Enum)

| Valor | Descripción |
|-------|-------------|
| idle | Esperando próxima ejecución |
| running | Ejecutándose actualmente |
| paused | Pausado manualmente |
| error | Error en última ejecución |
| circuit_open | Circuit breaker abierto |
| rate_limited | Esperando por rate limiting |

### CircuitBreakerState (Enum)

| Valor | Código | Descripción |
|-------|--------|-------------|
| closed | 0 | Normal, requests pasan |
| open | 1 | Abierto, requests rechazadas |
| half-open | 2 | Probando recuperación |

### ScraperResult

```json
{
  "scraper_name": "string",
  "source": "string",
  "success": "boolean",
  "items_count": "integer",
  "duration_seconds": "float",
  "error": "string | null",
  "error_type": "string | null",
  "started_at": "datetime",
  "completed_at": "datetime",
  "metadata": "object"
}
```

### OrchestratorStats

```json
{
  "total_runs": "integer",
  "successful_runs": "integer",
  "failed_runs": "integer",
  "total_items_scraped": "integer",
  "active_scrapers": "integer",
  "paused_scrapers": "integer",
  "circuit_open_scrapers": "integer",
  "uptime_seconds": "float",
  "started_at": "datetime"
}
```

---

## ❌ Códigos de Error

### Errores HTTP

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - Parámetros inválidos |
| 401 | Unauthorized - Autenticación requerida |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Códigos de Error Específicos

| Código | Descripción |
|--------|-------------|
| SCRAPER_NOT_FOUND | Scraper no existe |
| SCRAPER_ALREADY_RUNNING | Scraper ya está ejecutándose |
| SCRAPER_PAUSED | Scraper está pausado |
| CIRCUIT_BREAKER_OPEN | Circuit breaker está abierto |
| RATE_LIMIT_EXCEEDED | Límite de rate alcanzado |
| INVALID_CONFIGURATION | Configuración inválida |
| DATABASE_ERROR | Error de base de datos |
| REDIS_ERROR | Error de Redis |

### Ejemplo de Error

```json
{
  "success": false,
  "error": {
    "code": "CIRCUIT_BREAKER_OPEN",
    "message": "Circuit breaker is open for scraper 'facebook'",
    "details": {
      "state": "open",
      "will_reset_at": "2024-01-01T12:05:00Z",
      "failure_count": 5
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

## 📝 Ejemplos de Uso

### cURL

```bash
# Listar scrapers
curl -X GET http://localhost:5000/api/v1/scrapers

# Ejecutar scraper
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/run \
  -H "Content-Type: application/json" \
  -d '{"limit": 50, "async": false}'

# Pausar scraper
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/pause

# Resetear circuit breaker
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/circuit-breaker/reset
```

### Python

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"

# Obtener estado
response = requests.get(f"{BASE_URL}/scrapers/facebook/status")
data = response.json()

if data["success"]:
    print(f"State: {data['data']['state']}")
    print(f"Items: {data['data']['total_items']}")

# Ejecutar scraper
response = requests.post(
    f"{BASE_URL}/scrapers/facebook/run",
    json={"limit": 100, "async": True}
)
print(response.json())
```

### JavaScript

```javascript
const BASE_URL = "http://localhost:5000/api/v1";

// Obtener estado
fetch(`${BASE_URL}/scrapers/facebook/status`)
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log(`State: ${data.data.state}`);
      console.log(`Items: ${data.data.total_items}`);
    }
  });

// Ejecutar scraper
fetch(`${BASE_URL}/scrapers/facebook/run`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ limit: 100, async: true })
})
  .then(response => response.json())
  .then(console.log);
```

---

*Última actualización: Sprint 6 - Diciembre 2024*
