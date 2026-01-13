"""Mock provider implementations for testing."""

import asyncio
import time
from typing import Any, Dict

from app.providers.base import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)


class MockOpenAIProvider(BaseProvider):
    """Mock OpenAI provider for testing."""
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest,
        request_id: str
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
                        "content": f"Mock OpenAI response for: {request.messages[-1].get('content', '')}"
                    },
                    "finish_reason": "stop"
                }
            ],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        )
    
    async def health_check(self) -> ProviderHealth:
        """Mock health check."""
        return ProviderHealth(
            name=self.name,
            healthy=True,
            latency_ms=100.0
        )


class MockVLLMProvider(BaseProvider):
    """Mock vLLM provider for testing."""
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest,
        request_id: str
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
                        "content": f"Mock vLLM response for: {request.messages[-1].get('content', '')}"
                    },
                    "finish_reason": "stop"
                }
            ],
            usage={
                "prompt_tokens": 12,
                "completion_tokens": 18,
                "total_tokens": 30
            }
        )
    
    async def health_check(self) -> ProviderHealth:
        """Mock health check."""
        return ProviderHealth(
            name=self.name,
            healthy=True,
            latency_ms=200.0
        )