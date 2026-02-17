"""
Celery Tasks - Tareas Asíncronas para Reportes
Sistema OSINT EMI - Sprint 5

Este módulo define las tareas de Celery para:
- Generación asíncrona de reportes PDF/Excel
- Envío programado de reportes por email
- Ejecución de reportes programados

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from celery import Celery, Task
from celery.exceptions import MaxRetriesExceededError

# Configurar logging
logger = logging.getLogger("OSINT.Reports.Tasks")

# ========================================
# Configuración de Celery
# ========================================

# Configuración del broker (Redis)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Crear aplicación Celery
celery_app = Celery(
    'osint_reports',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configuración de Celery
celery_app.conf.update(
    # Serialización
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Timezone
    timezone='America/La_Paz',
    enable_utc=True,
    
    # Resultados
    result_expires=86400,  # 24 horas
    
    # Workers
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    
    # Reintentos
    task_default_retry_delay=60,  # 1 minuto
    task_max_retries=3,
    
    # Tracking
    task_track_started=True,
    task_send_sent_event=True,
    
    # Queues
    task_default_queue='reports',
    task_queues={
        'reports': {'exchange': 'reports'},
        'emails': {'exchange': 'emails'},
        'scheduled': {'exchange': 'scheduled'}
    }
)


# ========================================
# Clase Base para Tasks con Progress
# ========================================

class ProgressTask(Task):
    """Task base que soporta reporte de progreso."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Callback cuando la tarea falla."""
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_success(self, retval, task_id, args, kwargs):
        """Callback cuando la tarea tiene éxito."""
        logger.info(f"Task {task_id} completed successfully")
    
    def update_progress(self, progress: int, message: str = None):
        """Actualiza el progreso de la tarea."""
        self.update_state(
            state='PROGRESS',
            meta={
                'progress': progress,
                'message': message or f'Progreso: {progress}%'
            }
        )


# ========================================
# Tasks de Generación de Reportes
# ========================================

@celery_app.task(bind=True, base=ProgressTask, name='reports.generate_pdf')
def generate_pdf_report_async(
    self,
    report_type: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tarea asíncrona para generar reportes PDF.
    
    Args:
        report_type: Tipo de reporte ('executive', 'alerts', 'statistical', 'career')
        params: Parámetros del reporte
    
    Returns:
        Dict con status y file_path
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Iniciando generación de PDF: {report_type}")
    
    try:
        # Actualizar estado inicial
        self.update_state(state='PROCESSING', meta={'progress': 5, 'message': 'Iniciando...'})
        
        # Importar generador
        from reports.pdf_generator import PDFGenerator
        generator = PDFGenerator()
        
        # Función de callback para progreso
        def progress_callback(percent):
            self.update_state(
                state='PROCESSING',
                meta={'progress': percent, 'message': f'Generando reporte: {percent}%'}
            )
        
        # Generar según tipo
        if report_type == 'executive':
            file_path = generator.generate_executive_report(
                start_date=params.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),
                end_date=params.get('end_date', datetime.now().strftime('%Y-%m-%d')),
                filters=params.get('filters', {}),
                sections=params.get('sections'),
                callback=progress_callback
            )
        
        elif report_type == 'alerts':
            file_path = generator.generate_alerts_report(
                severity=params.get('severity'),
                days=params.get('days', 7),
                filters=params.get('filters', {}),
                callback=progress_callback
            )
        
        elif report_type == 'statistical':
            semester = params.get('semester', f"{datetime.now().year}-{'I' if datetime.now().month <= 6 else 'II'}")
            file_path = generator.generate_statistical_report(
                semester=semester,
                include_sections=params.get('include_sections'),
                callback=progress_callback
            )
        
        elif report_type == 'career':
            file_path = generator.generate_career_report(
                career_id=params.get('career_id', 1),
                career_name=params.get('career_name', 'Ingeniería de Sistemas'),
                start_date=params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
                end_date=params.get('end_date', datetime.now().strftime('%Y-%m-%d')),
                callback=progress_callback
            )
        
        else:
            raise ValueError(f"Tipo de reporte PDF no válido: {report_type}")
        
        # Verificar archivo generado
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo no generado: {file_path}")
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"[{task_id}] PDF generado: {file_path} ({file_size} bytes)")
        
        return {
            'status': 'success',
            'file_path': file_path,
            'file_size': file_size,
            'report_type': report_type,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[{task_id}] Error generando PDF: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0}
        )
        raise


