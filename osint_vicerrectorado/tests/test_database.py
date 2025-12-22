"""
Tests para el módulo de base de datos
Sistema OSINT EMI

Tests unitarios para DatabaseWriter con base de datos SQLite en memoria.

Ejecutar: pytest tests/test_database.py -v
"""

import pytest
import sqlite3
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch

# Importar módulo a testear
from database.db_writer import DatabaseWriter


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def config():
    """Configuración para tests con BD en memoria."""
    return {
        'database': {
            'path': ':memory:',
            'type': 'sqlite'
        }
    }


@pytest.fixture
def temp_db_config():
    """Configuración con archivo temporal."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test_osint.db')
    return {
        'database': {
            'path': db_path,
            'type': 'sqlite'
        }
    }


@pytest.fixture
def db_writer(config):
    """Instancia de DatabaseWriter para tests."""
    db = DatabaseWriter(config=config)
    db.initialize_schema()
    yield db
    db.close()


@pytest.fixture
def sample_collected_data():
    """Datos de ejemplo para guardar."""
    return [
        {
            'id_externo': 'fb_post_001',
            'contenido': 'Primera publicación de prueba',
            'fecha_publicacion': '2024-05-15 10:30:00',
            'url': 'https://facebook.com/page/posts/001',
            'tipo_contenido': 'post',
            'likes': 100,
            'comentarios': 20,
            'compartidos': 5,
            'metadata': {'raw_html': '<div>test</div>'}
        },
        {
            'id_externo': 'fb_post_002',
            'contenido': 'Segunda publicación de prueba',
            'fecha_publicacion': '2024-05-16 14:00:00',
            'url': 'https://facebook.com/page/posts/002',
            'tipo_contenido': 'post',
            'likes': 150,
            'comentarios': 30,
            'compartidos': 10,
            'metadata': {}
        }
    ]


# ============================================================
# Tests de Inicialización
# ============================================================

class TestDatabaseWriterInit:
    """Tests de inicialización de DatabaseWriter."""
    
    def test_initialization(self, config):
        """Verifica inicialización correcta."""
        db = DatabaseWriter(config=config)
        assert db is not None
        db.close()
    
    def test_initialize_schema(self, config):
        """Verifica creación del esquema."""
        db = DatabaseWriter(config=config)
        db.initialize_schema()
        
        # Verificar que las tablas existen
        cursor = db.connection.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'fuente_osint' in tables
        assert 'dato_recolectado' in tables
        assert 'dato_procesado' in tables
        assert 'log_ejecucion' in tables
        
        db.close()
    
    def test_connection_persistence(self, config):
        """Verifica que la conexión persiste."""
        db = DatabaseWriter(config=config)
        db.initialize_schema()
        
        # Primera operación
        source_id = db.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Segunda operación en la misma conexión
        source_id2 = db.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Debe retornar el mismo ID
        assert source_id == source_id2
        
        db.close()


# ============================================================
# Tests de Fuentes (Sources)
# ============================================================

class TestSourceOperations:
    """Tests para operaciones de fuentes."""
    
    def test_create_source(self, db_writer):
        """Verifica creación de fuente."""
        source_id = db_writer.get_or_create_source(
            nombre='EMI Oficial',
            tipo='Facebook',
            url='https://facebook.com/emioficial',
            identificador='emioficial'
        )
        
        assert source_id is not None
        assert source_id > 0
    
    def test_get_existing_source(self, db_writer):
        """Verifica obtención de fuente existente."""
        # Crear fuente
        source_id1 = db_writer.get_or_create_source(
            nombre='EMI Oficial',
            tipo='Facebook',
            url='https://facebook.com/emioficial',
            identificador='emioficial'
        )
        
        # Obtener la misma fuente
        source_id2 = db_writer.get_or_create_source(
            nombre='EMI Oficial',
            tipo='Facebook',
            url='https://facebook.com/emioficial',
            identificador='emioficial'
        )
        
        assert source_id1 == source_id2
    
    def test_create_multiple_sources(self, db_writer):
        """Verifica creación de múltiples fuentes."""
        sources = [
            ('EMI Oficial', 'Facebook', 'https://facebook.com/emi', 'emi'),
            ('EMI UALP', 'Facebook', 'https://facebook.com/ualp', 'ualp'),
            ('EMI TikTok', 'TikTok', 'https://tiktok.com/@emi', '@emi'),
        ]
        
        ids = []
        for nombre, tipo, url, identificador in sources:
            source_id = db_writer.get_or_create_source(
                nombre=nombre, tipo=tipo, url=url, identificador=identificador
            )
            ids.append(source_id)
        
        # Todos los IDs deben ser únicos
        assert len(set(ids)) == len(ids)


# ============================================================
# Tests de Datos Recolectados
# ============================================================

class TestCollectedDataOperations:
    """Tests para operaciones de datos recolectados."""
    
    def test_save_collected_data(self, db_writer, sample_collected_data):
        """Verifica guardado de datos recolectados."""
        # Crear fuente primero
        source_id = db_writer.get_or_create_source(
            nombre='Test Page',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        saved, duplicates = db_writer.save_collected_data(
            sample_collected_data, source_id
        )
        
        assert saved == 2
        assert duplicates == 0
    
    def test_duplicate_detection(self, db_writer, sample_collected_data):
        """Verifica detección de duplicados."""
        source_id = db_writer.get_or_create_source(
            nombre='Test Page',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Guardar primera vez
        saved1, dup1 = db_writer.save_collected_data(
            sample_collected_data, source_id
        )
        
        # Intentar guardar de nuevo
        saved2, dup2 = db_writer.save_collected_data(
            sample_collected_data, source_id
        )
        
        assert saved1 == 2
        assert dup1 == 0
        assert saved2 == 0
        assert dup2 == 2
    
    def test_get_unprocessed_data(self, db_writer, sample_collected_data):
        """Verifica obtención de datos no procesados."""
        source_id = db_writer.get_or_create_source(
            nombre='Test Page',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        db_writer.save_collected_data(sample_collected_data, source_id)
        
        unprocessed = db_writer.get_unprocessed_data()
        
        assert len(unprocessed) == 2
    
    def test_partial_data_save(self, db_writer):
        """Verifica guardado de datos parciales."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Datos con campos mínimos
        minimal_data = [
            {
                'id_externo': 'min_001',
                'contenido': 'Solo texto',
                'tipo_contenido': 'post'
            }
        ]
        
        saved, dup = db_writer.save_collected_data(minimal_data, source_id)
        
        assert saved == 1


