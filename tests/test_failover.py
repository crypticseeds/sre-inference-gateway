"""Failover drill tests for mock streaming providers."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app.config.models import CircuitBreakerConfig
from app.config.settings import get_gateway_config
from app.main import create_app
from app.providers.registry import provider_registry
from app.router.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitBreakerState,
    circuit_breaker_registry,
)
from app.router.resilience import resilience_registry
from app.router.retry import retry_registry
from app.router.router import RequestRouter


@pytest.fixture
def failover_client(monkeypatch):
    """Create a client with fresh providers and resilience registries."""
    monkeypatch.setenv("FAILOVER_DRILL_ADMIN", "1")
    config = get_gateway_config()
    circuit_breaker_registry._circuit_breakers.clear()
    resilience_registry._resilience_handlers.clear()
    retry_registry._retry_handlers.clear()
    asyncio.run(provider_registry.initialize_from_config(config.providers))

    with TestClient(create_app()) as client:
        yield client

    circuit_breaker_registry._circuit_breakers.clear()
    resilience_registry._resilience_handlers.clear()
    retry_registry._retry_handlers.clear()


def stream_request(client: TestClient, provider: str):
    """Send a pinned streaming request used by the failover drill."""
    return client.post(
        "/v1/chat/completions",
        headers={"X-Provider-Priority": provider},
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "failover drill"}],
            "stream": True,
        },
    )


def stream_content(response) -> str:
    """Reconstruct assistant content from an SSE response."""
    content = []
    for event in response.content.split(b"\n\n"):
        if not event.startswith(b"data: {"):
            continue
        chunk = json.loads(event.removeprefix(b"data: "))
        content.extend(
            choice["delta"].get("content", "") for choice in chunk["choices"]
        )
    return "".join(content)


def test_config_enables_both_streaming_mocks_for_same_model(failover_client):
    """Both no-key mocks are active and serve the drill's model."""
    config = get_gateway_config()
    mocks = {
        provider.name: provider
        for provider in config.providers
        if provider.type == "mock"
    }

    assert set(provider_registry.list_providers()) == {"mock_openai", "mock_vllm"}
    assert all(mocks[name].enabled and mocks[name].weight > 0 for name in mocks)
    assert {provider.model for provider in mocks.values()} == {"mock-model"}

    openai = stream_request(failover_client, "mock_openai")
    vllm = stream_request(failover_client, "mock_vllm")
    assert openai.status_code == vllm.status_code == 200
    assert "Mock OpenAI response" in stream_content(openai)
    assert "Mock vLLM response" in stream_content(vllm)


def test_admin_kill_fails_one_mock_while_other_streams(failover_client):
    """The runtime kill control affects only its named mock provider."""
    killed = failover_client.post("/admin/providers/mock_openai/fail")

    assert killed.json() == {"provider": "mock_openai", "failed": True}
    assert stream_request(failover_client, "mock_openai").status_code == 200
    survivor = stream_request(failover_client, "mock_vllm")
    assert survivor.status_code == 200
    assert "Mock vLLM response" in stream_content(survivor)


def test_admin_kill_requires_explicit_drill_opt_in(failover_client, monkeypatch):
    """The destructive local control is unavailable unless explicitly enabled."""
    monkeypatch.delenv("FAILOVER_DRILL_ADMIN")

    response = failover_client.post("/admin/providers/mock_openai/fail")

    assert response.status_code == 404


def test_router_skips_provider_with_open_circuit(failover_client):
    """Weighted and pinned routing omit providers whose breaker is OPEN."""
    assert failover_client.post("/admin/providers/mock_openai/fail").status_code == 200
    assert stream_request(failover_client, "mock_openai").status_code == 200
    assert stream_request(failover_client, "mock_openai").status_code == 200

    state = failover_client.get(
        "/health/circuit-breakers/mock_openai"
    ).json()["circuit_breaker"]
    assert state["state"] == "OPEN"

    router = RequestRouter({"mock_openai": 1.0, "mock_vllm": 0.0})
    assert router.select_provider("mock_openai").name == "mock_vllm"


def test_restore_recovers_through_half_open_probe(failover_client):
    """A restored mock closes its breaker after the recovery timeout probe."""
    assert failover_client.post("/admin/providers/mock_openai/fail").status_code == 200
    for _ in range(2):
        response = stream_request(failover_client, "mock_openai")
        assert response.status_code == 200
        assert "Mock vLLM response" in stream_content(response)

    assert failover_client.post("/admin/providers/mock_openai/restore").status_code == 200
    breaker = circuit_breaker_registry._circuit_breakers["mock_openai"]
    breaker.last_failure_time -= breaker.config.recovery_timeout

    recovered = stream_request(failover_client, "mock_openai")
    state = failover_client.get(
        "/health/circuit-breakers/mock_openai"
    ).json()["circuit_breaker"]
    assert recovered.status_code == 200
    assert "Mock OpenAI response" in stream_content(recovered)
    assert state["state"] == "CLOSED"


@pytest.mark.asyncio
async def test_only_one_half_open_recovery_probe_runs():
    """Concurrent recovery traffic cannot start multiple half-open probes."""
    breaker = CircuitBreaker(
        "mock_openai",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01),
    )
    breaker.state = CircuitBreakerState.OPEN
    breaker.last_failure_time = 0
    probe_started = asyncio.Event()
    release_probe = asyncio.Event()

    async def probe():
        probe_started.set()
        await release_probe.wait()
        return "recovered"

    first_probe = asyncio.create_task(breaker.call(probe))
    await probe_started.wait()

    with pytest.raises(CircuitBreakerOpenException):
        await breaker.call(probe)

    release_probe.set()
    assert await first_probe == "recovered"
    assert breaker.is_closed
