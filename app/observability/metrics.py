"""Prometheus metrics setup."""

import logging
import time
from collections.abc import AsyncIterator

from prometheus_client import Counter, Gauge, Histogram, Info

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total number of chat completion provider requests",
    ["provider", "model", "stream", "status_class"],
)

REQUEST_DURATION = Histogram(
    "gateway_request_duration_seconds",
    "Chat completion provider request duration in seconds",
    ["provider", "stream"],
)

STREAM_FIRST_BYTE = Histogram(
    "gateway_stream_first_byte_seconds",
    "Time until the first streaming response bytes are forwarded",
    ["provider"],
)

FAILURE_COUNT = Counter(
    "gateway_failures_total",
    "Total number of chat completion failures",
    ["provider", "error_type"],
)

IN_FLIGHT_REQUESTS = Gauge(
    "gateway_in_flight_requests",
    "Current chat completion provider requests in flight",
    ["provider"],
)

PROVIDER_HEALTH = Counter(
    "gateway_provider_health_checks_total",
    "Total number of provider health checks",
    ["provider", "status"],
)

SERVICE_INFO = Info("gateway_service_info", "Service information")


def setup_metrics() -> None:
    """Setup Prometheus metrics."""
    try:
        settings = get_settings()

        # Set service info
        SERVICE_INFO.info(
            {"version": settings.version, "service": "sre-inference-gateway"}
        )

        logger.info(
            "Prometheus metrics initialized (served via FastAPI /metrics endpoint)"
        )
    except Exception as e:
        logger.warning(f"Could not fully initialize metrics: {e}")


def record_request(provider: str, model: str, stream: bool, status_code: int) -> None:
    """Record a completed provider request."""
    REQUEST_COUNT.labels(
        provider=provider,
        model=model,
        stream=str(stream).lower(),
        status_class=f"{status_code // 100}xx",
    ).inc()


def record_request_duration(provider: str, stream: bool, started_at: float) -> None:
    """Record elapsed request time from a monotonic start timestamp."""
    REQUEST_DURATION.labels(provider=provider, stream=str(stream).lower()).observe(
        time.monotonic() - started_at
    )


def record_failure(provider: str, error_type: str) -> None:
    """Record a provider request failure by lifecycle stage."""
    FAILURE_COUNT.labels(provider=provider, error_type=error_type).inc()


async def instrument_stream(
    stream: AsyncIterator[bytes], provider: str, model: str, started_at: float
) -> AsyncIterator[bytes]:
    """Pass through stream bytes while tracking first byte and request lifetime."""
    first_byte_recorded = False
    IN_FLIGHT_REQUESTS.labels(provider=provider).inc()
    try:
        async for chunk in stream:
            if not first_byte_recorded:
                STREAM_FIRST_BYTE.labels(provider=provider).observe(
                    time.monotonic() - started_at
                )
                first_byte_recorded = True
            yield chunk
    finally:
        close = getattr(stream, "aclose", None)
        try:
            if close is not None:
                await close()
        finally:
            record_request(provider, model, True, 200)
            record_request_duration(provider, True, started_at)
            IN_FLIGHT_REQUESTS.labels(provider=provider).dec()


def record_provider_health(provider: str, healthy: bool) -> None:
    """Record provider health check.

    Args:
        provider: Provider name
        healthy: Health status
    """
    status = "healthy" if healthy else "unhealthy"
    PROVIDER_HEALTH.labels(provider=provider, status=status).inc()
