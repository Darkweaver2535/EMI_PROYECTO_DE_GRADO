"""
Tests para el servicio de Email
Sistema de Analítica OSINT - EMI Bolivia
Sprint 5: Reportes y Estadísticas
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os
import tempfile
import email
from email.mime.multipart import MIMEMultipart

# Import del módulo a testear
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.email_service import EmailService, EmailConfig


class TestEmailConfig:
    """Tests para la configuración de email"""
    
    def test_config_from_env(self):
        """Test carga de configuración desde variables de entorno"""
        with patch.dict(os.environ, {
            'SMTP_SERVER': 'smtp.test.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': 'test@test.com',
            'SMTP_PASSWORD': 'password123',
            'EMAIL_FROM': 'sender@test.com'
        }):
            config = EmailConfig.from_env()
            
            assert config.smtp_server == 'smtp.test.com'
            assert config.smtp_port == 587
            assert config.username == 'test@test.com'
            assert config.password == 'password123'
            assert config.from_address == 'sender@test.com'
    
    def test_config_defaults(self):
        """Test valores por defecto de configuración"""
        config = EmailConfig()
        
        assert config.smtp_port == 587
        assert config.use_tls == True
        assert config.timeout == 30


class TestEmailService:
    """Tests para el servicio de email"""
    
    @pytest.fixture
    def email_service(self):
        """Fixture para crear instancia del servicio"""
        config = EmailConfig(
            smtp_server='smtp.test.com',
            smtp_port=587,
            username='test@test.com',
            password='password123',
            from_address='sender@test.com'
        )
        return EmailService(config)
    
    @pytest.fixture
    def sample_attachment(self):
        """Crear archivo de prueba para adjunto"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'%PDF-1.4 test content')
            yield f.name
        os.unlink(f.name)
    
    def test_service_initialization(self, email_service):
        """Test que el servicio se inicializa correctamente"""
        assert email_service is not None
        assert email_service.config is not None
    
    def test_validate_email_valid(self, email_service):
        """Test validación de email válido"""
        valid_emails = [
            'test@example.com',
            'user.name@domain.org',
            'user+tag@subdomain.domain.co.uk'
        ]
        
        for email_addr in valid_emails:
            assert email_service._validate_email(email_addr), f"'{email_addr}' should be valid"
    
    def test_validate_email_invalid(self, email_service):
        """Test validación de email inválido"""
        invalid_emails = [
            'invalid',
            'missing@domain',
            '@nodomain.com',
            'spaces in@email.com',
            ''
        ]
        
        for email_addr in invalid_emails:
            assert not email_service._validate_email(email_addr), f"'{email_addr}' should be invalid"
    
    def test_create_message(self, email_service):
        """Test creación de mensaje"""
        msg = email_service._create_message(
            to=['recipient@test.com'],
            subject='Test Subject',
            body_html='<p>Test body</p>'
        )
        
        assert isinstance(msg, MIMEMultipart)
        assert msg['To'] == 'recipient@test.com'
        assert msg['Subject'] == 'Test Subject'
        assert msg['From'] == 'sender@test.com'
    
    def test_create_message_multiple_recipients(self, email_service):
        """Test mensaje con múltiples destinatarios"""
        recipients = ['user1@test.com', 'user2@test.com', 'user3@test.com']
        
        msg = email_service._create_message(
            to=recipients,
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        assert msg['To'] == ', '.join(recipients)
    
    def test_add_attachment(self, email_service, sample_attachment):
        """Test agregar adjunto al mensaje"""
        msg = email_service._create_message(
            to=['recipient@test.com'],
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        email_service._add_attachment(msg, sample_attachment)
        
        # Verificar que el mensaje tiene partes (HTML + adjunto)
        assert msg.is_multipart()
        
        # Buscar el adjunto
        has_attachment = False
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                has_attachment = True
                break
        
        assert has_attachment
    
    def test_attachment_size_check(self, email_service):
        """Test verificación de tamaño de adjunto"""
        # Crear archivo grande (simular >10MB)
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Escribir cabecera PDF mínima
            f.write(b'%PDF-1.4 ' + b'x' * (11 * 1024 * 1024))  # 11MB
            large_file = f.name
        
        try:
            # Debería fallar o advertir sobre archivo grande
            is_valid = email_service._validate_attachment_size(large_file)
            assert not is_valid
        finally:
            os.unlink(large_file)
    
    def test_attachment_size_valid(self, email_service, sample_attachment):
        """Test archivo de tamaño válido"""
        is_valid = email_service._validate_attachment_size(sample_attachment)
        assert is_valid
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp_class, email_service):
        """Test envío exitoso de email"""
        # Configurar mock
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)
        
        result = email_service.send(
            to=['recipient@test.com'],
            subject='Test Email',
            body_html='<p>Test content</p>'
        )
        
        assert result['success'] == True
        mock_smtp.sendmail.assert_called_once()
    
    @patch('smtplib.SMTP')
    def test_send_email_with_attachment(self, mock_smtp_class, email_service, sample_attachment):
        """Test envío de email con adjunto"""
        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)
        
        result = email_service.send(
            to=['recipient@test.com'],
            subject='Test Email with Attachment',
            body_html='<p>See attached</p>',
            attachments=[sample_attachment]
        )
        
        assert result['success'] == True
    
    @patch('smtplib.SMTP')
    def test_send_email_connection_error(self, mock_smtp_class, email_service):
        """Test manejo de error de conexión"""
        mock_smtp_class.side_effect = ConnectionRefusedError("Connection refused")
        
        result = email_service.send(
            to=['recipient@test.com'],
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        assert result['success'] == False
        assert 'error' in result
    
    @patch('smtplib.SMTP')
    def test_send_email_authentication_error(self, mock_smtp_class, email_service):
        """Test manejo de error de autenticación"""
        import smtplib
        
        mock_smtp = Mock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b'Authentication failed')
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)
        
        result = email_service.send(
            to=['recipient@test.com'],
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        assert result['success'] == False


class TestEmailRetry:
    """Tests para lógica de reintentos"""
    
    @pytest.fixture
    def email_service(self):
        """Fixture para crear instancia del servicio"""
        config = EmailConfig(
            smtp_server='smtp.test.com',
            smtp_port=587,
            username='test@test.com',
            password='password123',
            from_address='sender@test.com',
            max_retries=3,
            retry_delay=0.1  # Delay corto para tests
        )
        return EmailService(config)
    
    @patch('smtplib.SMTP')
    def test_retry_on_temporary_failure(self, mock_smtp_class, email_service):
        """Test reintento en fallo temporal"""
        import smtplib
        
        mock_smtp = Mock()
        # Fallar 2 veces, luego éxito
        mock_smtp.sendmail.side_effect = [
            smtplib.SMTPServerDisconnected("Disconnected"),
            smtplib.SMTPServerDisconnected("Disconnected"),
            None  # Éxito
        ]
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)
        
        result = email_service.send_with_retry(
            to=['recipient@test.com'],
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        # Debería tener éxito después de reintentos
        assert result['success'] == True
        assert mock_smtp.sendmail.call_count == 3
    
    @patch('smtplib.SMTP')
    def test_max_retries_exceeded(self, mock_smtp_class, email_service):
        """Test exceder máximo de reintentos"""
        import smtplib
        
        mock_smtp = Mock()
        mock_smtp.sendmail.side_effect = smtplib.SMTPServerDisconnected("Always fails")
        mock_smtp_class.return_value.__enter__ = Mock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = Mock(return_value=False)
        
        result = email_service.send_with_retry(
            to=['recipient@test.com'],
            subject='Test',
            body_html='<p>Test</p>'
        )
        
        assert result['success'] == False
        assert result['retries'] == 3


class TestEmailTemplates:
    """Tests para plantillas de email"""
    
    @pytest.fixture
    def email_service(self):
        """Fixture para crear instancia del servicio"""
        config = EmailConfig(
            smtp_server='smtp.test.com',
            smtp_port=587,
            username='test@test.com',
            password='password123',
            from_address='sender@test.com'
        )
        return EmailService(config)
    
    def test_report_notification_template(self, email_service):
        """Test plantilla de notificación de reporte"""
        html = email_service._render_report_notification(
            report_type='executive_summary',
            report_name='Reporte Ejecutivo Semanal',
            generated_at=datetime.now(),
            file_size='2.5 MB'
        )
        
        assert html is not None
        assert 'Reporte Ejecutivo Semanal' in html
        assert '2.5 MB' in html
        assert 'EMI' in html  # Branding institucional
    
    def test_schedule_notification_template(self, email_service):
        """Test plantilla de notificación de programación"""
        html = email_service._render_schedule_notification(
            schedule_name='Reporte Semanal',
            frequency='weekly',
            next_run=datetime.now()
        )
        
        assert html is not None
        assert 'Reporte Semanal' in html
    
    def test_error_notification_template(self, email_service):
        """Test plantilla de notificación de error"""
        html = email_service._render_error_notification(
            report_type='executive_summary',
            error_message='Connection timeout',
            timestamp=datetime.now()
        )
        
        assert html is not None
        assert 'error' in html.lower() or 'Error' in html


class TestEmailServiceIntegration:
    """Tests de integración (requieren configuración real)"""
    
    @pytest.fixture
    def real_email_service(self):
        """Fixture para servicio con config real (skip si no está configurado)"""
        if not os.environ.get('SMTP_SERVER'):
            pytest.skip("Email configuration not available")
        
        return EmailService(EmailConfig.from_env())
    
    @pytest.mark.integration
    @pytest.mark.skipif(
        not os.environ.get('SMTP_SERVER'),
        reason="Requires real SMTP configuration"
    )
    def test_real_email_send(self, real_email_service):
        """Test envío real de email (solo en CI/CD con config)"""
        result = real_email_service.send(
            to=[os.environ.get('TEST_EMAIL_RECIPIENT', 'test@example.com')],
            subject='[TEST] Sistema OSINT EMI - Prueba de Email',
            body_html='<p>Este es un email de prueba del sistema.</p>'
        )
        
        # Solo verificar estructura de respuesta
        assert 'success' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