@celery_app.task(bind=True, base=ProgressTask, name='reports.generate_excel')
def generate_excel_report_async(
    self,
    report_type: str,
    params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tarea asíncrona para generar reportes Excel.
    
    Args:
        report_type: Tipo de reporte ('sentiment', 'pivot', 'anomalies', 'combined')
        params: Parámetros del reporte
    
    Returns:
        Dict con status y file_path
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Iniciando generación de Excel: {report_type}")
    
    try:
        self.update_state(state='PROCESSING', meta={'progress': 5, 'message': 'Iniciando...'})
        
        from reports.excel_generator import ExcelGenerator
        generator = ExcelGenerator()
        
        def progress_callback(percent):
            self.update_state(
                state='PROCESSING',
                meta={'progress': percent, 'message': f'Generando Excel: {percent}%'}
            )
        
        if report_type == 'sentiment':
            file_path = generator.generate_sentiment_dataset(
                start_date=params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
                end_date=params.get('end_date', datetime.now().strftime('%Y-%m-%d')),
                filters=params.get('filters', {}),
                include_charts=params.get('include_charts', True),
                callback=progress_callback
            )
        
        elif report_type == 'pivot':
            file_path = generator.generate_pivot_table(
                dimension=params.get('dimension', 'career'),
                start_date=params.get('start_date'),
                end_date=params.get('end_date'),
                callback=progress_callback
            )
        
        elif report_type == 'anomalies':
            file_path = generator.generate_anomalies_report(
                days=params.get('days', 30),
                threshold=params.get('threshold', 2.0),
                callback=progress_callback
            )
        
        elif report_type == 'combined':
            file_path = generator.generate_combined_report(
                start_date=params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
                end_date=params.get('end_date', datetime.now().strftime('%Y-%m-%d')),
                include_sentiment=params.get('include_sentiment', True),
                include_alerts=params.get('include_alerts', True),
                include_trends=params.get('include_trends', True),
                callback=progress_callback
            )
        
        else:
            raise ValueError(f"Tipo de reporte Excel no válido: {report_type}")
        
        file_size = os.path.getsize(file_path)
        
        logger.info(f"[{task_id}] Excel generado: {file_path} ({file_size} bytes)")
        
        return {
            'status': 'success',
            'file_path': file_path,
            'file_size': file_size,
            'report_type': report_type,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[{task_id}] Error generando Excel: {e}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0}
        )
        raise


# ========================================
# Tasks de Envío de Email
# ========================================

@celery_app.task(bind=True, name='reports.send_email', max_retries=3)
def send_report_email_async(
    self,
    recipients: list,
    subject: str,
    attachment_path: str,
    report_type: str = 'general',
    body: str = None
) -> Dict[str, Any]:
    """
    Tarea asíncrona para enviar reportes por email.
    
    Args:
        recipients: Lista de destinatarios
        subject: Asunto del email
        attachment_path: Ruta del archivo adjunto
        report_type: Tipo de reporte
        body: Cuerpo del mensaje
    
    Returns:
        Dict con resultado del envío
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Enviando email a {len(recipients)} destinatario(s)")
    
    try:
        from reports.email_service import EmailService
        email_service = EmailService()
        
        result = email_service.send_report(
            recipients=recipients,
            subject=subject,
            attachment_path=attachment_path,
            body=body,
            report_type=report_type
        )
        
        if result['status'] == 'failed':
            # Reintentar si falló
            raise Exception(result.get('error', 'Error desconocido en envío'))
        
        logger.info(f"[{task_id}] Email enviado exitosamente")
        return result
        
    except Exception as e:
        logger.warning(f"[{task_id}] Error enviando email (intento {self.request.retries + 1}): {e}")
        
        try:
            # Reintento con backoff exponencial
            self.retry(countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            logger.error(f"[{task_id}] Máximo de reintentos alcanzado")
            return {
                'status': 'failed',
                'error': str(e),
                'retries': self.request.retries
            }


@celery_app.task(bind=True, name='reports.send_notification')
def send_notification_async(
    self,
    recipients: list,
    notification_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Tarea asíncrona para enviar notificaciones.
    
    Args:
        recipients: Lista de destinatarios
        notification_type: Tipo de notificación
        data: Datos del mensaje
    
    Returns:
        Dict con resultado
    """
    try:
        from reports.email_service import EmailService
        email_service = EmailService()
        
        return email_service.send_notification(
            recipients=recipients,
            notification_type=notification_type,
            data=data
        )
        
    except Exception as e:
        logger.error(f"Error enviando notificación: {e}")
        return {'status': 'failed', 'error': str(e)}


