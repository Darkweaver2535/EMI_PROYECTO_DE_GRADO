"""
Módulo de Reportes - Sistema OSINT EMI
Sprint 5: Generación, Programación y Distribución de Reportes

Este módulo implementa:
- Generación de reportes PDF profesionales
- Exportación de datos a Excel
- Sistema de programación con Celery
- Distribución automática por email

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

from reports.pdf_generator import PDFGenerator
from reports.excel_generator import ExcelGenerator
from reports.email_service import EmailService
from reports.scheduler import ReportScheduler

__all__ = [
    'PDFGenerator',
    'ExcelGenerator', 
    'EmailService',
    'ReportScheduler'
]

__version__ = '1.0.0'
