"""
Tests para el Scheduler de Reportes
Sistema de Analítica OSINT - EMI Bolivia
Sprint 5: Reportes y Estadísticas
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import tempfile
import sqlite3

# Import del módulo a testear
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.scheduler import ReportScheduler, ScheduleConfig, ScheduleFrequency


class TestScheduleConfig:
    """Tests para la configuración de programaciones"""
    
    def test_schedule_config_creation(self):
        """Test creación de configuración de programación"""
        config = ScheduleConfig(
            name='Reporte Semanal',
            report_type='executive_summary',
            frequency=ScheduleFrequency.WEEKLY,
            day_of_week=1,  # Martes
            hour=8,
            minute=0,
            recipients=['admin@emi.edu.bo'],
            enabled=True
        )
        
        assert config.name == 'Reporte Semanal'
        assert config.frequency == ScheduleFrequency.WEEKLY
        assert config.day_of_week == 1
    
    def test_frequency_enum(self):
        """Test enum de frecuencias"""
        assert ScheduleFrequency.DAILY.value == 'daily'
        assert ScheduleFrequency.WEEKLY.value == 'weekly'
        assert ScheduleFrequency.MONTHLY.value == 'monthly'
    
    def test_cron_expression_daily(self):
        """Test expresión cron para diario"""
        config = ScheduleConfig(
            name='Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=30,
            recipients=['test@test.com']
        )
        
        cron = config.to_cron_expression()
        assert cron == '30 8 * * *'
    
    def test_cron_expression_weekly(self):
        """Test expresión cron para semanal"""
        config = ScheduleConfig(
            name='Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.WEEKLY,
            day_of_week=1,  # Martes
            hour=9,
            minute=0,
            recipients=['test@test.com']
        )
        
        cron = config.to_cron_expression()
        assert cron == '0 9 * * 2'  # Cron usa 0=Domingo, 2=Martes
    
    def test_cron_expression_monthly(self):
        """Test expresión cron para mensual"""
        config = ScheduleConfig(
            name='Test',
            report_type='statistical_report',
            frequency=ScheduleFrequency.MONTHLY,
            day_of_month=15,
            hour=6,
            minute=0,
            recipients=['test@test.com']
        )
        
        cron = config.to_cron_expression()
        assert cron == '0 6 15 * *'


class TestReportScheduler:
    """Tests para el scheduler de reportes"""
    
    @pytest.fixture
    def scheduler(self):
        """Fixture para crear instancia del scheduler"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        sched = ReportScheduler(database_path=db_path)
        yield sched
        
        # Cleanup
        sched.close()
        os.unlink(db_path)
    
    def test_scheduler_initialization(self, scheduler):
        """Test que el scheduler se inicializa correctamente"""
        assert scheduler is not None
        assert scheduler.database_path is not None
    
    def test_database_table_creation(self, scheduler):
        """Test que las tablas de BD se crean correctamente"""
        # Verificar que las tablas existen
        conn = sqlite3.connect(scheduler.database_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='schedules'
        """)
        assert cursor.fetchone() is not None
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='execution_logs'
        """)
        assert cursor.fetchone() is not None
        
        conn.close()
    
    def test_create_schedule(self, scheduler):
        """Test crear una programación"""
        config = ScheduleConfig(
            name='Test Schedule',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        assert schedule_id is not None
        assert isinstance(schedule_id, str)
    
    def test_get_schedule(self, scheduler):
        """Test obtener una programación"""
        config = ScheduleConfig(
            name='Test Schedule',
            report_type='executive_summary',
            frequency=ScheduleFrequency.WEEKLY,
            day_of_week=0,
            hour=9,
            minute=30,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        schedule = scheduler.get_schedule(schedule_id)
        
        assert schedule is not None
        assert schedule['name'] == 'Test Schedule'
        assert schedule['frequency'] == 'weekly'
    
    def test_list_schedules(self, scheduler):
        """Test listar programaciones"""
        # Crear varias programaciones
        for i in range(3):
            config = ScheduleConfig(
                name=f'Schedule {i}',
                report_type='executive_summary',
                frequency=ScheduleFrequency.DAILY,
                hour=8,
                minute=0,
                recipients=['admin@test.com']
            )
            scheduler.create_schedule(config)
        
        schedules = scheduler.list_schedules()
        
        assert len(schedules) == 3
    
    def test_update_schedule(self, scheduler):
        """Test actualizar una programación"""
        config = ScheduleConfig(
            name='Original Name',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Actualizar
        scheduler.update_schedule(schedule_id, {'name': 'Updated Name'})
        
        schedule = scheduler.get_schedule(schedule_id)
        assert schedule['name'] == 'Updated Name'
    
    def test_delete_schedule(self, scheduler):
        """Test eliminar una programación"""
        config = ScheduleConfig(
            name='To Delete',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        scheduler.delete_schedule(schedule_id)
        
        schedule = scheduler.get_schedule(schedule_id)
        assert schedule is None
    
    def test_toggle_schedule(self, scheduler):
        """Test habilitar/deshabilitar programación"""
        config = ScheduleConfig(
            name='Toggle Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com'],
            enabled=True
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Debería estar habilitada
        schedule = scheduler.get_schedule(schedule_id)
        assert schedule['enabled'] == True
        
        # Deshabilitar
        scheduler.toggle_schedule(schedule_id)
        schedule = scheduler.get_schedule(schedule_id)
        assert schedule['enabled'] == False
        
        # Habilitar de nuevo
        scheduler.toggle_schedule(schedule_id)
        schedule = scheduler.get_schedule(schedule_id)
        assert schedule['enabled'] == True


class TestScheduleExecution:
    """Tests para la ejecución de programaciones"""
    
    @pytest.fixture
    def scheduler(self):
        """Fixture para crear instancia del scheduler"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        sched = ReportScheduler(database_path=db_path)
        yield sched
        
        sched.close()
        os.unlink(db_path)
    
    def test_calculate_next_run_daily(self, scheduler):
        """Test cálculo de próxima ejecución diaria"""
        now = datetime(2024, 1, 15, 10, 0, 0)  # 10:00 AM
        
        # Programación a las 8:00 AM
        next_run = scheduler._calculate_next_run(
            frequency='daily',
            hour=8,
            minute=0,
            current_time=now
        )
        
        # Debería ser mañana a las 8:00
        assert next_run.hour == 8
        assert next_run.minute == 0
        assert next_run.day == 16
    
    def test_calculate_next_run_weekly(self, scheduler):
        """Test cálculo de próxima ejecución semanal"""
        # Lunes 15 de enero
        now = datetime(2024, 1, 15, 10, 0, 0)
        
        # Programación para martes a las 9:00
        next_run = scheduler._calculate_next_run(
            frequency='weekly',
            day_of_week=1,  # Martes
            hour=9,
            minute=0,
            current_time=now
        )
        
        # Debería ser martes 16
        assert next_run.weekday() == 1
        assert next_run.hour == 9
    
    def test_calculate_next_run_monthly(self, scheduler):
        """Test cálculo de próxima ejecución mensual"""
        now = datetime(2024, 1, 20, 10, 0, 0)
        
        # Programación para el día 15
        next_run = scheduler._calculate_next_run(
            frequency='monthly',
            day_of_month=15,
            hour=6,
            minute=0,
            current_time=now
        )
        
        # Debería ser 15 de febrero
        assert next_run.day == 15
        assert next_run.month == 2
    
    def test_log_execution_success(self, scheduler):
        """Test registro de ejecución exitosa"""
        config = ScheduleConfig(
            name='Log Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Registrar ejecución exitosa
        scheduler.log_execution(
            schedule_id=schedule_id,
            status='success',
            report_file='report_20240115.pdf'
        )
        
        # Verificar log
        logs = scheduler.get_execution_logs(schedule_id)
        assert len(logs) == 1
        assert logs[0]['status'] == 'success'
        assert logs[0]['report_file'] == 'report_20240115.pdf'
    
    def test_log_execution_failure(self, scheduler):
        """Test registro de ejecución fallida"""
        config = ScheduleConfig(
            name='Error Log Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Registrar ejecución fallida
        scheduler.log_execution(
            schedule_id=schedule_id,
            status='error',
            error='Connection timeout'
        )
        
        logs = scheduler.get_execution_logs(schedule_id)
        assert logs[0]['status'] == 'error'
        assert logs[0]['error'] == 'Connection timeout'
    
    def test_get_due_schedules(self, scheduler):
        """Test obtener programaciones pendientes"""
        now = datetime.now()
        
        # Crear programación que debería ejecutarse
        config = ScheduleConfig(
            name='Due Schedule',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=now.hour,
            minute=now.minute,
            recipients=['admin@test.com'],
            enabled=True
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Establecer next_run en el pasado
        scheduler.update_schedule(schedule_id, {
            'next_run': (now - timedelta(minutes=5)).isoformat()
        })
        
        due_schedules = scheduler.get_due_schedules()
        
        # Debería incluir nuestra programación
        assert len(due_schedules) >= 1


class TestSchedulerIntegration:
    """Tests de integración del scheduler"""
    
    @pytest.fixture
    def scheduler(self):
        """Fixture para crear instancia del scheduler"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        sched = ReportScheduler(database_path=db_path)
        yield sched
        
        sched.close()
        os.unlink(db_path)
    
    @patch('reports.tasks.generate_pdf_report')
    def test_execute_scheduled_report(self, mock_task, scheduler):
        """Test ejecución de reporte programado"""
        config = ScheduleConfig(
            name='Integration Test',
            report_type='executive_summary',
            frequency=ScheduleFrequency.DAILY,
            hour=8,
            minute=0,
            recipients=['admin@test.com'],
            report_params={'sections': ['summary', 'alerts']}
        )
        
        schedule_id = scheduler.create_schedule(config)
        
        # Simular ejecución
        mock_task.delay.return_value = Mock(id='task-123')
        
        result = scheduler.execute_schedule(schedule_id)
        
        assert result['success'] == True
        assert 'task_id' in result
    
    def test_schedule_persistence(self, scheduler):
        """Test que las programaciones persisten entre sesiones"""
        db_path = scheduler.database_path
        
        # Crear programación
        config = ScheduleConfig(
            name='Persistent Schedule',
            report_type='executive_summary',
            frequency=ScheduleFrequency.WEEKLY,
            day_of_week=0,
            hour=8,
            minute=0,
            recipients=['admin@test.com']
        )
        
        schedule_id = scheduler.create_schedule(config)
        scheduler.close()
        
        # Crear nueva instancia
        new_scheduler = ReportScheduler(database_path=db_path)
        schedule = new_scheduler.get_schedule(schedule_id)
        
        assert schedule is not None
        assert schedule['name'] == 'Persistent Schedule'
        
        new_scheduler.close()


class TestCronParser:
    """Tests para el parser de expresiones cron"""
    
    def test_parse_cron_daily(self):
        """Test parsing de cron diario"""
        from reports.scheduler import parse_cron_expression
        
        result = parse_cron_expression('0 8 * * *')
        
        assert result['minute'] == 0
        assert result['hour'] == 8
        assert result['frequency'] == 'daily'
    
    def test_parse_cron_weekly(self):
        """Test parsing de cron semanal"""
        from reports.scheduler import parse_cron_expression
        
        result = parse_cron_expression('30 9 * * 2')
        
        assert result['minute'] == 30
        assert result['hour'] == 9
        assert result['day_of_week'] == 2
        assert result['frequency'] == 'weekly'
    
    def test_parse_cron_monthly(self):
        """Test parsing de cron mensual"""
        from reports.scheduler import parse_cron_expression
        
        result = parse_cron_expression('0 6 15 * *')
        
        assert result['minute'] == 0
        assert result['hour'] == 6
        assert result['day_of_month'] == 15
        assert result['frequency'] == 'monthly'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
