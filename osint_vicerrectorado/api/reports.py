"""
API Endpoints para el Módulo de Reportes
Sistema de Analítica OSINT - EMI Bolivia
Sprint 5: Reportes y Estadísticas
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from flask_cors import cross_origin
from datetime import datetime, timedelta
from functools import wraps
import os
import json
import uuid

# Importaciones del módulo de reportes
from reports import PDFGenerator, ExcelGenerator, EmailService, ReportScheduler
from reports.tasks import (
    generate_pdf_report_async,
    generate_excel_report_async,
    send_report_email_async,
    generate_and_send_report
)

# Crear Blueprint
reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Directorio de reportes generados
REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'reports', 'generated')


# ============================================================================
# UTILIDADES
# ============================================================================

def validate_json(f):
    """Decorador para validar que la petición tiene JSON válido."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'success': False,
                'error': 'Content-Type debe ser application/json'
            }), 400
        return f(*args, **kwargs)
    return decorated_function


def get_report_path(filename: str) -> str:
    """Obtiene la ruta completa de un archivo de reporte."""
    return os.path.join(REPORTS_DIR, filename)


def validate_date(date_str: str, param_name: str) -> tuple:
    """Valida y parsea una fecha en formato YYYY-MM-DD."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d'), None
    except ValueError:
        return None, f"Formato de fecha inválido para '{param_name}'. Use YYYY-MM-DD."


# ============================================================================
# ENDPOINTS DE GENERACIÓN DE REPORTES
# ============================================================================

@reports_bp.route('/generate/pdf', methods=['POST'])
@cross_origin()
@validate_json
def generate_pdf_report():
    """
    Genera un reporte PDF de forma asíncrona.
    
    Body JSON:
    {
        "report_type": "executive|alerts|statistical|career",
        "params": {
            "start_date": "2024-01-01",  // Para executive y career
            "end_date": "2024-01-31",    // Para executive y career
            "severity": "critical",       // Para alerts
            "days": 7,                    // Para alerts
            "semester": "I-2024",         // Para statistical
            "career_id": 1,               // Para career
            "career_name": "Ingeniería de Sistemas"  // Para career
        },
        "async": true  // Opcional, default true
    }
    
    Returns:
        - Si async=true: task_id para consultar estado
        - Si async=false: archivo PDF directamente
    """
    try:
        data = request.get_json()
        
        report_type = data.get('report_type')
        params = data.get('params', {})
        is_async = data.get('async', True)
        
        # Validar tipo de reporte
        valid_types = ['executive', 'alerts', 'statistical', 'career']
        if report_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f"Tipo de reporte inválido. Opciones: {', '.join(valid_types)}"
            }), 400
        
        # Validar parámetros según tipo
        if report_type == 'executive':
            if 'start_date' not in params or 'end_date' not in params:
                return jsonify({
                    'success': False,
                    'error': 'Se requieren start_date y end_date para reporte ejecutivo'
                }), 400
            
            start_date, error = validate_date(params['start_date'], 'start_date')
            if error:
                return jsonify({'success': False, 'error': error}), 400
                
            end_date, error = validate_date(params['end_date'], 'end_date')
            if error:
                return jsonify({'success': False, 'error': error}), 400
                
            params['start_date'] = start_date.isoformat()
            params['end_date'] = end_date.isoformat()
            
        elif report_type == 'alerts':
            params['severity'] = params.get('severity', 'all')
            params['days'] = params.get('days', 7)
            
        elif report_type == 'statistical':
            if 'semester' not in params:
                return jsonify({
                    'success': False,
                    'error': 'Se requiere semester para anuario estadístico'
                }), 400
                
        elif report_type == 'career':
            if 'career_id' not in params or 'career_name' not in params:
                return jsonify({
                    'success': False,
                    'error': 'Se requieren career_id y career_name para reporte de carrera'
                }), 400
            
            if 'start_date' in params:
                start_date, error = validate_date(params['start_date'], 'start_date')
                if error:
                    return jsonify({'success': False, 'error': error}), 400
                params['start_date'] = start_date.isoformat()
                
            if 'end_date' in params:
                end_date, error = validate_date(params['end_date'], 'end_date')
                if error:
                    return jsonify({'success': False, 'error': error}), 400
                params['end_date'] = end_date.isoformat()
        
        if is_async:
            # Generar de forma asíncrona con Celery
            task = generate_pdf_report_async.delay(report_type, params)
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'message': 'Generación de reporte PDF iniciada',
                'status_url': f'/api/reports/status/{task.id}'
            }), 202
        else:
            # Generar de forma síncrona
            generator = PDFGenerator()
            
            if report_type == 'executive':
                result = generator.generate_executive_report(
                    start_date=datetime.fromisoformat(params['start_date']),
                    end_date=datetime.fromisoformat(params['end_date']),
                    filters=params.get('filters', {}),
                    sections=params.get('sections', ['summary', 'sentiment', 'alerts', 'complaints', 'trends', 'recommendations'])
                )
            elif report_type == 'alerts':
                result = generator.generate_alerts_report(
                    severity=params.get('severity', 'all'),
                    days=params.get('days', 7),
                    filters=params.get('filters', {})
                )
            elif report_type == 'statistical':
                result = generator.generate_statistical_report(
                    semester=params['semester'],
                    include_sections=params.get('include_sections')
                )
            elif report_type == 'career':
                result = generator.generate_career_report(
                    career_id=params['career_id'],
                    career_name=params['career_name'],
                    start_date=datetime.fromisoformat(params['start_date']) if 'start_date' in params else None,
                    end_date=datetime.fromisoformat(params['end_date']) if 'end_date' in params else None
                )
            
            if result['success']:
                return send_file(
                    result['file_path'],
                    as_attachment=True,
                    download_name=os.path.basename(result['file_path']),
                    mimetype='application/pdf'
                )
            else:
                return jsonify(result), 500
                
    except Exception as e:
        current_app.logger.error(f"Error generando PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500


@reports_bp.route('/generate/excel', methods=['POST'])
@cross_origin()
@validate_json
def generate_excel_report():
    """
    Genera un reporte Excel de forma asíncrona.
    
    Body JSON:
    {
        "report_type": "sentiment_dataset|pivot_table|anomalies|combined",
        "params": {
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "dimension": "career|source|month",  // Para pivot_table
            "days": 30,                          // Para anomalies
            "threshold": 2.0                     // Para anomalies
        },
        "async": true
    }
    """
    try:
        data = request.get_json()
        
        report_type = data.get('report_type')
        params = data.get('params', {})
        is_async = data.get('async', True)
        
        # Validar tipo de reporte
        valid_types = ['sentiment_dataset', 'pivot_table', 'anomalies', 'combined']
        if report_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f"Tipo de reporte inválido. Opciones: {', '.join(valid_types)}"
            }), 400
        
        # Validar parámetros según tipo
        if report_type == 'pivot_table':
            valid_dimensions = ['career', 'source', 'month']
            if params.get('dimension') not in valid_dimensions:
                return jsonify({
                    'success': False,
                    'error': f"Dimensión inválida. Opciones: {', '.join(valid_dimensions)}"
                }), 400
        
        if is_async:
            task = generate_excel_report_async.delay(report_type, params)
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'message': 'Generación de reporte Excel iniciada',
                'status_url': f'/api/reports/status/{task.id}'
            }), 202
        else:
            generator = ExcelGenerator()
            
            if report_type == 'sentiment_dataset':
                start_date = datetime.fromisoformat(params['start_date']) if 'start_date' in params else None
                end_date = datetime.fromisoformat(params['end_date']) if 'end_date' in params else None
                result = generator.generate_sentiment_dataset(start_date, end_date)
            elif report_type == 'pivot_table':
                result = generator.generate_pivot_table(params['dimension'])
            elif report_type == 'anomalies':
                result = generator.generate_anomalies_report(
                    days=params.get('days', 30),
                    threshold=params.get('threshold', 2.0)
                )
            elif report_type == 'combined':
                result = generator.generate_combined_report()
            
            if result['success']:
                return send_file(
                    result['file_path'],
                    as_attachment=True,
                    download_name=os.path.basename(result['file_path']),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                return jsonify(result), 500
                
    except Exception as e:
        current_app.logger.error(f"Error generando Excel: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINTS DE ESTADO Y DESCARGA
# ============================================================================

@reports_bp.route('/status/<task_id>', methods=['GET'])
@cross_origin()
def get_task_status(task_id: str):
    """
    Consulta el estado de una tarea de generación de reporte.
    
    Returns:
        {
            "task_id": "...",
            "status": "PENDING|STARTED|PROGRESS|SUCCESS|FAILURE",
            "progress": 50,  // Porcentaje de progreso
            "message": "...",
            "result": {...}  // Solo si completado
        }
    """
    try:
        from celery.result import AsyncResult
        from reports.tasks import celery_app
        
        task = AsyncResult(task_id, app=celery_app)
        
        response = {
            'task_id': task_id,
            'status': task.status
        }
        
        if task.status == 'PENDING':
            response['message'] = 'Tarea en cola, esperando procesamiento'
            response['progress'] = 0
            
        elif task.status == 'STARTED':
            response['message'] = 'Tarea iniciada'
            response['progress'] = 5
            
        elif task.status == 'PROGRESS':
            info = task.info or {}
            response['progress'] = info.get('progress', 0)
            response['message'] = info.get('status', 'Procesando...')
            
        elif task.status == 'SUCCESS':
            result = task.result
            response['progress'] = 100
            response['message'] = 'Reporte generado exitosamente'
            response['result'] = result
            if result and result.get('success') and result.get('file_path'):
                filename = os.path.basename(result['file_path'])
                response['download_url'] = f'/api/reports/download/{filename}'
                
        elif task.status == 'FAILURE':
            response['progress'] = 0
            response['message'] = str(task.result) if task.result else 'Error desconocido'
            response['error'] = True
            
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error consultando estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error consultando estado: {str(e)}'
        }), 500


@reports_bp.route('/download/<filename>', methods=['GET'])
@cross_origin()
def download_report(filename: str):
    """
    Descarga un reporte generado.
    
    Args:
        filename: Nombre del archivo a descargar
    """
    try:
        # Sanitizar nombre de archivo
        filename = os.path.basename(filename)
        file_path = get_report_path(filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Archivo no encontrado'
            }), 404
        
        # Determinar MIME type
        if filename.endswith('.pdf'):
            mimetype = 'application/pdf'
        elif filename.endswith('.xlsx'):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        current_app.logger.error(f"Error descargando reporte: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error descargando reporte: {str(e)}'
        }), 500


@reports_bp.route('/history', methods=['GET'])
@cross_origin()
def get_reports_history():
    """
    Obtiene el historial de reportes generados.
    
    Query params:
        - type: Filtrar por tipo (pdf, excel)
        - days: Últimos N días (default: 30)
        - limit: Número máximo de resultados (default: 50)
    """
    try:
        report_type = request.args.get('type', 'all')
        days = int(request.args.get('days', 30))
        limit = int(request.args.get('limit', 50))
        
        # Asegurar que el directorio existe
        if not os.path.exists(REPORTS_DIR):
            return jsonify({
                'success': True,
                'reports': [],
                'total': 0
            })
        
        # Listar archivos
        reports = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        for filename in os.listdir(REPORTS_DIR):
            file_path = os.path.join(REPORTS_DIR, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            # Filtrar por tipo
            if report_type == 'pdf' and not filename.endswith('.pdf'):
                continue
            if report_type == 'excel' and not filename.endswith('.xlsx'):
                continue
            
            # Obtener información del archivo
            stat = os.stat(file_path)
            created_time = datetime.fromtimestamp(stat.st_mtime)
            
            # Filtrar por fecha
            if created_time < cutoff_date:
                continue
            
            # Determinar tipo de reporte por nombre
            report_info = {
                'filename': filename,
                'file_type': 'pdf' if filename.endswith('.pdf') else 'excel',
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created_at': created_time.isoformat(),
                'download_url': f'/api/reports/download/{filename}'
            }
            
            # Inferir tipo de reporte del nombre
            if 'ejecutivo' in filename.lower() or 'executive' in filename.lower():
                report_info['report_type'] = 'executive'
            elif 'alerta' in filename.lower() or 'alert' in filename.lower():
                report_info['report_type'] = 'alerts'
            elif 'estadistico' in filename.lower() or 'statistical' in filename.lower():
                report_info['report_type'] = 'statistical'
            elif 'carrera' in filename.lower() or 'career' in filename.lower():
                report_info['report_type'] = 'career'
            elif 'sentimiento' in filename.lower() or 'sentiment' in filename.lower():
                report_info['report_type'] = 'sentiment_dataset'
            elif 'pivot' in filename.lower():
                report_info['report_type'] = 'pivot_table'
            elif 'anomalia' in filename.lower() or 'anomal' in filename.lower():
                report_info['report_type'] = 'anomalies'
            else:
                report_info['report_type'] = 'other'
            
            reports.append(report_info)
        
        # Ordenar por fecha de creación (más reciente primero)
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Aplicar límite
        reports = reports[:limit]
        
        return jsonify({
            'success': True,
            'reports': reports,
            'total': len(reports)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo historial: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo historial: {str(e)}'
        }), 500


@reports_bp.route('/delete/<filename>', methods=['DELETE'])
@cross_origin()
def delete_report(filename: str):
    """Elimina un reporte generado."""
    try:
        filename = os.path.basename(filename)
        file_path = get_report_path(filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Archivo no encontrado'
            }), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'Reporte {filename} eliminado'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error eliminando reporte: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error eliminando reporte: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINTS DE PROGRAMACIÓN (SCHEDULING)
# ============================================================================

@reports_bp.route('/schedules', methods=['GET'])
@cross_origin()
def get_schedules():
    """Obtiene todas las programaciones de reportes."""
    try:
        scheduler = ReportScheduler()
        schedules = scheduler.get_all_schedules()
        
        return jsonify({
            'success': True,
            'schedules': [s.__dict__ for s in schedules],
            'total': len(schedules)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo programaciones: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo programaciones: {str(e)}'
        }), 500


@reports_bp.route('/schedules', methods=['POST'])
@cross_origin()
@validate_json
def create_schedule():
    """
    Crea una nueva programación de reporte.
    
    Body JSON:
    {
        "name": "Reporte Ejecutivo Semanal",
        "report_type": "executive",
        "frequency": "weekly",
        "day_of_week": 1,  // 0=Lunes, opcional
        "day_of_month": null,  // 1-31, opcional
        "hour": 8,
        "minute": 0,
        "params": {...},
        "recipients": ["email@example.com"],
        "enabled": true
    }
    """
    try:
        data = request.get_json()
        
        # Validar campos requeridos
        required_fields = ['name', 'report_type', 'frequency', 'hour', 'recipients']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido: {field}'
                }), 400
        
        # Validar frequency
        valid_frequencies = ['daily', 'weekly', 'monthly']
        if data['frequency'] not in valid_frequencies:
            return jsonify({
                'success': False,
                'error': f"Frecuencia inválida. Opciones: {', '.join(valid_frequencies)}"
            }), 400
        
        # Validar que weekly tenga day_of_week
        if data['frequency'] == 'weekly' and 'day_of_week' not in data:
            return jsonify({
                'success': False,
                'error': 'Se requiere day_of_week para frecuencia semanal'
            }), 400
        
        # Validar que monthly tenga day_of_month
        if data['frequency'] == 'monthly' and 'day_of_month' not in data:
            return jsonify({
                'success': False,
                'error': 'Se requiere day_of_month para frecuencia mensual'
            }), 400
        
        scheduler = ReportScheduler()
        schedule_id = scheduler.create_schedule(
            name=data['name'],
            report_type=data['report_type'],
            frequency=data['frequency'],
            day_of_week=data.get('day_of_week'),
            day_of_month=data.get('day_of_month'),
            hour=data['hour'],
            minute=data.get('minute', 0),
            params=data.get('params', {}),
            recipients=data['recipients'],
            enabled=data.get('enabled', True)
        )
        
        return jsonify({
            'success': True,
            'schedule_id': schedule_id,
            'message': 'Programación creada exitosamente'
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creando programación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error creando programación: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>', methods=['GET'])
@cross_origin()
def get_schedule(schedule_id: int):
    """Obtiene una programación específica."""
    try:
        scheduler = ReportScheduler()
        schedule = scheduler.get_schedule(schedule_id)
        
        if not schedule:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        return jsonify({
            'success': True,
            'schedule': schedule.__dict__
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo programación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo programación: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>', methods=['PUT'])
@cross_origin()
@validate_json
def update_schedule(schedule_id: int):
    """Actualiza una programación existente."""
    try:
        data = request.get_json()
        
        scheduler = ReportScheduler()
        
        # Verificar que existe
        existing = scheduler.get_schedule(schedule_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        success = scheduler.update_schedule(schedule_id, **data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Programación actualizada'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo actualizar la programación'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error actualizando programación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error actualizando programación: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>', methods=['DELETE'])
@cross_origin()
def delete_schedule(schedule_id: int):
    """Elimina una programación."""
    try:
        scheduler = ReportScheduler()
        
        existing = scheduler.get_schedule(schedule_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        success = scheduler.delete_schedule(schedule_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Programación eliminada'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo eliminar la programación'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error eliminando programación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error eliminando programación: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>/toggle', methods=['POST'])
@cross_origin()
def toggle_schedule(schedule_id: int):
    """Activa o desactiva una programación."""
    try:
        scheduler = ReportScheduler()
        
        existing = scheduler.get_schedule(schedule_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        success = scheduler.toggle_schedule(schedule_id)
        
        if success:
            # Obtener estado actualizado
            updated = scheduler.get_schedule(schedule_id)
            return jsonify({
                'success': True,
                'enabled': updated.enabled,
                'message': f'Programación {"activada" if updated.enabled else "desactivada"}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo cambiar el estado'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error cambiando estado: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error cambiando estado: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>/run', methods=['POST'])
@cross_origin()
def run_schedule_now(schedule_id: int):
    """Ejecuta una programación inmediatamente."""
    try:
        scheduler = ReportScheduler()
        
        existing = scheduler.get_schedule(schedule_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        # Ejecutar tarea asíncrona
        task = generate_and_send_report.delay(schedule_id)
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Ejecución iniciada',
            'status_url': f'/api/reports/status/{task.id}'
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Error ejecutando programación: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error ejecutando programación: {str(e)}'
        }), 500


@reports_bp.route('/schedules/<int:schedule_id>/history', methods=['GET'])
@cross_origin()
def get_schedule_history(schedule_id: int):
    """Obtiene el historial de ejecuciones de una programación."""
    try:
        limit = int(request.args.get('limit', 20))
        
        scheduler = ReportScheduler()
        
        existing = scheduler.get_schedule(schedule_id)
        if not existing:
            return jsonify({
                'success': False,
                'error': 'Programación no encontrada'
            }), 404
        
        history = scheduler.get_execution_history(schedule_id, limit)
        
        return jsonify({
            'success': True,
            'history': [h.__dict__ for h in history],
            'total': len(history)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo historial: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo historial: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINTS DE EMAIL
# ============================================================================

@reports_bp.route('/send', methods=['POST'])
@cross_origin()
@validate_json
def send_report_email():
    """
    Envía un reporte por email.
    
    Body JSON:
    {
        "recipients": ["email@example.com"],
        "subject": "Reporte Semanal EMI",
        "body": "Adjunto encontrará...",  // Opcional
        "attachment": "reporte_ejecutivo_2024-01-01.pdf"
    }
    """
    try:
        data = request.get_json()
        
        recipients = data.get('recipients', [])
        subject = data.get('subject')
        body = data.get('body', '')
        attachment = data.get('attachment')
        
        if not recipients:
            return jsonify({
                'success': False,
                'error': 'Se requiere al menos un destinatario'
            }), 400
        
        if not subject:
            return jsonify({
                'success': False,
                'error': 'Se requiere asunto del email'
            }), 400
        
        if not attachment:
            return jsonify({
                'success': False,
                'error': 'Se requiere archivo adjunto'
            }), 400
        
        # Verificar que el archivo existe
        attachment_path = get_report_path(os.path.basename(attachment))
        if not os.path.exists(attachment_path):
            return jsonify({
                'success': False,
                'error': 'Archivo adjunto no encontrado'
            }), 404
        
        # Enviar de forma asíncrona
        task = send_report_email_async.delay(
            recipients=recipients,
            subject=subject,
            attachment_path=attachment_path,
            body=body
        )
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Envío de email iniciado',
            'status_url': f'/api/reports/status/{task.id}'
        }), 202
        
    except Exception as e:
        current_app.logger.error(f"Error enviando email: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error enviando email: {str(e)}'
        }), 500


# ============================================================================
# ENDPOINTS DE ESTADÍSTICAS
# ============================================================================

@reports_bp.route('/stats', methods=['GET'])
@cross_origin()
def get_reports_stats():
    """Obtiene estadísticas generales del módulo de reportes."""
    try:
        scheduler = ReportScheduler()
        
        # Contar archivos
        pdf_count = 0
        excel_count = 0
        total_size = 0
        
        if os.path.exists(REPORTS_DIR):
            for filename in os.listdir(REPORTS_DIR):
                file_path = os.path.join(REPORTS_DIR, filename)
                if os.path.isfile(file_path):
                    if filename.endswith('.pdf'):
                        pdf_count += 1
                    elif filename.endswith('.xlsx'):
                        excel_count += 1
                    total_size += os.path.getsize(file_path)
        
        # Obtener estadísticas de programaciones
        schedules = scheduler.get_all_schedules()
        active_schedules = sum(1 for s in schedules if s.enabled)
        
        # Obtener estadísticas de ejecución
        exec_stats = scheduler.get_execution_stats()
        
        return jsonify({
            'success': True,
            'stats': {
                'reports': {
                    'pdf_count': pdf_count,
                    'excel_count': excel_count,
                    'total_count': pdf_count + excel_count,
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                },
                'schedules': {
                    'total': len(schedules),
                    'active': active_schedules,
                    'inactive': len(schedules) - active_schedules
                },
                'executions': exec_stats
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error obteniendo estadísticas: {str(e)}'
        }), 500


# ============================================================================
# REGISTRO DEL BLUEPRINT
# ============================================================================

def register_reports_blueprint(app):
    """Registra el blueprint de reportes en la aplicación Flask."""
    app.register_blueprint(reports_bp)
    
    # Crear directorio de reportes si no existe
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    app.logger.info("Blueprint de reportes registrado correctamente")
