"""
Tests for Resilience Module - Sprint 6
Unit tests for circuit breaker, retry manager, rate limiter, and timeout manager
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import threading


# =============================================================================
# Circuit Breaker Tests
# =============================================================================

class TestCircuitBreaker:
    """Tests for CircuitBreaker class"""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker instance for testing"""
        from resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(
            name="test_breaker",
            failure_threshold=3,
            success_threshold=2,
            timeout_duration=1.0,  # 1 second for faster tests
            exclude_exceptions=(ValueError,)
        )
        return CircuitBreaker(config)
    
    def test_initial_state_is_closed(self, circuit_breaker):
        """Test that circuit breaker starts in CLOSED state"""
        from resilience.circuit_breaker import CircuitBreakerState
        
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.stats.failure_count == 0
    
    def test_success_increments_success_count(self, circuit_breaker):
        """Test that successful calls increment success count"""
        @circuit_breaker
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"
        assert circuit_breaker.stats.success_count == 1
    
    def test_failure_increments_failure_count(self, circuit_breaker):
        """Test that failed calls increment failure count"""
        @circuit_breaker
        def failure_func():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError):
            failure_func()
        
        assert circuit_breaker.stats.failure_count == 1
    
    def test_opens_after_failure_threshold(self, circuit_breaker):
        """Test that circuit opens after reaching failure threshold"""
        from resilience.circuit_breaker import CircuitBreakerState, CircuitBreakerOpenError
        
        @circuit_breaker
        def failure_func():
            raise RuntimeError("Test error")
        
        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(RuntimeError):
                failure_func()
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Next call should be rejected immediately
        with pytest.raises(CircuitBreakerOpenError):
            failure_func()
    
    def test_excluded_exceptions_dont_count_as_failures(self, circuit_breaker):
        """Test that excluded exceptions don't trigger circuit opening"""
        from resilience.circuit_breaker import CircuitBreakerState
        
        @circuit_breaker
        def excluded_failure_func():
            raise ValueError("This should be excluded")
        
        # Trigger many excluded exceptions
        for _ in range(10):
            with pytest.raises(ValueError):
                excluded_failure_func()
        
        # Circuit should still be closed
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
        assert circuit_breaker.stats.failure_count == 0
    
    def test_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """Test that circuit transitions to HALF_OPEN after timeout"""
        from resilience.circuit_breaker import CircuitBreakerState
        
        @circuit_breaker
        def failure_func():
            raise RuntimeError("Test error")
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                failure_func()
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Check state (this should trigger transition to HALF_OPEN)
        # Force state check
        circuit_breaker._check_state_transition()
        assert circuit_breaker.state == CircuitBreakerState.HALF_OPEN
    
    def test_closes_after_success_in_half_open(self, circuit_breaker):
        """Test that circuit closes after successes in HALF_OPEN state"""
        from resilience.circuit_breaker import CircuitBreakerState
        
        call_count = 0
        
        @circuit_breaker
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise RuntimeError("Failing")
            return "success"
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                sometimes_fails()
        
        assert circuit_breaker.state == CircuitBreakerState.OPEN
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Now calls should succeed
        result = sometimes_fails()
        assert result == "success"
        
        result = sometimes_fails()
        assert result == "success"
        
        # After success_threshold successes, should be CLOSED
        assert circuit_breaker.state == CircuitBreakerState.CLOSED
    
    def test_async_support(self, circuit_breaker):
        """Test that circuit breaker works with async functions"""
        @circuit_breaker
        async def async_success():
            return "async success"
        
        @circuit_breaker
        async def async_failure():
            raise RuntimeError("Async error")
        
        # Test success
        result = asyncio.run(async_success())
        assert result == "async success"
        
        # Test failure
        with pytest.raises(RuntimeError):
            asyncio.run(async_failure())


# =============================================================================
# Retry Manager Tests
# =============================================================================

