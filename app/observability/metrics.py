"""Prometheus metrics setup."""

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info

from app.config.settings import get_gateway_config, get_settings

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

TOKENS = Counter(
    "gateway_tokens_total",
    "Provider-reported chat completion tokens",
    ["provider", "model", "type"],
)

COST_USD = Counter(
    "gateway_cost_usd_total",
    "Cost in USD calculated from provider-reported usage",
    ["provider", "model"],
)

UNPRICED_REQUESTS = Counter(
    "gateway_unpriced_requests_total",
    "Successful chat completions without recorded cost",
    ["provider", "model", "reason"],
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


def record_usage(provider: str, model: str, usage: Any) -> None:
    """Record provider-reported tokens and configured cost for a successful request."""
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    if not isinstance(usage, dict):
        UNPRICED_REQUESTS.labels(
            provider=provider, model=model, reason="missing_usage"
        ).inc()
        return

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    if (
        not isinstance(prompt_tokens, int)
        or isinstance(prompt_tokens, bool)
        or prompt_tokens < 0
        or not isinstance(completion_tokens, int)
        or isinstance(completion_tokens, bool)
        or completion_tokens < 0
    ):
        UNPRICED_REQUESTS.labels(
            provider=provider, model=model, reason="invalid_usage"
        ).inc()
        return

    TOKENS.labels(provider=provider, model=model, type="prompt").inc(prompt_tokens)
    TOKENS.labels(provider=provider, model=model, type="completion").inc(
        completion_tokens
    )

    pricing = get_gateway_config().pricing.get(model)
    if pricing is None:
        UNPRICED_REQUESTS.labels(
            provider=provider, model=model, reason="missing_pricing"
        ).inc()
        return

    cost = (
        prompt_tokens * pricing.input_per_1m
        + completion_tokens * pricing.output_per_1m
    ) / 1_000_000
    COST_USD.labels(provider=provider, model=model).inc(cost)

def _stream_tail_result(tail: bytes) -> tuple[Any, bool]:
    """Parse provider usage and terminal status after streaming has finished."""
    usage = None
    done = False
    for line in reversed(tail.splitlines()):
        line = line.strip()
        if not line.startswith(b"data:"):
            continue
        payload = line.removeprefix(b"data:").strip()
        if payload == b"[DONE]":
            done = True
            continue
        try:
            event = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(event, dict) and "usage" in event:
            usage = event["usage"]
    return usage, done


async def instrument_stream(
    stream: AsyncIterator[bytes], provider: str, model: str, started_at: float
) -> AsyncIterator[bytes]:
    """Pass through bytes and account from a bounded tail after streaming ends."""
    first_byte_recorded = False
    tail = b""
    exhausted = False
    close_succeeded = False
    IN_FLIGHT_REQUESTS.labels(provider=provider).inc()
    try:
        async for chunk in stream:
            if not first_byte_recorded:
                STREAM_FIRST_BYTE.labels(provider=provider).observe(
                    time.monotonic() - started_at
                )
                first_byte_recorded = True
            tail = (tail + chunk)[-2048:]
            yield chunk
        exhausted = True
    finally:
        close = getattr(stream, "aclose", None)
        try:
            if close is not None:
                await close()
            close_succeeded = True
        finally:
            usage, done = _stream_tail_result(tail)
            if exhausted and close_succeeded and done:
                record_usage(provider, model, usage)
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
