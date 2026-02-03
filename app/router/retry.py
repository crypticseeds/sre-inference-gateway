"""Retry logic with exponential backoff and jitter."""

import asyncio
import logging
from typing import Any, Callable

from fastapi import HTTPException
from prometheus_client import Counter, Histogram
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from app.config.models import RetryConfig

logger = logging.getLogger(__name__)

# Prometheus metrics
retry_attempts_total = Counter(
    "retry_attempts_total",
    "Total number of retry attempts",
    ["provider", "attempt"],
)
retry_failures_total = Counter(
    "retry_failures_total",
    "Total number of retry failures",
    ["provider", "exception_type"],
)
retry_successes_total = Counter(
    "retry_successes_total",
    "Total number of retry successes after retries",
    ["provider"],
)
retry_duration_seconds = Histogram(
    "retry_duration_seconds",
    "Time spent in retry logic",
    ["provider"],
)


class RetryableException(Exception):
    """Base class for retryable exceptions."""

    pass


class NonRetryableException(Exception):
    """Base class for non-retryable exceptions."""

    def __init__(self, message: str, status_code: int = 500):
        """Initialize non-retryable exception.

        Args:
            message: Exception message
            status_code: HTTP status code to use when converting to HTTPException
        """
        super().__init__(message)
        self.status_code = status_code


def classify_http_exception(exception: Exception) -> bool:
    """Classify HTTP exceptions as retryable or not.

    Args:
        exception: Exception to classify

    Returns:
        True if exception is retryable, False otherwise
    """
    if isinstance(exception, HTTPException):
        # Special cases: 429 (Too Many Requests) and 408 (Request Timeout) are retryable
        if exception.status_code in (429, 408):
            return True
        # Other 4xx errors are client errors and should not be retried
        if 400 <= exception.status_code < 500:
            return False
        # 5xx errors are server errors and can be retried
        if 500 <= exception.status_code < 600:
            return True

    # Network-related exceptions that should be retried
    retryable_exceptions = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        RetryableException,
    )

    # Non-retryable exceptions
    non_retryable_exceptions = (
        ValueError,
        TypeError,
        NonRetryableException,
    )

    if isinstance(exception, non_retryable_exceptions):
        return False

    if isinstance(exception, retryable_exceptions):
        return True

    # Default: do not retry unknown exceptions (safe default for non-idempotent operations)
    return False


