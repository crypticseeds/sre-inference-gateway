"""Pydantic models for request and response validation.

This module provides centralized access to all Pydantic models used throughout
the SRE Inference Gateway for request validation, response serialization, and
data transfer objects.

Models:
    ChatCompletionRequest: OpenAI-compatible chat completion request model
    ChatCompletionResponse: OpenAI-compatible chat completion response model
    ProviderHealth: Provider health status model

Usage:
    from app.models import ChatCompletionRequest, ChatCompletionResponse

    # Create a chat completion request
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    # Create a response
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        created=1234567890,
        model="gpt-3.5-turbo",
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": "Hi there!"},
            "finish_reason": "stop"
        }],
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    )
"""

# Import models from their source modules
from app.providers.base import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)

# Export all models for external use
__all__ = [
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ProviderHealth",
]
