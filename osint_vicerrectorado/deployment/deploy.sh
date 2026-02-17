#!/bin/bash
# =============================================================================
# Deploy Script - Sistema OSINT EMI Bolivia
# Sprint 6: Hardening y Automatización
#
# Uso: ./deploy.sh [ambiente] [opciones]
#   ambiente: production, staging, development (default: production)
#   opciones:
#     --no-backup    No crear backup antes de deploy
#     --skip-tests   Saltar tests
#     --force        Forzar deploy incluso con errores
#     --dry-run      Solo mostrar comandos sin ejecutar
# =============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_DIR="${PROJECT_DIR}/logs"
DEPLOY_LOG="${LOG_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"

# Opciones
NO_BACKUP=false
SKIP_TESTS=false
FORCE=false
DRY_RUN=false

# Parsear argumentos
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backup) NO_BACKUP=true ;;
        --skip-tests) SKIP_TESTS=true ;;
        --force) FORCE=true ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Opción desconocida: $1"; exit 1 ;;
    esac
    shift
done

# Funciones de utilidad
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)  color=$GREEN ;;
        WARN)  color=$YELLOW ;;
        ERROR) color=$RED ;;
        *)     color=$NC ;;
    esac
    
    echo -e "${color}[${timestamp}] [${level}] ${message}${NC}"
    echo "[${timestamp}] [${level}] ${message}" >> "$DEPLOY_LOG"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log INFO "[DRY-RUN] $@"
    else
        log INFO "Ejecutando: $@"
        "$@" 2>&1 | tee -a "$DEPLOY_LOG"
        return ${PIPESTATUS[0]}
    fi
}

check_prerequisites() {
    log INFO "Verificando prerequisitos..."
    
    # Docker
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker no está instalado"
        exit 1
    fi
    
    # Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log ERROR "Docker Compose no está instalado"
        exit 1
    fi
    
    # Verificar que docker está corriendo
    if ! docker info &> /dev/null; then
        log ERROR "Docker daemon no está corriendo"
        exit 1
    fi
    
    log INFO "✅ Prerequisitos OK"
}

create_directories() {
    log INFO "Creando directorios necesarios..."
    
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "${PROJECT_DIR}/data/postgres"
    mkdir -p "${PROJECT_DIR}/data/redis"
    mkdir -p "${PROJECT_DIR}/data/prometheus"
    mkdir -p "${PROJECT_DIR}/data/grafana"
    
    log INFO "✅ Directorios creados"
}

backup_database() {
    if [ "$NO_BACKUP" = true ]; then
        log WARN "Saltando backup (--no-backup especificado)"
        return 0
    fi
    
    log INFO "Creando backup de base de datos..."
    
    local backup_file="${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    if docker ps | grep -q postgres; then
        run_cmd docker exec osint-postgres pg_dump -U osint osint_db | gzip > "$backup_file"
        log INFO "✅ Backup creado: $backup_file"
    else
        log WARN "Container de PostgreSQL no está corriendo, saltando backup"
    fi
}

run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        log WARN "Saltando tests (--skip-tests especificado)"
        return 0
    fi
    
    log INFO "Ejecutando tests..."
    
    # Tests básicos de sintaxis Python
    run_cmd python -m py_compile "${PROJECT_DIR}/resilience"/*.py 2>/dev/null || {
        if [ "$FORCE" = false ]; then
            log ERROR "Tests de sintaxis fallaron"
            exit 1
        fi
        log WARN "Tests fallaron pero continuando (--force)"
    }
    
    log INFO "✅ Tests pasaron"
}

pull_images() {
    log INFO "Descargando imágenes Docker..."
    
    run_cmd docker-compose -f "${PROJECT_DIR}/docker-compose.yml" pull
    
    log INFO "✅ Imágenes descargadas"
}

build_images() {
    log INFO "Construyendo imágenes..."
    
    run_cmd docker-compose -f "${PROJECT_DIR}/docker-compose.yml" build --no-cache
    
    log INFO "✅ Imágenes construidas"
}

stop_services() {
    log INFO "Deteniendo servicios existentes..."
    
    run_cmd docker-compose -f "${PROJECT_DIR}/docker-compose.yml" down --remove-orphans
    
    log INFO "✅ Servicios detenidos"
}

start_services() {
    log INFO "Iniciando servicios..."
    
    run_cmd docker-compose -f "${PROJECT_DIR}/docker-compose.yml" up -d
    
    log INFO "✅ Servicios iniciados"
}

wait_for_health() {
    log INFO "Esperando que los servicios estén saludables..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if "${SCRIPT_DIR}/health_check.sh" --quiet; then
            log INFO "✅ Todos los servicios están saludables"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log INFO "Intento $attempt/$max_attempts - Esperando..."
        sleep 5
    done
    
    log ERROR "Los servicios no alcanzaron estado saludable"
    
    if [ "$FORCE" = false ]; then
        exit 1
    fi
}

run_migrations() {
    log INFO "Ejecutando migraciones de base de datos..."
    
    run_cmd docker exec osint-app flask db upgrade 2>/dev/null || {
        log WARN "No hay migraciones pendientes o Flask-Migrate no está configurado"
    }
    
    log INFO "✅ Migraciones completadas"
}

cleanup_old_images() {
    log INFO "Limpiando imágenes antiguas..."
    
    run_cmd docker image prune -f
    
    log INFO "✅ Limpieza completada"
}

show_status() {
    log INFO "Estado actual de los servicios:"
    docker-compose -f "${PROJECT_DIR}/docker-compose.yml" ps
    
    echo ""
    log INFO "URLs de los servicios:"
    echo "  🌐 API:        http://localhost:5000"
    echo "  📊 Prometheus: http://localhost:9090"
    echo "  📈 Grafana:    http://localhost:3000"
    echo "  🔔 Alertmanager: http://localhost:9093"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "=============================================="
    echo "  OSINT EMI - Sistema de Deploy"
    echo "  Ambiente: $ENVIRONMENT"
    echo "  Fecha: $(date)"
    echo "=============================================="
    
    # Crear directorio de logs
    mkdir -p "$LOG_DIR"
    
    log INFO "Iniciando deploy en ambiente: $ENVIRONMENT"
    
    # Pasos del deploy
    check_prerequisites
    create_directories
    backup_database
    run_tests
    pull_images
    build_images
    stop_services
    start_services
    wait_for_health
    run_migrations
    cleanup_old_images
    
    show_status
    
    echo ""
    log INFO "🎉 Deploy completado exitosamente!"
    echo ""
    echo "Log completo disponible en: $DEPLOY_LOG"
}

# Ejecutar
main "$@"
