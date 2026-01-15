"""Tests for vLLM provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers.vllm import VLLMAdapter
from app.providers.base import ChatCompletionRequest, ProviderHealth


@pytest.fixture
def vllm_config():
    """vLLM provider configuration."""
    return {
        "timeout": 30.0,
    }


@pytest.fixture
def vllm_provider(vllm_config):
    """Create vLLM adapter instance."""
    return VLLMAdapter(
        name="vllm",
        config=vllm_config,
        base_url="http://localhost:8001/v1",
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def sample_request():
    """Sample chat completion request."""
    return ChatCompletionRequest(
        model="facebook/opt-125m",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        temperature=0.7,
        max_tokens=100,
    )


@pytest.mark.asyncio
async def test_vllm_provider_initialization(vllm_provider):
    """Test vLLM provider initialization."""
    assert vllm_provider.name == "vllm"
    assert vllm_provider.base_url == "http://localhost:8001/v1"
    assert vllm_provider.timeout == 30.0
    assert vllm_provider.max_retries == 3


@pytest.mark.asyncio
async def test_vllm_provider_base_url_trailing_slash():
    """Test that trailing slash is removed from base_url."""
    provider = VLLMAdapter(
        name="vllm", config={}, base_url="http://localhost:8001/v1/", timeout=30.0
    )
    assert provider.base_url == "http://localhost:8001/v1"


@pytest.mark.asyncio
async def test_chat_completion_success(vllm_provider, sample_request):
    """Test successful chat completion."""
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

    with patch.object(vllm_provider.client, "post", return_value=mock_response):
        response = await vllm_provider.chat_completion(
            sample_request, "test-request-id"
        )

        assert response.id == "chatcmpl-123"
        assert response.model == "facebook/opt-125m"
        assert len(response.choices) == 1
        assert response.usage["total_tokens"] == 18


@pytest.mark.asyncio
async def test_chat_completion_http_error(vllm_provider, sample_request):
    """Test chat completion with HTTP error."""
    from fastapi import HTTPException

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(vllm_provider.client, "post", return_value=mock_response):
        with pytest.raises(HTTPException) as exc_info:
            await vllm_provider.chat_completion(sample_request, "test-id")

        assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_chat_completion_timeout(vllm_provider, sample_request):
    """Test chat completion with timeout."""
    from fastapi import HTTPException

    with patch.object(
        vllm_provider.client,
        "post",
        side_effect=httpx.TimeoutException("Request timeout"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await vllm_provider.chat_completion(sample_request, "test-id")

        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_health_check_success(vllm_provider):
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(vllm_provider.client, "get", return_value=mock_response):
        health = await vllm_provider.health_check()

        assert isinstance(health, ProviderHealth)
        assert health.name == "vllm"
        assert health.healthy is True
        assert health.latency_ms >= 0
        assert health.error is None


@pytest.mark.asyncio
async def test_health_check_failure(vllm_provider):
    """Test health check failure."""
    with patch.object(
        vllm_provider.client,
        "get",
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        health = await vllm_provider.health_check()

        assert health.name == "vllm"
        assert health.healthy is False
        assert "Connection refused" in health.error
