"""SSE streaming tests for the chat completions endpoint and mock provider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.observability.metrics import (
    COST_USD,
    FAILURE_COUNT,
    IN_FLIGHT_REQUESTS,
    STREAM_FIRST_BYTE,
    STREAM_INTERCHUNK,
    TOKENS,
    UNPRICED_REQUESTS,
    instrument_stream,
)
from app.providers.base import ChatCompletionRequest
from app.providers.mock import MockOpenAIAdapter
from app.providers.openai import OpenAIAdapter
from app.providers.streaming import stream_sse_response
from app.providers.vllm import VLLMAdapter


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(create_app())


@patch("app.router.router.provider_registry")
def test_streaming_passthrough_fidelity_and_headers(mock_registry, client):
    """Forward complete upstream SSE events without rewriting their bytes."""
    upstream = (
        b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"hello"}}],\n'
        b'data: "trace":"kept"}\n\n'
        b'data: {"choices":[],"usage":{"prompt_tokens":2,'
        b'"completion_tokens":1,"total_tokens":3}}\n\n'
        b"data: [DONE]\n\n"
    )

    async def chunks():
        yield upstream[:41]
        yield upstream[41:113]
        yield upstream[113:]

    provider = MagicMock()
    provider.name = "mock_openai"
    provider.chat_completion_stream = AsyncMock(return_value=chunks())
    mock_registry.get_provider.return_value = provider

    response = client.post(
        "/v1/chat/completions",
        headers={"Accept": "text/event-stream"},
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "hello"}],
            "max_completion_tokens": 8,
            "stream": True,
            "stream_options": {"include_usage": True},
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].split(";", 1)[0] == "text/event-stream"
    assert response.headers["X-Served-By"] == "mock_openai"
    assert "content-encoding" not in response.headers
    assert response.content == upstream
    forwarded = provider.chat_completion_stream.await_args.args[0]
    assert forwarded.max_completion_tokens == 8
    assert forwarded.stream_options == {"include_usage": True}


@pytest.mark.asyncio
async def test_mock_streaming_emits_content_usage_and_done():
    """The no-key mock emits multiple content events, optional usage, and DONE."""
    provider = MockOpenAIAdapter(
        "mock_openai",
        {"stream_chunk_delay": 0, "model": "mock-model"},
    )
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        max_completion_tokens=8,
        stream=True,
        stream_options={"include_usage": True},
    )

    stream = await provider.chat_completion_stream(request, "test-request")
    events = [event async for event in stream]
    payloads = [event.removeprefix(b"data: ").removesuffix(b"\n\n") for event in events]
    chunks = [json.loads(payload) for payload in payloads[:-1]]
    content = [
        choice["delta"]["content"]
        for chunk in chunks
        for choice in chunk["choices"]
        if choice["delta"].get("content")
    ]

    assert len(content) > 1
    assert chunks[-1]["usage"] == {
        "prompt_tokens": 10,
        "completion_tokens": 15,
        "total_tokens": 25,
    }
    assert payloads[-1] == b"[DONE]"


@pytest.mark.asyncio
async def test_provider_stream_forwards_bytes_without_application_buffering():
    """Transport chunks are forwarded immediately and remain byte-faithful."""
    upstream = b"data: first\ndata: second\n\ndata: [DONE]\n\n"

    class SplitStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield upstream[:8]
            yield upstream[8:29]
            yield upstream[29:]

    response = httpx.Response(200, stream=SplitStream())
    events = [event async for event in stream_sse_response(response, "test")]

    assert events == [upstream[:8], upstream[8:29], upstream[29:]]
    assert b"".join(events) == upstream


@pytest.mark.asyncio
async def test_midstream_failure_closes_cleanly_without_done():
    """Partial output is preserved and the failed upstream response is closed."""
    first_event = b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'

    class FailingStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield first_event
            raise httpx.ReadError("provider disconnected")

    provider = "truncation_test_provider"
    failures = FAILURE_COUNT.labels(
        provider=provider, error_type="mid_stream_truncation"
    )
    before = failures._value.get()
    response = httpx.Response(200, stream=FailingStream())
    close = AsyncMock(wraps=response.aclose)
    response.aclose = close

    chunks = [chunk async for chunk in stream_sse_response(response, provider)]

    assert chunks == [first_event]
    assert b"[DONE]" not in b"".join(chunks)
    close.assert_awaited_once()
    assert failures._value.get() == before + 1


@pytest.mark.asyncio
async def test_metrics_stream_wrapper_closes_source_on_early_disconnect():
    """Closing the response iterator releases its source and in-flight gauge."""
    provider = "disconnect_test_provider"
    closed = False

    async def source():
        nonlocal closed
        try:
            yield b"data: first\n\n"
            yield b"data: second\n\n"
        finally:
            closed = True

    stream = instrument_stream(source(), provider, "test-model", 0)
    assert await anext(stream) == b"data: first\n\n"
    assert IN_FLIGHT_REQUESTS.labels(provider=provider)._value.get() == 1

    await stream.aclose()

    assert closed
    assert IN_FLIGHT_REQUESTS.labels(provider=provider)._value.get() == 0


@pytest.mark.asyncio
async def test_metrics_stream_records_interchunk_latency_with_one_clock_read_per_chunk():
    """Each forwarded chunk contributes one timestamp and each gap is observed."""
    provider = "interchunk_test_provider"
    first_byte = STREAM_FIRST_BYTE.labels(provider=provider)
    interchunk = STREAM_INTERCHUNK.labels(provider=provider)
    before_first_count = sum(bucket.get() for bucket in first_byte._buckets)
    before_first_sum = first_byte._sum.get()
    before_interchunk_count = sum(bucket.get() for bucket in interchunk._buckets)
    before_interchunk_sum = interchunk._sum.get()

    async def source():
        yield b"first"
        yield b"second"
        yield b"third"

    with patch(
        "app.observability.metrics.time.monotonic",
        side_effect=[10.0, 10.05, 10.2, 10.3],
    ) as monotonic:
        chunks = [
            chunk
            async for chunk in instrument_stream(source(), provider, "test-model", 9.8)
        ]

    assert chunks == [b"first", b"second", b"third"]
    assert monotonic.call_count == len(chunks) + 1  # Final request-duration sample.
    assert sum(bucket.get() for bucket in first_byte._buckets) == before_first_count + 1
    assert first_byte._sum.get() == pytest.approx(before_first_sum + 0.2)
    assert (
        sum(bucket.get() for bucket in interchunk._buckets)
        == before_interchunk_count + 2
    )
    assert interchunk._sum.get() == pytest.approx(before_interchunk_sum + 0.2)


@pytest.mark.asyncio
async def test_metrics_stream_wrapper_cleans_up_when_source_close_fails():
    """A source close error cannot leak the in-flight gauge."""
    provider = "close_failure_test_provider"

    class FailingCloseStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

        async def aclose(self):
            raise RuntimeError("close failed")

    stream = instrument_stream(FailingCloseStream(), provider, "test-model", 0)

    with pytest.raises(RuntimeError, match="close failed"):
        await anext(stream)

    assert IN_FLIGHT_REQUESTS.labels(provider=provider)._value.get() == 0


@pytest.mark.asyncio
async def test_metrics_stream_records_usage_split_across_final_chunks():
    """The bounded tail reconstructs final usage split at chunk boundaries."""
    provider = "split_usage_test_provider"
    model = "mock-model"
    prompt = TOKENS.labels(provider=provider, model=model, type="prompt")
    completion = TOKENS.labels(provider=provider, model=model, type="completion")
    cost = COST_USD.labels(provider=provider, model=model)
    before = (prompt._value.get(), completion._value.get(), cost._value.get())

    async def source():
        yield b"x" * 3000
        yield b'\n\ndata: {"choices":[],"usa'
        yield b'ge":{"prompt_tokens":10,"completion_tokens":15,"total_tokens":25}}\n'
        yield b"\ndata: [DONE]\n\n"

    assert b"".join([chunk async for chunk in instrument_stream(source(), provider, model, 0)])
    assert prompt._value.get() == before[0] + 10
    assert completion._value.get() == before[1] + 15
    assert cost._value.get() == before[2] + 0.0000105


@pytest.mark.asyncio
async def test_metrics_stream_without_usage_records_unpriced():
    """A completed stream without provider usage is explicitly unpriced."""
    provider = "missing_stream_usage_test_provider"
    model = "mock-model"
    unpriced = UNPRICED_REQUESTS.labels(
        provider=provider, model=model, reason="missing_usage"
    )
    before = unpriced._value.get()

    async def source():
        yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    assert b"".join([chunk async for chunk in instrument_stream(source(), provider, model, 0)])
    assert unpriced._value.get() == before + 1


@pytest.mark.asyncio
async def test_incomplete_stream_does_not_record_retained_usage():
    """Usage retained before a truncated terminal sequence is not accounted."""
    provider = "truncated_usage_test_provider"
    model = "mock-model"
    prompt = TOKENS.labels(provider=provider, model=model, type="prompt")
    completion = TOKENS.labels(provider=provider, model=model, type="completion")
    cost = COST_USD.labels(provider=provider, model=model)
    before = (prompt._value.get(), completion._value.get(), cost._value.get())

    async def source():
        yield (
            b'data: {"choices":[],"usage":{"prompt_tokens":10,'
            b'"completion_tokens":15,"total_tokens":25}}\n\n'
        )

    assert b"".join([chunk async for chunk in instrument_stream(source(), provider, model, 0)])
    assert (prompt._value.get(), completion._value.get(), cost._value.get()) == before


@pytest.mark.asyncio
async def test_openai_stream_forwards_probe_options_and_disables_compression():
    """The real adapter forwards the probe fields when opening its SSE request."""
    adapter = OpenAIAdapter("openai", {}, "test-key", max_retries=1)
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        max_completion_tokens=8,
        stream=True,
        stream_options={"include_usage": True},
    )
    upstream = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b"data: [DONE]\n\n",
    )

    send = AsyncMock(return_value=upstream)
    with patch.object(adapter.client, "send", new=send):
        stream = await adapter._chat_completion_stream_impl(request, "test-request")
        assert [event async for event in stream] == [b"data: [DONE]\n\n"]

    sent_request = send.await_args.args[0]
    payload = json.loads(sent_request.content)
    assert payload["max_completion_tokens"] == 8
    assert payload["stream_options"] == {"include_usage": True}
    assert sent_request.headers["accept"] == "text/event-stream"
    assert sent_request.headers["accept-encoding"] == "identity"
    await adapter.close()


@pytest.mark.asyncio
async def test_vllm_stream_forwards_probe_options_and_disables_compression():
    """The vLLM adapter forwards the same OpenAI-compatible streaming fields."""
    adapter = VLLMAdapter("vllm", {}, max_retries=1)
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        max_completion_tokens=8,
        stream=True,
        stream_options={"include_usage": True},
    )
    upstream = httpx.Response(
        200,
        request=httpx.Request("POST", "http://localhost:8000/v1/chat/completions"),
        content=b"data: [DONE]\n\n",
    )
    send = AsyncMock(return_value=upstream)

    with patch.object(adapter.client, "send", new=send):
        stream = await adapter._chat_completion_stream_impl(request, "test-request")
        assert [event async for event in stream] == [b"data: [DONE]\n\n"]

    sent_request = send.await_args.args[0]
    payload = json.loads(sent_request.content)
    assert payload["max_completion_tokens"] == 8
    assert payload["stream_options"] == {"include_usage": True}
    assert sent_request.headers["accept"] == "text/event-stream"
    assert sent_request.headers["accept-encoding"] == "identity"
    await adapter.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("adapter_type", [OpenAIAdapter, VLLMAdapter])
async def test_provider_stream_error_body_is_read_and_closed(adapter_type):
    """Both real adapters release non-success streaming responses."""
    if adapter_type is OpenAIAdapter:
        adapter = adapter_type("provider", {}, "test-key", max_retries=1)
    else:
        adapter = adapter_type("provider", {}, max_retries=1)
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    upstream = MagicMock()
    upstream.status_code = 503
    upstream.text = "unavailable"
    upstream.aread = AsyncMock(return_value=b"unavailable")
    upstream.aclose = AsyncMock()
    upstream.raise_for_status.side_effect = httpx.HTTPStatusError(
        "unavailable",
        request=httpx.Request("POST", "http://provider/chat/completions"),
        response=upstream,
    )

    with patch.object(adapter.client, "send", new=AsyncMock(return_value=upstream)):
        with pytest.raises(Exception):
            await adapter._chat_completion_stream_impl(request, "test-request")

    upstream.aread.assert_awaited_once()
    upstream.aclose.assert_awaited_once()
    await adapter.close()


@pytest.mark.asyncio
async def test_openai_stream_maps_authentication_failure():
    """Streaming preserves the adapter's existing authentication error policy."""
    adapter = OpenAIAdapter("openai", {}, "test-key", max_retries=1)
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    upstream = httpx.Response(
        401,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b"unauthorized",
    )

    with patch.object(adapter.client, "send", new=AsyncMock(return_value=upstream)):
        with pytest.raises(Exception) as exc_info:
            await adapter._chat_completion_stream_impl(request, "test-request")

    assert exc_info.value.status_code == 500
    assert "authentication" in exc_info.value.detail
    await adapter.close()


@pytest.mark.asyncio
async def test_openai_stream_retries_rate_limit_before_headers():
    """A 429 can be retried safely before downstream streaming starts."""
    adapter = OpenAIAdapter("openai", {}, "test-key", max_retries=2)
    request = ChatCompletionRequest(
        model="mock-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=True,
    )
    rate_limited = httpx.Response(
        429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b"rate limited",
    )
    successful = httpx.Response(
        200,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
        content=b"data: [DONE]\n\n",
    )
    send = AsyncMock(side_effect=[rate_limited, successful])

    with (
        patch.object(adapter.client, "send", new=send),
        patch("app.providers.openai.asyncio.sleep", new=AsyncMock()) as sleep,
    ):
        stream = await adapter._chat_completion_stream_impl(request, "test-request")
        assert [event async for event in stream] == [b"data: [DONE]\n\n"]

    assert send.await_count == 2
    sleep.assert_awaited_once_with(1)
    await adapter.close()
