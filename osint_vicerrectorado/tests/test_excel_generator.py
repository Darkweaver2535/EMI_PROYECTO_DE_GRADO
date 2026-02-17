"""
Tests para el módulo de Reportes Excel
Sistema de Analítica OSINT - EMI Bolivia
Sprint 5: Reportes y Estadísticas
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import os
import tempfile
import pandas as pd

# Import del módulo a testear
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports.excel_generator import ExcelReportGenerator, ExcelReportType


class TestExcelReportGenerator:
    """Tests para el generador de reportes Excel"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    @pytest.fixture
    def sample_dataframe(self):
        """DataFrame de ejemplo para tests"""
        return pd.DataFrame({
            'fecha': pd.date_range('2024-01-01', periods=100),
            'carrera': ['Sistemas', 'Civil', 'Mecánica', 'Industrial', 'Electrónica'] * 20,
            'fuente': ['Facebook', 'Twitter', 'News'] * 33 + ['Facebook'],
            'sentimiento': ['positivo', 'neutral', 'negativo'] * 33 + ['positivo'],
            'score': [0.8, 0.5, -0.3, 0.6, -0.2] * 20,
            'texto': ['Test post ' + str(i) for i in range(100)]
        })
    
    def test_initialization(self, generator):
        """Test que el generador se inicializa correctamente"""
        assert generator is not None
        assert generator.output_dir is not None
    
    def test_report_types_enum(self):
        """Test que los tipos de reporte están definidos"""
        assert ExcelReportType.SENTIMENT_DATASET.value == 'sentiment_dataset'
        assert ExcelReportType.PIVOT_TABLE.value == 'pivot_table'
        assert ExcelReportType.ANOMALY_REPORT.value == 'anomaly_report'
        assert ExcelReportType.COMBINED_REPORT.value == 'combined_report'
    
    def test_create_summary_sheet(self, generator, sample_dataframe):
        """Test creación de hoja de resumen"""
        summary = generator._create_summary(sample_dataframe)
        
        assert 'total_records' in summary
        assert 'date_range' in summary
        assert 'careers_count' in summary
        
        assert summary['total_records'] == 100
        assert summary['careers_count'] == 5
    
    def test_create_pivot_by_career(self, generator, sample_dataframe):
        """Test creación de pivot por carrera"""
        pivot = generator._create_pivot_by_career(sample_dataframe)
        
        assert isinstance(pivot, pd.DataFrame)
        # Debería tener filas por cada carrera
        assert len(pivot) == 5
    
    def test_create_pivot_by_source(self, generator, sample_dataframe):
        """Test creación de pivot por fuente"""
        pivot = generator._create_pivot_by_source(sample_dataframe)
        
        assert isinstance(pivot, pd.DataFrame)
        # Debería tener filas por cada fuente
        assert len(pivot) == 3
    
    def test_create_pivot_by_month(self, generator, sample_dataframe):
        """Test creación de pivot por mes"""
        pivot = generator._create_pivot_by_month(sample_dataframe)
        
        assert isinstance(pivot, pd.DataFrame)
        assert len(pivot) > 0
    
    def test_detect_anomalies(self, generator, sample_dataframe):
        """Test detección de anomalías"""
        # Agregar datos anómalos
        df = sample_dataframe.copy()
        df.loc[0, 'score'] = -0.99  # Valor extremo negativo
        
        anomalies = generator._detect_anomalies(df)
        
        assert isinstance(anomalies, pd.DataFrame)
    
    def test_apply_conditional_formatting(self, generator):
        """Test que el formato condicional se aplica correctamente"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            # Crear archivo Excel de prueba
            df = pd.DataFrame({'score': [0.8, 0.5, -0.3, 0.1, -0.7]})
            
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Test', index=False)
                
                # Aplicar formato condicional
                ws = writer.sheets['Test']
                generator._apply_sentiment_formatting(ws, 'B', 2, 6)
            
            # Verificar que el archivo se creó
            assert os.path.exists(tmp.name)
            os.unlink(tmp.name)
    
    def test_filename_generation(self, generator):
        """Test que los nombres de archivo se generan correctamente"""
        filename = generator._generate_filename('sentiment_dataset')
        
        assert filename.endswith('.xlsx')
        assert 'sentiment_dataset' in filename
        assert datetime.now().strftime('%Y%m%d') in filename
    
    def test_generate_sentiment_dataset(self, generator, sample_dataframe):
        """Test generación de dataset de sentimientos"""
        filepath = generator.generate_sentiment_dataset(sample_dataframe)
        
        assert filepath is not None
        assert os.path.exists(filepath)
        assert filepath.endswith('.xlsx')
        
        # Verificar que tiene múltiples hojas
        excel_file = pd.ExcelFile(filepath)
        sheets = excel_file.sheet_names
        
        assert len(sheets) >= 2  # Al menos resumen y datos
    
    def test_generate_pivot_report(self, generator, sample_dataframe):
        """Test generación de reporte pivot"""
        filepath = generator.generate_pivot_report(
            sample_dataframe,
            pivot_by='career'
        )
        
        assert filepath is not None
        assert os.path.exists(filepath)
        
        # Verificar contenido
        df = pd.read_excel(filepath, sheet_name=0)
        assert len(df) > 0
    
    def test_generate_anomaly_report(self, generator, sample_dataframe):
        """Test generación de reporte de anomalías"""
        # Agregar datos anómalos para que haya algo que reportar
        df = sample_dataframe.copy()
        df.loc[0, 'score'] = -0.99
        df.loc[1, 'score'] = 0.99
        
        filepath = generator.generate_anomaly_report(df)
        
        assert filepath is not None
        assert os.path.exists(filepath)


class TestExcelFormatting:
    """Tests para el formateo de Excel"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    def test_color_scale_positive(self, generator):
        """Test escala de colores para valores positivos"""
        color = generator._get_sentiment_color(0.8)
        
        # Debería ser verde
        assert color is not None
        assert color.startswith('#') or color in ['green', 'lime']
    
    def test_color_scale_negative(self, generator):
        """Test escala de colores para valores negativos"""
        color = generator._get_sentiment_color(-0.8)
        
        # Debería ser rojo
        assert color is not None
        assert color.startswith('#') or color in ['red', 'coral']
    
    def test_color_scale_neutral(self, generator):
        """Test escala de colores para valores neutrales"""
        color = generator._get_sentiment_color(0.0)
        
        # Debería ser amarillo/gris
        assert color is not None
    
    def test_header_formatting(self, generator):
        """Test formateo de cabeceras"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
            
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Test', index=False)
                
                ws = writer.sheets['Test']
                generator._format_header(ws)
            
            # Verificar archivo
            result = pd.read_excel(tmp.name)
            assert len(result) == 2
            
            os.unlink(tmp.name)


class TestExcelCharts:
    """Tests para gráficos en Excel"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    def test_add_pie_chart(self, generator):
        """Test agregar gráfico de pie"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({
                'Sentimiento': ['Positivo', 'Neutral', 'Negativo'],
                'Cantidad': [45, 35, 20]
            })
            
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                ws = writer.sheets['Data']
                generator._add_pie_chart(ws, df, 'Distribución de Sentimiento')
            
            assert os.path.exists(tmp.name)
            os.unlink(tmp.name)
    
    def test_add_bar_chart(self, generator):
        """Test agregar gráfico de barras"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            df = pd.DataFrame({
                'Carrera': ['Sistemas', 'Civil', 'Mecánica'],
                'Positivo': [50, 45, 40],
                'Negativo': [15, 20, 25]
            })
            
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Data', index=False)
                
                ws = writer.sheets['Data']
                generator._add_bar_chart(ws, df, 'Sentimiento por Carrera')
            
            assert os.path.exists(tmp.name)
            os.unlink(tmp.name)


