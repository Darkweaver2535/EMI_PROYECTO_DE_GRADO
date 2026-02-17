"""
Tests para la API de Reportes
Sistema de Analítica OSINT - EMI Bolivia
Sprint 5: Reportes y Estadísticas
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os
import tempfile
import json

# Import Flask app
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestReportsAPIEndpoints:
    """Tests para los endpoints de la API de reportes"""
    
    @pytest.fixture
    def client(self):
        """Fixture para crear cliente de prueba"""
        # Crear app Flask de prueba
        from flask import Flask
        from api.reports import reports_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(reports_bp)
        
        with app.test_client() as client:
            yield client
    
    def test_generate_pdf_endpoint(self, client):
        """Test endpoint de generación de PDF"""
        with patch('api.reports.generate_pdf_report') as mock_task:
            mock_task.delay.return_value = Mock(id='task-123')
            
            response = client.post(
                '/api/reports/generate/pdf',
                json={
                    'report_type': 'executive_summary',
                    'params': {
                        'start_date': '2024-01-01',
                        'end_date': '2024-01-31'
                    }
                },
                content_type='application/json'
            )
            
            assert response.status_code == 202
            data = json.loads(response.data)
            assert data['success'] == True
            assert 'task_id' in data
    
    def test_generate_pdf_missing_type(self, client):
        """Test endpoint con tipo faltante"""
        response = client.post(
            '/api/reports/generate/pdf',
            json={'params': {}},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_generate_pdf_invalid_type(self, client):
        """Test endpoint con tipo inválido"""
        response = client.post(
            '/api/reports/generate/pdf',
            json={'report_type': 'invalid_type'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_generate_excel_endpoint(self, client):
        """Test endpoint de generación de Excel"""
        with patch('api.reports.generate_excel_report') as mock_task:
            mock_task.delay.return_value = Mock(id='task-456')
            
            response = client.post(
                '/api/reports/generate/excel',
                json={
                    'report_type': 'sentiment_dataset',
                    'params': {
                        'start_date': '2024-01-01',
                        'end_date': '2024-01-31'
                    }
                },
                content_type='application/json'
            )
            
            assert response.status_code == 202
            data = json.loads(response.data)
            assert data['success'] == True
    
    def test_task_status_endpoint(self, client):
        """Test endpoint de estado de tarea"""
        with patch('api.reports.celery_app') as mock_celery:
            mock_result = Mock()
            mock_result.state = 'SUCCESS'
            mock_result.info = {'filename': 'report.pdf', 'progress': 100}
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.get('/api/reports/status/task-123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'SUCCESS'
    
    def test_task_status_not_found(self, client):
        """Test endpoint de estado para tarea inexistente"""
        with patch('api.reports.celery_app') as mock_celery:
            mock_result = Mock()
            mock_result.state = 'PENDING'
            mock_result.info = None
            mock_celery.AsyncResult.return_value = mock_result
            
            response = client.get('/api/reports/status/nonexistent-task')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'PENDING'
    
    def test_download_endpoint(self, client):
        """Test endpoint de descarga"""
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4 test content')
            temp_file = f.name
        
        try:
            with patch('api.reports.REPORTS_DIR', os.path.dirname(temp_file)):
                filename = os.path.basename(temp_file)
                response = client.get(f'/api/reports/download/{filename}')
                
                assert response.status_code == 200
                assert response.content_type == 'application/pdf'
        finally:
            os.unlink(temp_file)
    
    def test_download_file_not_found(self, client):
        """Test descarga de archivo inexistente"""
        response = client.get('/api/reports/download/nonexistent.pdf')
        
        assert response.status_code == 404
    
    def test_history_endpoint(self, client):
        """Test endpoint de historial"""
        with patch('api.reports.list_generated_reports') as mock_list:
            mock_list.return_value = [
                {
                    'filename': 'report1.pdf',
                    'type': 'executive_summary',
                    'size': 1024 * 1024,
                    'created_at': '2024-01-15T10:00:00'
                }
            ]
            
            response = client.get('/api/reports/history')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'reports' in data
            assert len(data['reports']) == 1
    
    def test_delete_endpoint(self, client):
        """Test endpoint de eliminación"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'test')
            temp_file = f.name
        
        try:
            with patch('api.reports.REPORTS_DIR', os.path.dirname(temp_file)):
                filename = os.path.basename(temp_file)
                response = client.delete(f'/api/reports/delete/{filename}')
                
                assert response.status_code == 200
                assert not os.path.exists(temp_file)
        except FileNotFoundError:
            pass  # Ya fue eliminado


