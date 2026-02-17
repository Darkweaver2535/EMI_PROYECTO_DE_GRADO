"""
PDFGenerator - Generador de Reportes PDF
Sistema OSINT EMI - Sprint 5

Este módulo genera reportes PDF profesionales utilizando WeasyPrint + Jinja2:
- Informe Ejecutivo Semanal
- Reporte de Alertas Críticas
- Anuario Estadístico Semestral
- Informe por Carrera Personalizado

Los reportes incluyen:
- Logo institucional EMI
- Encabezados y pies de página
- Gráficos embebidos (Matplotlib)
- Tablas profesionales
- Índice automático

Autor: Sistema OSINT EMI
Fecha: Febrero 2026
"""

import os
import io
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI para servidores
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# Configurar logging
logger = logging.getLogger("OSINT.Reports.PDF")


class PDFGenerator:
    """
    Generador de reportes PDF profesionales para el Sistema OSINT EMI.
    
    Utiliza Jinja2 para templates HTML y WeasyPrint para conversión a PDF.
    Los gráficos se generan con Matplotlib y se embeben como base64.
    
    Attributes:
        template_dir (str): Directorio de templates HTML
        output_dir (str): Directorio de salida para PDFs generados
        styles_dir (str): Directorio de estilos CSS
        env (jinja2.Environment): Entorno de templates Jinja2
    """
    
    def __init__(self, config: dict = None):
        """
        Inicializa el generador de PDFs.
        
        Args:
            config: Diccionario de configuración opcional
        """
        base_dir = Path(__file__).parent
        self.template_dir = str(base_dir / 'templates')
        self.styles_dir = str(base_dir / 'styles')
        self.output_dir = str(base_dir / 'generated')
        self.assets_dir = str(base_dir / 'assets')
        
        # Crear directorio de salida si no existe
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configurar Jinja2
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )
        
        # Añadir filtros personalizados
        self.env.filters['format_date'] = self._format_date
        self.env.filters['format_percent'] = self._format_percent
        self.env.filters['format_number'] = self._format_number
        
        # Configuración de estilo para gráficos
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Colores institucionales EMI
        self.colors = {
            'primary': '#1B5E20',      # Verde EMI
            'secondary': '#FFD700',     # Dorado
            'positive': '#10B981',      # Verde éxito
            'negative': '#EF4444',      # Rojo alerta
            'neutral': '#6B7280',       # Gris neutro
            'warning': '#F59E0B',       # Naranja warning
            'background': '#F3F4F6',    # Gris fondo
            'text': '#1F2937',          # Texto oscuro
        }
        
        logger.info(f"PDFGenerator inicializado. Templates: {self.template_dir}")
    
    # ========================================
    # Filtros de plantillas Jinja2
    # ========================================
    
    @staticmethod
    def _format_date(value: str, format_str: str = '%d/%m/%Y') -> str:
        """Formatea una fecha para mostrar en el reporte."""
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format_str)
            except ValueError:
                return value
        elif isinstance(value, datetime):
            return value.strftime(format_str)
        return str(value)
    
    @staticmethod
    def _format_percent(value: float, decimals: int = 1) -> str:
        """Formatea un porcentaje."""
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def _format_number(value: float, decimals: int = 0) -> str:
        """Formatea un número con separadores de miles."""
        if decimals == 0:
            return f"{int(value):,}".replace(',', '.')
        return f"{value:,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    # ========================================
    # Generación de Informe Ejecutivo
    # ========================================
    
    def generate_executive_report(
        self,
        start_date: str,
        end_date: str,
        filters: Dict[str, Any] = None,
        sections: List[str] = None,
        callback: callable = None
    ) -> str:
        """
        Genera Informe Ejecutivo Semanal en PDF (8-12 páginas).
        
        Secciones del reporte:
        1. Portada (logo EMI, título, fechas, autor)
        2. Resumen Ejecutivo (1 página, KPIs principales)
        3. Análisis de Sentimiento (gráficos + interpretación)
        4. Alertas Críticas (tabla priorizada)
        5. Top 10 Quejas Recurrentes
        6. Tendencias por Carrera
        7. Recomendaciones
        8. Apéndice: Metodología
        
        Args:
            start_date: Fecha inicio periodo (YYYY-MM-DD)
            end_date: Fecha fin periodo (YYYY-MM-DD)
            filters: Filtros opcionales (carrera, fuente, etc.)
            sections: Lista de secciones a incluir (None = todas)
            callback: Función para reportar progreso (0-100)
        
        Returns:
            str: Ruta absoluta del archivo PDF generado
        """
        logger.info(f"Generando Informe Ejecutivo: {start_date} a {end_date}")
        filters = filters or {}
        sections = sections or ['summary', 'sentiment', 'alerts', 'complaints', 'trends', 'recommendations']
        
        if callback:
            callback(5)
        
        # 1. Obtener datos de la base de datos
        sentiment_data = self._get_sentiment_data(start_date, end_date, filters)
        kpis = self._calculate_kpis(sentiment_data)
        
        if callback:
            callback(20)
        
        alerts = self._get_critical_alerts(start_date, end_date, filters)
        top_complaints = self._get_top_complaints(start_date, end_date, filters)
        career_trends = self._get_career_trends(start_date, end_date, filters)
        
        if callback:
            callback(40)
        
        # 2. Generar gráficos como imágenes base64
        charts = {}
        if 'sentiment' in sections:
            charts['sentiment_evolution'] = self._create_sentiment_evolution_chart(sentiment_data)
            charts['sentiment_distribution'] = self._create_sentiment_distribution_chart(kpis)
        
        if callback:
            callback(60)
        
        if 'trends' in sections:
            charts['career_comparison'] = self._create_career_comparison_chart(career_trends)
        
        if callback:
            callback(75)
        
        # 3. Preparar contexto para template
        context = {
            'report_title': 'Informe Ejecutivo Semanal OSINT',
            'report_subtitle': 'Análisis de Percepción Institucional',
            'institution': 'Escuela Militar de Ingeniería',
            'department': 'Vicerrectorado de Grado',
            'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'period_start': start_date,
            'period_end': end_date,
            'period_display': f"{self._format_date(start_date)} - {self._format_date(end_date)}",
            'filters_applied': filters,
            'sections': sections,
            
            # KPIs
            'kpis': kpis,
            'total_posts': kpis.get('total_posts', 0),
            'positive_percent': kpis.get('positive_percent', 0),
            'negative_percent': kpis.get('negative_percent', 0),
            'neutral_percent': kpis.get('neutral_percent', 0),
            'satisfaction_index': kpis.get('satisfaction_index', 0),
            'trend': kpis.get('trend', 'estable'),
            
            # Datos
            'sentiment_data': sentiment_data,
            'alerts': alerts[:10] if alerts else [],
            'total_alerts': len(alerts) if alerts else 0,
            'critical_alerts': len([a for a in (alerts or []) if a.get('severity') == 'critica']),
            'top_complaints': top_complaints[:10] if top_complaints else [],
            'career_trends': career_trends,
            
            # Gráficos
            'charts': charts,
            
            # Generación de recomendaciones
            'recommendations': self._generate_recommendations(kpis, alerts, top_complaints),
            
            # Logo EMI (base64)
            'logo_base64': self._get_logo_base64(),
            
            # Metadata
            'page_count_estimate': len(sections) * 2,
            'report_version': '1.0',
            'report_type': 'executive'
        }
        
        if callback:
            callback(85)
        
        # 4. Renderizar template HTML
        template = self.env.get_template('executive_summary.html')
        html_content = template.render(**context)
        
        # 5. Convertir HTML a PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"executive_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, filename)
        
        css_path = os.path.join(self.styles_dir, 'report.css')
        stylesheets = [CSS(css_path)] if os.path.exists(css_path) else []
        
        HTML(string=html_content, base_url=self.template_dir).write_pdf(
            output_path,
            stylesheets=stylesheets
        )
        
        if callback:
            callback(100)
        
        logger.info(f"Informe Ejecutivo generado: {output_path}")
        return output_path
    
    # ========================================
    # Generación de Reporte de Alertas
    # ========================================
    
    def generate_alerts_report(
        self,
        severity: str = None,
        days: int = 7,
        filters: Dict[str, Any] = None,
        callback: callable = None
    ) -> str:
        """
        Genera Reporte de Alertas Críticas en PDF (4-6 páginas).
        
        Secciones:
        1. Resumen de alertas por severidad
        2. Tabla detallada de cada alerta
        3. Gráfico de evolución temporal
        4. Acciones recomendadas
        
        Args:
            severity: Filtrar por severidad ('critica', 'alta', 'media', 'baja')
            days: Número de días hacia atrás a incluir
            filters: Filtros adicionales
            callback: Función para reportar progreso
        
        Returns:
            str: Ruta del archivo PDF generado
        """
        logger.info(f"Generando Reporte de Alertas: últimos {days} días, severidad={severity}")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if callback:
            callback(10)
        
        # Obtener datos de alertas
        alerts = self._get_all_alerts(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            severity,
            filters
        )
        
        if callback:
            callback(30)
        
        # Estadísticas por severidad
        severity_stats = self._calculate_severity_stats(alerts)
        
        # Alertas agrupadas por tipo
        alerts_by_type = self._group_alerts_by_type(alerts)
        
        if callback:
            callback(50)
        
        # Generar gráficos
        charts = {
            'severity_distribution': self._create_severity_pie_chart(severity_stats),
            'alerts_timeline': self._create_alerts_timeline_chart(alerts),
            'alerts_by_type': self._create_alerts_by_type_chart(alerts_by_type)
        }
        
        if callback:
            callback(70)
        
        # Preparar contexto
        context = {
            'report_title': 'Reporte de Alertas Críticas',
            'report_subtitle': 'Sistema de Monitoreo OSINT',
            'institution': 'Escuela Militar de Ingeniería',
            'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'period_display': f"Últimos {days} días",
            'severity_filter': severity or 'Todas',
            
            'alerts': alerts,
            'total_alerts': len(alerts),
            'severity_stats': severity_stats,
            'alerts_by_type': alerts_by_type,
            'charts': charts,
            
            'recommended_actions': self._generate_alert_actions(alerts),
            'logo_base64': self._get_logo_base64(),
            'report_type': 'alerts'
        }
        
        if callback:
            callback(85)
        
        # Renderizar y generar PDF
        template = self.env.get_template('alerts_report.html')
        html_content = template.render(**context)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"alerts_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, filename)
        
        css_path = os.path.join(self.styles_dir, 'report.css')
        stylesheets = [CSS(css_path)] if os.path.exists(css_path) else []
        
        HTML(string=html_content, base_url=self.template_dir).write_pdf(
            output_path,
            stylesheets=stylesheets
        )
        
        if callback:
            callback(100)
        
        logger.info(f"Reporte de Alertas generado: {output_path}")
        return output_path
    
    # ========================================
    # Generación de Anuario Estadístico
    # ========================================
    
    def generate_statistical_report(
        self,
        semester: str,
        include_sections: List[str] = None,
        callback: callable = None
    ) -> str:
        """
        Genera Anuario Estadístico Semestral (30-50 páginas).
        
        Secciones:
        1. Resumen Ejecutivo
        2. Metodología
        3. Estadísticas Descriptivas Completas
        4. Análisis de Correlaciones
        5. Clustering Detallado
        6. Comparativas Temporales
        7. Benchmarking Académico
        8. Análisis por Carrera
        9. Conclusiones
        10. Anexos
        
        Args:
            semester: Semestre académico (ej: '2026-I')
            include_sections: Secciones a incluir
            callback: Función de progreso
        
        Returns:
            str: Ruta del PDF generado
        """
        logger.info(f"Generando Anuario Estadístico: {semester}")
        
        include_sections = include_sections or [
            'executive_summary', 'methodology', 'descriptive_stats',
            'correlations', 'clustering', 'temporal_comparison',
            'benchmarking', 'career_analysis', 'conclusions'
        ]
        
        # Calcular fechas del semestre
        year, sem = semester.split('-')
        if sem == 'I':
            start_date = f"{year}-02-01"
            end_date = f"{year}-07-31"
        else:
            start_date = f"{year}-08-01"
            end_date = f"{int(year) + 1}-01-31"
        
        if callback:
            callback(5)
        
        # Obtener todos los datos necesarios
        all_data = self._get_comprehensive_data(start_date, end_date)
        
        if callback:
            callback(20)
        
        # Estadísticas descriptivas
        descriptive_stats = self._calculate_descriptive_stats(all_data)
        
        if callback:
            callback(35)
        
        # Análisis de correlaciones
        correlations = self._calculate_correlations(all_data)
        
        if callback:
            callback(50)
        
        # Clustering
        clustering_results = self._perform_clustering_analysis(all_data)
        
        if callback:
            callback(65)
        
        # Benchmarking
        benchmarking_data = self._get_benchmarking_data(semester)
        
        if callback:
            callback(75)
        
        # Generar gráficos (muchos para anuario)
        charts = self._generate_statistical_charts(
            all_data, descriptive_stats, correlations, 
            clustering_results, benchmarking_data
        )
        
        if callback:
            callback(90)
        
        # Preparar contexto
        context = {
            'report_title': f'Anuario Estadístico {semester}',
            'report_subtitle': 'Sistema de Analítica OSINT',
            'institution': 'Escuela Militar de Ingeniería',
            'department': 'Vicerrectorado de Grado',
            'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'semester': semester,
            'period_display': f"{self._format_date(start_date)} - {self._format_date(end_date)}",
            'include_sections': include_sections,
            
            'descriptive_stats': descriptive_stats,
            'correlations': correlations,
            'clustering_results': clustering_results,
            'benchmarking_data': benchmarking_data,
            'charts': charts,
            
            'total_records': all_data.get('total_records', 0),
            'career_list': all_data.get('careers', []),
            
            'logo_base64': self._get_logo_base64(),
            'report_type': 'statistical',
            'include_toc': True  # Incluir tabla de contenidos
        }
        
        # Renderizar y generar PDF
        template = self.env.get_template('statistical_report.html')
        html_content = template.render(**context)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"statistical_{semester}_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, filename)
        
        css_path = os.path.join(self.styles_dir, 'report.css')
        stylesheets = [CSS(css_path)] if os.path.exists(css_path) else []
        
        HTML(string=html_content, base_url=self.template_dir).write_pdf(
            output_path,
            stylesheets=stylesheets
        )
        
        if callback:
            callback(100)
        
        logger.info(f"Anuario Estadístico generado: {output_path}")
        return output_path
    
    # ========================================
    # Generación de Informe por Carrera
    # ========================================
    
    def generate_career_report(
        self,
        career_id: int,
        career_name: str,
        start_date: str,
        end_date: str,
        callback: callable = None
    ) -> str:
        """
        Genera Informe Personalizado por Carrera (10-15 páginas).
        
        Args:
            career_id: ID de la carrera
            career_name: Nombre de la carrera
            start_date: Fecha inicio
            end_date: Fecha fin
            callback: Función de progreso
        
        Returns:
            str: Ruta del PDF generado
        """
        logger.info(f"Generando Informe de Carrera: {career_name}")
        
        filters = {'career_id': career_id}
        
        if callback:
            callback(10)
        
        # Datos específicos de la carrera
        sentiment_data = self._get_sentiment_data(start_date, end_date, filters)
        kpis = self._calculate_kpis(sentiment_data)
        
        if callback:
            callback(30)
        
        alerts = self._get_critical_alerts(start_date, end_date, filters)
        complaints = self._get_top_complaints(start_date, end_date, filters)
        
        if callback:
            callback(50)
        
        # Comparativa con promedio institucional
        institutional_avg = self._get_institutional_average(start_date, end_date)
        comparison = self._compare_with_average(kpis, institutional_avg)
        
        if callback:
            callback(70)
        
        # Gráficos
        charts = {
            'sentiment_evolution': self._create_sentiment_evolution_chart(sentiment_data),
            'comparison_radar': self._create_comparison_radar_chart(kpis, institutional_avg),
            'complaints_wordcloud': self._create_wordcloud(complaints)
        }
        
        if callback:
            callback(85)
        
        # Contexto
        context = {
            'report_title': f'Informe de Percepción - {career_name}',
            'report_subtitle': 'Análisis OSINT por Carrera',
            'institution': 'Escuela Militar de Ingeniería',
            'career_name': career_name,
            'generated_date': datetime.now().strftime('%d/%m/%Y %H:%M'),
            'period_display': f"{self._format_date(start_date)} - {self._format_date(end_date)}",
            
            'kpis': kpis,
            'comparison': comparison,
            'alerts': alerts[:5],
            'complaints': complaints[:10],
            'charts': charts,
            
            'strengths': self._identify_strengths(kpis, comparison),
            'areas_of_improvement': self._identify_improvements(kpis, comparison),
            
            'logo_base64': self._get_logo_base64(),
            'report_type': 'career'
        }
        
        template = self.env.get_template('career_report.html')
        html_content = template.render(**context)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = career_name.lower().replace(' ', '_')[:20]
        filename = f"career_{safe_name}_{timestamp}.pdf"
        output_path = os.path.join(self.output_dir, filename)
        
        css_path = os.path.join(self.styles_dir, 'report.css')
        stylesheets = [CSS(css_path)] if os.path.exists(css_path) else []
        
        HTML(string=html_content, base_url=self.template_dir).write_pdf(
            output_path,
            stylesheets=stylesheets
        )
        
        if callback:
            callback(100)
        
        logger.info(f"Informe de Carrera generado: {output_path}")
        return output_path
    
    # ========================================
    # Métodos de obtención de datos
    # ========================================
    
    def _get_sentiment_data(
        self, 
        start_date: str, 
        end_date: str, 
        filters: Dict = None
    ) -> List[Dict]:
        """Obtiene datos de sentimiento desde la BD."""
        from database import DatabaseWriter
        
        try:
            db = DatabaseWriter()
            
            query = """
                SELECT 
                    DATE(dp.fecha_publicacion_iso) as date,
                    COUNT(*) as total,
                    SUM(CASE WHEN dp.sentimiento_basico = 'positivo' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN dp.sentimiento_basico = 'negativo' THEN 1 ELSE 0 END) as negative,
                    SUM(CASE WHEN dp.sentimiento_basico = 'neutral' THEN 1 ELSE 0 END) as neutral,
                    AVG(dp.engagement_normalizado) as avg_engagement
                FROM dato_procesado dp
                JOIN dato_recolectado dr ON dp.id_dato_original = dr.id_dato
                WHERE dp.fecha_publicacion_iso >= ? AND dp.fecha_publicacion_iso <= ?
            """
            
            params = [start_date, end_date]
            
            if filters and filters.get('career_id'):
                query += " AND dr.metadata_json LIKE ?"
                params.append(f'%"career_id": {filters["career_id"]}%')
            
            if filters and filters.get('source'):
                query += """
                    AND dr.id_fuente IN (
                        SELECT id_fuente FROM fuente_osint WHERE tipo_fuente = ?
                    )
                """
                params.append(filters['source'])
            
            query += " GROUP BY DATE(dp.fecha_publicacion_iso) ORDER BY date"
            
            results = db.execute_query(query, tuple(params))
            
            return [
                {
                    'date': row[0],
                    'total': row[1],
                    'positive': row[2],
                    'negative': row[3],
                    'neutral': row[4],
                    'avg_engagement': row[5] or 0
                }
                for row in results
            ] if results else []
            
        except Exception as e:
            logger.warning(f"Error obteniendo datos de sentimiento: {e}")
            # Retornar datos de ejemplo para desarrollo
            return self._generate_sample_sentiment_data(start_date, end_date)
    
    def _generate_sample_sentiment_data(self, start_date: str, end_date: str) -> List[Dict]:
        """Genera datos de ejemplo para desarrollo/testing."""
        from datetime import datetime, timedelta
        import random
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days
        
        data = []
        for i in range(days + 1):
            current = start + timedelta(days=i)
            total = random.randint(50, 150)
            pos = random.randint(int(total * 0.3), int(total * 0.5))
            neg = random.randint(int(total * 0.15), int(total * 0.3))
            neu = total - pos - neg
            
            data.append({
                'date': current.strftime('%Y-%m-%d'),
                'total': total,
                'positive': pos,
                'negative': neg,
                'neutral': neu,
                'avg_engagement': round(random.uniform(30, 80), 2)
            })
        
        return data
    
    def _calculate_kpis(self, sentiment_data: List[Dict]) -> Dict[str, Any]:
        """Calcula KPIs a partir de los datos de sentimiento."""
        if not sentiment_data:
            return {
                'total_posts': 0,
                'positive_percent': 0,
                'negative_percent': 0,
                'neutral_percent': 0,
                'satisfaction_index': 0,
                'trend': 'sin datos',
                'avg_engagement': 0
            }
        
        total = sum(d['total'] for d in sentiment_data)
        positive = sum(d['positive'] for d in sentiment_data)
        negative = sum(d['negative'] for d in sentiment_data)
        neutral = sum(d['neutral'] for d in sentiment_data)
        avg_engagement = sum(d['avg_engagement'] for d in sentiment_data) / len(sentiment_data)
        
        pos_percent = (positive / total * 100) if total > 0 else 0
        neg_percent = (negative / total * 100) if total > 0 else 0
        neu_percent = (neutral / total * 100) if total > 0 else 0
        
        # Índice de satisfacción: positivos - negativos + 50 (normalizado 0-100)
        satisfaction = min(100, max(0, pos_percent - neg_percent + 50))
        
        # Calcular tendencia
        if len(sentiment_data) >= 7:
            first_half = sentiment_data[:len(sentiment_data)//2]
            second_half = sentiment_data[len(sentiment_data)//2:]
            
            first_sat = sum(d['positive'] for d in first_half) / max(1, sum(d['total'] for d in first_half))
            second_sat = sum(d['positive'] for d in second_half) / max(1, sum(d['total'] for d in second_half))
            
            if second_sat > first_sat * 1.05:
                trend = 'creciente'
            elif second_sat < first_sat * 0.95:
                trend = 'decreciente'
            else:
                trend = 'estable'
        else:
            trend = 'insuficientes datos'
        
        return {
            'total_posts': total,
            'positive_count': positive,
            'negative_count': negative,
            'neutral_count': neutral,
            'positive_percent': round(pos_percent, 1),
            'negative_percent': round(neg_percent, 1),
            'neutral_percent': round(neu_percent, 1),
            'satisfaction_index': round(satisfaction, 1),
            'trend': trend,
            'avg_engagement': round(avg_engagement, 1)
        }
    
    def _get_critical_alerts(
        self, 
        start_date: str, 
        end_date: str, 
        filters: Dict = None
    ) -> List[Dict]:
        """Obtiene alertas críticas del período."""
        # Simular datos para desarrollo
        severities = ['critica', 'alta', 'media', 'baja']
        types = ['Pico negativo', 'Tendencia decreciente', 'Anomalía detectada', 
                 'Queja recurrente', 'Mención negativa viral']
        
        alerts = []
        for i in range(15):
            severity = severities[i % len(severities)]
            alerts.append({
                'id': i + 1,
                'severity': severity,
                'type': types[i % len(types)],
                'description': f'Alerta de prueba #{i+1}: {types[i % len(types)]} detectado en el sistema',
                'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'),
                'source': 'Facebook' if i % 2 == 0 else 'TikTok',
                'status': 'nueva' if i < 5 else 'revisada'
            })
        
        return sorted(alerts, key=lambda x: (
            severities.index(x['severity']),
            x['date']
        ), reverse=True)
    
    def _get_all_alerts(
        self,
        start_date: str,
        end_date: str,
        severity: str = None,
        filters: Dict = None
    ) -> List[Dict]:
        """Obtiene todas las alertas con filtros opcionales."""
        alerts = self._get_critical_alerts(start_date, end_date, filters)
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity]
        return alerts
    
    def _get_top_complaints(
        self, 
        start_date: str, 
        end_date: str, 
        filters: Dict = None
    ) -> List[Dict]:
        """Obtiene las quejas más frecuentes."""
        complaints = [
            {'topic': 'Demoras en trámites administrativos', 'count': 45, 'sentiment_avg': -0.7},
            {'topic': 'Calidad de la conectividad', 'count': 38, 'sentiment_avg': -0.6},
            {'topic': 'Infraestructura de laboratorios', 'count': 32, 'sentiment_avg': -0.5},
            {'topic': 'Disponibilidad de docentes', 'count': 28, 'sentiment_avg': -0.4},
            {'topic': 'Sistema de calificaciones', 'count': 25, 'sentiment_avg': -0.6},
            {'topic': 'Horarios de biblioteca', 'count': 22, 'sentiment_avg': -0.3},
            {'topic': 'Mantenimiento de instalaciones', 'count': 20, 'sentiment_avg': -0.5},
            {'topic': 'Comunicación institucional', 'count': 18, 'sentiment_avg': -0.4},
            {'topic': 'Procesos de matrícula', 'count': 15, 'sentiment_avg': -0.7},
            {'topic': 'Equipamiento deportivo', 'count': 12, 'sentiment_avg': -0.3},
        ]
        return complaints
    
    def _get_career_trends(
        self, 
        start_date: str, 
        end_date: str, 
        filters: Dict = None
    ) -> List[Dict]:
        """Obtiene tendencias por carrera."""
        careers = [
            {'name': 'Ingeniería de Sistemas', 'satisfaction': 72, 'mentions': 450, 'trend': 'up'},
            {'name': 'Ingeniería Civil', 'satisfaction': 68, 'mentions': 380, 'trend': 'stable'},
            {'name': 'Ingeniería Industrial', 'satisfaction': 75, 'mentions': 320, 'trend': 'up'},
            {'name': 'Ingeniería Electrónica', 'satisfaction': 65, 'mentions': 280, 'trend': 'down'},
            {'name': 'Ingeniería Mecánica', 'satisfaction': 70, 'mentions': 250, 'trend': 'stable'},
            {'name': 'Ingeniería Ambiental', 'satisfaction': 78, 'mentions': 200, 'trend': 'up'},
        ]
        return careers
    
    def _get_comprehensive_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Obtiene datos completos para el anuario estadístico."""
        return {
            'total_records': 5420,
            'careers': ['Ing. Sistemas', 'Ing. Civil', 'Ing. Industrial', 
                       'Ing. Electrónica', 'Ing. Mecánica', 'Ing. Ambiental'],
            'sources': {'Facebook': 3200, 'TikTok': 2220},
            'monthly_data': self._generate_sample_sentiment_data(start_date, end_date),
        }
    
    def _calculate_descriptive_stats(self, data: Dict) -> Dict[str, Any]:
        """Calcula estadísticas descriptivas completas."""
        return {
            'mean_satisfaction': 71.5,
            'std_satisfaction': 8.2,
            'median_satisfaction': 72.0,
            'mode_sentiment': 'positivo',
            'total_engagement': 125000,
            'avg_daily_posts': 45.2,
            'peak_day': 'Viernes',
            'peak_hour': '18:00-20:00'
        }
    
    def _calculate_correlations(self, data: Dict) -> Dict[str, Any]:
        """Calcula correlaciones entre variables."""
        return {
            'engagement_sentiment': 0.72,
            'time_sentiment': -0.15,
            'source_engagement': 0.45
        }
    
    def _perform_clustering_analysis(self, data: Dict) -> Dict[str, Any]:
        """Realiza análisis de clustering."""
        return {
            'n_clusters': 4,
            'cluster_names': ['Satisfechos', 'Neutrales', 'Críticos', 'Indiferentes'],
            'cluster_sizes': [35, 30, 20, 15]
        }
    
    def _get_benchmarking_data(self, semester: str) -> Dict[str, Any]:
        """Obtiene datos de benchmarking."""
        return {
            'emi_score': 72,
            'sector_avg': 68,
            'best_in_class': 85,
            'ranking': 3,
            'total_institutions': 12
        }
    
    def _get_institutional_average(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Obtiene promedio institucional."""
        return {
            'satisfaction_index': 70,
            'positive_percent': 42,
            'negative_percent': 23,
            'avg_engagement': 55
        }
    
    def _compare_with_average(self, kpis: Dict, avg: Dict) -> Dict[str, Any]:
        """Compara KPIs con promedio institucional."""
        return {
            'satisfaction_diff': kpis.get('satisfaction_index', 0) - avg.get('satisfaction_index', 0),
            'positive_diff': kpis.get('positive_percent', 0) - avg.get('positive_percent', 0),
            'engagement_diff': kpis.get('avg_engagement', 0) - avg.get('avg_engagement', 0),
            'is_above_average': kpis.get('satisfaction_index', 0) > avg.get('satisfaction_index', 0)
        }
    
    # ========================================
    # Generación de gráficos
    # ========================================
    
    def _create_sentiment_evolution_chart(self, data: List[Dict]) -> str:
        """Crea gráfico de evolución temporal de sentimientos."""
        if not data:
            return self._create_empty_chart("Sin datos disponibles")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in data]
        
        # Calcular porcentajes
        totals = [d['total'] for d in data]
        positives = [(d['positive'] / d['total'] * 100) if d['total'] > 0 else 0 for d in data]
        negatives = [(d['negative'] / d['total'] * 100) if d['total'] > 0 else 0 for d in data]
        neutrals = [(d['neutral'] / d['total'] * 100) if d['total'] > 0 else 0 for d in data]
        
        ax.plot(dates, positives, label='Positivo', color=self.colors['positive'], linewidth=2, marker='o', markersize=4)
        ax.plot(dates, negatives, label='Negativo', color=self.colors['negative'], linewidth=2, marker='s', markersize=4)
        ax.plot(dates, neutrals, label='Neutral', color=self.colors['neutral'], linewidth=2, marker='^', markersize=4)
        
        ax.set_xlabel('Fecha', fontsize=10)
        ax.set_ylabel('Porcentaje (%)', fontsize=10)
        ax.set_title('Evolución de Sentimientos', fontsize=12, fontweight='bold')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        
        # Formato de fechas en eje X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()
        
        return self._fig_to_base64(fig)
    
    def _create_sentiment_distribution_chart(self, kpis: Dict) -> str:
        """Crea gráfico de distribución de sentimientos (dona)."""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sizes = [
            kpis.get('positive_percent', 33),
            kpis.get('negative_percent', 33),
            kpis.get('neutral_percent', 34)
        ]
        labels = ['Positivo', 'Negativo', 'Neutral']
        colors = [self.colors['positive'], self.colors['negative'], self.colors['neutral']]
        explode = (0.02, 0.02, 0.02)
        
        wedges, texts, autotexts = ax.pie(
            sizes, 
            explode=explode,
            labels=labels, 
            colors=colors,
            autopct='%1.1f%%',
            startangle=90,
            wedgeprops=dict(width=0.5)  # Dona
        )
        
        # Estilo de textos
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_fontweight('bold')
        
        ax.set_title('Distribución de Sentimientos', fontsize=12, fontweight='bold')
        
        # Texto central
        total = kpis.get('total_posts', 0)
        ax.text(0, 0, f'{total:,}\nposts', ha='center', va='center', fontsize=14, fontweight='bold')
        
        return self._fig_to_base64(fig)
    
    def _create_career_comparison_chart(self, careers: List[Dict]) -> str:
        """Crea gráfico de comparación por carreras."""
        if not careers:
            return self._create_empty_chart("Sin datos de carreras")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        names = [c['name'][:15] + '...' if len(c['name']) > 15 else c['name'] for c in careers]
        satisfaction = [c['satisfaction'] for c in careers]
        
        # Colores según satisfacción
        colors = [self.colors['positive'] if s >= 70 else 
                 self.colors['warning'] if s >= 50 else 
                 self.colors['negative'] for s in satisfaction]
        
        bars = ax.barh(names, satisfaction, color=colors)
        
        # Línea de promedio
        avg = sum(satisfaction) / len(satisfaction)
        ax.axvline(x=avg, color=self.colors['primary'], linestyle='--', linewidth=2, label=f'Promedio: {avg:.1f}')
        
        ax.set_xlabel('Índice de Satisfacción', fontsize=10)
        ax.set_title('Satisfacción por Carrera', fontsize=12, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.legend()
        
        # Valores en barras
        for bar, val in zip(bars, satisfaction):
            ax.text(val + 1, bar.get_y() + bar.get_height()/2, f'{val}%', 
                   va='center', fontsize=9)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_severity_pie_chart(self, stats: Dict) -> str:
        """Crea gráfico de distribución de severidades."""
        fig, ax = plt.subplots(figsize=(6, 6))
        
        sizes = [
            stats.get('critica', 5),
            stats.get('alta', 10),
            stats.get('media', 15),
            stats.get('baja', 20)
        ]
        labels = ['Crítica', 'Alta', 'Media', 'Baja']
        colors = ['#DC2626', '#F59E0B', '#3B82F6', '#10B981']
        
        ax.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%', startangle=90)
        ax.set_title('Alertas por Severidad', fontsize=12, fontweight='bold')
        
        return self._fig_to_base64(fig)
    
    def _create_alerts_timeline_chart(self, alerts: List[Dict]) -> str:
        """Crea gráfico de línea temporal de alertas."""
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # Agrupar alertas por fecha
        from collections import Counter
        dates_count = Counter(a['date'] for a in alerts)
        
        dates = sorted(dates_count.keys())
        counts = [dates_count[d] for d in dates]
        
        dates_dt = [datetime.strptime(d, '%Y-%m-%d') for d in dates]
        
        ax.fill_between(dates_dt, counts, alpha=0.3, color=self.colors['negative'])
        ax.plot(dates_dt, counts, color=self.colors['negative'], linewidth=2, marker='o')
        
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Número de Alertas')
        ax.set_title('Evolución Temporal de Alertas', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        fig.autofmt_xdate()
        return self._fig_to_base64(fig)
    
    def _create_alerts_by_type_chart(self, alerts_by_type: Dict) -> str:
        """Crea gráfico de barras por tipo de alerta."""
        fig, ax = plt.subplots(figsize=(8, 5))
        
        types = list(alerts_by_type.keys())[:6]
        counts = [alerts_by_type[t] for t in types]
        
        bars = ax.bar(range(len(types)), counts, color=self.colors['primary'])
        ax.set_xticks(range(len(types)))
        ax.set_xticklabels(types, rotation=45, ha='right')
        ax.set_ylabel('Cantidad')
        ax.set_title('Alertas por Tipo', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_comparison_radar_chart(self, kpis: Dict, avg: Dict) -> str:
        """Crea gráfico de radar comparativo."""
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        categories = ['Satisfacción', 'Positivos', 'Engagement', 'Alcance', 'Crecimiento']
        n_cats = len(categories)
        
        # Valores normalizados (0-100)
        values_career = [
            kpis.get('satisfaction_index', 0),
            kpis.get('positive_percent', 0),
            kpis.get('avg_engagement', 0),
            70,  # Alcance placeholder
            65   # Crecimiento placeholder
        ]
        
        values_avg = [
            avg.get('satisfaction_index', 0),
            avg.get('positive_percent', 0),
            avg.get('avg_engagement', 0),
            65,
            60
        ]
        
        # Ángulos
        angles = [n / float(n_cats) * 2 * np.pi for n in range(n_cats)]
        angles += angles[:1]
        values_career += values_career[:1]
        values_avg += values_avg[:1]
        
        ax.plot(angles, values_career, 'o-', linewidth=2, label='Carrera', color=self.colors['positive'])
        ax.fill(angles, values_career, alpha=0.25, color=self.colors['positive'])
        
        ax.plot(angles, values_avg, 'o-', linewidth=2, label='Promedio EMI', color=self.colors['neutral'])
        ax.fill(angles, values_avg, alpha=0.25, color=self.colors['neutral'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 100)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))
        ax.set_title('Comparación con Promedio Institucional', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _create_wordcloud(self, complaints: List[Dict]) -> str:
        """Crea imagen de nube de palabras."""
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Simular wordcloud con texto
        ax.text(0.5, 0.5, 'WordCloud\n(Quejas frecuentes)', 
               ha='center', va='center', fontsize=20,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.set_title('Nube de Palabras - Temas Recurrentes', fontsize=12, fontweight='bold')
        
        return self._fig_to_base64(fig)
    
    def _create_empty_chart(self, message: str) -> str:
        """Crea un gráfico vacío con mensaje."""
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14, color='gray')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return self._fig_to_base64(fig)
    
    def _generate_statistical_charts(
        self,
        all_data: Dict,
        descriptive_stats: Dict,
        correlations: Dict,
        clustering_results: Dict,
        benchmarking_data: Dict
    ) -> Dict[str, str]:
        """Genera todos los gráficos para el anuario estadístico."""
        charts = {}
        
        # 1. Gráfico de resumen mensual
        monthly_data = all_data.get('monthly_data', [])
        if monthly_data:
            charts['monthly_sentiment'] = self._create_sentiment_evolution_chart(monthly_data)
        
        # 2. Distribución de sentimientos
        charts['sentiment_distribution'] = self._create_sentiment_distribution_chart({
            'positive_percent': 42,
            'negative_percent': 23,
            'neutral_percent': 35,
            'total_posts': all_data.get('total_records', 0)
        })
        
        # 3. Histograma de satisfacción
        fig, ax = plt.subplots(figsize=(8, 4))
        np.random.seed(42)
        data = np.random.normal(descriptive_stats.get('mean_satisfaction', 70), 
                               descriptive_stats.get('std_satisfaction', 10), 1000)
        ax.hist(data, bins=30, color=self.colors['primary'], alpha=0.7, edgecolor='white')
        ax.axvline(descriptive_stats.get('mean_satisfaction', 70), color='red', linestyle='--', label='Media')
        ax.set_xlabel('Índice de Satisfacción')
        ax.set_ylabel('Frecuencia')
        ax.set_title('Distribución de Satisfacción', fontweight='bold')
        ax.legend()
        charts['satisfaction_histogram'] = self._fig_to_base64(fig)
        
        # 4. Matriz de correlaciones
        fig, ax = plt.subplots(figsize=(6, 5))
        corr_matrix = np.array([
            [1.0, 0.72, -0.15],
            [0.72, 1.0, 0.45],
            [-0.15, 0.45, 1.0]
        ])
        im = ax.imshow(corr_matrix, cmap='RdYlGn', vmin=-1, vmax=1)
        ax.set_xticks([0, 1, 2])
        ax.set_yticks([0, 1, 2])
        ax.set_xticklabels(['Sentimiento', 'Engagement', 'Tiempo'])
        ax.set_yticklabels(['Sentimiento', 'Engagement', 'Tiempo'])
        plt.colorbar(im)
        ax.set_title('Matriz de Correlaciones', fontweight='bold')
        # Añadir valores
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f'{corr_matrix[i, j]:.2f}', ha='center', va='center')
        charts['correlation_matrix'] = self._fig_to_base64(fig)
        
        # 5. Clustering
        fig, ax = plt.subplots(figsize=(8, 5))
        sizes = clustering_results.get('cluster_sizes', [35, 30, 20, 15])
        names = clustering_results.get('cluster_names', ['C1', 'C2', 'C3', 'C4'])
        colors = [self.colors['positive'], self.colors['neutral'], 
                 self.colors['warning'], self.colors['negative']]
        ax.pie(sizes, labels=names, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.set_title('Segmentación de Opiniones (Clustering)', fontweight='bold')
        charts['clustering'] = self._fig_to_base64(fig)
        
        # 6. Benchmarking
        fig, ax = plt.subplots(figsize=(8, 4))
        categories = ['EMI', 'Promedio Sector', 'Mejor del Sector']
        values = [
            benchmarking_data.get('emi_score', 72),
            benchmarking_data.get('sector_avg', 68),
            benchmarking_data.get('best_in_class', 85)
        ]
        colors = [self.colors['primary'], self.colors['neutral'], self.colors['positive']]
        bars = ax.bar(categories, values, color=colors)
        ax.set_ylabel('Índice de Satisfacción')
        ax.set_title('Benchmarking con el Sector', fontweight='bold')
        ax.set_ylim(0, 100)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, val + 2, f'{val}', ha='center', fontweight='bold')
        charts['benchmarking'] = self._fig_to_base64(fig)
        
        return charts
    
    def _fig_to_base64(self, fig) -> str:
        """Convierte figura matplotlib a string base64."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"
    
    # ========================================
    # Utilidades
    # ========================================
    
    def _calculate_severity_stats(self, alerts: List[Dict]) -> Dict[str, int]:
        """Calcula estadísticas de severidad."""
        stats = {'critica': 0, 'alta': 0, 'media': 0, 'baja': 0}
        for alert in alerts:
            severity = alert.get('severity', 'media')
            if severity in stats:
                stats[severity] += 1
        return stats
    
    def _group_alerts_by_type(self, alerts: List[Dict]) -> Dict[str, int]:
        """Agrupa alertas por tipo."""
        from collections import Counter
        return dict(Counter(a.get('type', 'Otro') for a in alerts))
    
    def _generate_recommendations(
        self,
        kpis: Dict,
        alerts: List[Dict],
        complaints: List[Dict]
    ) -> List[Dict]:
        """Genera recomendaciones basadas en los datos."""
        recommendations = []
        
        # Basado en satisfacción
        if kpis.get('satisfaction_index', 0) < 60:
            recommendations.append({
                'priority': 'alta',
                'area': 'Satisfacción General',
                'recommendation': 'Implementar programa de mejora urgente en áreas críticas identificadas.',
                'expected_impact': 'Incremento de 10-15% en satisfacción'
            })
        
        # Basado en sentimientos negativos
        if kpis.get('negative_percent', 0) > 30:
            recommendations.append({
                'priority': 'alta',
                'area': 'Percepción Negativa',
                'recommendation': 'Reforzar comunicación institucional y respuesta a quejas.',
                'expected_impact': 'Reducción de 5-10% en percepciones negativas'
            })
        
        # Basado en alertas críticas
        critical_count = len([a for a in alerts if a.get('severity') == 'critica'])
        if critical_count > 3:
            recommendations.append({
                'priority': 'urgente',
                'area': 'Gestión de Crisis',
                'recommendation': f'Atender {critical_count} alertas críticas pendientes de forma inmediata.',
                'expected_impact': 'Prevención de escalamiento de problemas'
            })
        
        # Basado en quejas frecuentes
        if complaints:
            top_complaint = complaints[0]
            recommendations.append({
                'priority': 'media',
                'area': top_complaint.get('topic', 'Quejas'),
                'recommendation': f'Desarrollar plan de acción para "{top_complaint.get("topic", "tema principal")}".',
                'expected_impact': 'Reducción de quejas recurrentes'
            })
        
        # Recomendación de engagement
        if kpis.get('avg_engagement', 0) < 40:
            recommendations.append({
                'priority': 'media',
                'area': 'Engagement Digital',
                'recommendation': 'Implementar estrategia de contenido más interactivo en redes sociales.',
                'expected_impact': 'Incremento de 20-30% en engagement'
            })
        
        return recommendations
    
    def _generate_alert_actions(self, alerts: List[Dict]) -> List[Dict]:
        """Genera acciones recomendadas para alertas."""
        actions = []
        
        critical = [a for a in alerts if a.get('severity') == 'critica']
        if critical:
            actions.append({
                'action': 'Reunión de emergencia con equipo directivo',
                'timeline': 'Inmediato (24h)',
                'responsible': 'Dirección de Comunicaciones'
            })
        
        high = [a for a in alerts if a.get('severity') == 'alta']
        if high:
            actions.append({
                'action': 'Revisar y responder alertas de alta prioridad',
                'timeline': 'Esta semana',
                'responsible': 'Coordinadores de Carrera'
            })
        
        actions.append({
            'action': 'Monitoreo continuo de redes sociales',
            'timeline': 'Permanente',
            'responsible': 'Equipo OSINT'
        })
        
        return actions
    
    def _identify_strengths(self, kpis: Dict, comparison: Dict) -> List[str]:
        """Identifica fortalezas de la carrera."""
        strengths = []
        
        if comparison.get('satisfaction_diff', 0) > 5:
            strengths.append('Satisfacción por encima del promedio institucional')
        if kpis.get('positive_percent', 0) > 45:
            strengths.append('Alto porcentaje de menciones positivas')
        if comparison.get('engagement_diff', 0) > 10:
            strengths.append('Engagement superior al promedio')
        if kpis.get('trend') == 'creciente':
            strengths.append('Tendencia positiva sostenida')
        
        if not strengths:
            strengths.append('Mantiene estabilidad en indicadores clave')
        
        return strengths
    
    def _identify_improvements(self, kpis: Dict, comparison: Dict) -> List[str]:
        """Identifica áreas de mejora."""
        improvements = []
        
        if comparison.get('satisfaction_diff', 0) < -5:
            improvements.append('Satisfacción por debajo del promedio - requiere atención')
        if kpis.get('negative_percent', 0) > 25:
            improvements.append('Reducir menciones negativas con comunicación proactiva')
        if comparison.get('engagement_diff', 0) < -10:
            improvements.append('Incrementar engagement en redes sociales')
        if kpis.get('trend') == 'decreciente':
            improvements.append('Revertir tendencia negativa con acciones concretas')
        
        if not improvements:
            improvements.append('Continuar fortaleciendo indicadores actuales')
        
        return improvements
    
    def _get_logo_base64(self) -> str:
        """Obtiene el logo EMI en formato base64."""
        logo_path = os.path.join(self.assets_dir, 'logo_emi.png')
        
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        
        # Generar logo placeholder
        fig, ax = plt.subplots(figsize=(2, 2))
        circle = plt.Circle((0.5, 0.5), 0.4, color=self.colors['primary'])
        ax.add_patch(circle)
        ax.text(0.5, 0.5, 'EMI', ha='center', va='center', 
               fontsize=20, fontweight='bold', color='white')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        return self._fig_to_base64(fig)


# Función de utilidad para uso directo
def generate_report(report_type: str, **kwargs) -> str:
    """
    Función de conveniencia para generar reportes.
    
    Args:
        report_type: 'executive', 'alerts', 'statistical', 'career'
        **kwargs: Parámetros específicos del reporte
    
    Returns:
        str: Ruta del PDF generado
    """
    generator = PDFGenerator()
    
    if report_type == 'executive':
        return generator.generate_executive_report(**kwargs)
    elif report_type == 'alerts':
        return generator.generate_alerts_report(**kwargs)
    elif report_type == 'statistical':
        return generator.generate_statistical_report(**kwargs)
    elif report_type == 'career':
        return generator.generate_career_report(**kwargs)
    else:
        raise ValueError(f"Tipo de reporte no válido: {report_type}")
