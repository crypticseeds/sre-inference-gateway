"""Mock provider implementations for testing."""

import asyncio
import json
import time
from collections.abc import AsyncIterator

from app.providers.base import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)


class MockOpenAIAdapter(BaseProvider):
    """Mock OpenAI adapter for testing."""

    async def _chat_completion_impl(
        self, request: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """Mock chat completion response."""
        # Simulate processing delay
        await asyncio.sleep(0.1)

        return ChatCompletionResponse(
            id=request_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock OpenAI response for: {request.messages[-1].get('content', '') if request.messages else ''}",
                    },
                    "finish_reason": "stop",
                }
            ],
            usage={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
        )

    async def _health_check_impl(self) -> ProviderHealth:
        """Mock health check."""
        return ProviderHealth(name=self.name, healthy=True, latency_ms=100.0)

    async def _chat_completion_stream_impl(
        self, request: ChatCompletionRequest, request_id: str
    ) -> AsyncIterator[bytes]:
        """Create a deterministic OpenAI-compatible mock SSE stream."""
        delay = float(self.config.get("stream_chunk_delay", 0.05))
        chunk_count = int(self.config.get("stream_content_chunks", 3))
        model = self.config.get("model") or request.model
        created = int(time.time())
        text = (
            "Mock OpenAI response for: "
            f"{request.messages[-1].get('content', '') if request.messages else ''}"
        )
        chunk_count = min(chunk_count, len(text))
        chunks = [
            text[len(text) * index // chunk_count : len(text) * (index + 1) // chunk_count]
            for index in range(chunk_count)
        ]

        async def generate() -> AsyncIterator[bytes]:
            async def event(payload: object) -> bytes:
                await asyncio.sleep(delay)
                return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()

            common = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
            }
            yield await event(
                {
                    **common,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"role": "assistant", "content": ""},
                            "finish_reason": None,
                        }
                    ],
                }
            )
            for content in chunks:
                yield await event(
                    {
                        **common,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None,
                            }
                        ],
                    }
                )
            yield await event(
                {
                    **common,
                    "choices": [
                        {"index": 0, "delta": {}, "finish_reason": "stop"}
                    ],
                }
            )
            if request.stream_options and request.stream_options.get("include_usage"):
                yield await event(
                    {
                        **common,
                        "choices": [],
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 15,
                            "total_tokens": 25,
                        },
                    }
                )
            await asyncio.sleep(delay)
            yield b"data: [DONE]\n\n"

        return generate()


class MockVLLMAdapter(BaseProvider):
    """Mock vLLM adapter for testing."""

    async def _chat_completion_impl(
        self, request: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """Mock chat completion response."""
        # Simulate processing delay
        await asyncio.sleep(0.2)

        return ChatCompletionResponse(
            id=request_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"Mock vLLM response for: {request.messages[-1].get('content', '') if request.messages else ''}",
                    },
                    "finish_reason": "stop",
                }
            ],
            usage={"prompt_tokens": 12, "completion_tokens": 18, "total_tokens": 30},
        )

    async def _health_check_impl(self) -> ProviderHealth:
        """Mock health check."""
        return ProviderHealth(name=self.name, healthy=True, latency_ms=200.0)

    async def _chat_completion_stream_impl(
        self, request: ChatCompletionRequest, request_id: str
    ) -> AsyncIterator[bytes]:
        """Reuse the OpenAI-compatible mock stream format."""
        return await MockOpenAIAdapter._chat_completion_stream_impl(
            self, request, request_id
        )