class TestExcelDataValidation:
    """Tests para validación de datos en Excel"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    def test_validate_dataframe_required_columns(self, generator):
        """Test validación de columnas requeridas"""
        # DataFrame válido
        df_valid = pd.DataFrame({
            'fecha': ['2024-01-01'],
            'sentimiento': ['positivo'],
            'score': [0.8]
        })
        
        assert generator._validate_dataframe(df_valid, ['fecha', 'sentimiento'])
        
        # DataFrame inválido (falta columna)
        df_invalid = pd.DataFrame({
            'fecha': ['2024-01-01']
        })
        
        assert not generator._validate_dataframe(df_invalid, ['fecha', 'sentimiento'])
    
    def test_handle_empty_dataframe(self, generator):
        """Test manejo de DataFrame vacío"""
        df_empty = pd.DataFrame()
        
        # Debería manejar sin errores
        result = generator._handle_empty_data(df_empty)
        assert result is not None


class TestExcelIntegration:
    """Tests de integración para generación de Excel"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    @pytest.fixture
    def large_dataframe(self):
        """DataFrame grande para tests de rendimiento"""
        n_rows = 10000
        return pd.DataFrame({
            'fecha': pd.date_range('2024-01-01', periods=n_rows),
            'carrera': ['Sistemas', 'Civil', 'Mecánica'] * (n_rows // 3) + ['Sistemas'],
            'fuente': ['Facebook', 'Twitter'] * (n_rows // 2),
            'sentimiento': ['positivo', 'neutral', 'negativo'] * (n_rows // 3) + ['positivo'],
            'score': [0.5] * n_rows,
            'texto': ['Test ' + str(i) for i in range(n_rows)]
        })
    
    @pytest.mark.integration
    def test_full_combined_report_generation(self, generator, large_dataframe):
        """Test completo de generación de reporte combinado"""
        import time
        
        start_time = time.time()
        filepath = generator.generate_combined_report(large_dataframe)
        elapsed_time = time.time() - start_time
        
        assert filepath is not None
        assert os.path.exists(filepath)
        
        # Verificar tiempo de generación (< 10 segundos)
        assert elapsed_time < 10, f"Generación tardó {elapsed_time:.2f}s, máximo permitido: 10s"
        
        # Verificar tamaño (< 10MB)
        file_size = os.path.getsize(filepath) / (1024 * 1024)
        assert file_size < 10, f"Archivo pesa {file_size:.2f}MB, máximo permitido: 10MB"
        
        # Verificar hojas
        excel = pd.ExcelFile(filepath)
        assert len(excel.sheet_names) >= 4  # Resumen, datos, pivots, anomalías
    
    @pytest.mark.integration
    def test_file_size_limit(self, generator, large_dataframe):
        """Test que los archivos no excedan límite de tamaño"""
        filepath = generator.generate_sentiment_dataset(large_dataframe)
        
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        assert file_size_mb < 10, f"Archivo excede 10MB: {file_size_mb:.2f}MB"


class TestProgressCallback:
    """Tests para callbacks de progreso"""
    
    @pytest.fixture
    def generator(self):
        """Fixture para crear instancia del generador"""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = ExcelReportGenerator(output_dir=tmpdir)
            yield gen
    
    def test_progress_callback_sequence(self, generator):
        """Test secuencia de callbacks de progreso"""
        progress_values = []
        
        def callback(progress, message):
            progress_values.append((progress, message))
        
        # Simular progreso
        generator._update_progress(callback, 0, "Iniciando")
        generator._update_progress(callback, 25, "Procesando datos")
        generator._update_progress(callback, 50, "Generando pivots")
        generator._update_progress(callback, 75, "Aplicando formato")
        generator._update_progress(callback, 100, "Completado")
        
        # Verificar secuencia
        assert len(progress_values) == 5
        assert progress_values[0][0] == 0
        assert progress_values[-1][0] == 100
        
        # Verificar que el progreso es incremental
        for i in range(1, len(progress_values)):
            assert progress_values[i][0] >= progress_values[i-1][0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
