"""Tests for resilience patterns (circuit breaker and retry logic)."""

import asyncio
import uuid
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.config.models import CircuitBreakerConfig, RetryConfig, ResilienceConfig
from app.router.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    circuit_breaker_registry,
)
from app.router.retry import (
    RetryHandler,
    NonRetryableException,
    classify_http_exception,
    retry_registry,
)
from app.router.resilience import (
    ResilienceHandler,
    resilience_registry,
    execute_with_resilience,
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Circuit breaker configuration for testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception="Exception",
        )

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Circuit breaker instance for testing."""
        provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
        return CircuitBreaker(provider_name, circuit_breaker_config)

    @pytest.mark.asyncio
    async def test_circuit_breaker_closed_state(self, circuit_breaker):
        """Test circuit breaker in closed state."""
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
        assert not circuit_breaker.is_half_open

    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call through circuit breaker."""

        async def success_func():
            return "success"

        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, circuit_breaker):
        """Test circuit breaker opens after threshold failures."""

        async def failing_func():
            raise ConnectionError("Test failure")

        # Trigger failures up to threshold
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing_func)

        # Circuit should now be open
        assert circuit_breaker.is_open
        assert circuit_breaker.failure_count == 3

        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenException):
            await circuit_breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self, circuit_breaker):
        """Test circuit breaker recovery through half-open state."""

        async def failing_func():
            raise ConnectionError("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to half-open and succeed
        result = await circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.is_closed
        assert circuit_breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_failure(self, circuit_breaker):
        """Test circuit breaker failure in half-open state."""

        async def failing_func():
            raise ConnectionError("Test failure")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(failing_func)

        assert circuit_breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to half-open but fail
        with pytest.raises(ConnectionError):
            await circuit_breaker.call(failing_func)

        # Should be open again
        assert circuit_breaker.is_open

    def test_circuit_breaker_state_info(self, circuit_breaker):
        """Test circuit breaker state information."""
        state_info = circuit_breaker.get_state_info()

        assert state_info["provider"] == circuit_breaker.provider_name
        assert state_info["state"] == "CLOSED"
        assert state_info["failure_count"] == 0
        assert state_info["failure_threshold"] == 3
        assert state_info["recovery_timeout"] == 1.0


class TestRetryHandler:
    """Test retry handler functionality."""

    @pytest.fixture
    def retry_config(self):
        """Retry configuration for testing."""
        return RetryConfig(
            max_attempts=3,
            min_wait=0.1,
            max_wait=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable tests
        )

    @pytest.fixture
    def retry_handler(self, retry_config):
        """Retry handler instance for testing."""
        provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
        return RetryHandler(provider_name, retry_config)

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self, retry_handler):
        """Test successful call without retries."""

        async def success_func():
            return "success"

        result = await retry_handler.execute_with_retry(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_retryable_exception(self, retry_handler):
        """Test retry on retryable exceptions."""
        call_count = 0

        async def failing_then_success_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = await retry_handler.execute_with_retry(failing_then_success_func)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_exception(self, retry_handler):
        """Test no retry on non-retryable exceptions."""
        call_count = 0

        async def non_retryable_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(NonRetryableException):
            await retry_handler.execute_with_retry(non_retryable_func)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, retry_handler):
        """Test retry exhaustion after max attempts."""
        call_count = 0

        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            await retry_handler.execute_with_retry(always_failing_func)

        assert call_count == 3  # max_attempts

    def test_classify_http_exception_4xx(self):
        """Test HTTP 4xx exceptions are not retryable."""
        http_400 = HTTPException(status_code=400, detail="Bad Request")
        http_404 = HTTPException(status_code=404, detail="Not Found")

        assert not classify_http_exception(http_400)
        assert not classify_http_exception(http_404)

    def test_classify_http_exception_5xx(self):
        """Test HTTP 5xx exceptions are retryable."""
        http_500 = HTTPException(status_code=500, detail="Internal Server Error")
        http_503 = HTTPException(status_code=503, detail="Service Unavailable")

        assert classify_http_exception(http_500)
        assert classify_http_exception(http_503)

    def test_classify_network_exceptions(self):
        """Test network exceptions are retryable."""
        assert classify_http_exception(ConnectionError("Network error"))
        assert classify_http_exception(TimeoutError("Timeout"))
        assert classify_http_exception(asyncio.TimeoutError("Async timeout"))

    def test_classify_non_retryable_exceptions(self):
        """Test non-retryable exceptions."""
        assert not classify_http_exception(ValueError("Invalid value"))
        assert not classify_http_exception(TypeError("Type error"))
        assert not classify_http_exception(NonRetryableException("Non-retryable"))


