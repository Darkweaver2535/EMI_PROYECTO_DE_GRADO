# 🔧 Guía de Troubleshooting - Sistema OSINT EMI Bolivia

## Sprint 6: Hardening y Automatización del Módulo de Recolección

---

## 📋 Índice de Problemas

1. [Problemas de Scrapers](#problemas-de-scrapers)
2. [Problemas de Resiliencia](#problemas-de-resiliencia)
3. [Problemas de Base de Datos](#problemas-de-base-de-datos)
4. [Problemas de Redis/Celery](#problemas-de-rediscelery)
5. [Problemas de Monitoreo](#problemas-de-monitoreo)
6. [Problemas de Docker](#problemas-de-docker)
7. [Errores Comunes](#errores-comunes)

---

## 🕷️ Problemas de Scrapers

### Scraper no recolecta datos

**Síntomas:**
- `scraper_items_scraped_total` no incrementa
- Alerta `NoItemsScraped` activa

**Diagnóstico:**
```bash
# Ver logs del scraper
docker-compose logs -f api 2>&1 | grep "facebook"

# Verificar estado
curl http://localhost:5000/api/v1/scrapers/facebook/status
```

**Posibles Causas y Soluciones:**

| Causa | Verificación | Solución |
|-------|--------------|----------|
| Selectores CSS obsoletos | Inspeccionar HTML de la fuente | Actualizar `css_selectors` en sources.yaml |
| Circuit breaker abierto | `circuit_breaker_state == 1` | Esperar o resetear manualmente |
| Rate limiting excesivo | `rate_limiter_current_rate_rpm < 15` | Esperar recuperación automática |
| Bloqueo de IP | Verificar respuestas 403/captcha | Rotar IP, usar proxy |
| Cambio de API | Revisar logs de errores de parsing | Actualizar scraper |

### Scraper muy lento

**Síntomas:**
- P95 latency > 30s
- Pocos items por hora

**Diagnóstico:**
```promql
# Ver latencia P95
histogram_quantile(0.95, sum(rate(scraper_request_duration_seconds_bucket[5m])) by (scraper_name, le))
```

**Soluciones:**
1. Verificar timeouts en sources.yaml
2. Revisar si el sitio está lento (probar manualmente)
3. Reducir `max_concurrent_scrapers` si hay sobrecarga
4. Verificar recursos del sistema (CPU, memoria)

### Error de parsing frecuente

**Síntomas:**
- Logs con "Failed to parse item"
- `scraper_items_failed_total` alto

**Solución:**
```python
# Agregar selectores CSS alternativos en sources.yaml
css_selectors:
  post_content:
    - "selector_principal"
    - "selector_alternativo_1"
    - "selector_alternativo_2"
```

---

## 🛡️ Problemas de Resiliencia

### Circuit Breaker siempre abierto

**Síntomas:**
- Alerta `CircuitBreakerStuckOpen`
- Scraper no ejecuta requests

**Diagnóstico:**
```bash
# Ver estado del circuit breaker
curl http://localhost:5000/api/v1/scrapers/facebook/circuit-breaker/stats

# Ver historial de fallas
docker-compose logs api | grep "Circuit breaker" | tail -20
```

**Soluciones:**

1. **Resetear manualmente:**
```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/circuit-breaker/reset
```

2. **Ajustar configuración:**
```yaml
# sources.yaml - ser más tolerante
failure_threshold: 10  # (era 5)
circuit_timeout_seconds: 600  # (era 300)
```

3. **Investigar causa raíz:**
- ¿El sitio está caído?
- ¿Hubo cambio de estructura HTML?
- ¿La IP está bloqueada?

### Rate Limiter demasiado agresivo

**Síntomas:**
- `rate_limiter_current_rate_rpm` muy bajo (<15)
- Scraping muy lento

**Diagnóstico:**
```promql
# Ver tasa actual vs base
rate_limiter_current_rate_rpm / on(scraper_name) group_left rate_limiter_base_rpm
```

**Soluciones:**

1. **Esperar recuperación automática** (5 min sin 429)

2. **Resetear rate limiter:**
```bash
curl -X POST http://localhost:5000/api/v1/scrapers/facebook/rate-limiter/reset
```

3. **Ajustar configuración:**
```yaml
min_rpm: 20  # Aumentar mínimo
```

### Demasiados reintentos

**Síntomas:**
- Alto `scraper_retries_total`
- Latencias infladas por backoff

**Solución:**
```yaml
# Reducir reintentos para fallar más rápido
max_retries: 2  # (era 3)
max_retry_delay: 30.0  # (era 60.0)
```

---

## 🗄️ Problemas de Base de Datos

### PostgreSQL no responde

**Síntomas:**
- Alerta `PostgreSQLDown`
- Errores de conexión en logs

**Diagnóstico:**
```bash
# Ver estado del container
docker-compose ps postgres

# Ver logs
docker-compose logs postgres | tail -50

# Probar conexión
docker exec -it osint-postgres psql -U osint -c "SELECT 1"
```

**Soluciones:**

1. **Reiniciar container:**
```bash
docker-compose restart postgres
```

2. **Verificar espacio en disco:**
```bash
docker exec osint-postgres df -h
```

3. **Restaurar desde backup si corrupto:**
```bash
docker-compose down
docker volume rm osint_postgres_data
docker-compose up -d postgres
# Esperar inicio
./deployment/backup.sh restore database backups/postgres_latest.sql.gz
```

### Conexiones agotadas

**Síntomas:**
- Alerta `PostgreSQLHighConnections`
- Errores "too many connections"

**Solución:**
```bash
# Ver conexiones activas
docker exec osint-postgres psql -U osint -c "SELECT count(*) FROM pg_stat_activity"

# Terminar conexiones idle
docker exec osint-postgres psql -U osint -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND query_start < now() - interval '5 minutes'
"
```

---

## 📮 Problemas de Redis/Celery

### Redis sin memoria

**Síntomas:**
- Alerta `RedisHighMemory`
- Errores OOM en logs

**Solución:**
```bash
# Ver uso de memoria
docker exec osint-redis redis-cli INFO memory

# Limpiar cache si necesario
docker exec osint-redis redis-cli FLUSHDB

# O configurar política de evicción (ya configurado)
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### Celery workers no procesan tareas

**Síntomas:**
- Alerta `CeleryTasksBacklog`
- Cola creciendo

**Diagnóstico:**
```bash
# Ver estado de workers
docker exec osint-celery-worker celery -A reports.tasks inspect active

# Ver cola
docker exec osint-redis redis-cli LLEN celery
```

**Soluciones:**

1. **Reiniciar workers:**
```bash
docker-compose restart celery-worker
```

2. **Escalar workers:**
```bash
docker-compose up -d --scale celery-worker=3
```

3. **Verificar conexión a Redis:**
```bash
docker exec osint-celery-worker celery -A reports.tasks inspect ping
```

---

## 📊 Problemas de Monitoreo

### Prometheus sin métricas

**Síntomas:**
- Dashboards vacíos
- No hay datos en queries

**Diagnóstico:**
```bash
# Verificar que el endpoint de métricas responde
curl http://localhost:9090/metrics

# Verificar targets en Prometheus
curl http://localhost:9091/api/v1/targets
```

**Soluciones:**

1. **Verificar configuración:**
```bash
# Validar prometheus.yml
docker exec osint-prometheus promtool check config /etc/prometheus/prometheus.yml
```

2. **Reiniciar Prometheus:**
```bash
docker-compose restart prometheus
```

### Grafana sin datos

**Síntomas:**
- "No data" en paneles
- Datasource error

**Soluciones:**

1. **Verificar datasource:**
   - Ir a Settings > Data Sources > Prometheus
   - Click "Test"

2. **Verificar URL:**
   - Debe ser `http://prometheus:9090` (interno)
   - No `http://localhost:9091`

### AlertManager no envía alertas

**Diagnóstico:**
```bash
# Ver alertas activas
curl http://localhost:9093/api/v2/alerts

# Ver configuración
docker exec osint-alertmanager amtool config show
```

**Soluciones:**

1. **Verificar configuración SMTP** en alertmanager.yml
2. **Verificar ruta de alertas** (group_by, routes)
3. **Revisar logs:**
```bash
docker-compose logs alertmanager
```

---

## 🐳 Problemas de Docker

### Container en restart loop

**Diagnóstico:**
```bash
docker-compose ps
docker-compose logs api --tail=100
```

**Soluciones:**

1. **Verificar errores de inicio:**
```bash
docker-compose logs api 2>&1 | grep -i "error\|exception\|failed"
```

2. **Recrear container:**
```bash
docker-compose up -d --force-recreate api
```

3. **Verificar recursos:**
```bash
docker stats --no-stream
```

### Sin espacio en disco

**Síntomas:**
- Errores "no space left on device"
- Containers no inician

**Solución:**
```bash
# Limpiar Docker
docker system prune -a --volumes

# O más selectivo
docker image prune -a
docker volume prune
docker container prune
```

### Network issues entre containers

**Diagnóstico:**
```bash
# Verificar red
docker network inspect emi_network

# Probar conectividad
docker exec osint-app ping redis
docker exec osint-app nc -zv postgres 5432
```

---

## ❌ Errores Comunes

### `TimeoutError: Connection timed out`

**Causas:**
- Servidor destino lento
- Timeout configurado muy bajo

**Solución:**
```yaml
# Aumentar timeouts en sources.yaml
connect_timeout: 20.0
read_timeout: 60.0
total_timeout: 120.0
```

### `aiohttp.ClientResponseError: 429`

**Causa:** Rate limiting del servidor

**Solución:**
- El sistema se adapta automáticamente
- Si persiste, reducir `requests_per_minute` base

### `pybreaker.CircuitBreakerError`

**Causa:** Circuit breaker está abierto

**Solución:**
- Esperar `circuit_timeout_seconds`
- O resetear manualmente si la causa se resolvió

### `ConnectionResetError: Connection reset by peer`

**Causas:**
- Servidor cerró conexión abruptamente
- Posible bloqueo

**Solución:**
- Verificar si la IP está bloqueada
- Rotar User-Agent
- Usar proxy si disponible

### `json.JSONDecodeError`

**Causa:** Respuesta no es JSON válido (posible HTML de error/captcha)

**Solución:**
- Verificar manualmente el sitio
- Revisar si hay captcha
- Actualizar lógica de parsing

---

## 📞 Escalación

Si el problema persiste después de seguir esta guía:

1. **Recopilar información:**
   - Logs relevantes
   - Screenshots de Grafana
   - Output de health_check.sh

2. **Contactar soporte:**
   - Email: soporte@emi.edu.bo
   - Incluir toda la información recopilada

3. **Para emergencias críticas:**
   - Teléfono: +591 XXXXXXXX
   - Disponible 24/7

---

*Última actualización: Sprint 6 - Diciembre 2024*
