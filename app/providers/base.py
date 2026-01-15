"""Base provider abstract class."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel


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

    @abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest, request_id: str
    ) -> ChatCompletionResponse:
        """Process chat completion request.

        Args:
            request: Chat completion request
            request_id: Unique request identifier

        Returns:
            Chat completion response
        """
        pass

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check provider health.

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
