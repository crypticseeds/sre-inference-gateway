"""Base provider abstract class."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.router.resilience import execute_with_resilience


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""

    model: str
    messages: list[Dict[str, Any]]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stream: bool = False
    user: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Dict[str, Any]]
    usage: Dict[str, int]


class ProviderHealth(BaseModel):
    """Provider health status."""

    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for inference providers."""

    def __init__(self, name: str, config: Dict[str, Any]):
        """Initialize provider.

        Args:
            name: Provider name
            config: Provider configuration
        """
        self.name = name
        self.config = config

    async def chat_completion(
        self, request: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """Process chat completion request with resilience patterns.

        Args:
            request: Chat completion request
            request_id: Unique request identifier

        Returns:
            Chat completion response
        """
        # Get resilience config from gateway config
        from app.config.settings import get_gateway_config

        gateway_config = get_gateway_config()
        resilience_config = gateway_config.resilience

        # Execute with resilience patterns
        return await execute_with_resilience(
            self._chat_completion_impl,
            self.name,
            resilience_config,
            request,
            request_id,
        )

    @abstractmethod
    async def _chat_completion_impl(
        self, request: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """Internal chat completion implementation.

        This method should be implemented by concrete providers and will be
        wrapped with resilience patterns by the public chat_completion method.

        Args:
            request: Chat completion request
            request_id: Unique request identifier

        Returns:
            Chat completion response
        """
        pass

    async def health_check(self) -> ProviderHealth:
        """Check provider health with resilience patterns.

        Returns:
            Provider health status
        """
        # Get resilience config from gateway config
        from app.config.settings import get_gateway_config

        gateway_config = get_gateway_config()
        resilience_config = gateway_config.resilience

        # Execute with resilience patterns
        return await execute_with_resilience(
            self._health_check_impl,
            self.name,
            resilience_config,
        )

    @abstractmethod
    async def _health_check_impl(self) -> ProviderHealth:
        """Internal health check implementation.

        This method should be implemented by concrete providers and will be
        wrapped with resilience patterns by the public health_check method.

        Returns:
            Provider health status
        """
        pass

    def generate_request_id(self) -> str:
        """Generate unique request ID.

        Returns:
            Unique request identifier
        """
        return f"chatcmpl-{uuid.uuid4().hex[:29]}"
