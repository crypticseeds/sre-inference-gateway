"""Concurrency admission and load-shedding tests."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.completions import create_chat_completion
from app.config.models import GatewayConfig, LoadSheddingConfig
from app.models.requests import ChatCompletionRequest
from app.observability.metrics import SHED_REQUESTS
from app.observability.metrics import IN_FLIGHT_REQUESTS
from app.providers.mock import MockOpenAIAdapter
from app.router.load_shedding import LoadShedder, load_shedder
from app.router.router import RequestRouter


def request() -> Request:
    """Create the minimum Starlette request needed by the endpoint."""
    return Request({"type": "http", "method": "POST", "path": "/", "headers": []})


def chat_request(stream: bool = False) -> ChatCompletionRequest:
    """Create a valid mock completion request."""
    return ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=stream,
    )


@pytest.fixture(autouse=True)
def reset_load_shedder():
    """Keep process-wide admission state isolated between tests."""
    load_shedder.configure(LoadSheddingConfig())
    yield
    load_shedder.configure(LoadSheddingConfig())


@pytest.mark.asyncio
async def test_global_cap_returns_503_retry_after_and_records_metric():
    """A full gateway rejects immediately with the documented response shape."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=1, per_provider_max_in_flight=1)
    )
    held = await load_shedder.try_acquire_global()
    shed = SHED_REQUESTS.labels(scope="global", provider="")
    before = shed._value.get()

    with pytest.raises(HTTPException) as exc_info:
        await create_chat_completion(
            request(), chat_request(), "request-1", None, RequestRouter({"mock": 1}), None
        )

    held.release()
    assert exc_info.value.status_code == 503
    assert exc_info.value.headers == {"Retry-After": "1"}
    assert "Gateway concurrency limit" in exc_info.value.detail
    assert shed._value.get() == before + 1


@pytest.mark.asyncio
async def test_saturated_provider_is_skipped_for_healthy_fallback():
    """Routing treats provider saturation like circuit ineligibility."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=10, per_provider_max_in_flight=1)
    )
    saturated = MockOpenAIAdapter("saturated", {"stream_chunk_delay": 0})
    healthy = MockOpenAIAdapter("healthy", {"stream_chunk_delay": 0})
    held = await load_shedder.try_acquire_provider("saturated")
    router = RequestRouter({"saturated": 1, "healthy": 0})

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.side_effect = lambda name: {
            "saturated": saturated,
            "healthy": healthy,
        }.get(name)
        response = await create_chat_completion(
            request(), chat_request(), "request-2", "saturated", router, None
        )

    held.release()
    assert response.model == "mock-model"


@pytest.mark.asyncio
async def test_provider_cap_returns_503_retry_after_and_records_metric():
    """A request is shed when every selectable provider is saturated."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=10, per_provider_max_in_flight=1)
    )
    provider = MockOpenAIAdapter("only", {"stream_chunk_delay": 0})
    held = await load_shedder.try_acquire_provider("only")
    shed = SHED_REQUESTS.labels(scope="provider", provider="only")
    before = shed._value.get()

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.return_value = provider
        with pytest.raises(HTTPException) as exc_info:
            await create_chat_completion(
                request(), chat_request(), "request-3", None, RequestRouter({"only": 1}), None
            )

    held.release()
    assert exc_info.value.status_code == 503
    assert exc_info.value.headers == {"Retry-After": "1"}
    assert "providers are at capacity" in exc_info.value.detail
    assert shed._value.get() == before + 1


