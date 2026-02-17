#!/bin/bash
# =============================================================================
# Health Check Script - Sistema OSINT EMI Bolivia
# Sprint 6: Hardening y Automatización
#
# Uso: ./health_check.sh [opciones]
#   opciones:
#     --quiet        Solo mostrar errores
#     --json         Output en formato JSON
#     --service NAME Verificar solo un servicio específico
# =============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuración
QUIET=false
JSON_OUTPUT=false
SPECIFIC_SERVICE=""
OVERALL_STATUS=0

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --quiet) QUIET=true ;;
        --json) JSON_OUTPUT=true ;;
        --service) SPECIFIC_SERVICE="$2"; shift ;;
        *) echo "Opción desconocida: $1"; exit 1 ;;
    esac
    shift
done

# Funciones de utilidad
log() {
    if [ "$QUIET" = false ] && [ "$JSON_OUTPUT" = false ]; then
        echo -e "$@"
    fi
}

check_service() {
    local service_name=$1
    local check_type=$2
    local check_cmd=$3
    local expected=$4
    
    if [ -n "$SPECIFIC_SERVICE" ] && [ "$SPECIFIC_SERVICE" != "$service_name" ]; then
        return 0
    fi
    
    local status="unknown"
    local details=""
    
    case $check_type in
        http)
            local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$check_cmd" 2>/dev/null || echo "000")
            if [ "$response" = "$expected" ]; then
                status="healthy"
                details="HTTP $response"
            else
                status="unhealthy"
                details="HTTP $response (expected $expected)"
                OVERALL_STATUS=1
            fi
            ;;
        tcp)
            if nc -z -w 2 $(echo "$check_cmd" | tr ':' ' ') 2>/dev/null; then
                status="healthy"
                details="Port open"
            else
                status="unhealthy"
                details="Port closed"
                OVERALL_STATUS=1
            fi
            ;;
        docker)
            local container_status=$(docker inspect --format='{{.State.Health.Status}}' "$check_cmd" 2>/dev/null || echo "not_found")
            if [ "$container_status" = "healthy" ] || [ "$container_status" = "running" ]; then
                status="healthy"
                details="Container $container_status"
            elif [ "$container_status" = "not_found" ]; then
                status="unhealthy"
                details="Container not found"
                OVERALL_STATUS=1
            else
                status="unhealthy"
                details="Container $container_status"
                OVERALL_STATUS=1
            fi
            ;;
        container_running)
            if docker ps --format '{{.Names}}' | grep -q "^${check_cmd}$"; then
                status="healthy"
                details="Running"
            else
                status="unhealthy"
                details="Not running"
                OVERALL_STATUS=1
            fi
            ;;
    esac
    
    if [ "$JSON_OUTPUT" = true ]; then
        echo "{\"service\": \"$service_name\", \"status\": \"$status\", \"details\": \"$details\"}"
    else
        local color=$GREEN
        local icon="✅"
        if [ "$status" = "unhealthy" ]; then
            color=$RED
            icon="❌"
        fi
        log "${color}${icon} ${service_name}: ${status} (${details})${NC}"
    fi
}

check_disk_space() {
    local threshold=80
    local usage=$(df -h / | awk 'NR==2 {gsub(/%/,"",$5); print $5}')
    
    if [ "$JSON_OUTPUT" = true ]; then
        echo "{\"service\": \"disk_space\", \"status\": \"$([ $usage -lt $threshold ] && echo healthy || echo warning)\", \"details\": \"${usage}% used\"}"
    else
        if [ $usage -lt $threshold ]; then
            log "${GREEN}✅ Disk Space: ${usage}% used${NC}"
        else
            log "${YELLOW}⚠️  Disk Space: ${usage}% used (threshold: ${threshold}%)${NC}"
        fi
    fi
}

check_memory() {
    local threshold=85
    local usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    
    if [ "$JSON_OUTPUT" = true ]; then
        echo "{\"service\": \"memory\", \"status\": \"$([ $usage -lt $threshold ] && echo healthy || echo warning)\", \"details\": \"${usage}% used\"}"
    else
        if [ $usage -lt $threshold ]; then
            log "${GREEN}✅ Memory: ${usage}% used${NC}"
        else
            log "${YELLOW}⚠️  Memory: ${usage}% used (threshold: ${threshold}%)${NC}"
        fi
    fi
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    if [ "$JSON_OUTPUT" = true ]; then
        echo "["
    else
        log "=============================================="
        log "  OSINT EMI - Health Check"
        log "  Fecha: $(date)"
        log "=============================================="
        log ""
        log "${YELLOW}Verificando servicios...${NC}"
        log ""
    fi
    
    # Servicios principales
    check_service "osint-app" "container_running" "osint-app" ""
    check_service "api-health" "http" "http://localhost:5000/health" "200"
    check_service "metrics-endpoint" "http" "http://localhost:9090/metrics" "200"
    
    # Base de datos
    check_service "postgresql" "container_running" "osint-postgres" ""
    check_service "postgresql-port" "tcp" "localhost:5432" ""
    
    # Redis
    check_service "redis" "container_running" "osint-redis" ""
    check_service "redis-port" "tcp" "localhost:6379" ""
    
    # Celery
    check_service "celery-worker" "container_running" "osint-celery-worker" ""
    
    # Monitoring
    check_service "prometheus" "container_running" "osint-prometheus" ""
    check_service "prometheus-ui" "http" "http://localhost:9090/-/healthy" "200"
    
    check_service "grafana" "container_running" "osint-grafana" ""
    check_service "grafana-ui" "http" "http://localhost:3000/api/health" "200"
    
    check_service "alertmanager" "container_running" "osint-alertmanager" ""
    check_service "alertmanager-ui" "http" "http://localhost:9093/-/healthy" "200"
    
    if [ "$JSON_OUTPUT" = false ]; then
        log ""
        log "${YELLOW}Verificando recursos del sistema...${NC}"
        log ""
    fi
    
    # Recursos del sistema
    check_disk_space
    check_memory
    
    if [ "$JSON_OUTPUT" = true ]; then
        echo "]"
    else
        log ""
        if [ $OVERALL_STATUS -eq 0 ]; then
            log "${GREEN}=============================================="
            log "  ✅ Todos los servicios están saludables"
            log "==============================================${NC}"
        else
            log "${RED}=============================================="
            log "  ❌ Algunos servicios tienen problemas"
            log "==============================================${NC}"
        fi
    fi
    
    exit $OVERALL_STATUS
}

main