class RetryHandler:
    """Async retry handler with exponential backoff and jitter."""

    def __init__(self, provider_name: str, config: RetryConfig):
        """Initialize retry handler.

        Args:
            provider_name: Name of the provider this handler is for
            config: Retry configuration
        """
        self.provider_name = provider_name
        self.config = config

        # Create wait strategy with jitter
        if config.jitter:
            wait_strategy = wait_exponential(
                exp_base=config.exponential_base,
                min=config.min_wait,
                max=config.max_wait,
            )
        else:
            # Custom wait strategy without jitter
            wait_strategy = self._wait_exponential_no_jitter

        # Create retry strategy
        self.retry_strategy = AsyncRetrying(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_strategy,
            retry=self._should_retry,  # Use custom retry condition
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

        logger.info(
            f"Retry handler initialized for provider {provider_name} "
            f"with max_attempts={config.max_attempts}, "
            f"min_wait={config.min_wait}, max_wait={config.max_wait}, "
            f"exponential_base={config.exponential_base}, jitter={config.jitter}"
        )

    def _should_retry(self, retry_state) -> bool:
        """Determine if an exception should be retried.

        Args:
            retry_state: Tenacity retry state

        Returns:
            True if the exception should be retried
        """
        if retry_state.outcome is None:
            return False

        exception = retry_state.outcome.exception()
        if exception is None:
            return False

        return classify_http_exception(exception)

    def _wait_exponential_no_jitter(self, retry_state) -> float:
        """Custom wait strategy without jitter.

        Args:
            retry_state: Tenacity retry state

        Returns:
            Wait time in seconds
        """
        attempt_number = retry_state.attempt_number
        wait_time = min(
            self.config.min_wait
            * (self.config.exponential_base ** (attempt_number - 1)),
            self.config.max_wait,
        )
        return wait_time

    async def execute_with_retry(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            Exception: Final exception after all retries exhausted
        """
        start_time = asyncio.get_event_loop().time()

        try:
            async for attempt in self.retry_strategy:
                with attempt:
                    # Record attempt
                    retry_attempts_total.labels(
                        provider=self.provider_name,
                        attempt=str(attempt.retry_state.attempt_number),
                    ).inc()

                    try:
                        if asyncio.iscoroutinefunction(func):
                            result = await func(*args, **kwargs)
                        else:
                            result = func(*args, **kwargs)

                        # Success - record metrics
                        if attempt.retry_state.attempt_number > 1:
                            retry_successes_total.labels(
                                provider=self.provider_name
                            ).inc()
                            logger.info(
                                f"Retry succeeded for {self.provider_name} "
                                f"after {attempt.retry_state.attempt_number} attempts"
                            )

                        return result

                    except Exception as e:
                        # Check if exception should be retried
                        if not classify_http_exception(e):
                            logger.info(
                                f"Non-retryable exception for {self.provider_name}: {e}"
                            )
                            retry_failures_total.labels(
                                provider=self.provider_name,
                                exception_type=type(e).__name__,
                            ).inc()

                            # Determine appropriate status code
                            status_code = 500  # Default
                            if isinstance(e, HTTPException):
                                status_code = e.status_code
                            elif isinstance(e, (ValueError, TypeError)):
                                status_code = 400

                            raise NonRetryableException(
                                f"Non-retryable error: {e}", status_code=status_code
                            ) from e

                        logger.warning(
                            f"Retryable exception for {self.provider_name} "
                            f"(attempt {attempt.retry_state.attempt_number}): {e}"
                        )

                        # Re-raise to trigger retry
                        raise

        except RetryError as e:
            # All retries exhausted
            retry_failures_total.labels(
                provider=self.provider_name,
                exception_type=type(e.last_attempt.exception()).__name__,
            ).inc()

            logger.error(
                f"All retries exhausted for {self.provider_name} "
                f"after {self.config.max_attempts} attempts: "
                f"{e.last_attempt.exception()}"
            )

            # Guard against None exception
            exc = e.last_attempt.exception()
            if exc is None:
                raise RuntimeError(
                    f"Retry failed for {self.provider_name} after "
                    f"{self.config.max_attempts} attempts with no exception details"
                ) from e

            # Re-raise the original exception
            raise exc

        finally:
            # Record total duration
            duration = asyncio.get_event_loop().time() - start_time
            retry_duration_seconds.labels(provider=self.provider_name).observe(duration)


class RetryRegistry:
    """Registry for managing retry handlers per provider."""

    def __init__(self):
        """Initialize retry registry."""
        self._retry_handlers: dict[str, RetryHandler] = {}
        self._lock = asyncio.Lock()

    async def get_retry_handler(
        self, provider_name: str, config: RetryConfig
    ) -> RetryHandler:
        """Get or create retry handler for provider.

        Args:
            provider_name: Name of the provider
            config: Retry configuration

        Returns:
            Retry handler instance
        """
        async with self._lock:
            if provider_name in self._retry_handlers:
                existing_handler = self._retry_handlers[provider_name]
                # Compare configs to detect changes
                if existing_handler.config != config:
                    logger.warning(
                        f"Retry config changed for provider {provider_name}. "
                        f"Old config: {existing_handler.config}, New config: {config}. "
                        f"Recreating handler with new configuration."
                    )
                    # Recreate handler with new config
                    self._retry_handlers[provider_name] = RetryHandler(
                        provider_name, config
                    )
                    logger.info(
                        f"Recreated retry handler for provider: {provider_name}"
                    )

                return self._retry_handlers[provider_name]
            else:
                self._retry_handlers[provider_name] = RetryHandler(
                    provider_name, config
                )
                logger.info(f"Created retry handler for provider: {provider_name}")

            return self._retry_handlers[provider_name]


# Global retry registry
retry_registry = RetryRegistry()


# Convenience functions for common retry patterns
async def retry_on_failure(
    func: Callable[..., Any],
    provider_name: str,
    config: RetryConfig,
    *args,
    **kwargs,
) -> Any:
    """Execute function with retry logic.

    Args:
        func: Function to execute
        provider_name: Name of the provider
        config: Retry configuration
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result
    """
    retry_handler = await retry_registry.get_retry_handler(provider_name, config)
    return await retry_handler.execute_with_retry(func, *args, **kwargs)