class TestResilienceHandler:
    """Test resilience handler combining circuit breaker and retry."""

    @pytest.fixture
    def resilience_config(self):
        """Resilience configuration for testing."""
        return ResilienceConfig(
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.5,
            ),
            retry=RetryConfig(
                max_attempts=2,
                min_wait=0.1,
                max_wait=0.5,
                jitter=False,
            ),
        )

    @pytest.fixture
    def resilience_handler(self, resilience_config):
        """Resilience handler instance for testing."""
        provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
        return ResilienceHandler(provider_name, resilience_config)

    @pytest.mark.asyncio
    async def test_successful_execution(self, resilience_handler):
        """Test successful execution with resilience patterns."""

        async def success_func():
            return "success"

        result = await resilience_handler.execute_with_resilience(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_then_success(self, resilience_handler):
        """Test retry logic with eventual success."""
        call_count = 0

        async def failing_then_success_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            return "success"

        result = await resilience_handler.execute_with_resilience(
            failing_then_success_func
        )
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, resilience_handler):
        """Test circuit breaker opens after repeated failures."""

        async def always_failing_func():
            raise ConnectionError("Network error")

        # First call should exhaust retries and fail
        with pytest.raises(HTTPException) as exc_info:
            await resilience_handler.execute_with_resilience(always_failing_func)
        assert exc_info.value.status_code == 502

        # Second call should also exhaust retries and fail, opening circuit
        with pytest.raises(HTTPException) as exc_info:
            await resilience_handler.execute_with_resilience(always_failing_func)
        assert exc_info.value.status_code == 502

        # Third call should fail fast due to open circuit
        with pytest.raises(HTTPException) as exc_info:
            await resilience_handler.execute_with_resilience(always_failing_func)
        assert exc_info.value.status_code == 503  # Service Unavailable

    @pytest.mark.asyncio
    async def test_non_retryable_error_handling(self, resilience_handler):
        """Test non-retryable error handling."""

        async def non_retryable_func():
            raise ValueError("Invalid input")

        with pytest.raises(HTTPException) as exc_info:
            await resilience_handler.execute_with_resilience(non_retryable_func)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_http_4xx_error_handling(self, resilience_handler):
        """Test HTTP 4xx error handling."""

        async def http_4xx_func():
            raise HTTPException(status_code=400, detail="Bad Request")

        with pytest.raises(HTTPException) as exc_info:
            await resilience_handler.execute_with_resilience(http_4xx_func)

        assert exc_info.value.status_code == 400


