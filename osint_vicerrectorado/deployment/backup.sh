#!/bin/bash
# =============================================================================
# Backup Script - Sistema OSINT EMI Bolivia
# Sprint 6: Hardening y Automatización
#
# Uso: ./backup.sh [tipo] [opciones]
#   tipo: full, database, redis, config (default: full)
#   opciones:
#     --output DIR   Directorio de salida
#     --compress     Comprimir backup (default: true)
#     --encrypt      Encriptar backup con GPG
#     --retention N  Mantener últimos N backups (default: 7)
# =============================================================================

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_TYPE="${1:-full}"
BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPRESS=true
ENCRYPT=false
RETENTION=7

# Parsear argumentos
shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        --output) BACKUP_DIR="$2"; shift ;;
        --compress) COMPRESS=true ;;
        --no-compress) COMPRESS=false ;;
        --encrypt) ENCRYPT=true ;;
        --retention) RETENTION="$2"; shift ;;
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
}

# Crear directorio de backup
mkdir -p "$BACKUP_DIR"

backup_database() {
    log INFO "Realizando backup de PostgreSQL..."
    
    local db_backup="${BACKUP_DIR}/postgres_${TIMESTAMP}.sql"
    
    if docker ps | grep -q osint-postgres; then
        docker exec osint-postgres pg_dump -U osint osint_db > "$db_backup"
        
        if [ "$COMPRESS" = true ]; then
            gzip "$db_backup"
            db_backup="${db_backup}.gz"
        fi
        
        log INFO "✅ Backup de PostgreSQL creado: $db_backup"
        echo "$db_backup"
    else
        log ERROR "Container de PostgreSQL no está corriendo"
        return 1
    fi
}

backup_redis() {
    log INFO "Realizando backup de Redis..."
    
    local redis_backup="${BACKUP_DIR}/redis_${TIMESTAMP}.rdb"
    
    if docker ps | grep -q osint-redis; then
        # Forzar guardado de RDB
        docker exec osint-redis redis-cli BGSAVE
        sleep 2
        
        # Copiar archivo RDB
        docker cp osint-redis:/data/dump.rdb "$redis_backup"
        
        if [ "$COMPRESS" = true ]; then
            gzip "$redis_backup"
            redis_backup="${redis_backup}.gz"
        fi
        
        log INFO "✅ Backup de Redis creado: $redis_backup"
        echo "$redis_backup"
    else
        log ERROR "Container de Redis no está corriendo"
        return 1
    fi
}

backup_config() {
    log INFO "Realizando backup de configuración..."
    
    local config_backup="${BACKUP_DIR}/config_${TIMESTAMP}.tar"
    
    # Archivos de configuración a incluir
    local config_files=(
        "docker-compose.yml"
        ".env"
        "scrapers/config/sources.yaml"
        "monitoring/prometheus/prometheus.yml"
        "monitoring/prometheus/alerts.yml"
    )
    
    # Crear archivo tar con configuraciones
    cd "$PROJECT_DIR"
    tar -cvf "$config_backup" ${config_files[@]} 2>/dev/null || true
    
    if [ "$COMPRESS" = true ]; then
        gzip "$config_backup"
        config_backup="${config_backup}.gz"
    fi
    
    log INFO "✅ Backup de configuración creado: $config_backup"
    echo "$config_backup"
}

backup_data() {
    log INFO "Realizando backup de datos..."
    
    local data_backup="${BACKUP_DIR}/data_${TIMESTAMP}.tar"
    
    # Directorios de datos
    cd "$PROJECT_DIR"
    tar -cvf "$data_backup" data/ 2>/dev/null || true
    
    if [ "$COMPRESS" = true ]; then
        gzip "$data_backup"
        data_backup="${data_backup}.gz"
    fi
    
    log INFO "✅ Backup de datos creado: $data_backup"
    echo "$data_backup"
}

backup_full() {
    log INFO "Realizando backup completo..."
    
    local full_backup_dir="${BACKUP_DIR}/full_${TIMESTAMP}"
    mkdir -p "$full_backup_dir"
    
    # Backup de todos los componentes
    backup_database > "${full_backup_dir}/postgres_path.txt" 2>&1 || true
    backup_redis > "${full_backup_dir}/redis_path.txt" 2>&1 || true
    backup_config > "${full_backup_dir}/config_path.txt" 2>&1 || true
    
    # Crear archivo tar con todo
    cd "$BACKUP_DIR"
    tar -cvf "full_${TIMESTAMP}.tar" "full_${TIMESTAMP}/"
    
    if [ "$COMPRESS" = true ]; then
        gzip "full_${TIMESTAMP}.tar"
        log INFO "✅ Backup completo creado: ${BACKUP_DIR}/full_${TIMESTAMP}.tar.gz"
    fi
    
    # Limpiar directorio temporal
    rm -rf "$full_backup_dir"
}

encrypt_backup() {
    local file=$1
    
    if [ "$ENCRYPT" = true ] && [ -f "$file" ]; then
        log INFO "Encriptando backup..."
        
        if command -v gpg &> /dev/null; then
            gpg --symmetric --cipher-algo AES256 "$file"
            rm "$file"
            log INFO "✅ Backup encriptado: ${file}.gpg"
        else
            log WARN "GPG no está instalado, saltando encriptación"
        fi
    fi
}

cleanup_old_backups() {
    log INFO "Limpiando backups antiguos (manteniendo últimos $RETENTION)..."
    
    # Limpiar backups de PostgreSQL
    ls -t "${BACKUP_DIR}"/postgres_*.sql* 2>/dev/null | tail -n +$((RETENTION + 1)) | xargs -r rm -f
    
    # Limpiar backups de Redis
    ls -t "${BACKUP_DIR}"/redis_*.rdb* 2>/dev/null | tail -n +$((RETENTION + 1)) | xargs -r rm -f
    
    # Limpiar backups de configuración
    ls -t "${BACKUP_DIR}"/config_*.tar* 2>/dev/null | tail -n +$((RETENTION + 1)) | xargs -r rm -f
    
    # Limpiar backups completos
    ls -t "${BACKUP_DIR}"/full_*.tar* 2>/dev/null | tail -n +$((RETENTION + 1)) | xargs -r rm -f
    
    log INFO "✅ Limpieza completada"
}

show_backup_info() {
    log INFO ""
    log INFO "=============================================="
    log INFO "  Información del Backup"
    log INFO "=============================================="
    log INFO "Directorio: $BACKUP_DIR"
    log INFO "Tipo: $BACKUP_TYPE"
    log INFO "Timestamp: $TIMESTAMP"
    log INFO ""
    log INFO "Backups existentes:"
    ls -lh "$BACKUP_DIR" 2>/dev/null || echo "  (vacío)"
    log INFO ""
    log INFO "Espacio utilizado:"
    du -sh "$BACKUP_DIR" 2>/dev/null || echo "  0"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "=============================================="
    echo "  OSINT EMI - Backup System"
    echo "  Tipo: $BACKUP_TYPE"
    echo "  Fecha: $(date)"
    echo "=============================================="
    
    case $BACKUP_TYPE in
        full)
            backup_full
            ;;
        database|postgres|db)
            backup_database
            ;;
        redis)
            backup_redis
            ;;
        config)
            backup_config
            ;;
        data)
            backup_data
            ;;
        *)
            log ERROR "Tipo de backup desconocido: $BACKUP_TYPE"
            echo "Tipos válidos: full, database, redis, config, data"
            exit 1
            ;;
    esac
    
    cleanup_old_backups
    show_backup_info
    
    log INFO ""
    log INFO "🎉 Backup completado exitosamente!"
}

main
