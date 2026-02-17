"""
Tests for Scraper Orchestrator - Sprint 6
Integration tests for concurrent scraper execution
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import List, Optional


# =============================================================================
# Mock Scraper for Testing
# =============================================================================

class MockScraper:
    """Mock scraper for testing orchestrator"""
    
    def __init__(
        self,
        name: str,
        should_fail: bool = False,
        fail_count: int = 0,
        delay: float = 0.1,
        items_to_return: int = 10
    ):
        self.name = name
        self.source = f"{name}.test"
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_fails = 0
        self.delay = delay
        self.items_to_return = items_to_return
        self.run_count = 0
        self.is_async = False
    
    def run(self) -> List[dict]:
        """Synchronous run method"""
        self.run_count += 1
        time.sleep(self.delay)
        
        if self.should_fail:
            if self.fail_count == 0 or self.current_fails < self.fail_count:
                self.current_fails += 1
                raise RuntimeError(f"Mock scraper {self.name} failed")
        
        return [{"id": i, "source": self.name} for i in range(self.items_to_return)]
    
    async def run_async(self) -> List[dict]:
        """Asynchronous run method"""
        self.run_count += 1
        await asyncio.sleep(self.delay)
        
        if self.should_fail:
            if self.fail_count == 0 or self.current_fails < self.fail_count:
                self.current_fails += 1
                raise RuntimeError(f"Mock scraper {self.name} failed")
        
        return [{"id": i, "source": self.name} for i in range(self.items_to_return)]


# =============================================================================
# Orchestrator Tests
# =============================================================================

class TestScraperOrchestrator:
    """Tests for ScraperOrchestrator class"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create an orchestrator instance for testing"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=3,
            default_interval_minutes=1,
            health_check_interval=30,
            graceful_shutdown_timeout=5
        )
        return ScraperOrchestrator(config)
    
    @pytest.fixture
    def mock_scrapers(self):
        """Create mock scrapers for testing"""
        return [
            MockScraper("scraper1", delay=0.1, items_to_return=5),
            MockScraper("scraper2", delay=0.1, items_to_return=10),
            MockScraper("scraper3", delay=0.1, items_to_return=15),
        ]
    
    def test_register_scraper(self, orchestrator):
        """Test registering a scraper"""
        scraper = MockScraper("test_scraper")
        
        orchestrator.register_scraper(
            scraper=scraper,
            interval_minutes=5,
            enabled=True
        )
        
        assert "test_scraper" in orchestrator.scrapers
    
    def test_register_multiple_scrapers(self, orchestrator, mock_scrapers):
        """Test registering multiple scrapers"""
        for scraper in mock_scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        assert len(orchestrator.scrapers) == 3
    
    def test_unregister_scraper(self, orchestrator):
        """Test unregistering a scraper"""
        scraper = MockScraper("to_remove")
        orchestrator.register_scraper(scraper=scraper)
        
        orchestrator.unregister_scraper("to_remove")
        
        assert "to_remove" not in orchestrator.scrapers
    
    def test_run_single_scraper(self, orchestrator):
        """Test running a single scraper"""
        scraper = MockScraper("single", delay=0.05, items_to_return=5)
        orchestrator.register_scraper(scraper=scraper)
        
        result = orchestrator.run_scraper("single")
        
        assert result.success is True
        assert result.items_count == 5
        assert scraper.run_count == 1
    
    def test_run_all_scrapers(self, orchestrator, mock_scrapers):
        """Test running all scrapers"""
        for scraper in mock_scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        results = orchestrator.run_all()
        
        assert len(results) == 3
        assert all(r.success for r in results)
        total_items = sum(r.items_count for r in results)
        assert total_items == 30  # 5 + 10 + 15
    
    def test_handles_scraper_failure(self, orchestrator):
        """Test handling scraper failure"""
        scraper = MockScraper("failing", should_fail=True)
        orchestrator.register_scraper(scraper=scraper)
        
        result = orchestrator.run_scraper("failing")
        
        assert result.success is False
        assert result.error is not None
    
    def test_partial_failures(self, orchestrator):
        """Test that partial failures don't stop other scrapers"""
        scrapers = [
            MockScraper("success1", delay=0.05, items_to_return=5),
            MockScraper("failing", should_fail=True, delay=0.05),
            MockScraper("success2", delay=0.05, items_to_return=5),
        ]
        
        for scraper in scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        results = orchestrator.run_all()
        
        assert len(results) == 3
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        
        assert len(successes) == 2
        assert len(failures) == 1
    
    def test_respects_concurrency_limit(self, orchestrator):
        """Test that concurrency limit is respected"""
        # Create more scrapers than concurrency limit
        scrapers = [MockScraper(f"scraper_{i}", delay=0.2) for i in range(6)]
        
        for scraper in scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        # Track concurrent executions
        max_concurrent = [0]
        current_concurrent = [0]
        original_run = MockScraper.run
        
        def tracking_run(self):
            current_concurrent[0] += 1
            max_concurrent[0] = max(max_concurrent[0], current_concurrent[0])
            try:
                return original_run(self)
            finally:
                current_concurrent[0] -= 1
        
        with patch.object(MockScraper, 'run', tracking_run):
            orchestrator.run_all()
        
        # Should not exceed max concurrent limit
        assert max_concurrent[0] <= orchestrator.config.max_concurrent_scrapers
    
    def test_pause_scraper(self, orchestrator):
        """Test pausing a scraper"""
        scraper = MockScraper("pausable")
        orchestrator.register_scraper(scraper=scraper)
        
        orchestrator.pause_scraper("pausable")
        
        task = orchestrator.scrapers["pausable"]
        assert task.paused is True
    
    def test_resume_scraper(self, orchestrator):
        """Test resuming a scraper"""
        scraper = MockScraper("resumable")
        orchestrator.register_scraper(scraper=scraper)
        
        orchestrator.pause_scraper("resumable")
        orchestrator.resume_scraper("resumable")
        
        task = orchestrator.scrapers["resumable"]
        assert task.paused is False
    
    def test_paused_scraper_skipped_in_run_all(self, orchestrator):
        """Test that paused scrapers are skipped"""
        scrapers = [
            MockScraper("active", delay=0.05),
            MockScraper("paused", delay=0.05),
        ]
        
        for scraper in scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        orchestrator.pause_scraper("paused")
        
        results = orchestrator.run_all()
        
        # Only active scraper should run
        assert len(results) == 1
        assert results[0].scraper_name == "active"
    
    def test_get_stats(self, orchestrator, mock_scrapers):
        """Test getting orchestrator stats"""
        for scraper in mock_scrapers:
            orchestrator.register_scraper(scraper=scraper)
        
        # Run all scrapers
        orchestrator.run_all()
        
        stats = orchestrator.get_stats()
        
        assert stats.total_runs == 3
        assert stats.successful_runs == 3
        assert stats.failed_runs == 0
        assert stats.total_items_scraped == 30
    
    def test_get_scraper_status(self, orchestrator):
        """Test getting individual scraper status"""
        scraper = MockScraper("status_test", items_to_return=5)
        orchestrator.register_scraper(scraper=scraper)
        
        # Run the scraper
        orchestrator.run_scraper("status_test")
        
        status = orchestrator.get_scraper_status("status_test")
        
        assert status is not None
        assert status["name"] == "status_test"
        assert status["total_runs"] == 1
        assert status["last_success"] is not None


