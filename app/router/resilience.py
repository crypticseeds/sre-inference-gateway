"""Resilience patterns implementation combining circuit breaker and retry logic."""

import asyncio
import logging
from typing import Any, Callable, Dict

from fastapi import HTTPException
from prometheus_client import Counter, Histogram

from app.config.models import ResilienceConfig
from app.router.circuit_breaker import (
    CircuitBreakerOpenException,
    circuit_breaker_registry,
)
from app.router.retry import NonRetryableException, retry_registry

logger = logging.getLogger(__name__)

# Prometheus metrics
resilience_calls_total = Counter(
    "resilience_calls_total",
    "Total number of resilience pattern calls",
    ["provider", "pattern"],
)
resilience_failures_total = Counter(
    "resilience_failures_total",
    "Total number of resilience pattern failures",
    ["provider", "failure_type"],
)
resilience_duration_seconds = Histogram(
    "resilience_duration_seconds",
    "Time spent in resilience patterns",
    ["provider"],
)


class ResilienceHandler:
    """Handler that combines circuit breaker and retry patterns."""

    def __init__(self, provider_name: str, config: ResilienceConfig):
        """Initialize resilience handler.

        Args:
            provider_name: Name of the provider
            config: Resilience configuration
        """
        self.provider_name = provider_name
        self.config = config

        logger.info(
            f"Resilience handler initialized for provider {provider_name} "
            f"with circuit breaker and retry patterns"
        )

    async def execute_with_resilience(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> Any:
        """Execute function with full resilience patterns.

        The execution flow is:
        1. Check circuit breaker state
        2. If closed/half-open, execute with retry logic
        3. Circuit breaker monitors success/failure
        4. Retry logic handles transient failures

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: When circuit breaker is open
            NonRetryableException: When error is not retryable
            Exception: Final exception after all patterns applied
        """
        start_time = asyncio.get_running_loop().time()

        try:
            # Get circuit breaker and retry handler
            circuit_breaker = await circuit_breaker_registry.get_circuit_breaker(
                self.provider_name, self.config.circuit_breaker
            )
            retry_handler = await retry_registry.get_retry_handler(
                self.provider_name, self.config.retry
            )

            # Record call attempt
            resilience_calls_total.labels(
                provider=self.provider_name, pattern="combined"
            ).inc()

            # Execute with circuit breaker protection and retry logic
            async def resilient_execution():
                """Inner function that combines retry with the original function."""
                return await retry_handler.execute_with_retry(func, *args, **kwargs)

            # Circuit breaker wraps the retry logic
            result = await circuit_breaker.call(resilient_execution)

            logger.debug(
                f"Resilient execution succeeded for provider {self.provider_name}"
            )
            return result

        except CircuitBreakerOpenException as e:
            # Circuit breaker is open - fail fast
            resilience_failures_total.labels(
                provider=self.provider_name, failure_type="circuit_breaker_open"
            ).inc()

            logger.warning(
                f"Circuit breaker open for provider {self.provider_name}, failing fast"
            )

            # Convert to HTTP 503 Service Unavailable
            raise HTTPException(
                status_code=503,
                detail=f"Provider {self.provider_name} is temporarily unavailable",
            ) from e

        except NonRetryableException as e:
            # Non-retryable error - fail fast
            resilience_failures_total.labels(
                provider=self.provider_name, failure_type="non_retryable"
            ).inc()

            logger.warning(
                f"Non-retryable error for provider {self.provider_name}: {e}"
            )

            # Extract status code from exception
            status_code = 500  # Default fallback

            # Try to get status_code attribute first
            if hasattr(e, "status_code") and isinstance(e.status_code, int):
                status_code = e.status_code
            else:
                # Try to parse status code from string
                import re

                match = re.search(r"\b([4-5]\d{2})\b", str(e))
                if match:
                    parsed_code = int(match.group(1))
                    if 400 <= parsed_code < 500:
                        status_code = parsed_code  # Use original 4xx code
                    else:
                        status_code = 500  # Map other codes to 500

            raise HTTPException(status_code=status_code, detail=str(e)) from e

        except Exception as e:
            # All other failures
            resilience_failures_total.labels(
                provider=self.provider_name, failure_type="exhausted"
            ).inc()

            logger.error(
                f"All resilience patterns exhausted for provider "
                f"{self.provider_name}: {e}"
            )

            # Convert to HTTP 502 Bad Gateway
            raise HTTPException(
                status_code=502,
                detail=f"Provider {self.provider_name} failed after all retry attempts",
            ) from e

        finally:
            # Record total duration
            duration = asyncio.get_running_loop().time() - start_time
            resilience_duration_seconds.labels(provider=self.provider_name).observe(
                duration
            )


class ResilienceRegistry:
    """Registry for managing resilience handlers per provider."""

    def __init__(self):
        """Initialize resilience registry."""
        self._resilience_handlers: Dict[str, ResilienceHandler] = {}
        self._lock = asyncio.Lock()

    async def get_resilience_handler(
        self, provider_name: str, config: ResilienceConfig
    ) -> ResilienceHandler:
        """Get or create resilience handler for provider.

        Args:
            provider_name: Name of the provider
            config: Resilience configuration

        Returns:
            Resilience handler instance
        """
        async with self._lock:
            if provider_name in self._resilience_handlers:
                existing_handler = self._resilience_handlers[provider_name]
                # Compare configs to detect changes
                if existing_handler.config != config:
                    logger.warning(
                        f"Resilience config changed for provider {provider_name}. "
                        f"Old config: {existing_handler.config}, New config: {config}. "
                        f"Recreating handler with new configuration."
                    )
                    # Recreate handler with new config
                    self._resilience_handlers[provider_name] = ResilienceHandler(
                        provider_name, config
                    )
                    logger.info(
                        f"Recreated resilience handler for provider: {provider_name}"
                    )

                return self._resilience_handlers[provider_name]
            else:
                self._resilience_handlers[provider_name] = ResilienceHandler(
                    provider_name, config
                )
                logger.info(f"Created resilience handler for provider: {provider_name}")

            return self._resilience_handlers[provider_name]

    def get_all_circuit_breaker_states(self) -> Dict[str, Dict[str, Any]]:
        """Get circuit breaker states for all providers.

        Returns:
            Dictionary mapping provider names to circuit breaker state info
        """
        return circuit_breaker_registry.get_all_states()


# Global resilience registry
resilience_registry = ResilienceRegistry()


# Convenience function for applying resilience patterns
async def execute_with_resilience(
    func: Callable[..., Any],
    provider_name: str,
    config: ResilienceConfig,
    *args,
    **kwargs,
) -> Any:
    """Execute function with resilience patterns.

    Args:
        func: Function to execute
        provider_name: Name of the provider
        config: Resilience configuration
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function

    Returns:
        Function result
    """
    resilience_handler = await resilience_registry.get_resilience_handler(
        provider_name, config
    )
    return await resilience_handler.execute_with_resilience(func, *args, **kwargs)
