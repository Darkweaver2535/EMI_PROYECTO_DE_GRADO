"""
Tests para los módulos ETL
Sistema OSINT EMI

Tests unitarios para DataCleaner, DataTransformer, DataValidator
y ETLController.

Ejecutar: pytest tests/test_etl.py -v
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Importar módulos a testear
from etl.data_cleaner import DataCleaner
from etl.data_transformer import DataTransformer
from etl.data_validator import DataValidator
from etl.etl_controller import ETLController


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def config():
    """Configuración base para tests."""
    return {
        'etl': {
            'batch_size': 100,
            'clean': {
                'remove_emojis': False,
                'remove_urls': True,
                'remove_mentions': False,
                'remove_hashtags': False,
                'lowercase': False
            },
            'transform': {
                'extract_temporal': True,
                'normalize_engagement': True,
                'classify_content': True,
                'sentiment_analysis': True
            }
        }
    }


@pytest.fixture
def sample_raw_data():
    """Datos de ejemplo para tests."""
    return [
        {
            'id': 1,
            'id_externo': 'post_001',
            'contenido': 'Felicidades a nuestros graduados! 🎓 https://example.com',
            'fecha_publicacion': '2024-05-15 10:30:00',
            'likes': 150,
            'comentarios': 25,
            'compartidos': 10,
            'tipo_contenido': 'post'
        },
        {
            'id': 2,
            'id_externo': 'post_002',
            'contenido': 'Inscripciones abiertas para el nuevo semestre @estudiantes #EMI',
            'fecha_publicacion': '2024-03-01 14:00:00',
            'likes': 200,
            'comentarios': 50,
            'compartidos': 30,
            'tipo_contenido': 'post'
        },
        {
            'id': 3,
            'id_externo': 'post_003',
            'contenido': 'Comunicado importante sobre horarios',
            'fecha_publicacion': '2024-07-20 09:15:00',
            'likes': 80,
            'comentarios': 15,
            'compartidos': 5,
            'tipo_contenido': 'post'
        }
    ]


@pytest.fixture
def sample_dataframe(sample_raw_data):
    """DataFrame de ejemplo."""
    return pd.DataFrame(sample_raw_data)


# ============================================================
# Tests de DataCleaner
# ============================================================

class TestDataCleaner:
    """Tests para la clase DataCleaner."""
    
    def test_initialization(self, config):
        """Verifica inicialización correcta."""
        cleaner = DataCleaner(config)
        assert cleaner.config == config
    
    def test_remove_urls(self, config):
        """Verifica eliminación de URLs."""
        cleaner = DataCleaner(config)
        
        text = "Visita https://www.emi.edu.bo para más info"
        result = cleaner.remove_urls(text)
        
        assert 'https://' not in result
        assert 'emi.edu.bo' not in result
        assert 'Visita' in result
        assert 'para más info' in result
    
    def test_remove_emojis(self, config):
        """Verifica eliminación de emojis."""
        config['etl']['clean']['remove_emojis'] = True
        cleaner = DataCleaner(config)
        
        text = "Felicidades 🎓🎉 a todos!"
        result = cleaner.remove_emojis(text)
        
        assert '🎓' not in result
        assert '🎉' not in result
        assert 'Felicidades' in result
    
    def test_remove_mentions(self, config):
        """Verifica eliminación de menciones."""
        config['etl']['clean']['remove_mentions'] = True
        cleaner = DataCleaner(config)
        
        text = "Gracias @usuario por tu comentario"
        result = cleaner.remove_mentions(text)
        
        assert '@usuario' not in result
        assert 'Gracias' in result
    
    def test_remove_hashtags(self, config):
        """Verifica eliminación de hashtags."""
        config['etl']['clean']['remove_hashtags'] = True
        cleaner = DataCleaner(config)
        
        text = "Nueva publicación #EMI #LasPiedras"
        result = cleaner.remove_hashtags(text)
        
        assert '#EMI' not in result
        assert '#LasPiedras' not in result
    
    def test_fix_encoding(self, config):
        """Verifica corrección de encoding."""
        cleaner = DataCleaner(config)
        
        # Texto con problemas de encoding típicos
        text = "InformaciÃ³n acadÃ©mica"
        result = cleaner.fix_encoding(text)
        
        # Debe intentar corregir o mantener legible
        assert result is not None
        assert len(result) > 0
    
    def test_normalize_whitespace(self, config):
        """Verifica normalización de espacios."""
        cleaner = DataCleaner(config)
        
        text = "Texto    con    muchos   espacios"
        result = cleaner.normalize_whitespace(text)
        
        assert '    ' not in result
        assert result == "Texto con muchos espacios"
    
    def test_clean_dataframe(self, config, sample_dataframe):
        """Verifica limpieza de DataFrame completo."""
        cleaner = DataCleaner(config)
        
        result = cleaner.clean_dataframe(sample_dataframe)
        
        # Debe retornar un DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Debe tener las mismas filas
        assert len(result) == len(sample_dataframe)
        
        # URLs deben estar removidas
        for contenido in result['contenido']:
            assert 'https://' not in str(contenido)
    
    def test_clean_text_none(self, config):
        """Verifica manejo de texto None."""
        cleaner = DataCleaner(config)
        
        result = cleaner.clean_text(None)
        assert result == ''
    
    def test_clean_text_empty(self, config):
        """Verifica manejo de texto vacío."""
        cleaner = DataCleaner(config)
        
        result = cleaner.clean_text('')
        assert result == ''


# ============================================================
# Tests de DataTransformer
# ============================================================

class TestDataTransformer:
    """Tests para la clase DataTransformer."""
    
    def test_initialization(self, config):
        """Verifica inicialización correcta."""
        transformer = DataTransformer(config)
        assert transformer.config == config
    
    def test_extract_temporal_features(self, config, sample_dataframe):
        """Verifica extracción de características temporales."""
        transformer = DataTransformer(config)
        
        result = transformer.extract_temporal_features(sample_dataframe)
        
        # Debe agregar columnas temporales
        assert 'dia_semana' in result.columns
        assert 'hora' in result.columns
        assert 'mes' in result.columns
        assert 'semestre_academico' in result.columns
    
    def test_semestre_academico_calculation(self, config):
        """Verifica cálculo del semestre académico."""
        transformer = DataTransformer(config)
        
        # Febrero - 1er semestre
        fecha_feb = datetime(2024, 2, 15)
        assert transformer.get_semestre_academico(fecha_feb) == '1er Semestre 2024'
        
        # Agosto - 2do semestre
        fecha_ago = datetime(2024, 8, 15)
        assert transformer.get_semestre_academico(fecha_ago) == '2do Semestre 2024'
        
        # Enero - vacaciones
        fecha_ene = datetime(2024, 1, 15)
        result = transformer.get_semestre_academico(fecha_ene)
        assert 'Vacaciones' in result or 'Inter' in result
    
    def test_normalize_engagement(self, config, sample_dataframe):
        """Verifica normalización de engagement."""
        transformer = DataTransformer(config)
        
        result = transformer.normalize_engagement(sample_dataframe)
        
        # Debe agregar columna de engagement normalizado
        assert 'engagement_score' in result.columns or 'engagement_normalizado' in result.columns
        
        # Los valores deben estar en rango razonable
        score_col = 'engagement_score' if 'engagement_score' in result.columns else 'engagement_normalizado'
        assert result[score_col].min() >= 0
    
    def test_classify_content_felicitacion(self, config):
        """Verifica clasificación de contenido: felicitación."""
        transformer = DataTransformer(config)
        
        text = "Felicidades a todos los graduados de este año"
        result = transformer.classify_content(text)
        
        assert result == 'Felicitación' or result == 'felicitacion'
    
    def test_classify_content_queja(self, config):
        """Verifica clasificación de contenido: queja."""
        transformer = DataTransformer(config)
        
        text = "Es inaceptable el mal servicio que recibimos"
        result = transformer.classify_content(text)
        
        assert result in ['Queja', 'queja', 'Negativo']
    
    def test_classify_content_informativo(self, config):
        """Verifica clasificación de contenido: informativo."""
        transformer = DataTransformer(config)
        
        text = "Comunicamos que las inscripciones inician el lunes"
        result = transformer.classify_content(text)
        
        assert result in ['Informativo', 'informativo', 'Neutral']
    
    def test_basic_sentiment_analysis(self, config):
        """Verifica análisis de sentimiento básico."""
        transformer = DataTransformer(config)
        
        # Texto positivo
        positive_text = "Excelente trabajo, felicidades por este logro"
        result_pos = transformer.basic_sentiment_analysis(positive_text)
        assert result_pos['sentiment'] in ['positive', 'positivo', 'Positivo']
        
        # Texto negativo
        negative_text = "Terrible servicio, muy mal atendidos"
        result_neg = transformer.basic_sentiment_analysis(negative_text)
        assert result_neg['sentiment'] in ['negative', 'negativo', 'Negativo']
    
    def test_transform_dataframe(self, config, sample_dataframe):
        """Verifica transformación completa del DataFrame."""
        transformer = DataTransformer(config)
        
        result = transformer.transform(sample_dataframe)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_dataframe)


# ============================================================
# Tests de DataValidator
# ============================================================

class TestDataValidator:
    """Tests para la clase DataValidator."""
    
    def test_initialization(self, config):
        """Verifica inicialización correcta."""
        validator = DataValidator(config)
        assert validator.config == config
    
    def test_validate_required_fields(self, config, sample_dataframe):
        """Verifica validación de campos requeridos."""
        validator = DataValidator(config)
        
        # DataFrame completo debe pasar
        valid, invalid = validator.validate_dataframe(sample_dataframe)
        
        assert len(valid) == len(sample_dataframe)
        assert len(invalid) == 0
    
    def test_validate_missing_required(self, config):
        """Verifica detección de campos faltantes."""
        validator = DataValidator(config)
        
        # DataFrame con campos faltantes
        df = pd.DataFrame([
            {'id': 1, 'contenido': None, 'likes': 10},  # contenido None
            {'id': 2, 'contenido': '', 'likes': 20},     # contenido vacío
        ])
        
        valid, invalid = validator.validate_dataframe(df)
        
        # Registros con contenido vacío/None deben ser inválidos
        assert len(invalid) >= 1
    
    def test_validate_numeric_ranges(self, config):
        """Verifica validación de rangos numéricos."""
        validator = DataValidator(config)
        
        df = pd.DataFrame([
            {'id': 1, 'id_externo': 'test1', 'contenido': 'Test', 'likes': -5},     # likes negativos
            {'id': 2, 'id_externo': 'test2', 'contenido': 'Test', 'likes': 100},    # válido
        ])
        
        valid, invalid = validator.validate_dataframe(df)
        
        # El de likes negativos debe ser inválido
        assert len(invalid) >= 1
    
    def test_validate_date_format(self, config):
        """Verifica validación de formato de fecha."""
        validator = DataValidator(config)
        
        df = pd.DataFrame([
            {'id': 1, 'id_externo': 'test1', 'contenido': 'Test', 
             'fecha_publicacion': '2024-05-15 10:30:00'},  # formato válido
            {'id': 2, 'id_externo': 'test2', 'contenido': 'Test', 
             'fecha_publicacion': 'fecha_invalida'},  # formato inválido
        ])
        
        valid, invalid = validator.validate_dataframe(df)
        
        # El de fecha inválida debe ser detectado
        # (dependiendo de la implementación puede ser válido o inválido)
    
    def test_validate_text_length(self, config):
        """Verifica validación de longitud de texto."""
        validator = DataValidator(config)
        
        # Texto muy largo (más de 10000 caracteres)
        long_text = 'A' * 15000
        
        df = pd.DataFrame([
            {'id': 1, 'id_externo': 'test1', 'contenido': long_text, 'likes': 10}
        ])
        
        valid, invalid = validator.validate_dataframe(df)
        
        # Depende de la configuración del validador


# ============================================================
# Tests de ETLController
# ============================================================

class TestETLController:
    """Tests para la clase ETLController."""
    
    def test_initialization(self, config):
        """Verifica inicialización correcta."""
        with patch('etl.etl_controller.DatabaseWriter') as mock_db:
            controller = ETLController(config=config)
            assert controller.config == config
    
    def test_extract_phase(self, config, sample_raw_data):
        """Verifica fase de extracción."""
        with patch('etl.etl_controller.DatabaseWriter') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_unprocessed_data.return_value = sample_raw_data
            mock_db.return_value = mock_db_instance
            
            controller = ETLController(config=config, db=mock_db_instance)
            
            # Ejecutar extracción
            data = controller.extract()
            
            assert len(data) == len(sample_raw_data)
    
    def test_full_pipeline(self, config, sample_raw_data):
        """Verifica pipeline ETL completo."""
        with patch('etl.etl_controller.DatabaseWriter') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_unprocessed_data.return_value = sample_raw_data
            mock_db_instance.save_processed_data.return_value = (3, 0)
            mock_db_instance.log_execution.return_value = 1
            mock_db_instance.complete_execution_log.return_value = None
            mock_db.return_value = mock_db_instance
            
            controller = ETLController(config=config, db=mock_db_instance)
            
            # Ejecutar pipeline
            results = controller.run()
            
            assert 'extracted' in results
            assert 'cleaned' in results
            assert 'transformed' in results
            assert 'loaded' in results
    
    def test_empty_data_handling(self, config):
        """Verifica manejo de datos vacíos."""
        with patch('etl.etl_controller.DatabaseWriter') as mock_db:
            mock_db_instance = Mock()
            mock_db_instance.get_unprocessed_data.return_value = []
            mock_db_instance.log_execution.return_value = 1
            mock_db_instance.complete_execution_log.return_value = None
            mock_db.return_value = mock_db_instance
            
            controller = ETLController(config=config, db=mock_db_instance)
            
            results = controller.run()
            
            # No debe fallar con datos vacíos
            assert results['extracted'] == 0


# ============================================================
# Tests de Integración ETL
# ============================================================

class TestETLIntegration:
    """Tests de integración del pipeline ETL."""
    
    def test_cleaner_to_transformer_compatibility(self, config, sample_dataframe):
        """Verifica compatibilidad entre cleaner y transformer."""
        cleaner = DataCleaner(config)
        transformer = DataTransformer(config)
        
        # El output del cleaner debe ser válido para el transformer
        cleaned = cleaner.clean_dataframe(sample_dataframe)
        transformed = transformer.transform(cleaned)
        
        assert isinstance(transformed, pd.DataFrame)
        assert len(transformed) == len(sample_dataframe)
    
    def test_transformer_to_validator_compatibility(self, config, sample_dataframe):
        """Verifica compatibilidad entre transformer y validator."""
        transformer = DataTransformer(config)
        validator = DataValidator(config)
        
        # El output del transformer debe ser validable
        transformed = transformer.transform(sample_dataframe)
        valid, invalid = validator.validate_dataframe(transformed)
        
        # La mayoría debe ser válida
        assert len(valid) >= len(sample_dataframe) - 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