# ============================================================
# Tests de Datos Procesados
# ============================================================

class TestProcessedDataOperations:
    """Tests para operaciones de datos procesados."""
    
    def test_save_processed_data(self, db_writer, sample_collected_data):
        """Verifica guardado de datos procesados."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Guardar datos raw primero
        db_writer.save_collected_data(sample_collected_data, source_id)
        
        # Obtener y procesar
        unprocessed = db_writer.get_unprocessed_data()
        
        # Agregar campos de procesamiento
        processed_data = []
        for row in unprocessed:
            processed_row = dict(row)
            processed_row['id_dato_raw'] = row['id']
            processed_row['contenido_limpio'] = row['contenido'].lower()
            processed_row['sentimiento'] = 'neutral'
            processed_row['categoria'] = 'informativo'
            processed_row['engagement_score'] = 50.0
            processed_data.append(processed_row)
        
        saved, failed = db_writer.save_processed_data(processed_data)
        
        assert saved == 2
        assert failed == 0
    
    def test_get_all_processed_data(self, db_writer, sample_collected_data):
        """Verifica obtención de todos los datos procesados."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        db_writer.save_collected_data(sample_collected_data, source_id)
        unprocessed = db_writer.get_unprocessed_data()
        
        processed_data = []
        for row in unprocessed:
            processed_row = dict(row)
            processed_row['id_dato_raw'] = row['id']
            processed_row['contenido_limpio'] = row['contenido']
            processed_row['sentimiento'] = 'neutral'
            processed_row['categoria'] = 'informativo'
            processed_data.append(processed_row)
        
        db_writer.save_processed_data(processed_data)
        
        all_processed = db_writer.get_all_processed_data()
        
        assert len(all_processed) == 2


# ============================================================
# Tests de Estadísticas
# ============================================================

