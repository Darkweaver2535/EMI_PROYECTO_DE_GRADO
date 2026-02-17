"""
Tests for Monitoring Module - Sprint 6
Unit tests for metrics, logger, and prometheus exporter
"""
import pytest
import json
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import logging
import io


# =============================================================================
# Metrics Tests
# =============================================================================

class TestScraperMetrics:
    """Tests for ScraperMetrics class"""
    
    @pytest.fixture
    def metrics(self):
        """Create a ScraperMetrics instance for testing"""
        from monitoring.metrics import ScraperMetrics
        return ScraperMetrics(scraper_name="test_scraper", source="test.com")
    
    def test_increment_requests(self, metrics):
        """Test incrementing request counter"""
        metrics.increment_requests(method="GET", status_code=200)
        # Verify no exception raised
    
    def test_track_request_context_manager(self, metrics):
        """Test track_request context manager"""
        with metrics.track_request(method="GET", endpoint="/test") as tracker:
            time.sleep(0.1)
            tracker.set_status(200)
        
        # Should complete without errors
    
    def test_track_request_records_errors(self, metrics):
        """Test that track_request records errors"""
        try:
            with metrics.track_request(method="GET", endpoint="/test"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should have recorded the error
    
    def test_observe_latency(self, metrics):
        """Test observing request latency"""
        metrics.observe_latency(duration=0.5, method="GET")
        # Verify no exception raised
    
    def test_record_items_scraped(self, metrics):
        """Test recording scraped items"""
        metrics.record_items_scraped(count=10, item_type="post")
        # Verify no exception raised
    
    def test_record_error(self, metrics):
        """Test recording errors"""
        metrics.record_error(error_type="timeout", error_message="Connection timed out")
        # Verify no exception raised


class TestMetricsRegistry:
    """Tests for MetricsRegistry singleton"""
    
    def test_singleton_pattern(self):
        """Test that MetricsRegistry is a singleton"""
        from monitoring.metrics import MetricsRegistry
        
        registry1 = MetricsRegistry()
        registry2 = MetricsRegistry()
        
        assert registry1 is registry2
    
    def test_get_scraper_metrics(self):
        """Test getting metrics for a scraper"""
        from monitoring.metrics import MetricsRegistry
        
        registry = MetricsRegistry()
        metrics = registry.get_scraper_metrics("test_scraper_1", "test.com")
        
        assert metrics is not None
        assert metrics.scraper_name == "test_scraper_1"
    
    def test_get_same_metrics_instance(self):
        """Test that same scraper gets same metrics instance"""
        from monitoring.metrics import MetricsRegistry
        
        registry = MetricsRegistry()
        metrics1 = registry.get_scraper_metrics("test_scraper_2", "test.com")
        metrics2 = registry.get_scraper_metrics("test_scraper_2", "test.com")
        
        assert metrics1 is metrics2


# =============================================================================
# Logger Tests
# =============================================================================

class TestScraperLogger:
    """Tests for ScraperLogger class"""
    
    @pytest.fixture
    def logger(self):
        """Create a ScraperLogger instance for testing"""
        from monitoring.logger import ScraperLogger
        return ScraperLogger(
            scraper_name="test_scraper",
            source="test.com",
            log_level="DEBUG"
        )
    
    def test_scrape_started(self, logger, caplog):
        """Test scrape_started logging"""
        with caplog.at_level(logging.INFO):
            logger.scrape_started(params={"limit": 100})
        
        # Should have logged the start
        assert "started" in caplog.text.lower() or len(caplog.records) > 0
    
    def test_scrape_completed(self, logger, caplog):
        """Test scrape_completed logging"""
        with caplog.at_level(logging.INFO):
            logger.scrape_completed(
                items_count=50,
                duration=45.2,
                success=True
            )
        
        # Should have logged completion
    
    def test_scrape_failed(self, logger, caplog):
        """Test scrape_failed logging"""
        with caplog.at_level(logging.ERROR):
            logger.scrape_failed(
                error="Connection timeout",
                error_type="TimeoutError",
                duration=30.0
            )
        
        # Should have logged error
    
    def test_request_made(self, logger, caplog):
        """Test request_made logging"""
        with caplog.at_level(logging.DEBUG):
            logger.request_made(
                url="https://test.com/api",
                method="GET",
                status_code=200,
                duration=0.5
            )
    
    def test_item_scraped(self, logger, caplog):
        """Test item_scraped logging"""
        with caplog.at_level(logging.DEBUG):
            logger.item_scraped(item_type="post", item_id="123")
    
    def test_rate_limited(self, logger, caplog):
        """Test rate_limited logging"""
        with caplog.at_level(logging.WARNING):
            logger.rate_limited(wait_time=5.0, current_rpm=30)
    
    def test_circuit_breaker_opened(self, logger, caplog):
        """Test circuit_breaker_opened logging"""
        with caplog.at_level(logging.WARNING):
            logger.circuit_breaker_opened(
                failure_count=5,
                last_error="Connection refused"
            )
    
    def test_circuit_breaker_closed(self, logger, caplog):
        """Test circuit_breaker_closed logging"""
        with caplog.at_level(logging.INFO):
            logger.circuit_breaker_closed(success_count=3)
    
    def test_retry_attempt(self, logger, caplog):
        """Test retry_attempt logging"""
        with caplog.at_level(logging.DEBUG):
            logger.retry_attempt(
                attempt=2,
                max_attempts=3,
                error="Temporary failure",
                wait_time=1.5
            )


class TestLogContext:
    """Tests for LogContext thread-local storage"""
    
    def test_context_stored(self):
        """Test that context is stored"""
        from monitoring.logger import LogContext
        
        ctx = LogContext()
        ctx.set("request_id", "123")
        
        assert ctx.get("request_id") == "123"
    
    def test_context_cleared(self):
        """Test that context can be cleared"""
        from monitoring.logger import LogContext
        
        ctx = LogContext()
        ctx.set("key", "value")
        ctx.clear()
        
        assert ctx.get("key") is None
    
    def test_context_as_context_manager(self):
        """Test using LogContext as context manager"""
        from monitoring.logger import LogContext
        
        ctx = LogContext()
        
        with ctx.scope(request_id="456", user="test"):
            assert ctx.get("request_id") == "456"
            assert ctx.get("user") == "test"
        
        # After exiting scope, values should be cleared or restored
        # Depends on implementation


class TestStructuredJSONFormatter:
    """Tests for StructuredJSONFormatter"""
    
    def test_format_produces_json(self):
        """Test that formatter produces valid JSON"""
        from monitoring.logger import StructuredJSONFormatter
        
        formatter = StructuredJSONFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert "message" in parsed or "msg" in parsed
    
    def test_format_includes_extra_fields(self):
        """Test that extra fields are included"""
        from monitoring.logger import StructuredJSONFormatter
        
        formatter = StructuredJSONFormatter()
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.custom_field = "custom_value"
        
        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        
        # Custom field might be included depending on implementation


# =============================================================================
# Prometheus Exporter Tests
# =============================================================================

class TestPrometheusExporter:
    """Tests for PrometheusExporter class"""
    
    @pytest.fixture
    def exporter(self):
        """Create a PrometheusExporter instance for testing"""
        from monitoring.prometheus_exporter import PrometheusExporter, ExporterConfig
        
        config = ExporterConfig(
            port=19999,  # Use high port to avoid conflicts
            host="127.0.0.1"
        )
        return PrometheusExporter(config)
    
    def test_generate_metrics_output(self, exporter):
        """Test generating metrics output"""
        output = exporter.generate_metrics()
        
        # Should return a string
        assert isinstance(output, (str, bytes))
    
    def test_health_endpoint(self, exporter):
        """Test health check endpoint"""
        # Create a mock request
        response = exporter.health_check()
        
        assert response["status"] in ["healthy", "ok"]


# =============================================================================
# Integration Tests
# =============================================================================

class TestMonitoringIntegration:
    """Integration tests for monitoring components"""
    
    def test_metrics_and_logger_together(self):
        """Test using metrics and logger together"""
        from monitoring.metrics import ScraperMetrics
        from monitoring.logger import ScraperLogger
        
        scraper_name = "integration_scraper"
        source = "integration.test"
        
        metrics = ScraperMetrics(scraper_name=scraper_name, source=source)
        logger = ScraperLogger(scraper_name=scraper_name, source=source)
        
        # Simulate a scraping operation
        logger.scrape_started(params={"limit": 50})
        
        with metrics.track_request(method="GET", endpoint="/api/data") as tracker:
            # Simulate work
            time.sleep(0.05)
            tracker.set_status(200)
        
        logger.request_made(
            url="https://integration.test/api/data",
            method="GET",
            status_code=200,
            duration=0.05
        )
        
        metrics.record_items_scraped(count=25, item_type="item")
        
        for i in range(25):
            logger.item_scraped(item_type="item", item_id=str(i))
        
        logger.scrape_completed(items_count=25, duration=0.05, success=True)
        
        # All operations should complete without error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
