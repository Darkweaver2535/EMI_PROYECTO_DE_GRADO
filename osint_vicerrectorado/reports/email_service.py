"""
EmailService - Servicio de Distribución de Reportes por Email
Sistema OSINT EMI - Sprint 5

Este módulo maneja el envío automático de reportes generados:
- Envío con adjuntos (PDF/Excel)
- Templates de email profesionales
- Reintentos automáticos ante fallos
- Logs de entrega
- Notificaciones de estado

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import os
import smtplib
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logger = logging.getLogger("OSINT.Reports.Email")


class DeliveryStatus(Enum):
    """Estados de entrega de email."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class EmailConfig:
    """Configuración del servidor de email."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    default_sender: str = "osint-reports@emi.edu.bo"
    max_attachment_size: int = 10 * 1024 * 1024  # 10 MB


class EmailService:
    """
    Servicio de envío de emails para distribución de reportes.
    
    Maneja el envío de reportes con adjuntos, reintentos automáticos,
    y logging de entregas para auditoría.
    
    Attributes:
        config (EmailConfig): Configuración del servidor SMTP
        delivery_log (list): Log de entregas realizadas
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Inicializa el servicio de email.
        
        Args:
            config: Diccionario de configuración SMTP
        """
        # Cargar configuración
        self.config = EmailConfig()
        
        if config:
            self.config.smtp_server = config.get('smtp_server', self.config.smtp_server)
            self.config.smtp_port = config.get('smtp_port', self.config.smtp_port)
            self.config.use_tls = config.get('use_tls', self.config.use_tls)
            self.config.username = config.get('username', os.getenv('SMTP_USERNAME', ''))
            self.config.password = config.get('password', os.getenv('SMTP_PASSWORD', ''))
            self.config.default_sender = config.get('default_sender', self.config.default_sender)
        else:
            # Intentar cargar de variables de entorno
            self.config.username = os.getenv('SMTP_USERNAME', '')
            self.config.password = os.getenv('SMTP_PASSWORD', '')
            self.config.smtp_server = os.getenv('SMTP_SERVER', self.config.smtp_server)
            self.config.smtp_port = int(os.getenv('SMTP_PORT', str(self.config.smtp_port)))
        
        # Log de entregas en memoria (en producción usar BD)
        self.delivery_log: List[Dict] = []
        
        # Directorio para templates
        self.template_dir = Path(__file__).parent / 'templates' / 'email'
        
        logger.info(f"EmailService inicializado. SMTP: {self.config.smtp_server}:{self.config.smtp_port}")
    
    # ========================================
    # Envío de Reportes
    # ========================================
    
    def send_report(
        self,
        recipients: List[str],
        subject: str,
        attachment_path: str,
        body: str = None,
        report_type: str = "general",
        sender: str = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Envía un reporte por email con reintentos automáticos.
        
        Args:
            recipients: Lista de emails destinatarios
            subject: Asunto del email
            attachment_path: Ruta al archivo adjunto (PDF/Excel)
            body: Cuerpo del mensaje (opcional)
            report_type: Tipo de reporte para template
            sender: Email del remitente (opcional)
            max_retries: Número máximo de reintentos
        
        Returns:
            Dict con status, attempt, timestamp y detalles
        """
        logger.info(f"Enviando reporte a {len(recipients)} destinatario(s)")
        
        # Validar adjunto
        if not os.path.exists(attachment_path):
            error = f"Archivo adjunto no encontrado: {attachment_path}"
            logger.error(error)
            return self._create_delivery_result(
                DeliveryStatus.FAILED, 0, error=error
            )
        
        # Verificar tamaño
        file_size = os.path.getsize(attachment_path)
        if file_size > self.config.max_attachment_size:
            error = f"Archivo excede tamaño máximo ({file_size} > {self.config.max_attachment_size})"
            logger.error(error)
            return self._create_delivery_result(
                DeliveryStatus.FAILED, 0, error=error
            )
        
        # Crear mensaje
        msg = self._create_message(
            recipients=recipients,
            subject=subject,
            body=body,
            attachment_path=attachment_path,
            report_type=report_type,
            sender=sender or self.config.default_sender
        )
        
        # Intentar envío con reintentos
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                self._send_smtp(msg, recipients)
                
                result = self._create_delivery_result(
                    DeliveryStatus.SENT, 
                    attempt,
                    recipients=recipients,
                    attachment=os.path.basename(attachment_path)
                )
                
                logger.info(f"Email enviado exitosamente en intento {attempt}")
                return result
                
            except smtplib.SMTPAuthenticationError as e:
                last_error = f"Error de autenticación SMTP: {str(e)}"
                logger.error(last_error)
                break  # No reintentar errores de autenticación
                
            except smtplib.SMTPRecipientsRefused as e:
                last_error = f"Destinatarios rechazados: {str(e)}"
                logger.error(last_error)
                break  # No reintentar destinatarios inválidos
                
            except (smtplib.SMTPException, OSError) as e:
                last_error = f"Error SMTP (intento {attempt}): {str(e)}"
                logger.warning(last_error)
                
                if attempt < max_retries:
                    # Backoff exponencial
                    wait_time = 2 ** attempt
                    logger.info(f"Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
        
        # Todos los reintentos fallaron
        return self._create_delivery_result(
            DeliveryStatus.FAILED,
            max_retries,
            error=last_error,
            recipients=recipients
        )
    
    def send_notification(
        self,
        recipients: List[str],
        notification_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envía una notificación de estado (sin adjuntos).
        
        Args:
            recipients: Lista de destinatarios
            notification_type: Tipo de notificación
                - 'report_ready': Reporte listo para descarga
                - 'report_failed': Fallo en generación
                - 'alert': Alerta crítica detectada
            data: Datos para el template
        
        Returns:
            Dict con resultado del envío
        """
        logger.info(f"Enviando notificación {notification_type} a {len(recipients)} destinatario(s)")
        
        subject, body = self._get_notification_content(notification_type, data)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = self.config.default_sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        
        # Body HTML
        html_body = self._render_notification_template(notification_type, data)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        try:
            self._send_smtp(msg, recipients)
            return self._create_delivery_result(DeliveryStatus.SENT, 1)
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
            return self._create_delivery_result(DeliveryStatus.FAILED, 1, error=str(e))
    
    def send_bulk_reports(
        self,
        report_configs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Envía múltiples reportes de forma secuencial.
        
        Args:
            report_configs: Lista de configuraciones de envío
                [{recipients, subject, attachment_path, ...}, ...]
        
        Returns:
            Lista de resultados de cada envío
        """
        results = []
        
        for idx, config in enumerate(report_configs, 1):
            logger.info(f"Procesando envío {idx}/{len(report_configs)}")
            
            result = self.send_report(
                recipients=config.get('recipients', []),
                subject=config.get('subject', 'Reporte OSINT EMI'),
                attachment_path=config.get('attachment_path', ''),
                body=config.get('body'),
                report_type=config.get('report_type', 'general')
            )
            
            result['config_index'] = idx
            results.append(result)
            
            # Pequeña pausa entre envíos para evitar rate limiting
            time.sleep(1)
        
        # Resumen
        sent = sum(1 for r in results if r['status'] == DeliveryStatus.SENT.value)
        failed = len(results) - sent
        logger.info(f"Envío masivo completado: {sent} enviados, {failed} fallidos")
        
        return results
    
    # ========================================
    # Métodos de construcción de mensajes
    # ========================================
    
    def _create_message(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        attachment_path: str,
        report_type: str,
        sender: str
    ) -> MIMEMultipart:
        """Crea el mensaje MIME con adjunto."""
        msg = MIMEMultipart('mixed')
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = subject
        
        # Headers adicionales
        msg['X-Priority'] = '3'
        msg['X-Mailer'] = 'OSINT EMI Report System'
        
        # Body alternativo (texto plano + HTML)
        msg_alternative = MIMEMultipart('alternative')
        
        # Texto plano
        plain_body = body or self._get_default_body_text(report_type)
        msg_alternative.attach(MIMEText(plain_body, 'plain', 'utf-8'))
        
        # HTML
        html_body = self._render_email_template(
            subject=subject,
            body=body or plain_body,
            report_type=report_type,
            attachment_name=os.path.basename(attachment_path)
        )
        msg_alternative.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        msg.attach(msg_alternative)
        
        # Adjunto
        self._attach_file(msg, attachment_path)
        
        return msg
    
    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Adjunta un archivo al mensaje."""
        filename = os.path.basename(file_path)
        
        # Determinar tipo MIME
        if file_path.endswith('.pdf'):
            mime_type = 'application/pdf'
        elif file_path.endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif file_path.endswith('.xls'):
            mime_type = 'application/vnd.ms-excel'
        else:
            mime_type = 'application/octet-stream'
        
        with open(file_path, 'rb') as f:
            attachment = MIMEBase(*mime_type.split('/'))
            attachment.set_payload(f.read())
        
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        
        msg.attach(attachment)
    
    def _send_smtp(self, msg: MIMEMultipart, recipients: List[str]):
        """Envía el mensaje via SMTP."""
        with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
            if self.config.use_tls:
                server.starttls()
            
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            
            server.send_message(msg, to_addrs=recipients)
    
    # ========================================
    # Templates de Email
    # ========================================
    
    def _render_email_template(
        self,
        subject: str,
        body: str,
        report_type: str,
        attachment_name: str
    ) -> str:
        """Renderiza template HTML para el email."""
        
        # Colores institucionales
        primary_color = '#1B5E20'  # Verde EMI
        secondary_color = '#FFD700'  # Dorado
        
        # Icono según tipo de reporte
        icons = {
            'executive': '📊',
            'alerts': '🚨',
            'statistical': '📈',
            'sentiment': '💬',
            'general': '📄'
        }
        icon = icons.get(report_type, '📄')
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; background-color: #f4f4f4;">
            <table role="presentation" style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td align="center" style="padding: 40px 0;">
                        <table role="presentation" style="width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, {primary_color} 0%, #2E7D32 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px;">
                                        {icon} Sistema OSINT EMI
                                    </h1>
                                    <p style="color: {secondary_color}; margin: 10px 0 0 0; font-size: 14px;">
                                        Escuela Militar de Ingeniería
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 20px;">
                                        {subject}
                                    </h2>
                                    
                                    <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
                                        {body}
                                    </p>
                                    
                                    <!-- Attachment Info -->
                                    <table role="presentation" style="width: 100%; background-color: #f8f9fa; border-radius: 6px; margin: 20px 0;">
                                        <tr>
                                            <td style="padding: 15px;">
                                                <table role="presentation" style="width: 100%;">
                                                    <tr>
                                                        <td style="width: 40px; vertical-align: top;">
                                                            <span style="font-size: 24px;">📎</span>
                                                        </td>
                                                        <td>
                                                            <p style="margin: 0; color: #333; font-weight: bold;">
                                                                Archivo adjunto
                                                            </p>
                                                            <p style="margin: 5px 0 0 0; color: #666; font-size: 13px;">
                                                                {attachment_name}
                                                            </p>
                                                        </td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="color: #999999; font-size: 12px; margin: 20px 0 0 0;">
                                        Este reporte fue generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}.
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-radius: 0 0 8px 8px; border-top: 1px solid #e9ecef;">
                                    <p style="color: #999999; font-size: 12px; margin: 0;">
                                        Sistema de Analítica OSINT - Vicerrectorado de Grado
                                    </p>
                                    <p style="color: #999999; font-size: 11px; margin: 10px 0 0 0;">
                                        Este es un mensaje automático. Por favor no responda a este correo.
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def _render_notification_template(
        self,
        notification_type: str,
        data: Dict[str, Any]
    ) -> str:
        """Renderiza template HTML para notificaciones."""
        
        # Configuración según tipo
        configs = {
            'report_ready': {
                'color': '#10B981',
                'icon': '✅',
                'title': 'Reporte Disponible'
            },
            'report_failed': {
                'color': '#EF4444',
                'icon': '❌',
                'title': 'Error en Generación'
            },
            'alert': {
                'color': '#F59E0B',
                'icon': '⚠️',
                'title': 'Alerta Detectada'
            }
        }
        
        config = configs.get(notification_type, configs['report_ready'])
        
        message = data.get('message', 'Notificación del sistema OSINT')
        details = data.get('details', '')
        action_url = data.get('action_url', '')
        action_text = data.get('action_text', 'Ver detalles')
        
        action_button = ""
        if action_url:
            action_button = f"""
                <a href="{action_url}" 
                   style="display: inline-block; padding: 12px 24px; background-color: {config['color']}; 
                          color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: bold;">
                    {action_text}
                </a>
            """
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <table style="width: 100%;">
                <tr>
                    <td align="center" style="padding: 40px 0;">
                        <table style="width: 500px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            
                            <!-- Icon -->
                            <tr>
                                <td style="padding: 30px; text-align: center;">
                                    <span style="font-size: 48px;">{config['icon']}</span>
                                    <h2 style="color: {config['color']}; margin: 15px 0 0 0;">
                                        {config['title']}
                                    </h2>
                                </td>
                            </tr>
                            
                            <!-- Message -->
                            <tr>
                                <td style="padding: 0 30px 30px 30px; text-align: center;">
                                    <p style="color: #333; font-size: 16px; margin: 0 0 15px 0;">
                                        {message}
                                    </p>
                                    
                                    {f'<p style="color: #666; font-size: 14px; margin: 0 0 20px 0;">{details}</p>' if details else ''}
                                    
                                    {action_button}
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 8px 8px;">
                                    <p style="color: #999; font-size: 11px; margin: 0;">
                                        Sistema OSINT EMI - {datetime.now().strftime('%d/%m/%Y %H:%M')}
                                    </p>
                                </td>
                            </tr>
                            
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def _get_notification_content(
        self,
        notification_type: str,
        data: Dict[str, Any]
    ) -> tuple:
        """Obtiene asunto y cuerpo texto para notificación."""
        
        subjects = {
            'report_ready': '✅ Tu reporte OSINT está listo',
            'report_failed': '❌ Error al generar reporte',
            'alert': '⚠️ Alerta OSINT detectada'
        }
        
        subject = subjects.get(notification_type, 'Notificación OSINT EMI')
        
        bodies = {
            'report_ready': f"Tu reporte ha sido generado exitosamente. {data.get('message', '')}",
            'report_failed': f"Hubo un error al generar el reporte: {data.get('error', 'Error desconocido')}",
            'alert': f"Se ha detectado una alerta: {data.get('message', '')}"
        }
        
        body = bodies.get(notification_type, data.get('message', ''))
        
        return subject, body
    
    def _get_default_body_text(self, report_type: str) -> str:
        """Obtiene texto por defecto según tipo de reporte."""
        texts = {
            'executive': 'Adjunto encontrará el Informe Ejecutivo Semanal con el análisis de percepción institucional.',
            'alerts': 'Adjunto encontrará el Reporte de Alertas Críticas detectadas por el sistema de monitoreo.',
            'statistical': 'Adjunto encontrará el Anuario Estadístico con el análisis completo del período.',
            'sentiment': 'Adjunto encontrará el dataset de análisis de sentimientos en formato Excel.',
            'general': 'Adjunto encontrará el reporte solicitado del Sistema de Analítica OSINT.'
        }
        return texts.get(report_type, texts['general'])
    
    # ========================================
    # Gestión de Logs
    # ========================================
    
    def _create_delivery_result(
        self,
        status: DeliveryStatus,
        attempt: int,
        error: str = None,
        recipients: List[str] = None,
        attachment: str = None
    ) -> Dict[str, Any]:
        """Crea resultado de entrega y lo registra."""
        result = {
            'status': status.value,
            'attempt': attempt,
            'timestamp': datetime.now().isoformat(),
            'recipients': recipients or [],
            'attachment': attachment,
            'error': error
        }
        
        # Agregar al log
        self.delivery_log.append(result)
        
        return result
    
    def get_delivery_log(
        self,
        status: DeliveryStatus = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtiene el log de entregas.
        
        Args:
            status: Filtrar por status
            limit: Número máximo de registros
        
        Returns:
            Lista de registros de entrega
        """
        logs = self.delivery_log[-limit:]
        
        if status:
            logs = [l for l in logs if l['status'] == status.value]
        
        return logs
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de entregas."""
        total = len(self.delivery_log)
        
        if total == 0:
            return {
                'total': 0,
                'sent': 0,
                'failed': 0,
                'success_rate': 0
            }
        
        sent = sum(1 for l in self.delivery_log if l['status'] == DeliveryStatus.SENT.value)
        failed = sum(1 for l in self.delivery_log if l['status'] == DeliveryStatus.FAILED.value)
        
        return {
            'total': total,
            'sent': sent,
            'failed': failed,
            'success_rate': round(sent / total * 100, 1) if total > 0 else 0
        }
    
    def clear_delivery_log(self):
        """Limpia el log de entregas."""
        self.delivery_log.clear()
        logger.info("Log de entregas limpiado")
    
    # ========================================
    # Validaciones
    # ========================================
    
    def validate_email(self, email: str) -> bool:
        """Valida formato de email."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_recipients(self, recipients: List[str]) -> tuple:
        """
        Valida lista de destinatarios.
        
        Returns:
            (valid_emails, invalid_emails)
        """
        valid = []
        invalid = []
        
        for email in recipients:
            if self.validate_email(email):
                valid.append(email)
            else:
                invalid.append(email)
        
        return valid, invalid
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión SMTP.
        
        Returns:
            Dict con resultado de la prueba
        """
        try:
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                
                if self.config.username and self.config.password:
                    server.login(self.config.username, self.config.password)
                
                server.noop()  # Comando de prueba
            
            logger.info("Conexión SMTP exitosa")
            return {
                'success': True,
                'message': 'Conexión SMTP establecida correctamente',
                'server': self.config.smtp_server,
                'port': self.config.smtp_port
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Error de autenticación: {e}")
            return {
                'success': False,
                'error': 'Error de autenticación',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            return {
                'success': False,
                'error': 'Error de conexión',
                'details': str(e)
            }


# Funciones de utilidad
def send_report_email(
    recipients: List[str],
    subject: str,
    attachment_path: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Función de conveniencia para enviar un reporte.
    
    Args:
        recipients: Lista de destinatarios
        subject: Asunto
        attachment_path: Ruta del archivo
        **kwargs: Argumentos adicionales
    
    Returns:
        Resultado del envío
    """
    service = EmailService()
    return service.send_report(
        recipients=recipients,
        subject=subject,
        attachment_path=attachment_path,
        **kwargs
    )


def send_notification_email(
    recipients: List[str],
    notification_type: str,
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Función de conveniencia para enviar notificación.
    
    Args:
        recipients: Lista de destinatarios
        notification_type: Tipo de notificación
        data: Datos del mensaje
    
    Returns:
        Resultado del envío
    """
    service = EmailService()
    return service.send_notification(
        recipients=recipients,
        notification_type=notification_type,
        data=data
    )