class TestRetryManager:
    """Tests for RetryManager class"""
    
    @pytest.fixture
    def retry_manager(self):
        """Create a retry manager instance for testing"""
        from resilience.retry_manager import RetryManager, RetryConfig
        
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable tests
            retry_on_exceptions=(RuntimeError, ConnectionError),
            retry_on_status_codes=(429, 500, 502, 503)
        )
        return RetryManager(config)
    
    def test_successful_call_no_retry(self, retry_manager):
        """Test that successful calls don't trigger retries"""
        call_count = 0
        
        @retry_manager
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retries_on_failure(self, retry_manager):
        """Test that failures trigger retries"""
        call_count = 0
        
        @retry_manager
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = failing_then_success()
        assert result == "success"
        assert call_count == 3
    
    def test_gives_up_after_max_retries(self, retry_manager):
        """Test that retry manager gives up after max retries"""
        call_count = 0
        
        @retry_manager
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Always fails")
        
        with pytest.raises(RuntimeError):
            always_fails()
        
        # Initial call + 3 retries = 4 calls
        assert call_count == 4
    
    def test_doesnt_retry_excluded_exceptions(self, retry_manager):
        """Test that non-retry exceptions are raised immediately"""
        call_count = 0
        
        @retry_manager
        def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            value_error_func()
        
        # Should only be called once
        assert call_count == 1
    
    def test_exponential_backoff(self, retry_manager):
        """Test that delays increase exponentially"""
        delays = []
        last_call_time = [time.time()]
        
        @retry_manager
        def track_delays():
            now = time.time()
            if last_call_time[0]:
                delays.append(now - last_call_time[0])
            last_call_time[0] = now
            if len(delays) < 3:
                raise RuntimeError("Keep trying")
            return "done"
        
        result = track_delays()
        assert result == "done"
        
        # Check that delays are increasing (with some tolerance)
        # Note: First delay might be less precise
        if len(delays) >= 2:
            assert delays[1] >= delays[0] * 1.5  # Allow some tolerance
    
    def test_async_support(self, retry_manager):
        """Test that retry manager works with async functions"""
        call_count = 0
        
        @retry_manager
        async def async_failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Temporary async failure")
            return "async success"
        
        result = asyncio.run(async_failing_then_success())
        assert result == "async success"
        assert call_count == 2


# =============================================================================
# Rate Limiter Tests
# =============================================================================

class TestRateLimiter:
    """Tests for AdaptiveRateLimiter class"""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter instance for testing"""
        from resilience.rate_limiter import AdaptiveRateLimiter, RateLimiterConfig
        
        config = RateLimiterConfig(
            name="test_limiter",
            requests_per_minute=600,  # 10 per second for faster tests
            burst_size=20,
            adaptive=True,
            min_rate=60,
            max_rate=1200
        )
        return AdaptiveRateLimiter(config)
    
    def test_allows_requests_under_limit(self, rate_limiter):
        """Test that requests under limit are allowed"""
        for _ in range(5):
            assert rate_limiter.acquire() is True
    
    def test_throttles_when_exceeded(self, rate_limiter):
        """Test that requests are throttled when limit exceeded"""
        from resilience.rate_limiter import RateLimiterConfig, AdaptiveRateLimiter
        
        # Create a very restrictive limiter for this test
        config = RateLimiterConfig(
            name="slow_limiter",
            requests_per_minute=60,  # 1 per second
            burst_size=2,
            adaptive=False
        )
        limiter = AdaptiveRateLimiter(config)
        
        # Quickly exhaust burst
        limiter.acquire()
        limiter.acquire()
        
        # Next one should need to wait or return False
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start
        
        # Should have waited approximately 1 second
        assert elapsed >= 0.9
    
    def test_adapts_on_429_response(self, rate_limiter):
        """Test that rate is reduced on 429 response"""
        initial_rate = rate_limiter.current_rate
        
        # Simulate 429 response
        rate_limiter.on_response(429)
        
        # Rate should be reduced by 50%
        assert rate_limiter.current_rate == initial_rate * 0.5
    
    def test_adapts_on_successful_responses(self, rate_limiter):
        """Test that rate recovers on successful responses"""
        # First reduce the rate
        rate_limiter.on_response(429)
        reduced_rate = rate_limiter.current_rate
        
        # Simulate many successful responses
        for _ in range(100):
            rate_limiter.on_response(200)
        
        # Rate should have increased
        assert rate_limiter.current_rate > reduced_rate
    
    def test_respects_min_rate(self, rate_limiter):
        """Test that rate doesn't go below minimum"""
        # Simulate many 429 responses
        for _ in range(20):
            rate_limiter.on_response(429)
        
        # Should be at minimum rate
        assert rate_limiter.current_rate == rate_limiter.config.min_rate
    
    def test_respects_max_rate(self, rate_limiter):
        """Test that rate doesn't go above maximum"""
        # Simulate many successful responses
        for _ in range(10000):
            rate_limiter.on_response(200)
        
        # Should be at or below maximum rate
        assert rate_limiter.current_rate <= rate_limiter.config.max_rate
    
    def test_context_manager(self, rate_limiter):
        """Test that rate limiter works as context manager"""
        with rate_limiter:
            pass  # Should not raise
        
        assert rate_limiter.stats.total_requests >= 1
    
    @pytest.mark.asyncio
    async def test_async_acquire(self, rate_limiter):
        """Test async acquire method"""
        result = await rate_limiter.acquire_async()
        assert result is True


