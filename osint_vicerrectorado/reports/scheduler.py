"""
ReportScheduler - Sistema de Programación de Reportes
Sistema OSINT EMI - Sprint 5

Este módulo gestiona la programación y ejecución automática de reportes:
- Configuración de reportes recurrentes (diarios, semanales, mensuales)
- Almacenamiento de configuraciones
- Integración con Celery Beat
- Historial de ejecuciones

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import sqlite3
from pathlib import Path

# Configurar logging
logger = logging.getLogger("OSINT.Reports.Scheduler")


class ScheduleFrequency(Enum):
    """Frecuencias de programación disponibles."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class ScheduleStatus(Enum):
    """Estados de programación."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class ExecutionStatus(Enum):
    """Estados de ejecución."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class ReportConfig:
    """Configuración de un reporte programado."""
    id: int = None
    name: str = ""
    report_type: str = "executive"  # executive, alerts, statistical, excel
    schedule_type: str = "weekly"  # daily, weekly, monthly, custom
    cron_expression: str = "0 8 * * 1"  # Por defecto: lunes 8am
    recipients: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    created_by: int = None
    created_at: str = None
    updated_at: str = None
    last_run: str = None
    next_run: str = None
    run_count: int = 0
    fail_count: int = 0
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ReportConfig':
        """Crea instancia desde diccionario."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionLog:
    """Log de ejecución de reporte."""
    id: int = None
    config_id: int = None
    started_at: str = None
    completed_at: str = None
    status: str = "pending"
    file_path: str = None
    file_size: int = 0
    email_sent: bool = False
    email_recipients: List[str] = field(default_factory=list)
    error_message: str = None
    execution_time: float = 0
    
    def to_dict(self) -> Dict:
        """Convierte a diccionario."""
        data = asdict(self)
        data['email_recipients'] = json.dumps(data['email_recipients'])
        return data


class ReportScheduler:
    """
    Gestor de programación de reportes.
    
    Maneja la configuración, almacenamiento y seguimiento de
    reportes programados con diferentes frecuencias.
    
    Attributes:
        db_path (str): Ruta a la base de datos SQLite
        configs (list): Cache de configuraciones activas
    """
    
    def __init__(self, db_path: str = None):
        """
        Inicializa el scheduler.
        
        Args:
            db_path: Ruta a la BD. Si es None, usa ubicación por defecto.
        """
        base_dir = Path(__file__).parent.parent
        self.db_path = db_path or str(base_dir / 'data' / 'reports_scheduler.db')
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Inicializar BD
        self._init_database()
        
        logger.info(f"ReportScheduler inicializado. DB: {self.db_path}")
    
    def _init_database(self):
        """Inicializa las tablas de la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de configuraciones de reportes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL,
                    report_type VARCHAR(50) NOT NULL,
                    schedule_type VARCHAR(20) NOT NULL,
                    cron_expression VARCHAR(100),
                    recipients TEXT,
                    params TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    run_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0
                )
            """)
            
            # Tabla de historial de ejecuciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_id INTEGER NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending',
                    file_path VARCHAR(255),
                    file_size INTEGER DEFAULT 0,
                    email_sent BOOLEAN DEFAULT 0,
                    email_recipients TEXT,
                    error_message TEXT,
                    execution_time REAL DEFAULT 0,
                    FOREIGN KEY (config_id) REFERENCES report_configs(id)
                )
            """)
            
            # Índices
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_status 
                ON report_configs(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_next_run 
                ON report_configs(next_run)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_config 
                ON execution_logs(config_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_status 
                ON execution_logs(status)
            """)
            
            conn.commit()
    
    # ========================================
    # CRUD de Configuraciones
    # ========================================
    
    def create_schedule(
        self,
        name: str,
        report_type: str,
        schedule_type: str,
        recipients: List[str],
        params: Dict[str, Any] = None,
        cron_expression: str = None,
        created_by: int = None
    ) -> ReportConfig:
        """
        Crea una nueva programación de reporte.
        
        Args:
            name: Nombre descriptivo
            report_type: Tipo de reporte ('executive', 'alerts', 'statistical', 'excel')
            schedule_type: Frecuencia ('daily', 'weekly', 'monthly', 'custom')
            recipients: Lista de emails destinatarios
            params: Parámetros del reporte (filtros, rango fechas, etc.)
            cron_expression: Expresión cron personalizada
            created_by: ID del usuario creador
        
        Returns:
            ReportConfig creada
        """
        # Generar cron si no se proporciona
        if not cron_expression:
            cron_expression = self._generate_cron(schedule_type)
        
        config = ReportConfig(
            name=name,
            report_type=report_type,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            recipients=recipients,
            params=params or {},
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            next_run=self._calculate_next_run(cron_expression)
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO report_configs 
                (name, report_type, schedule_type, cron_expression, recipients, 
                 params, status, created_by, created_at, updated_at, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.name,
                config.report_type,
                config.schedule_type,
                config.cron_expression,
                json.dumps(config.recipients),
                json.dumps(config.params),
                config.status,
                config.created_by,
                config.created_at,
                config.updated_at,
                config.next_run
            ))
            config.id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"Programación creada: {config.name} (ID: {config.id})")
        return config
    
    def get_schedule(self, config_id: int) -> Optional[ReportConfig]:
        """
        Obtiene una configuración por ID.
        
        Args:
            config_id: ID de la configuración
        
        Returns:
            ReportConfig o None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM report_configs WHERE id = ?", (config_id,))
            row = cursor.fetchone()
            
            if row:
                data = dict(row)
                data['recipients'] = json.loads(data['recipients'] or '[]')
                data['params'] = json.loads(data['params'] or '{}')
                return ReportConfig.from_dict(data)
        
        return None
    
    def get_all_schedules(
        self,
        status: str = None,
        report_type: str = None,
        created_by: int = None
    ) -> List[ReportConfig]:
        """
        Obtiene todas las configuraciones con filtros opcionales.
        
        Args:
            status: Filtrar por estado
            report_type: Filtrar por tipo de reporte
            created_by: Filtrar por creador
        
        Returns:
            Lista de ReportConfig
        """
        query = "SELECT * FROM report_configs WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type)
        if created_by:
            query += " AND created_by = ?"
            params.append(created_by)
        
        query += " ORDER BY created_at DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            configs = []
            for row in rows:
                data = dict(row)
                data['recipients'] = json.loads(data['recipients'] or '[]')
                data['params'] = json.loads(data['params'] or '{}')
                configs.append(ReportConfig.from_dict(data))
            
            return configs
    
    def update_schedule(
        self,
        config_id: int,
        updates: Dict[str, Any]
    ) -> Optional[ReportConfig]:
        """
        Actualiza una configuración existente.
        
        Args:
            config_id: ID de la configuración
            updates: Campos a actualizar
        
        Returns:
            ReportConfig actualizada o None
        """
        allowed_fields = [
            'name', 'report_type', 'schedule_type', 'cron_expression',
            'recipients', 'params', 'status'
        ]
        
        set_clauses = []
        values = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                if field in ['recipients', 'params']:
                    values.append(json.dumps(value))
                else:
                    values.append(value)
        
        if not set_clauses:
            return self.get_schedule(config_id)
        
        # Actualizar timestamp
        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        
        # Recalcular next_run si cambió el cron
        if 'cron_expression' in updates:
            set_clauses.append("next_run = ?")
            values.append(self._calculate_next_run(updates['cron_expression']))
        
        values.append(config_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE report_configs SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            conn.commit()
        
        logger.info(f"Programación actualizada: ID {config_id}")
        return self.get_schedule(config_id)
    
    def delete_schedule(self, config_id: int) -> bool:
        """
        Elimina una configuración.
        
        Args:
            config_id: ID de la configuración
        
        Returns:
            True si se eliminó, False si no existía
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM report_configs WHERE id = ?", (config_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        
        if deleted:
            logger.info(f"Programación eliminada: ID {config_id}")
        
        return deleted
    
    def toggle_schedule(self, config_id: int) -> Optional[ReportConfig]:
        """
        Activa/desactiva una programación.
        
        Args:
            config_id: ID de la configuración
        
        Returns:
            ReportConfig actualizada
        """
        config = self.get_schedule(config_id)
        if not config:
            return None
        
        new_status = 'paused' if config.status == 'active' else 'active'
        return self.update_schedule(config_id, {'status': new_status})
    
    # ========================================
    # Ejecución y Logs
    # ========================================
    
    def log_execution_start(self, config_id: int) -> int:
        """
        Registra el inicio de una ejecución.
        
        Args:
            config_id: ID de la configuración
        
        Returns:
            ID del log de ejecución
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO execution_logs (config_id, started_at, status)
                VALUES (?, ?, ?)
            """, (config_id, datetime.now().isoformat(), ExecutionStatus.RUNNING.value))
            log_id = cursor.lastrowid
            conn.commit()
        
        return log_id
    
    def log_execution_complete(
        self,
        log_id: int,
        success: bool,
        file_path: str = None,
        file_size: int = 0,
        email_sent: bool = False,
        email_recipients: List[str] = None,
        error_message: str = None
    ):
        """
        Registra la finalización de una ejecución.
        
        Args:
            log_id: ID del log
            success: Si fue exitosa
            file_path: Ruta del archivo generado
            file_size: Tamaño del archivo
            email_sent: Si se envió email
            email_recipients: Lista de destinatarios
            error_message: Mensaje de error si falló
        """
        completed_at = datetime.now().isoformat()
        status = ExecutionStatus.SUCCESS.value if success else ExecutionStatus.FAILED.value
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Obtener tiempo de inicio
            cursor.execute("SELECT started_at FROM execution_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            started_at = datetime.fromisoformat(row[0]) if row else datetime.now()
            execution_time = (datetime.fromisoformat(completed_at) - started_at).total_seconds()
            
            cursor.execute("""
                UPDATE execution_logs SET
                    completed_at = ?,
                    status = ?,
                    file_path = ?,
                    file_size = ?,
                    email_sent = ?,
                    email_recipients = ?,
                    error_message = ?,
                    execution_time = ?
                WHERE id = ?
            """, (
                completed_at,
                status,
                file_path,
                file_size,
                email_sent,
                json.dumps(email_recipients or []),
                error_message,
                execution_time,
                log_id
            ))
            
            # Obtener config_id para actualizar estadísticas
            cursor.execute("SELECT config_id FROM execution_logs WHERE id = ?", (log_id,))
            config_row = cursor.fetchone()
            
            if config_row:
                config_id = config_row[0]
                
                # Actualizar estadísticas de la configuración
                if success:
                    cursor.execute("""
                        UPDATE report_configs SET 
                            run_count = run_count + 1,
                            last_run = ?,
                            next_run = ?
                        WHERE id = ?
                    """, (
                        completed_at,
                        self._calculate_next_run_from_config(config_id),
                        config_id
                    ))
                else:
                    cursor.execute("""
                        UPDATE report_configs SET 
                            fail_count = fail_count + 1,
                            last_run = ?
                        WHERE id = ?
                    """, (completed_at, config_id))
            
            conn.commit()
        
        logger.info(f"Ejecución {'exitosa' if success else 'fallida'}: log_id={log_id}")
    
    def get_execution_history(
        self,
        config_id: int = None,
        status: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Obtiene historial de ejecuciones.
        
        Args:
            config_id: Filtrar por configuración
            status: Filtrar por estado
            limit: Número máximo de registros
        
        Returns:
            Lista de logs de ejecución
        """
        query = """
            SELECT e.*, c.name as config_name, c.report_type
            FROM execution_logs e
            JOIN report_configs c ON e.config_id = c.id
            WHERE 1=1
        """
        params = []
        
        if config_id:
            query += " AND e.config_id = ?"
            params.append(config_id)
        if status:
            query += " AND e.status = ?"
            params.append(status)
        
        query += f" ORDER BY e.started_at DESC LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                log = dict(row)
                log['email_recipients'] = json.loads(log['email_recipients'] or '[]')
                logs.append(log)
            
            return logs
    
    def get_execution_stats(self, config_id: int = None) -> Dict[str, Any]:
        """
        Obtiene estadísticas de ejecución.
        
        Args:
            config_id: Filtrar por configuración
        
        Returns:
            Dict con estadísticas
        """
        where = f"WHERE config_id = {config_id}" if config_id else ""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(execution_time) as avg_time,
                    SUM(file_size) as total_size
                FROM execution_logs {where}
            """)
            
            row = cursor.fetchone()
            
            return {
                'total_executions': row[0] or 0,
                'successful': row[1] or 0,
                'failed': row[2] or 0,
                'success_rate': round((row[1] or 0) / max(row[0] or 1, 1) * 100, 1),
                'avg_execution_time': round(row[3] or 0, 2),
                'total_files_size': row[4] or 0
            }
    
    # ========================================
    # Utilidades de Cron
    # ========================================
    
    def _generate_cron(self, schedule_type: str) -> str:
        """
        Genera expresión cron según tipo de frecuencia.
        
        Args:
            schedule_type: Tipo de frecuencia
        
        Returns:
            Expresión cron
        """
        crons = {
            'daily': '0 8 * * *',        # Todos los días a las 8am
            'weekly': '0 8 * * 1',        # Lunes a las 8am
            'monthly': '0 10 1 * *',      # Día 1 de cada mes a las 10am
            'custom': '0 8 * * *'         # Por defecto: diario
        }
        return crons.get(schedule_type, crons['daily'])
    
    def _calculate_next_run(self, cron_expression: str) -> str:
        """
        Calcula la próxima ejecución basada en cron.
        
        Args:
            cron_expression: Expresión cron
        
        Returns:
            Timestamp ISO de próxima ejecución
        """
        try:
            from croniter import croniter
            cron = croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
            return next_run.isoformat()
        except ImportError:
            # Fallback simple si croniter no está disponible
            return self._simple_next_run(cron_expression)
        except Exception as e:
            logger.warning(f"Error calculando next_run: {e}")
            return (datetime.now() + timedelta(days=1)).isoformat()
    
    def _simple_next_run(self, cron_expression: str) -> str:
        """Cálculo simple de próxima ejecución sin croniter."""
        parts = cron_expression.split()
        if len(parts) < 5:
            return (datetime.now() + timedelta(days=1)).isoformat()
        
        minute, hour, day, month, weekday = parts[:5]
        
        now = datetime.now()
        next_run = now.replace(second=0, microsecond=0)
        
        # Configurar hora
        if hour != '*':
            next_run = next_run.replace(hour=int(hour))
        if minute != '*':
            next_run = next_run.replace(minute=int(minute))
        
        # Si ya pasó hoy, avanzar según frecuencia
        if next_run <= now:
            if weekday != '*':
                # Semanal
                target_day = int(weekday)
                days_ahead = target_day - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
            elif day != '*':
                # Mensual
                next_month = now.month + 1 if now.month < 12 else 1
                next_year = now.year if now.month < 12 else now.year + 1
                next_run = next_run.replace(year=next_year, month=next_month, day=int(day))
            else:
                # Diario
                next_run += timedelta(days=1)
        
        return next_run.isoformat()
    
    def _calculate_next_run_from_config(self, config_id: int) -> str:
        """Calcula próxima ejecución desde una configuración."""
        config = self.get_schedule(config_id)
        if config:
            return self._calculate_next_run(config.cron_expression)
        return (datetime.now() + timedelta(days=1)).isoformat()
    
    # ========================================
    # Reportes Pendientes
    # ========================================
    
    def get_pending_reports(self) -> List[ReportConfig]:
        """
        Obtiene reportes que deben ejecutarse.
        
        Returns:
            Lista de configuraciones pendientes de ejecución
        """
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM report_configs 
                WHERE status = 'active' 
                AND (next_run IS NULL OR next_run <= ?)
                ORDER BY next_run
            """, (now,))
            rows = cursor.fetchall()
            
            configs = []
            for row in rows:
                data = dict(row)
                data['recipients'] = json.loads(data['recipients'] or '[]')
                data['params'] = json.loads(data['params'] or '{}')
                configs.append(ReportConfig.from_dict(data))
            
            return configs
    
    def reschedule_all(self):
        """Recalcula next_run para todas las configuraciones activas."""
        configs = self.get_all_schedules(status='active')
        
        for config in configs:
            new_next = self._calculate_next_run(config.cron_expression)
            self.update_schedule(config.id, {})  # Forzar actualización de next_run
        
        logger.info(f"Reprogramadas {len(configs)} configuraciones")


# ========================================
# Configuración de Celery Beat
# ========================================

def get_celery_beat_schedule() -> Dict[str, Dict]:
    """
    Genera configuración de Celery Beat desde las programaciones activas.
    
    Returns:
        Dict compatible con celery_beat_schedule
    """
    from celery.schedules import crontab
    
    scheduler = ReportScheduler()
    configs = scheduler.get_all_schedules(status='active')
    
    schedule = {}
    
    for config in configs:
        task_name = f"report-{config.report_type}-{config.id}"
        
        # Parsear cron expression
        parts = config.cron_expression.split()
        if len(parts) >= 5:
            minute, hour, day, month, weekday = parts[:5]
            
            schedule[task_name] = {
                'task': 'reports.tasks.generate_and_send_report',
                'schedule': crontab(
                    minute=minute,
                    hour=hour,
                    day_of_week=weekday if weekday != '*' else None,
                    day_of_month=day if day != '*' else None,
                    month_of_year=month if month != '*' else None
                ),
                'args': (config.id,)
            }
    
    return schedule


# Programaciones por defecto para demostración
DEFAULT_SCHEDULES = [
    {
        'name': 'Reporte Ejecutivo Semanal',
        'report_type': 'executive',
        'schedule_type': 'weekly',
        'cron_expression': '0 8 * * 1',  # Lunes 8am
        'recipients': ['vicerrector@emi.edu.bo'],
        'params': {
            'sections': ['summary', 'sentiment', 'alerts', 'trends'],
            'days_back': 7
        }
    },
    {
        'name': 'Alertas Diarias',
        'report_type': 'alerts',
        'schedule_type': 'daily',
        'cron_expression': '0 9 * * *',  # Todos los días 9am
        'recipients': ['monitoreo@emi.edu.bo'],
        'params': {
            'severity': None,
            'days': 1
        }
    },
    {
        'name': 'Anuario Estadístico Mensual',
        'report_type': 'statistical',
        'schedule_type': 'monthly',
        'cron_expression': '0 10 1 * *',  # Día 1 del mes 10am
        'recipients': ['direccion@emi.edu.bo'],
        'params': {
            'include_benchmarking': True
        }
    }
]


def init_default_schedules():
    """Inicializa las programaciones por defecto."""
    scheduler = ReportScheduler()
    
    # Verificar si ya existen configuraciones
    existing = scheduler.get_all_schedules()
    if existing:
        logger.info(f"Ya existen {len(existing)} programaciones. Saltando inicialización.")
        return
    
    for config in DEFAULT_SCHEDULES:
        scheduler.create_schedule(**config)
    
    logger.info(f"Inicializadas {len(DEFAULT_SCHEDULES)} programaciones por defecto")