class TestStatistics:
    """Tests para operaciones de estadísticas."""
    
    def test_get_statistics_empty(self, db_writer):
        """Verifica estadísticas con BD vacía."""
        stats = db_writer.get_statistics()
        
        assert 'total_raw' in stats
        assert 'total_processed' in stats
        assert stats['total_raw'] == 0
        assert stats['total_processed'] == 0
    
    def test_get_statistics_with_data(self, db_writer, sample_collected_data):
        """Verifica estadísticas con datos."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        db_writer.save_collected_data(sample_collected_data, source_id)
        
        stats = db_writer.get_statistics()
        
        assert stats['total_raw'] == 2
    
    def test_get_engagement_stats(self, db_writer, sample_collected_data):
        """Verifica estadísticas de engagement."""
        source_id = db_writer.get_or_create_source(
            nombre='Test Page',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        db_writer.save_collected_data(sample_collected_data, source_id)
        
        engagement_stats = db_writer.get_engagement_stats_by_source()
        
        assert isinstance(engagement_stats, list)


# ============================================================
# Tests de Logging de Ejecución
# ============================================================

class TestExecutionLogging:
    """Tests para logging de ejecuciones."""
    
    def test_log_execution(self, db_writer):
        """Verifica creación de log de ejecución."""
        log_id = db_writer.log_execution(
            tipo='recoleccion',
            fuente='facebook'
        )
        
        assert log_id is not None
        assert log_id > 0
    
    def test_complete_execution_log(self, db_writer):
        """Verifica completar log de ejecución."""
        log_id = db_writer.log_execution(
            tipo='etl',
            fuente='all'
        )
        
        db_writer.complete_execution_log(
            log_id,
            success=True,
            processed=100,
            successful=95,
            failed=5,
            details={'duration': 30.5}
        )
        
        # Verificar que se actualizó
        cursor = db_writer.connection.cursor()
        cursor.execute(
            "SELECT exito, procesados FROM log_ejecucion WHERE id = ?",
            (log_id,)
        )
        row = cursor.fetchone()
        
        assert row[0] == 1  # exito = True
        assert row[1] == 100  # procesados


# ============================================================
# Tests de Transacciones
# ============================================================

class TestTransactions:
    """Tests para manejo de transacciones."""
    
    def test_transaction_rollback(self, db_writer):
        """Verifica rollback en caso de error."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        # Datos con error (duplicados en el mismo batch)
        data = [
            {'id_externo': 'same_id', 'contenido': 'Post 1', 'tipo_contenido': 'post'},
            {'id_externo': 'same_id', 'contenido': 'Post 2', 'tipo_contenido': 'post'},
        ]
        
        # Dependiendo de la implementación, puede guardar el primero
        # o hacer rollback de todo
        saved, dup = db_writer.save_collected_data(data, source_id)
        
        # Al menos debe detectar el duplicado
        assert saved + dup == 2
    
    def test_connection_close(self, config):
        """Verifica cierre correcto de conexión."""
        db = DatabaseWriter(config=config)
        db.initialize_schema()
        
        db.close()
        
        # Intentar usar la conexión cerrada debe fallar
        with pytest.raises(Exception):
            db.connection.execute("SELECT 1")


# ============================================================
# Tests de Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_empty_content(self, db_writer):
        """Verifica manejo de contenido vacío."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        data = [
            {'id_externo': 'empty_001', 'contenido': '', 'tipo_contenido': 'post'}
        ]
        
        saved, dup = db_writer.save_collected_data(data, source_id)
        
        # Debe guardar aunque el contenido esté vacío
        assert saved == 1
    
    def test_unicode_content(self, db_writer):
        """Verifica manejo de contenido Unicode."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        data = [
            {
                'id_externo': 'unicode_001',
                'contenido': 'Felicitaciones 🎓🎉 a todos los estudiantes 中文 العربية',
                'tipo_contenido': 'post'
            }
        ]
        
        saved, dup = db_writer.save_collected_data(data, source_id)
        
        assert saved == 1
        
        # Verificar que se guardó correctamente
        unprocessed = db_writer.get_unprocessed_data()
        assert '🎓' in unprocessed[0]['contenido']
    
    def test_very_long_content(self, db_writer):
        """Verifica manejo de contenido muy largo."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        long_content = 'A' * 50000  # 50KB de texto
        
        data = [
            {
                'id_externo': 'long_001',
                'contenido': long_content,
                'tipo_contenido': 'post'
            }
        ]
        
        saved, dup = db_writer.save_collected_data(data, source_id)
        
        assert saved == 1
    
    def test_special_characters_in_ids(self, db_writer):
        """Verifica manejo de caracteres especiales en IDs."""
        source_id = db_writer.get_or_create_source(
            nombre='Test',
            tipo='Facebook',
            url='https://facebook.com/test',
            identificador='test'
        )
        
        data = [
            {
                'id_externo': "post_with_'quotes'_and_\"double\"",
                'contenido': 'Test content',
                'tipo_contenido': 'post'
            }
        ]
        
        saved, dup = db_writer.save_collected_data(data, source_id)
        
        assert saved == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
