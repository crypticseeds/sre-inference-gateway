"""Golden-signal metrics tests for chat completions."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from app.main import create_app
from app.observability.metrics import (
    FAILURE_COUNT,
    IN_FLIGHT_REQUESTS,
    REQUEST_COUNT,
    REQUEST_DURATION,
    STREAM_FIRST_BYTE,
)
from app.router.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.config.models import CircuitBreakerConfig


def histogram_count(metric, **labels) -> float:
    """Return the observed count for a histogram child."""
    return sum(bucket.get() for bucket in metric.labels(**labels)._buckets)


@patch("app.router.router.provider_registry")
def test_request_metrics_move_for_streaming_and_non_streaming(mock_registry):
    """Requests update traffic, latency, TTFB, and saturation signals."""
    provider_name = "golden_signal_test_provider"
    model = "metrics-test-model"
    provider = MagicMock()
    provider.name = provider_name
    provider.chat_completion = AsyncMock(
        return_value=MagicMock(
            id="metrics-test-id",
            object="chat.completion",
            created=1234567890,
            model=model,
            choices=[],
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )
    )

    async def chunks() -> AsyncIterator[bytes]:
        yield b'data: {"choices":[]}\n\n'
        yield b"data: [DONE]\n\n"

    provider.chat_completion_stream = AsyncMock(side_effect=lambda *_: chunks())
    mock_registry.get_provider.return_value = provider

    false_requests = REQUEST_COUNT.labels(
        provider=provider_name,
        model=model,
        stream="false",
        status_class="2xx",
    )
    true_requests = REQUEST_COUNT.labels(
        provider=provider_name,
        model=model,
        stream="true",
        status_class="2xx",
    )
    before_false_requests = false_requests._value.get()
    before_true_requests = true_requests._value.get()
    before_false_duration = histogram_count(
        REQUEST_DURATION, provider=provider_name, stream="false"
    )
    before_true_duration = histogram_count(
        REQUEST_DURATION, provider=provider_name, stream="true"
    )
    before_first_byte = histogram_count(STREAM_FIRST_BYTE, provider=provider_name)

    with TestClient(create_app()) as client:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "metrics"}],
        }
        non_streaming = client.post(
            "/v1/chat/completions",
            headers={"X-Provider-Priority": provider_name},
            json=payload,
        )
        streaming = client.post(
            "/v1/chat/completions",
            headers={"X-Provider-Priority": provider_name},
            json={**payload, "stream": True},
        )

    assert non_streaming.status_code == streaming.status_code == 200
    assert false_requests._value.get() == before_false_requests + 1
    assert true_requests._value.get() == before_true_requests + 1
    assert histogram_count(
        REQUEST_DURATION, provider=provider_name, stream="false"
    ) == before_false_duration + 1
    assert histogram_count(
        REQUEST_DURATION, provider=provider_name, stream="true"
    ) == before_true_duration + 1
    assert histogram_count(
        STREAM_FIRST_BYTE, provider=provider_name
    ) == before_first_byte + 1
    assert IN_FLIGHT_REQUESTS.labels(provider=provider_name)._value.get() == 0


@pytest.mark.parametrize(
    ("status_code", "status_class", "error_type"),
    [
        (400, "4xx", "client_4xx"),
        (429, "4xx", "establishment"),
        (503, "5xx", "establishment"),
    ],
)
@patch("app.router.router.provider_registry")
def test_failure_metrics_classify_provider_errors(
    mock_registry, status_code, status_class, error_type
):
    """Provider errors update traffic, failures, latency, and saturation."""
    provider_name = f"failure_metrics_{status_code}"
    model = "failure-metrics-model"
    provider = MagicMock()
    provider.name = provider_name
    provider.chat_completion = AsyncMock(
        side_effect=HTTPException(status_code=status_code, detail="provider error")
    )
    mock_registry.get_provider.side_effect = lambda name: (
        provider if name == provider_name else None
    )
    requests = REQUEST_COUNT.labels(
        provider=provider_name,
        model=model,
        stream="false",
        status_class=status_class,
    )
    failures = FAILURE_COUNT.labels(provider=provider_name, error_type=error_type)
    before_requests = requests._value.get()
    before_failures = failures._value.get()

    with TestClient(create_app()) as client:
        response = client.post(
            "/v1/chat/completions",
            headers={"X-Provider-Priority": provider_name},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "fail"}],
            },
        )

    assert response.status_code == status_code
    assert requests._value.get() == before_requests + 1
    assert failures._value.get() == before_failures + 1
    assert IN_FLIGHT_REQUESTS.labels(provider=provider_name)._value.get() == 0


async def test_circuit_breaker_gauge_exports_state():
    """The exported circuit-breaker gauge follows state transitions."""
    provider_name = "gauge_test_provider"
    breaker = CircuitBreaker(
        provider_name,
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60),
    )

    async def fail() -> None:
        raise ConnectionError("provider unavailable")

    try:
        await breaker.call(fail)
    except ConnectionError:
        pass

    assert breaker.state is CircuitBreakerState.OPEN
    output = generate_latest().decode()
    assert f'circuit_breaker_state{{provider="{provider_name}"}} 1.0' in output