@pytest.mark.asyncio
async def test_stream_holds_slots_until_iterator_cleanup():
    """Gateway and provider capacity remain occupied for the full stream."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=1, per_provider_max_in_flight=1)
    )
    provider = MockOpenAIAdapter("streaming", {"stream_chunk_delay": 0})

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.return_value = provider
        response = await create_chat_completion(
            request(),
            chat_request(stream=True),
            "request-4",
            None,
            RequestRouter({"streaming": 1}),
            None,
        )

    assert await load_shedder.try_acquire_global() is None
    assert not load_shedder.provider_has_capacity("streaming")
    assert IN_FLIGHT_REQUESTS.labels(provider="streaming")._value.get() == 1
    await response.body_iterator.aclose()
    global_lease = await load_shedder.try_acquire_global()
    provider_lease = await load_shedder.try_acquire_provider("streaming")
    assert global_lease is not None
    assert provider_lease is not None
    assert IN_FLIGHT_REQUESTS.labels(provider="streaming")._value.get() == 0
    global_lease.release()
    provider_lease.release()


@pytest.mark.asyncio
async def test_stream_send_failure_releases_slots_and_in_flight_gauge():
    """A downstream send failure cannot leak stream admission."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=1, per_provider_max_in_flight=1)
    )
    provider = MockOpenAIAdapter("disconnect", {"stream_chunk_delay": 0})

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.return_value = provider
        response = await create_chat_completion(
            request(),
            chat_request(stream=True),
            "request-5",
            None,
            RequestRouter({"disconnect": 1}),
            None,
        )

    sends = 0

    async def send(_message):
        nonlocal sends
        sends += 1
        if sends == 2:
            raise OSError("client disconnected")

    async def receive():
        return {"type": "http.request"}

    with pytest.raises(Exception):
        await response(
            {"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send
        )

    global_lease = await load_shedder.try_acquire_global()
    provider_lease = await load_shedder.try_acquire_provider("disconnect")
    assert global_lease is not None
    assert provider_lease is not None
    assert IN_FLIGHT_REQUESTS.labels(provider="disconnect")._value.get() == 0
    global_lease.release()
    provider_lease.release()


@pytest.mark.asyncio
async def test_disabled_load_shedding_bypasses_all_limits():
    """Disabling admission leaves routing and concurrency unrestricted."""
    shedder = LoadShedder()
    shedder.configure(
        LoadSheddingConfig(
            enabled=False, global_max_in_flight=1, per_provider_max_in_flight=1
        )
    )
    global_leases = [await shedder.try_acquire_global() for _ in range(3)]
    provider_leases = [await shedder.try_acquire_provider("provider") for _ in range(3)]

    assert all(global_leases)
    assert all(provider_leases)
    assert shedder.provider_has_capacity("provider")


@pytest.mark.asyncio
async def test_defaults_allow_30_concurrent_mock_streams():
    """Generous defaults do not shed benchmark-like stream concurrency."""
    defaults = GatewayConfig().load_shedding
    load_shedder.configure(defaults)
    provider = MockOpenAIAdapter("benchmark", {"stream_chunk_delay": 0.001})
    router = RequestRouter({"benchmark": 1})

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.return_value = provider
        responses = await asyncio.gather(
            *[
                create_chat_completion(
                    request(), chat_request(stream=True), f"benchmark-{index}", None, router, None
                )
                for index in range(30)
            ]
        )
        bodies = await asyncio.gather(
            *[
                asyncio.create_task(_consume(response.body_iterator))
                for response in responses
            ]
        )

    assert len(bodies) == 30
    assert all(b"data: [DONE]" in body for body in bodies)


@pytest.mark.asyncio
async def test_natural_stream_completion_releases_slots():
    """Normal stream exhaustion returns both admission permits."""
    load_shedder.configure(
        LoadSheddingConfig(global_max_in_flight=1, per_provider_max_in_flight=1)
    )
    provider = MockOpenAIAdapter("complete", {"stream_chunk_delay": 0})

    with patch("app.router.router.provider_registry") as registry:
        registry.get_provider.return_value = provider
        response = await create_chat_completion(
            request(),
            chat_request(stream=True),
            "request-complete",
            None,
            RequestRouter({"complete": 1}),
            None,
        )
        assert b"data: [DONE]" in await _consume(response.body_iterator)

    global_lease = await load_shedder.try_acquire_global()
    provider_lease = await load_shedder.try_acquire_provider("complete")
    assert global_lease is not None
    assert provider_lease is not None
    assert IN_FLIGHT_REQUESTS.labels(provider="complete")._value.get() == 0
    global_lease.release()
    provider_lease.release()


async def _consume(iterator) -> bytes:
    """Consume a streaming response body."""
    return b"".join([chunk async for chunk in iterator])
