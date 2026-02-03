"""Circuit breaker implementation for provider resilience."""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

from prometheus_client import Counter, Gauge

from app.config.models import CircuitBreakerConfig

logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar("T")

# Prometheus metrics
circuit_breaker_state_gauge = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["provider"],
)
circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    ["provider"],
)
circuit_breaker_successes_total = Counter(
    "circuit_breaker_successes_total",
    "Total number of circuit breaker successes",
    ["provider"],
)
circuit_breaker_calls_total = Counter(
    "circuit_breaker_calls_total",
    "Total number of circuit breaker calls",
    ["provider", "state"],
)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = 0  # Normal operation
    OPEN = 1  # Failing fast
    HALF_OPEN = 2  # Testing recovery


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, provider_name: str):
        """Initialize exception.

        Args:
            provider_name: Name of the provider with open circuit
        """
        self.provider_name = provider_name
        super().__init__(f"Circuit breaker is open for provider: {provider_name}")


class CircuitBreaker:
    """Async circuit breaker implementation."""

    def __init__(self, provider_name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker.

        Args:
            provider_name: Name of the provider this circuit breaker protects
            config: Circuit breaker configuration
        """
        self.provider_name = provider_name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
        self._half_open_in_flight = False  # Flag to prevent concurrent HALF_OPEN probes

        # Initialize metrics
        circuit_breaker_state_gauge.labels(provider=provider_name).set(self.state.value)

        logger.info(
            f"Circuit breaker initialized for provider {provider_name} "
            f"with failure_threshold={config.failure_threshold}, "
            f"recovery_timeout={config.recovery_timeout}"
        )

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenException: When circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            # Record call attempt
            circuit_breaker_calls_total.labels(
                provider=self.provider_name, state=self.state.name.lower()
            ).inc()

            # Check if we should attempt recovery
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self._half_open_in_flight = True  # Set in-flight flag
                    circuit_breaker_state_gauge.labels(provider=self.provider_name).set(
                        self.state.value
                    )
                    logger.info(
                        f"Circuit breaker for {self.provider_name} "
                        "transitioning to HALF_OPEN"
                    )
                else:
                    logger.warning(
                        f"Circuit breaker for {self.provider_name} is OPEN, "
                        "failing fast"
                    )
                    raise CircuitBreakerOpenException(self.provider_name)
            elif self.state == CircuitBreakerState.HALF_OPEN and self._half_open_in_flight:
                # Reject concurrent probes while one is already in flight
                logger.warning(
                    f"Circuit breaker for {self.provider_name} is HALF_OPEN "
                    "with probe in flight, rejecting concurrent request"
                )
                raise CircuitBreakerOpenException(self.provider_name)

        # Execute function outside of lock to avoid blocking other calls
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success - update state
            async with self._lock:
                await self._on_success()

            return result

        except Exception as e:
            # Failure - update state
            async with self._lock:
                await self._on_failure(e)
            raise

    async def _on_success(self) -> None:
        """Handle successful function execution."""
        circuit_breaker_successes_total.labels(provider=self.provider_name).inc()

        if self.state == CircuitBreakerState.HALF_OPEN:
            # Recovery successful - close circuit and clear in-flight flag
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self._half_open_in_flight = False  # Clear in-flight flag
            circuit_breaker_state_gauge.labels(provider=self.provider_name).set(
                self.state.value
            )
            logger.info(
                f"Circuit breaker for {self.provider_name} "
                "recovered and transitioned to CLOSED"
            )
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    async def _on_failure(self, exception: Exception) -> None:
        """Handle failed function execution.

        Args:
            exception: Exception that occurred
        """
        circuit_breaker_failures_total.labels(provider=self.provider_name).inc()

        self.failure_count += 1
        self.last_failure_time = time.time()

        # Clear in-flight flag on failure (allows subsequent attempts)
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_in_flight = False

        logger.warning(
            f"Circuit breaker for {self.provider_name} recorded failure "
            f"({self.failure_count}/{self.config.failure_threshold}): {exception}"
        )

        # Check if we should open the circuit
        if (
            self.state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]
            and self.failure_count >= self.config.failure_threshold
        ):
            self.state = CircuitBreakerState.OPEN
            circuit_breaker_state_gauge.labels(provider=self.provider_name).set(
                self.state.value
            )
            logger.error(
                f"Circuit breaker for {self.provider_name} "
                f"OPENED after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset.

        Returns:
            True if reset should be attempted
        """
        if self.last_failure_time is None:
            return True

        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed.

        Returns:
            True if circuit is closed
        """
        return self.state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open.

        Returns:
            True if circuit is open
        """
        return self.state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open.

        Returns:
            True if circuit is half-open
        """
        return self.state == CircuitBreakerState.HALF_OPEN

    def get_state_info(self) -> Dict[str, Any]:
        """Get circuit breaker state information.

        Returns:
            Dictionary with state information
        """
        return {
            "provider": self.provider_name,
            "state": self.state.name,
            "failure_count": self.failure_count,
            "failure_threshold": self.config.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "recovery_timeout": self.config.recovery_timeout,
        }


class CircuitBreakerRegistry:
    """Registry for managing circuit breakers per provider."""

    def __init__(self):
        """Initialize circuit breaker registry."""
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_circuit_breaker(
        self, provider_name: str, config: CircuitBreakerConfig
    ) -> CircuitBreaker:
        """Get or create circuit breaker for provider.

        Args:
            provider_name: Name of the provider
            config: Circuit breaker configuration

        Returns:
            Circuit breaker instance
        """
        async with self._lock:
            if provider_name in self._circuit_breakers:
                existing_breaker = self._circuit_breakers[provider_name]
                # Compare configs to detect changes
                if existing_breaker.config != config:
                    logger.info(
                        f"Circuit breaker config changed for provider {provider_name}. "
                        f"Recreating breaker with new configuration."
                    )
                    # Replace with new circuit breaker
                    self._circuit_breakers[provider_name] = CircuitBreaker(
                        provider_name, config
                    )
                    logger.info(
                        f"Recreated circuit breaker for provider: {provider_name}"
                    )

                return self._circuit_breakers[provider_name]
            else:
                self._circuit_breakers[provider_name] = CircuitBreaker(
                    provider_name, config
                )
                logger.info(f"Created circuit breaker for provider: {provider_name}")

            return self._circuit_breakers[provider_name]

    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Get state information for all circuit breakers.

        Returns:
            Dictionary mapping provider names to state information
        """
        async with self._lock:
            # Take a snapshot of circuit breakers to avoid RuntimeError
            # if the dict is mutated during iteration
            circuit_breakers_snapshot = list(self._circuit_breakers.items())
        
        # Call get_state_info() outside the lock to avoid blocking
        return {
            name: cb.get_state_info() for name, cb in circuit_breakers_snapshot
        }


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()