class TestRegistries:
    """Test registry classes."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_registry(self):
        """Test circuit breaker registry."""
        config = CircuitBreakerConfig()

        # Get circuit breaker for provider
        cb1 = await circuit_breaker_registry.get_circuit_breaker("provider1", config)
        cb2 = await circuit_breaker_registry.get_circuit_breaker("provider1", config)

        # Should return same instance
        assert cb1 is cb2

        # Different provider should get different instance
        cb3 = await circuit_breaker_registry.get_circuit_breaker("provider2", config)
        assert cb1 is not cb3

    @pytest.mark.asyncio
    async def test_retry_registry(self):
        """Test retry registry."""
        config = RetryConfig()

        # Get retry handler for provider
        rh1 = await retry_registry.get_retry_handler("provider1", config)
        rh2 = await retry_registry.get_retry_handler("provider1", config)

        # Should return same instance
        assert rh1 is rh2

        # Different provider should get different instance
        rh3 = await retry_registry.get_retry_handler("provider2", config)
        assert rh1 is not rh3

    @pytest.mark.asyncio
    async def test_resilience_registry(self):
        """Test resilience registry."""
        config = ResilienceConfig()

        # Get resilience handler for provider
        rh1 = await resilience_registry.get_resilience_handler("provider1", config)
        rh2 = await resilience_registry.get_resilience_handler("provider1", config)

        # Should return same instance
        assert rh1 is rh2

        # Different provider should get different instance
        rh3 = await resilience_registry.get_resilience_handler("provider2", config)
        assert rh1 is not rh3


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.mark.asyncio
    async def test_execute_with_resilience_function(self):
        """Test execute_with_resilience convenience function."""
        provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
        config = ResilienceConfig()

        async def success_func():
            return "success"

        result = await execute_with_resilience(success_func, provider_name, config)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_resilience_failure(self):
        """Test execute_with_resilience with failure."""
        provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
        config = ResilienceConfig(
            retry=RetryConfig(max_attempts=1)  # Single attempt
        )

        async def failing_func():
            raise ConnectionError("Network error")

        with pytest.raises(HTTPException) as exc_info:
            await execute_with_resilience(failing_func, provider_name, config)

        assert exc_info.value.status_code == 502


class TestMetricsIntegration:
    """Test Prometheus metrics integration."""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Circuit breaker configuration for testing."""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=1.0,
            expected_exception="Exception",
        )

    @pytest.fixture
    def circuit_breaker(self, circuit_breaker_config):
        """Circuit breaker instance for testing."""
        return CircuitBreaker("metrics_test_provider", circuit_breaker_config)

    @pytest.fixture
    def retry_config(self):
        """Retry configuration for testing."""
        return RetryConfig(
            max_attempts=3,
            min_wait=0.1,
            max_wait=1.0,
            exponential_base=2.0,
            jitter=False,
        )

    @pytest.fixture
    def retry_handler(self, retry_config):
        """Retry handler instance for testing."""
        return RetryHandler("metrics_test_provider", retry_config)

    @pytest.fixture
    def resilience_config(self):
        """Resilience configuration for testing."""
        return ResilienceConfig(
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=0.5,
            ),
            retry=RetryConfig(
                max_attempts=2,
                min_wait=0.1,
                max_wait=0.5,
                jitter=False,
            ),
        )

    @pytest.fixture
    def resilience_handler(self, resilience_config):
        """Resilience handler instance for testing."""
        return ResilienceHandler("metrics_test_provider", resilience_config)

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics(self, circuit_breaker):
        """Test circuit breaker metrics are recorded."""
        with patch(
            "app.router.circuit_breaker.circuit_breaker_state_gauge"
        ) as mock_gauge:
            with patch(
                "app.router.circuit_breaker.circuit_breaker_calls_total"
            ) as mock_counter:

                async def success_func():
                    return "success"

                await circuit_breaker.call(success_func)

                # Verify metrics were called
                mock_gauge.labels.assert_called()
                mock_counter.labels.assert_called()

    @pytest.mark.asyncio
    async def test_retry_metrics(self, retry_handler):
        """Test retry metrics are recorded."""
        with patch("app.router.retry.retry_attempts_total") as mock_counter:
            with patch("app.router.retry.retry_duration_seconds") as mock_histogram:

                async def success_func():
                    return "success"

                await retry_handler.execute_with_retry(success_func)

                # Verify metrics were called
                mock_counter.labels.assert_called()
                mock_histogram.labels.assert_called()

    @pytest.mark.asyncio
    async def test_resilience_metrics(self, resilience_handler):
        """Test resilience metrics are recorded."""
        with patch("app.router.resilience.resilience_calls_total") as mock_counter:
            with patch(
                "app.router.resilience.resilience_duration_seconds"
            ) as mock_histogram:

                async def success_func():
                    return "success"

                await resilience_handler.execute_with_resilience(success_func)

                # Verify metrics were called
                mock_counter.labels.assert_called()
                mock_histogram.labels.assert_called()
