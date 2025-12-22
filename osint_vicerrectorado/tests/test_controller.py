"""
Tests para el controlador OSINT
Sistema OSINT EMI

Tests unitarios para OSINTController con mocks de scrapers y base de datos.

Ejecutar: pytest tests/test_controller.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Importar módulo a testear
from controllers.osint_controller import OSINTController


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def config():
    """Configuración base para tests."""
    return {
        'database': {
            'path': ':memory:',
            'type': 'sqlite'
        },
        'sources': {
            'facebook': {
                'enabled': True,
                'pages': [
                    {'name': 'EMI Oficial', 'url': 'https://facebook.com/emioficial'},
                    {'name': 'EMI UALP', 'url': 'https://facebook.com/emi.ualp'}
                ]
            },
            'tiktok': {
                'enabled': True,
                'accounts': [
                    {'name': 'EMI La Paz', 'username': 'emilapaz', 
                     'url': 'https://tiktok.com/@emilapaz'}
                ]
            }
        },
        'scheduler': {
            'collection_interval_hours': 12,
            'etl_interval_hours': 6,
            'timezone': 'America/La_Paz'
        },
        'scraping': {
            'min_delay_seconds': 0.1,
            'max_delay_seconds': 0.2,
            'max_retries': 2
        },
        'rate_limits': {
            'facebook': {'requests_per_hour': 60},
            'tiktok': {'requests_per_hour': 30}
        }
    }


@pytest.fixture
def mock_db():
    """Mock de DatabaseWriter."""
    db = Mock()
    db.initialize_schema = Mock()
    db.get_or_create_source = Mock(return_value=1)
    db.save_collected_data = Mock(return_value=(5, 2))
    db.get_statistics = Mock(return_value={
        'total_raw': 100,
        'total_processed': 80,
        'pending_etl': 20,
        'by_source': {'Facebook': 60, 'TikTok': 40}
    })
    db.get_engagement_stats_by_source = Mock(return_value=[])
    db.log_execution = Mock(return_value=1)
    db.complete_execution_log = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_scrapers():
    """Mocks para los scrapers."""
    with patch('controllers.osint_controller.FacebookScraper') as fb_mock, \
         patch('controllers.osint_controller.TikTokScraper') as tt_mock:
        
        # Mock de FacebookScraper
        fb_instance = AsyncMock()
        fb_instance.run = AsyncMock(return_value=[
            {'id_externo': 'fb_1', 'contenido': 'Post 1'},
            {'id_externo': 'fb_2', 'contenido': 'Post 2'}
        ])
        fb_instance._extract_page_id = Mock(return_value='emioficial')
        fb_mock.return_value = fb_instance
        
        # Mock de TikTokScraper
        tt_instance = AsyncMock()
        tt_instance.run = AsyncMock(return_value=[
            {'id_externo': 'tt_1', 'contenido': 'Video 1'},
            {'id_externo': 'tt_2', 'contenido': 'Video 2'}
        ])
        tt_instance.username = 'emilapaz'
        tt_mock.return_value = tt_instance
        
        yield {
            'facebook': fb_mock,
            'tiktok': tt_mock,
            'fb_instance': fb_instance,
            'tt_instance': tt_instance
        }


# ============================================================
# Tests de Inicialización
# ============================================================

class TestOSINTControllerInit:
    """Tests de inicialización del controlador."""
    
    def test_initialization(self, config, mock_db):
        """Verifica inicialización correcta."""
        controller = OSINTController(config=config, db=mock_db)
        
        assert controller.config == config
        assert controller.db == mock_db
        assert controller.scheduler_running == False
        
        controller.close()
    
    def test_scrapers_registration(self, config, mock_db):
        """Verifica registro automático de scrapers."""
        controller = OSINTController(config=config, db=mock_db)
        
        # Debe tener scrapers registrados según config
        assert len(controller.scrapers) == 3  # 2 FB + 1 TT
        
        controller.close()
    
    def test_rate_limiters_creation(self, config, mock_db):
        """Verifica creación de rate limiters."""
        controller = OSINTController(config=config, db=mock_db)
        
        assert 'facebook' in controller.rate_limiters
        assert 'tiktok' in controller.rate_limiters
        
        controller.close()
    
    def test_stats_initialization(self, config, mock_db):
        """Verifica inicialización de estadísticas."""
        controller = OSINTController(config=config, db=mock_db)
        
        assert controller.stats['total_collections'] == 0
        assert controller.stats['total_items_collected'] == 0
        assert controller.stats['last_collection'] is None
        
        controller.close()


# ============================================================
# Tests de Registro de Scrapers
# ============================================================

class TestScraperRegistration:
    """Tests para registro de scrapers."""
    
    def test_register_facebook_scraper(self, config, mock_db):
        """Verifica registro de scraper de Facebook."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.register_facebook_scraper(
            scraper_id='fb_test',
            page_url='https://facebook.com/testpage',
            page_name='Test Page'
        )
        
        assert 'fb_test' in controller.scrapers
        assert controller.scrapers['fb_test']['type'] == 'facebook'
        
        controller.close()
    
    def test_register_tiktok_scraper(self, config, mock_db):
        """Verifica registro de scraper de TikTok."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.register_tiktok_scraper(
            scraper_id='tt_test',
            profile_url='https://tiktok.com/@testuser',
            account_name='Test User'
        )
        
        assert 'tt_test' in controller.scrapers
        assert controller.scrapers['tt_test']['type'] == 'tiktok'
        
        controller.close()


# ============================================================
# Tests de Recolección
# ============================================================

class TestCollection:
    """Tests para recolección de datos."""
    
    @pytest.mark.asyncio
    async def test_trigger_collection_all(self, config, mock_db, mock_scrapers):
        """Verifica recolección de todas las fuentes."""
        controller = OSINTController(config=config, db=mock_db)
        
        results = await controller.trigger_collection(source='all', limit=10)
        
        assert results['success'] == True
        assert results['total_collected'] > 0
        
        controller.close()
    
    @pytest.mark.asyncio
    async def test_trigger_collection_single_source(self, config, mock_db, mock_scrapers):
        """Verifica recolección de una fuente específica."""
        controller = OSINTController(config=config, db=mock_db)
        
        # Obtener el ID de un scraper registrado
        scraper_id = list(controller.scrapers.keys())[0]
        
        results = await controller.trigger_collection(source=scraper_id, limit=10)
        
        assert results['success'] == True
        assert scraper_id in results['by_source']
        
        controller.close()
    
    @pytest.mark.asyncio
    async def test_trigger_collection_invalid_source(self, config, mock_db):
        """Verifica error con fuente inválida."""
        controller = OSINTController(config=config, db=mock_db)
        
        results = await controller.trigger_collection(source='invalid_source', limit=10)
        
        assert results['success'] == False
        assert len(results['errors']) > 0
        
        controller.close()
    
    @pytest.mark.asyncio
    async def test_collection_updates_stats(self, config, mock_db, mock_scrapers):
        """Verifica que la recolección actualiza estadísticas."""
        controller = OSINTController(config=config, db=mock_db)
        
        initial_collections = controller.stats['total_collections']
        
        await controller.trigger_collection(source='all', limit=5)
        
        assert controller.stats['total_collections'] > initial_collections
        assert controller.stats['last_collection'] is not None
        
        controller.close()


# ============================================================
# Tests de Estado
# ============================================================

class TestStatus:
    """Tests para obtención de estado."""
    
    def test_get_collection_status(self, config, mock_db):
        """Verifica obtención de estado."""
        controller = OSINTController(config=config, db=mock_db)
        
        status = controller.get_collection_status()
        
        assert 'scrapers_registered' in status
        assert 'scrapers' in status
        assert 'scheduler_running' in status
        assert 'global_stats' in status
        assert 'database_stats' in status
        
        controller.close()
    
    def test_get_engagement_stats(self, config, mock_db):
        """Verifica obtención de estadísticas de engagement."""
        controller = OSINTController(config=config, db=mock_db)
        
        stats = controller.get_engagement_stats()
        
        assert isinstance(stats, list)
        
        controller.close()


# ============================================================
# Tests de Scheduler
# ============================================================

class TestScheduler:
    """Tests para el scheduler."""
    
    def test_start_scheduler(self, config, mock_db):
        """Verifica inicio del scheduler."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.start_scheduler()
        
        assert controller.scheduler_running == True
        
        # Verificar jobs creados
        jobs = controller.get_scheduled_jobs()
        assert len(jobs) >= 2  # Al menos collection y ETL
        
        controller.close()
    
    def test_stop_scheduler(self, config, mock_db):
        """Verifica detención del scheduler."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.start_scheduler()
        controller.stop_scheduler()
        
        assert controller.scheduler_running == False
        
        controller.close()
    
    def test_start_scheduler_twice(self, config, mock_db):
        """Verifica que no se puede iniciar scheduler dos veces."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.start_scheduler()
        controller.start_scheduler()  # Segunda vez
        
        # Debe seguir corriendo (no error)
        assert controller.scheduler_running == True
        
        controller.close()
    
    def test_get_scheduled_jobs(self, config, mock_db):
        """Verifica obtención de jobs programados."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.start_scheduler()
        
        jobs = controller.get_scheduled_jobs()
        
        assert isinstance(jobs, list)
        for job in jobs:
            assert 'id' in job
            assert 'name' in job
            assert 'next_run' in job
        
        controller.close()


# ============================================================
# Tests de Cierre
# ============================================================

class TestClose:
    """Tests para cierre del controlador."""
    
    def test_close_stops_scheduler(self, config, mock_db):
        """Verifica que close detiene el scheduler."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.start_scheduler()
        controller.close()
        
        assert controller.scheduler_running == False
    
    def test_close_closes_db(self, config, mock_db):
        """Verifica que close cierra la BD."""
        controller = OSINTController(config=config, db=mock_db)
        
        controller.close()
        
        mock_db.close.assert_called_once()


