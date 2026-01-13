"""Prometheus metrics setup."""

import logging
from prometheus_client import Counter, Histogram, Info

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status_code", "provider"]
)

REQUEST_DURATION = Histogram(
    "gateway_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "provider"]
)

PROVIDER_HEALTH = Counter(
    "gateway_provider_health_checks_total",
    "Total number of provider health checks",
    ["provider", "status"]
)

SERVICE_INFO = Info(
    "gateway_service_info",
    "Service information"
)


def setup_metrics() -> None:
    """Setup Prometheus metrics."""
    settings = get_settings()
    
    # Set service info
    SERVICE_INFO.info({
        "version": settings.version,
        "service": "sre-inference-gateway"
    })
    
    logger.info("Prometheus metrics initialized (served via FastAPI /metrics endpoint)")


def record_request(
    method: str,
    endpoint: str,
    status_code: int,
    provider: str,
    duration: float
) -> None:
    """Record request metrics.
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        provider: Provider name
        duration: Request duration in seconds
    """
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        provider=provider
    ).inc()
    
    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint,
        provider=provider
    ).observe(duration)


def record_provider_health(provider: str, healthy: bool) -> None:
    """Record provider health check.
    
    Args:
        provider: Provider name
        healthy: Health status
    """
    status = "healthy" if healthy else "unhealthy"
    PROVIDER_HEALTH.labels(provider=provider, status=status).inc()