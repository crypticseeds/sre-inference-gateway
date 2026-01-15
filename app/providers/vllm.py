"""vLLM provider implementation."""

import time
from typing import Any, Dict

import httpx
from opentelemetry import trace

from app.providers.base import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)

tracer = trace.get_tracer(__name__)


class VLLMProvider(BaseProvider):
    """vLLM provider for local inference.
    
    Connects to vLLM service running with OpenAI-compatible API.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize vLLM provider.
        
        Args:
            name: Provider name
            config: Provider configuration with base_url and timeout
        """
        super().__init__(name, config)
        self.base_url = config.get("base_url", "http://localhost:8001")
        self.timeout = config.get("timeout", 30.0)
        self.api_key = config.get("api_key", "EMPTY")
        self.base_url = self.base_url.rstrip("/")
    
    async def chat_completion(
        self, 
        request: ChatCompletionRequest,
        request_id: str
    ) -> ChatCompletionResponse:
        """Process chat completion request via vLLM."""
        with tracer.start_as_current_span(
            "vllm_chat_completion",
            attributes={
                "provider": self.name,
                "model": request.model,
                "request_id": request_id,
            }
        ):
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": request.model,
                    "messages": request.messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "top_p": request.top_p,
                    "frequency_penalty": request.frequency_penalty,
                    "presence_penalty": request.presence_penalty,
                    "stream": request.stream,
                }
                payload = {k: v for k, v in payload.items() if v is not None}
                if request.user:
                    payload["user"] = request.user
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return ChatCompletionResponse(
                    id=data.get("id", request_id),
                    object=data.get("object", "chat.completion"),
                    created=data.get("created", int(time.time())),
                    model=data.get("model", request.model),
                    choices=data.get("choices", []),
                    usage=data.get("usage", {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    })
                )
    
    async def health_check(self) -> ProviderHealth:
        """Check vLLM service health."""
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                latency_ms = (time.time() - start_time) * 1000
                return ProviderHealth(
                    name=self.name,
                    healthy=True,
                    latency_ms=latency_ms
                )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ProviderHealth(
                name=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e)
            )