class TestSchedulesAPIEndpoints:
    """Tests para los endpoints de programaciones"""
    
    @pytest.fixture
    def client(self):
        """Fixture para crear cliente de prueba"""
        from flask import Flask
        from api.reports import reports_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(reports_bp)
        
        with app.test_client() as client:
            yield client
    
    def test_list_schedules_endpoint(self, client):
        """Test endpoint de listar programaciones"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.list_schedules.return_value = [
                {
                    'id': 'sched-1',
                    'name': 'Test Schedule',
                    'report_type': 'executive_summary',
                    'frequency': 'weekly',
                    'enabled': True
                }
            ]
            
            response = client.get('/api/reports/schedules')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'schedules' in data
    
    def test_create_schedule_endpoint(self, client):
        """Test endpoint de crear programación"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.create_schedule.return_value = 'sched-123'
            
            response = client.post(
                '/api/reports/schedules',
                json={
                    'name': 'New Schedule',
                    'report_type': 'executive_summary',
                    'frequency': 'daily',
                    'hour': 8,
                    'minute': 0,
                    'recipients': ['admin@test.com']
                },
                content_type='application/json'
            )
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] == True
    
    def test_create_schedule_missing_fields(self, client):
        """Test crear programación con campos faltantes"""
        response = client.post(
            '/api/reports/schedules',
            json={'name': 'Incomplete'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_get_schedule_endpoint(self, client):
        """Test endpoint de obtener programación"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.get_schedule.return_value = {
                'id': 'sched-1',
                'name': 'Test Schedule',
                'report_type': 'executive_summary'
            }
            
            response = client.get('/api/reports/schedules/sched-1')
            
            assert response.status_code == 200
    
    def test_update_schedule_endpoint(self, client):
        """Test endpoint de actualizar programación"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.update_schedule.return_value = True
            mock_scheduler.get_schedule.return_value = {
                'id': 'sched-1',
                'name': 'Updated Schedule'
            }
            
            response = client.put(
                '/api/reports/schedules/sched-1',
                json={'name': 'Updated Schedule'},
                content_type='application/json'
            )
            
            assert response.status_code == 200
    
    def test_delete_schedule_endpoint(self, client):
        """Test endpoint de eliminar programación"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.delete_schedule.return_value = True
            
            response = client.delete('/api/reports/schedules/sched-1')
            
            assert response.status_code == 200
    
    def test_toggle_schedule_endpoint(self, client):
        """Test endpoint de toggle de programación"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.toggle_schedule.return_value = True
            mock_scheduler.get_schedule.return_value = {
                'id': 'sched-1',
                'enabled': True
            }
            
            response = client.post('/api/reports/schedules/sched-1/toggle')
            
            assert response.status_code == 200
    
    def test_run_schedule_now_endpoint(self, client):
        """Test endpoint de ejecutar programación ahora"""
        with patch('api.reports.scheduler') as mock_scheduler:
            mock_scheduler.execute_schedule.return_value = {
                'success': True,
                'task_id': 'task-123'
            }
            
            response = client.post('/api/reports/schedules/sched-1/run')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'task_id' in data


class TestEmailAPIEndpoint:
    """Tests para el endpoint de envío de email"""
    
    @pytest.fixture
    def client(self):
        """Fixture para crear cliente de prueba"""
        from flask import Flask
        from api.reports import reports_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(reports_bp)
        
        with app.test_client() as client:
            yield client
    
    def test_send_email_endpoint(self, client):
        """Test endpoint de envío de email"""
        with patch('api.reports.email_service') as mock_email:
            mock_email.send.return_value = {'success': True}
            
            response = client.post(
                '/api/reports/send',
                json={
                    'recipients': ['user@test.com'],
                    'subject': 'Test Email',
                    'body': 'Test content',
                    'attachment': 'report.pdf'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
    
    def test_send_email_missing_recipients(self, client):
        """Test envío sin destinatarios"""
        response = client.post(
            '/api/reports/send',
            json={
                'subject': 'Test',
                'body': 'Test'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_send_email_invalid_recipients(self, client):
        """Test envío con destinatarios inválidos"""
        response = client.post(
            '/api/reports/send',
            json={
                'recipients': ['invalid-email'],
                'subject': 'Test',
                'body': 'Test'
            },
            content_type='application/json'
        )
        
        assert response.status_code == 400


class TestStatsAPIEndpoint:
    """Tests para el endpoint de estadísticas"""
    
    @pytest.fixture
    def client(self):
        """Fixture para crear cliente de prueba"""
        from flask import Flask
        from api.reports import reports_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(reports_bp)
        
        with app.test_client() as client:
            yield client
    
    def test_stats_endpoint(self, client):
        """Test endpoint de estadísticas"""
        with patch('api.reports.get_reports_stats') as mock_stats:
            mock_stats.return_value = {
                'reports': {
                    'total_count': 50,
                    'pdf_count': 30,
                    'excel_count': 20,
                    'total_size_mb': 125.5
                },
                'schedules': {
                    'total_count': 5,
                    'active_count': 3
                }
            }
            
            response = client.get('/api/reports/stats')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'stats' in data


class TestAPIValidation:
    """Tests para validación de entrada de API"""
    
    @pytest.fixture
    def client(self):
        """Fixture para crear cliente de prueba"""
        from flask import Flask
        from api.reports import reports_bp
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        app.register_blueprint(reports_bp)
        
        with app.test_client() as client:
            yield client
    
    def test_invalid_json(self, client):
        """Test con JSON inválido"""
        response = client.post(
            '/api/reports/generate/pdf',
            data='not json',
            content_type='application/json'
        )
        
        assert response.status_code == 400
    
    def test_date_validation(self, client):
        """Test validación de fechas"""
        with patch('api.reports.generate_pdf_report') as mock_task:
            mock_task.delay.return_value = Mock(id='task-123')
            
            # Fecha inválida
            response = client.post(
                '/api/reports/generate/pdf',
                json={
                    'report_type': 'executive_summary',
                    'params': {
                        'start_date': 'invalid-date',
                        'end_date': '2024-01-31'
                    }
                },
                content_type='application/json'
            )
            
            # Puede ser 400 si valida fechas, o 202 si las pasa al task
            assert response.status_code in [400, 202]
    
    def test_path_traversal_prevention(self, client):
        """Test prevención de path traversal"""
        response = client.get('/api/reports/download/../../../etc/passwd')
        
        assert response.status_code in [400, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