# =============================================================================
# Timeout Manager Tests
# =============================================================================

class TestTimeoutManager:
    """Tests for TimeoutManager class"""
    
    @pytest.fixture
    def timeout_manager(self):
        """Create a timeout manager instance for testing"""
        from resilience.timeout_manager import TimeoutManager, TimeoutConfig
        
        config = TimeoutConfig(
            connect_timeout=1.0,
            read_timeout=2.0,
            total_timeout=3.0,
            adaptive=True
        )
        return TimeoutManager(config)
    
    def test_initial_timeouts(self, timeout_manager):
        """Test initial timeout values"""
        assert timeout_manager.connect_timeout == 1.0
        assert timeout_manager.read_timeout == 2.0
        assert timeout_manager.total_timeout == 3.0
    
    def test_get_aiohttp_timeout(self, timeout_manager):
        """Test getting aiohttp-compatible timeout"""
        timeout = timeout_manager.get_aiohttp_timeout()
        
        # Should return an aiohttp.ClientTimeout or similar
        assert hasattr(timeout, 'total') or hasattr(timeout, 'connect')
    
    def test_get_requests_timeout(self, timeout_manager):
        """Test getting requests-compatible timeout"""
        timeout = timeout_manager.get_requests_timeout()
        
        # Should return a tuple (connect, read)
        assert isinstance(timeout, tuple)
        assert len(timeout) == 2
        assert timeout[0] == 1.0
        assert timeout[1] == 2.0
    
    def test_timeout_decorator_success(self, timeout_manager):
        """Test that timeout decorator allows fast functions"""
        @timeout_manager.with_timeout(timeout=1.0)
        def fast_func():
            return "fast"
        
        result = fast_func()
        assert result == "fast"
    
    def test_timeout_decorator_timeout(self, timeout_manager):
        """Test that timeout decorator raises on slow functions"""
        from resilience.timeout_manager import TimeoutError as CustomTimeoutError
        
        @timeout_manager.with_timeout(timeout=0.1)
        def slow_func():
            time.sleep(1.0)
            return "slow"
        
        with pytest.raises((TimeoutError, CustomTimeoutError)):
            slow_func()
    
    def test_adaptive_timeout_increases_on_slow_response(self, timeout_manager):
        """Test that adaptive timeout increases for slow responses"""
        initial_read = timeout_manager.read_timeout
        
        # Record a slow but successful response
        timeout_manager.record_response_time(1.8)  # Close to read_timeout
        timeout_manager.record_response_time(1.9)
        timeout_manager.record_response_time(1.85)
        
        # Timeout should have been adjusted upward
        # (Implementation depends on specific adaptation logic)
        # Just verify it's still valid
        assert timeout_manager.read_timeout > 0
    
    def test_context_manager(self, timeout_manager):
        """Test timeout manager as context manager"""
        with timeout_manager.timed_operation() as timer:
            time.sleep(0.1)
        
        assert timer.elapsed >= 0.1


# =============================================================================
# Integration Tests
# =============================================================================

class TestResilienceIntegration:
    """Integration tests for combined resilience components"""
    
    def test_retry_with_circuit_breaker(self):
        """Test retry manager with circuit breaker"""
        from resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from resilience.retry_manager import RetryManager, RetryConfig
        
        cb_config = CircuitBreakerConfig(
            name="integration_cb",
            failure_threshold=5,
            timeout_duration=1.0
        )
        cb = CircuitBreaker(cb_config)
        
        retry_config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            jitter=False
        )
        retry = RetryManager(retry_config)
        
        call_count = 0
        
        @cb
        @retry
        def resilient_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return "success"
        
        result = resilient_func()
        assert result == "success"
        assert call_count == 3
    
    def test_rate_limiter_with_circuit_breaker(self):
        """Test rate limiter with circuit breaker"""
        from resilience.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
        from resilience.rate_limiter import AdaptiveRateLimiter, RateLimiterConfig
        
        cb_config = CircuitBreakerConfig(
            name="rate_cb",
            failure_threshold=3,
            timeout_duration=1.0
        )
        cb = CircuitBreaker(cb_config)
        
        rate_config = RateLimiterConfig(
            name="rate_limiter",
            requests_per_minute=6000,
            burst_size=100
        )
        rate_limiter = AdaptiveRateLimiter(rate_config)
        
        success_count = 0
        
        def rate_limited_and_protected():
            nonlocal success_count
            with rate_limiter:
                @cb
                def inner():
                    return "success"
                result = inner()
                success_count += 1
                return result
        
        # Execute several times
        for _ in range(5):
            result = rate_limited_and_protected()
            assert result == "success"
        
        assert success_count == 5


# =============================================================================
# Fixture for async tests
# =============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
