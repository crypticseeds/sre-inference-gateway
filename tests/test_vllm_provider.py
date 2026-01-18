"""Tests for vLLM provider adapter implementation.

This module provides comprehensive unit tests for the VLLMAdapter class,
validating initialization, chat completion requests, error handling, and
health monitoring using mocked HTTP responses.

Test Coverage:
    - VLLMAdapter initialization and configuration
    - Chat completion request handling (success and error cases)
    - HTTP error handling (timeouts, server errors, service unavailable)
    - Health check functionality (success and failure scenarios)
    - Base URL normalization

Example Usage:
    Run all vLLM provider tests:
        doppler run -- uv run pytest tests/test_vllm_provider.py -v

    Run specific test:
        doppler run -- uv run pytest tests/test_vllm_provider.py::test_chat_completion_success -v
"""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import httpx
from fastapi import HTTPException

from app.providers.vllm import VLLMAdapter
from app.providers.base import ChatCompletionRequest, ProviderHealth


@pytest.fixture
def vllm_config():
    """Create vLLM provider configuration for testing.

    Returns:
        dict: Configuration dictionary with timeout setting.
    """
    return {
        "timeout": 30.0,
    }


@pytest.fixture
def vllm_provider(vllm_config):
    """Create vLLM adapter instance for testing.

    Args:
        vllm_config: Configuration fixture for the adapter.

    Returns:
        VLLMAdapter: Configured adapter instance for testing.
    """
    return VLLMAdapter(
        name="vllm",
        config=vllm_config,
        base_url="http://localhost:8080/v1",
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def sample_request():
    """Create sample chat completion request for testing.

    Returns:
        ChatCompletionRequest: Test request with standard parameters.
    """
    return ChatCompletionRequest(
        model="facebook/opt-125m",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        temperature=0.7,
        max_tokens=100,
    )


@pytest.mark.asyncio
async def test_vllm_provider_initialization(vllm_provider):
    """Test vLLM provider initialization with correct configuration.

    Verifies that the VLLMAdapter initializes with the expected
    configuration values including name, base_url, timeout, and max_retries.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
    """
    assert vllm_provider.name == "vllm"
    assert vllm_provider.base_url == "http://localhost:8080/v1"
    assert vllm_provider.timeout == 30.0
    assert vllm_provider.max_retries == 3


@pytest.mark.asyncio
async def test_vllm_provider_base_url_trailing_slash():
    """Test that trailing slash is removed from base_url during initialization.

    Verifies that the VLLMAdapter properly normalizes base URLs by
    removing trailing slashes to ensure consistent URL formatting.
    """
    provider = VLLMAdapter(
        name="vllm",
        config={},
        base_url="http://localhost:8080/v1/",
        timeout=30.0,
        max_retries=3,
    )
    assert provider.base_url == "http://localhost:8080/v1"


@pytest.mark.asyncio
async def test_chat_completion_success(vllm_provider, sample_request):
    """Test successful chat completion request handling.

    Verifies that the VLLMAdapter correctly processes a successful
    chat completion request and returns the expected response format.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
        sample_request: ChatCompletionRequest fixture.
    """
    mock_response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "facebook/opt-125m",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data

    with patch.object(
        vllm_provider.client, "post", new=AsyncMock(return_value=mock_response)
    ):
        response = await vllm_provider._chat_completion_impl(
            sample_request, "test-request-id"
        )

        assert response.id == "chatcmpl-123"
        assert response.model == "facebook/opt-125m"
        assert len(response.choices) == 1
        assert response.usage["total_tokens"] == 18


@pytest.mark.asyncio
async def test_chat_completion_http_error(vllm_provider, sample_request):
    """Test chat completion handling of HTTP server errors.

    Verifies that the VLLMAdapter properly handles HTTP 500 errors
    by raising an HTTPException with the appropriate status code.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
        sample_request: ChatCompletionRequest fixture.
    """
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(
        vllm_provider.client, "post", new=AsyncMock(return_value=mock_response)
    ):
        with pytest.raises(HTTPException) as exc_info:
            await vllm_provider._chat_completion_impl(sample_request, "test-id")

        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_chat_completion_timeout(vllm_provider, sample_request):
    """Test chat completion handling of request timeouts.

    Verifies that the VLLMAdapter properly handles timeout exceptions
    by raising an HTTPException with status code 504.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
        sample_request: ChatCompletionRequest fixture.
    """
    with patch.object(
        vllm_provider.client,
        "post",
        new=AsyncMock(side_effect=httpx.TimeoutException("Request timeout")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await vllm_provider._chat_completion_impl(sample_request, "test-id")

        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_health_check_success(vllm_provider):
    """Test successful health check operation.

    Verifies that the VLLMAdapter correctly performs health checks
    and returns a healthy status with valid latency measurements.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(
        vllm_provider.client, "get", new=AsyncMock(return_value=mock_response)
    ):
        health = await vllm_provider._health_check_impl()

        assert isinstance(health, ProviderHealth)
        assert health.name == "vllm"
        assert health.healthy is True
        assert health.latency_ms >= 0
        assert health.error is None


@pytest.mark.asyncio
async def test_health_check_failure(vllm_provider):
    """Test health check failure handling.

    Verifies that the VLLMAdapter properly handles connection failures
    during health checks and returns an unhealthy status with error details.

    Args:
        vllm_provider: VLLMAdapter fixture instance.
    """
    with patch.object(
        vllm_provider.client,
        "get",
        new=AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
    ):
        health = await vllm_provider._health_check_impl()

        assert health.name == "vllm"
        assert health.healthy is False
        assert "Connection refused" in health.error