# =============================================================================
# Async Orchestrator Tests
# =============================================================================

class TestAsyncOrchestrator:
    """Tests for async orchestrator functionality"""
    
    @pytest.fixture
    def async_orchestrator(self):
        """Create an async orchestrator instance"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=3,
            use_async=True
        )
        return ScraperOrchestrator(config)
    
    @pytest.mark.asyncio
    async def test_async_run_single(self, async_orchestrator):
        """Test async run of single scraper"""
        scraper = MockScraper("async_single", delay=0.05)
        scraper.is_async = True
        async_orchestrator.register_scraper(scraper=scraper)
        
        result = await async_orchestrator.run_scraper_async("async_single")
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_async_run_all(self, async_orchestrator):
        """Test async run of all scrapers"""
        scrapers = [
            MockScraper(f"async_{i}", delay=0.1, items_to_return=i+1)
            for i in range(3)
        ]
        
        for scraper in scrapers:
            scraper.is_async = True
            async_orchestrator.register_scraper(scraper=scraper)
        
        results = await async_orchestrator.run_all_async()
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_async_concurrent_execution(self, async_orchestrator):
        """Test that async scrapers run concurrently"""
        # Create scrapers with measurable delay
        scrapers = [
            MockScraper(f"concurrent_{i}", delay=0.2)
            for i in range(3)
        ]
        
        for scraper in scrapers:
            scraper.is_async = True
            async_orchestrator.register_scraper(scraper=scraper)
        
        start = time.time()
        await async_orchestrator.run_all_async()
        elapsed = time.time() - start
        
        # If running concurrently, should take ~0.2s, not ~0.6s
        assert elapsed < 0.5


# =============================================================================
# Scheduling Tests
# =============================================================================

class TestOrchestratorScheduling:
    """Tests for orchestrator scheduling functionality"""
    
    @pytest.fixture
    def scheduled_orchestrator(self):
        """Create orchestrator for scheduling tests"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=2,
            default_interval_minutes=0.01  # Very short for testing
        )
        return ScraperOrchestrator(config)
    
    def test_schedule_scraper(self, scheduled_orchestrator):
        """Test scheduling a scraper"""
        scraper = MockScraper("scheduled")
        
        scheduled_orchestrator.register_scraper(
            scraper=scraper,
            interval_minutes=5,
            enabled=True
        )
        
        task = scheduled_orchestrator.scrapers["scheduled"]
        assert task.interval_minutes == 5
        assert task.enabled is True
    
    def test_get_next_run_time(self, scheduled_orchestrator):
        """Test getting next scheduled run time"""
        scraper = MockScraper("next_run")
        
        scheduled_orchestrator.register_scraper(
            scraper=scraper,
            interval_minutes=10
        )
        
        # Run once
        scheduled_orchestrator.run_scraper("next_run")
        
        next_run = scheduled_orchestrator.get_next_run_time("next_run")
        
        assert next_run is not None
        # Next run should be in the future
        assert next_run > datetime.now()


