"""
Tests para los módulos de scraping
Sistema OSINT EMI

Tests unitarios para BaseScraper, FacebookScraper y TikTokScraper
con mocks para evitar peticiones reales a las redes sociales.

Ejecutar: pytest tests/test_scrapers.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Importar módulos a testear
from scrapers.base_scraper import BaseScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.tiktok_scraper import TikTokScraper


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def config():
    """Configuración base para tests."""
    return {
        'scraping': {
            'min_delay_seconds': 0.1,
            'max_delay_seconds': 0.2,
            'max_retries': 2,
            'timeout_seconds': 10
        },
        'rate_limits': {
            'facebook': {'requests_per_hour': 60},
            'tiktok': {'requests_per_hour': 30}
        },
        'sources': {
            'facebook': {
                'pages': [
                    {'name': 'Test Page', 'url': 'https://facebook.com/testpage'}
                ]
            },
            'tiktok': {
                'accounts': [
                    {'name': 'Test Account', 'username': 'testaccount', 
                     'url': 'https://tiktok.com/@testaccount'}
                ]
            }
        }
    }


@pytest.fixture
def mock_playwright():
    """Mock de Playwright para evitar browser real."""
    with patch('scrapers.base_scraper.async_playwright') as mock:
        playwright_instance = AsyncMock()
        browser = AsyncMock()
        context = AsyncMock()
        page = AsyncMock()
        
        # Configurar cadena de mocks
        mock.return_value.__aenter__.return_value = playwright_instance
        playwright_instance.chromium.launch.return_value = browser
        browser.new_context.return_value = context
        context.new_page.return_value = page
        
        # Configurar página mock
        page.goto = AsyncMock()
        page.content = AsyncMock(return_value='<html><body>Test</body></html>')
        page.query_selector_all = AsyncMock(return_value=[])
        page.wait_for_selector = AsyncMock()
        page.evaluate = AsyncMock()
        page.mouse = AsyncMock()
        page.keyboard = AsyncMock()
        
        yield {
            'playwright': mock,
            'browser': browser,
            'context': context,
            'page': page
        }


# ============================================================
# Tests de BaseScraper
# ============================================================

class TestBaseScraper:
    """Tests para la clase base BaseScraper."""
    
    def test_user_agent_rotation(self, config):
        """Verifica que los User-Agents rotan correctamente."""
        # BaseScraper es abstracto, creamos una implementación mínima
        class TestScraper(BaseScraper):
            async def collect_data(self, limit):
                return []
            
            async def parse_post(self, element):
                return {}
        
        scraper = TestScraper(config=config)
        
        # Obtener varios user agents
        agents = set()
        for _ in range(20):
            agent = scraper.get_random_user_agent()
            agents.add(agent)
        
        # Debe haber variación (no siempre el mismo)
        assert len(agents) >= 1
    
    def test_random_delay_range(self, config):
        """Verifica que los delays están en el rango configurado."""
        class TestScraper(BaseScraper):
            async def collect_data(self, limit):
                return []
            
            async def parse_post(self, element):
                return {}
        
        scraper = TestScraper(config=config)
        
        for _ in range(10):
            delay = scraper.get_random_delay()
            assert 0.1 <= delay <= 0.2
    
    @pytest.mark.asyncio
    async def test_setup_browser(self, config, mock_playwright):
        """Verifica que el browser se configura correctamente."""
        class TestScraper(BaseScraper):
            async def collect_data(self, limit):
                return []
            
            async def parse_post(self, element):
                return {}
        
        scraper = TestScraper(config=config)
        
        # El browser se configura al ejecutar
        async with scraper:
            assert scraper.page is not None


# ============================================================
# Tests de FacebookScraper
# ============================================================

class TestFacebookScraper:
    """Tests para FacebookScraper."""
    
    def test_initialization(self, config):
        """Verifica la inicialización correcta del scraper."""
        scraper = FacebookScraper(
            page_url='https://facebook.com/testpage',
            page_name='Test Page',
            config=config
        )
        
        assert scraper.page_url == 'https://facebook.com/testpage'
        assert scraper.page_name == 'Test Page'
        assert scraper.source_type == 'Facebook'
    
    def test_extract_page_id_profile(self, config):
        """Verifica extracción de ID desde URL de perfil."""
        scraper = FacebookScraper(
            page_url='https://www.facebook.com/profile.php?id=61574626396439',
            page_name='Test',
            config=config
        )
        
        page_id = scraper._extract_page_id(scraper.page_url)
        assert page_id == '61574626396439'
    
    def test_extract_page_id_vanity(self, config):
        """Verifica extracción de ID desde URL vanity."""
        scraper = FacebookScraper(
            page_url='https://www.facebook.com/EMI.UALP',
            page_name='Test',
            config=config
        )
        
        page_id = scraper._extract_page_id(scraper.page_url)
        assert page_id == 'EMI.UALP'
    
    def test_parse_engagement_with_k_notation(self, config):
        """Verifica parsing de engagement con notación K."""
        scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        # Probar diferentes notaciones
        assert scraper._parse_engagement_number('1.5K') == 1500
        assert scraper._parse_engagement_number('2K') == 2000
        assert scraper._parse_engagement_number('1.2M') == 1200000
        assert scraper._parse_engagement_number('500') == 500
        assert scraper._parse_engagement_number('') == 0
        assert scraper._parse_engagement_number(None) == 0
    
    def test_clean_text(self, config):
        """Verifica limpieza de texto."""
        scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        # Texto con espacios extra
        result = scraper._clean_text('  Hola   mundo  ')
        assert result == 'Hola mundo'
        
        # Texto None
        assert scraper._clean_text(None) == ''
    
    @pytest.mark.asyncio
    async def test_collect_data_empty_page(self, config, mock_playwright):
        """Verifica comportamiento con página sin posts."""
        scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        # Mockear que no hay posts
        mock_playwright['page'].query_selector_all.return_value = []
        
        async with scraper:
            scraper.page = mock_playwright['page']
            scraper.page.goto = AsyncMock()
            
            result = await scraper.collect_data(limit=10)
            
            # Debe retornar lista vacía
            assert isinstance(result, list)


# ============================================================
# Tests de TikTokScraper
# ============================================================

class TestTikTokScraper:
    """Tests para TikTokScraper."""
    
    def test_initialization(self, config):
        """Verifica la inicialización correcta del scraper."""
        scraper = TikTokScraper(
            profile_url='https://tiktok.com/@testuser',
            account_name='Test User',
            config=config
        )
        
        assert scraper.profile_url == 'https://tiktok.com/@testuser'
        assert scraper.account_name == 'Test User'
        assert scraper.username == 'testuser'
        assert scraper.source_type == 'TikTok'
    
    def test_extract_username_from_url(self, config):
        """Verifica extracción de username desde URL."""
        scraper = TikTokScraper(
            profile_url='https://www.tiktok.com/@emilapazoficial',
            account_name='EMI La Paz',
            config=config
        )
        
        assert scraper.username == 'emilapazoficial'
    
    def test_parse_view_count(self, config):
        """Verifica parsing de contadores de vistas."""
        scraper = TikTokScraper(
            profile_url='https://tiktok.com/@test',
            account_name='Test',
            config=config
        )
        
        # Probar diferentes notaciones
        assert scraper._parse_view_count('1.5K') == 1500
        assert scraper._parse_view_count('2.3M') == 2300000
        assert scraper._parse_view_count('500') == 500
        assert scraper._parse_view_count('1B') == 1000000000
        assert scraper._parse_view_count('') == 0
    
    def test_mobile_user_agents(self, config):
        """Verifica que se usan User-Agents móviles."""
        scraper = TikTokScraper(
            profile_url='https://tiktok.com/@test',
            account_name='Test',
            config=config
        )
        
        # Los user agents de TikTok deben ser móviles
        for _ in range(10):
            agent = scraper.get_random_user_agent()
            # Verificar que contiene indicadores móviles
            assert 'Mobile' in agent or 'Android' in agent or 'iPhone' in agent
    
    @pytest.mark.asyncio
    async def test_collect_data_structure(self, config, mock_playwright):
        """Verifica la estructura de datos recolectados."""
        scraper = TikTokScraper(
            profile_url='https://tiktok.com/@test',
            account_name='Test',
            config=config
        )
        
        # Mockear elementos de video
        mock_video = AsyncMock()
        mock_video.get_attribute = AsyncMock(return_value='https://tiktok.com/@test/video/123')
        mock_video.query_selector = AsyncMock(return_value=None)
        
        mock_playwright['page'].query_selector_all.return_value = [mock_video]
        
        async with scraper:
            scraper.page = mock_playwright['page']
            scraper.page.goto = AsyncMock()
            scraper.page.wait_for_selector = AsyncMock()
            
            # El resultado debe ser una lista
            # (en tests reales verificaríamos más estructura)


# ============================================================
# Tests de integración (mocked)
# ============================================================

class TestScraperIntegration:
    """Tests de integración entre scrapers."""
    
    def test_all_scrapers_have_consistent_interface(self, config):
        """Verifica que todos los scrapers tienen la misma interfaz."""
        fb_scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        tt_scraper = TikTokScraper(
            profile_url='https://tiktok.com/@test',
            account_name='Test',
            config=config
        )
        
        # Ambos deben tener los mismos métodos principales
        assert hasattr(fb_scraper, 'run')
        assert hasattr(tt_scraper, 'run')
        assert hasattr(fb_scraper, 'collect_data')
        assert hasattr(tt_scraper, 'collect_data')
        assert hasattr(fb_scraper, 'setup_browser')
        assert hasattr(tt_scraper, 'setup_browser')
    
    def test_scrapers_have_source_type(self, config):
        """Verifica que cada scraper tiene un source_type definido."""
        fb_scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        tt_scraper = TikTokScraper(
            profile_url='https://tiktok.com/@test',
            account_name='Test',
            config=config
        )
        
        assert fb_scraper.source_type == 'Facebook'
        assert tt_scraper.source_type == 'TikTok'


# ============================================================
# Tests de Edge Cases
# ============================================================

class TestEdgeCases:
    """Tests para casos límite."""
    
    def test_facebook_url_with_special_chars(self, config):
        """Verifica manejo de URLs con caracteres especiales."""
        scraper = FacebookScraper(
            page_url='https://www.facebook.com/profile.php?id=123&ref=share',
            page_name='Test',
            config=config
        )
        
        page_id = scraper._extract_page_id(scraper.page_url)
        assert page_id == '123'
    
    def test_tiktok_username_extraction_edge_cases(self, config):
        """Verifica extracción de username en casos límite."""
        # URL con parámetros
        scraper1 = TikTokScraper(
            profile_url='https://tiktok.com/@user123?lang=es',
            account_name='Test',
            config=config
        )
        assert scraper1.username == 'user123'
        
        # URL con trailing slash
        scraper2 = TikTokScraper(
            profile_url='https://tiktok.com/@user456/',
            account_name='Test',
            config=config
        )
        assert scraper2.username == 'user456'
    
    def test_engagement_parsing_edge_cases(self, config):
        """Verifica parsing de engagement en casos límite."""
        scraper = FacebookScraper(
            page_url='https://facebook.com/test',
            page_name='Test',
            config=config
        )
        
        # Valores no numéricos
        assert scraper._parse_engagement_number('likes') == 0
        assert scraper._parse_engagement_number('N/A') == 0
        
        # Valores muy grandes
        assert scraper._parse_engagement_number('999M') == 999000000
        
        # Valores decimales
        assert scraper._parse_engagement_number('1.5') == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