# ============================================================
# Tests de Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_empty_sources_config(self, mock_db):
        """Verifica comportamiento sin fuentes configuradas."""
        config = {
            'sources': {},
            'scheduler': {'timezone': 'America/La_Paz'},
            'database': {'path': ':memory:'}
        }
        
        controller = OSINTController(config=config, db=mock_db)
        
        # No debe haber scrapers registrados
        assert len(controller.scrapers) == 0
        
        controller.close()
    
    def test_disabled_sources(self, config, mock_db):
        """Verifica que fuentes deshabilitadas no se registran."""
        config['sources']['facebook']['enabled'] = False
        config['sources']['tiktok']['enabled'] = False
        
        controller = OSINTController(config=config, db=mock_db)
        
        # No debe haber scrapers registrados
        assert len(controller.scrapers) == 0
        
        controller.close()
    
    @pytest.mark.asyncio
    async def test_scraper_error_handling(self, config, mock_db):
        """Verifica manejo de errores en scrapers."""
        with patch('controllers.osint_controller.FacebookScraper') as fb_mock:
            # Simular error en scraper
            fb_instance = AsyncMock()
            fb_instance.run = AsyncMock(side_effect=Exception("Scraper error"))
            fb_mock.return_value = fb_instance
            
            controller = OSINTController(config=config, db=mock_db)
            
            results = await controller.trigger_collection(source='all', limit=5)
            
            # Debe manejar el error sin crash
            assert len(results['errors']) > 0
            
            controller.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