# =============================================================================
# Health Check Tests
# =============================================================================

class TestOrchestratorHealthChecks:
    """Tests for orchestrator health check functionality"""
    
    @pytest.fixture
    def health_orchestrator(self):
        """Create orchestrator for health check tests"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=3,
            health_check_interval=1
        )
        return ScraperOrchestrator(config)
    
    def test_health_check_healthy(self, health_orchestrator):
        """Test health check when all scrapers healthy"""
        scrapers = [MockScraper(f"healthy_{i}") for i in range(3)]
        
        for scraper in scrapers:
            health_orchestrator.register_scraper(scraper=scraper)
        
        # Run all successfully
        health_orchestrator.run_all()
        
        health = health_orchestrator.health_check()
        
        assert health["status"] == "healthy"
        assert health["scrapers"]["healthy"] == 3
    
    def test_health_check_degraded(self, health_orchestrator):
        """Test health check when some scrapers failing"""
        scrapers = [
            MockScraper("good1"),
            MockScraper("bad", should_fail=True),
            MockScraper("good2"),
        ]
        
        for scraper in scrapers:
            health_orchestrator.register_scraper(scraper=scraper)
        
        health_orchestrator.run_all()
        
        health = health_orchestrator.health_check()
        
        # Status should be degraded or unhealthy
        assert health["status"] in ["degraded", "unhealthy"]


# =============================================================================
# Error Recovery Tests
# =============================================================================

class TestOrchestratorErrorRecovery:
    """Tests for orchestrator error recovery"""
    
    @pytest.fixture
    def recovery_orchestrator(self):
        """Create orchestrator for recovery tests"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=2,
            max_consecutive_failures=3
        )
        return ScraperOrchestrator(config)
    
    def test_tracks_consecutive_failures(self, recovery_orchestrator):
        """Test that consecutive failures are tracked"""
        scraper = MockScraper("failing", should_fail=True)
        recovery_orchestrator.register_scraper(scraper=scraper)
        
        # Run multiple times
        for _ in range(3):
            recovery_orchestrator.run_scraper("failing")
        
        task = recovery_orchestrator.scrapers["failing"]
        assert task.consecutive_failures == 3
    
    def test_resets_failures_on_success(self, recovery_orchestrator):
        """Test that consecutive failures reset on success"""
        scraper = MockScraper("recovering", should_fail=True, fail_count=2)
        recovery_orchestrator.register_scraper(scraper=scraper)
        
        # First two runs fail
        recovery_orchestrator.run_scraper("recovering")
        recovery_orchestrator.run_scraper("recovering")
        
        task = recovery_orchestrator.scrapers["recovering"]
        assert task.consecutive_failures == 2
        
        # Third run succeeds
        recovery_orchestrator.run_scraper("recovering")
        
        assert task.consecutive_failures == 0