# ========================================
# Tasks de Reportes Programados
# ========================================

@celery_app.task(bind=True, name='reports.scheduled.generate_and_send')
def generate_and_send_report(self, config_id: int) -> Dict[str, Any]:
    """
    Tarea programada: genera un reporte y lo envía por email.
    
    Args:
        config_id: ID de la configuración del reporte
    
    Returns:
        Dict con resultado de generación y envío
    """
    task_id = self.request.id
    logger.info(f"[{task_id}] Ejecutando reporte programado: config_id={config_id}")
    
    from reports.scheduler import ReportScheduler
    scheduler = ReportScheduler()
    
    # Registrar inicio de ejecución
    log_id = scheduler.log_execution_start(config_id)
    
    try:
        # Obtener configuración
        config = scheduler.get_schedule(config_id)
        if not config:
            raise ValueError(f"Configuración no encontrada: {config_id}")
        
        if config.status != 'active':
            logger.info(f"[{task_id}] Configuración inactiva, saltando")
            return {'status': 'skipped', 'reason': 'Configuration not active'}
        
        # Determinar si es PDF o Excel
        pdf_types = ['executive', 'alerts', 'statistical', 'career']
        excel_types = ['sentiment', 'pivot', 'anomalies', 'combined', 'excel']
        
        if config.report_type in pdf_types:
            # Generar PDF
            result = generate_pdf_report_async.apply(
                args=(config.report_type, config.params)
            ).get(timeout=600)  # 10 minutos máximo
        elif config.report_type in excel_types:
            # Generar Excel
            report_subtype = 'sentiment' if config.report_type == 'excel' else config.report_type
            result = generate_excel_report_async.apply(
                args=(report_subtype, config.params)
            ).get(timeout=600)
        else:
            raise ValueError(f"Tipo de reporte no soportado: {config.report_type}")
        
        if result['status'] != 'success':
            raise Exception(result.get('error', 'Error en generación'))
        
        file_path = result['file_path']
        file_size = result.get('file_size', 0)
        
        # Enviar por email si hay destinatarios
        email_sent = False
        if config.recipients:
            subject = f"Reporte {config.name} - {datetime.now().strftime('%d/%m/%Y')}"
            
            email_result = send_report_email_async.apply(
                args=(config.recipients, subject, file_path, config.report_type)
            ).get(timeout=300)  # 5 minutos máximo
            
            email_sent = email_result.get('status') == 'sent'
        
        # Registrar éxito
        scheduler.log_execution_complete(
            log_id=log_id,
            success=True,
            file_path=file_path,
            file_size=file_size,
            email_sent=email_sent,
            email_recipients=config.recipients if email_sent else []
        )
        
        logger.info(f"[{task_id}] Reporte programado completado: {file_path}")
        
        return {
            'status': 'success',
            'config_id': config_id,
            'file_path': file_path,
            'email_sent': email_sent,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[{task_id}] Error en reporte programado: {e}")
        
        # Registrar fallo
        scheduler.log_execution_complete(
            log_id=log_id,
            success=False,
            error_message=str(e)
        )
        
        # Notificar error
        config = scheduler.get_schedule(config_id)
        if config and config.recipients:
            send_notification_async.delay(
                recipients=config.recipients,
                notification_type='report_failed',
                data={
                    'message': f'Error al generar {config.name}',
                    'error': str(e)
                }
            )
        
        return {
            'status': 'failed',
            'config_id': config_id,
            'error': str(e)
        }


@celery_app.task(name='reports.scheduled.check_pending')
def check_pending_reports() -> Dict[str, Any]:
    """
    Tarea periódica: verifica y ejecuta reportes pendientes.
    
    Esta tarea se ejecuta frecuentemente (ej: cada 5 minutos) y
    verifica si hay reportes que deben generarse según su next_run.
    
    Returns:
        Dict con resumen de ejecuciones
    """
    logger.info("Verificando reportes pendientes...")
    
    from reports.scheduler import ReportScheduler
    scheduler = ReportScheduler()
    
    pending = scheduler.get_pending_reports()
    
    if not pending:
        logger.info("No hay reportes pendientes")
        return {'status': 'ok', 'pending': 0, 'executed': 0}
    
    logger.info(f"Encontrados {len(pending)} reportes pendientes")
    
    executed = 0
    for config in pending:
        try:
            # Ejecutar reporte de forma asíncrona
            generate_and_send_report.delay(config.id)
            executed += 1
        except Exception as e:
            logger.error(f"Error encolando reporte {config.id}: {e}")
    
    return {
        'status': 'ok',
        'pending': len(pending),
        'executed': executed
    }


# ========================================
# Tasks de Mantenimiento
# ========================================

@celery_app.task(name='reports.cleanup.old_files')
def cleanup_old_reports(days: int = 30) -> Dict[str, Any]:
    """
    Tarea de limpieza: elimina reportes antiguos.
    
    Args:
        days: Eliminar archivos más antiguos que estos días
    
    Returns:
        Dict con resumen de limpieza
    """
    logger.info(f"Limpiando reportes más antiguos que {days} días...")
    
    import glob
    from pathlib import Path
    
    reports_dir = Path(__file__).parent / 'generated'
    cutoff = datetime.now() - timedelta(days=days)
    
    deleted = 0
    freed_space = 0
    
    for pattern in ['*.pdf', '*.xlsx', '*.xls']:
        for file_path in reports_dir.glob(pattern):
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted += 1
                    freed_space += size
            except Exception as e:
                logger.warning(f"Error eliminando {file_path}: {e}")
    
    logger.info(f"Limpieza completada: {deleted} archivos eliminados, {freed_space / 1024 / 1024:.2f} MB liberados")
    
    return {
        'status': 'ok',
        'deleted_files': deleted,
        'freed_space_mb': round(freed_space / 1024 / 1024, 2)
    }


@celery_app.task(name='reports.cleanup.old_logs')
def cleanup_old_logs(days: int = 90) -> Dict[str, Any]:
    """
    Tarea de limpieza: elimina logs de ejecución antiguos.
    
    Args:
        days: Eliminar logs más antiguos que estos días
    
    Returns:
        Dict con resumen
    """
    logger.info(f"Limpiando logs más antiguos que {days} días...")
    
    from reports.scheduler import ReportScheduler
    import sqlite3
    
    scheduler = ReportScheduler()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    
    with sqlite3.connect(scheduler.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM execution_logs WHERE started_at < ?",
            (cutoff,)
        )
        deleted = cursor.rowcount
        conn.commit()
    
    logger.info(f"Limpieza de logs completada: {deleted} registros eliminados")
    
    return {
        'status': 'ok',
        'deleted_logs': deleted
    }


# ========================================
# Configuración de Celery Beat Schedule
# ========================================

celery_app.conf.beat_schedule = {
    # Verificar reportes pendientes cada 5 minutos
    'check-pending-reports': {
        'task': 'reports.scheduled.check_pending',
        'schedule': 300.0,  # 5 minutos
    },
    
    # Limpieza diaria de archivos antiguos (3am)
    'cleanup-old-files': {
        'task': 'reports.cleanup.old_files',
        'schedule': {
            'minute': 0,
            'hour': 3,
        },
        'args': (30,)
    },
    
    # Limpieza semanal de logs (domingos 4am)
    'cleanup-old-logs': {
        'task': 'reports.cleanup.old_logs',
        'schedule': {
            'minute': 0,
            'hour': 4,
            'day_of_week': 0,  # Domingo
        },
        'args': (90,)
    },
}


# ========================================
# Funciones de utilidad
# ========================================

def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Obtiene el estado de una tarea.
    
    Args:
        task_id: ID de la tarea
    
    Returns:
        Dict con estado y metadata
    """
    result = celery_app.AsyncResult(task_id)
    
    response = {
        'task_id': task_id,
        'state': result.state,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None,
    }
    
    if result.state == 'PROGRESS' or result.state == 'PROCESSING':
        response['progress'] = result.info.get('progress', 0)
        response['message'] = result.info.get('message', '')
    elif result.state == 'SUCCESS':
        response['result'] = result.result
    elif result.state == 'FAILURE':
        response['error'] = str(result.result)
    
    return response


def cancel_task(task_id: str) -> bool:
    """
    Cancela una tarea en ejecución.
    
    Args:
        task_id: ID de la tarea
    
    Returns:
        True si se canceló
    """
    celery_app.control.revoke(task_id, terminate=True)
    return True


def get_queue_status() -> Dict[str, Any]:
    """
    Obtiene estado de las colas de Celery.
    
    Returns:
        Dict con información de colas
    """
    inspect = celery_app.control.inspect()
    
    return {
        'active': inspect.active() or {},
        'scheduled': inspect.scheduled() or {},
        'reserved': inspect.reserved() or {},
        'stats': inspect.stats() or {}
    }