# =============================================================================
# Configuration Tests
# =============================================================================

class TestOrchestratorConfig:
    """Tests for OrchestratorConfig"""
    
    def test_default_config(self):
        """Test default configuration values"""
        from orchestrator.scraper_orchestrator import OrchestratorConfig
        
        config = OrchestratorConfig()
        
        assert config.max_concurrent_scrapers > 0
        assert config.default_interval_minutes > 0
    
    def test_custom_config(self):
        """Test custom configuration"""
        from orchestrator.scraper_orchestrator import OrchestratorConfig
        
        config = OrchestratorConfig(
            max_concurrent_scrapers=10,
            default_interval_minutes=30,
            health_check_interval=120,
            graceful_shutdown_timeout=60
        )
        
        assert config.max_concurrent_scrapers == 10
        assert config.default_interval_minutes == 30
        assert config.health_check_interval == 120
        assert config.graceful_shutdown_timeout == 60


# =============================================================================
# Integration with Resilience
# =============================================================================

class TestOrchestratorResilienceIntegration:
    """Tests for orchestrator integration with resilience components"""
    
    def test_circuit_breaker_integration(self):
        """Test that circuit breaker is used"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            use_circuit_breaker=True,
            circuit_breaker_threshold=2
        )
        orchestrator = ScraperOrchestrator(config)
        
        scraper = MockScraper("cb_test", should_fail=True)
        orchestrator.register_scraper(scraper=scraper)
        
        # Run until circuit breaker trips
        for _ in range(5):
            orchestrator.run_scraper("cb_test")
        
        # Check if circuit breaker opened
        status = orchestrator.get_scraper_status("cb_test")
        
        # Should have circuit breaker info
        assert "circuit_breaker" in status or status.get("circuit_open") is not None
    
    def test_rate_limiter_integration(self):
        """Test that rate limiter is used"""
        from orchestrator.scraper_orchestrator import ScraperOrchestrator, OrchestratorConfig
        
        config = OrchestratorConfig(
            use_rate_limiter=True,
            default_rpm=60
        )
        orchestrator = ScraperOrchestrator(config)
        
        scraper = MockScraper("rl_test")
        orchestrator.register_scraper(
            scraper=scraper,
            rate_limit_rpm=120
        )
        
        status = orchestrator.get_scraper_status("rl_test")
        
        # Should have rate limiter info
        assert "rate_limiter" in status or "current_rpm" in str(status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
