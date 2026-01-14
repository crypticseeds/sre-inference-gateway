"""Tests for vLLM provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers.vllm import VLLMProvider
from app.providers.base import ChatCompletionRequest, ProviderHealth


@pytest.fixture
def vllm_config():
    """vLLM provider configuration."""
    return {
        "base_url": "http://localhost:8001",
        "timeout": 30.0,
        "api_key": "EMPTY"
    }


@pytest.fixture
def vllm_provider(vllm_config):
    """Create vLLM provider instance."""
    return VLLMProvider(name="vllm", config=vllm_config)


@pytest.fixture
def sample_request():
    """Sample chat completion request."""
    return ChatCompletionRequest(
        model="facebook/opt-125m",
        messages=[{"role": "user", "content": "Hello, how are you?"}],
        temperature=0.7,
        max_tokens=100
    )


@pytest.mark.asyncio
async def test_vllm_provider_initialization(vllm_provider):
    """Test vLLM provider initialization."""
    assert vllm_provider.name == "vllm"
    assert vllm_provider.base_url == "http://localhost:8001"
    assert vllm_provider.timeout == 30.0
    assert vllm_provider.api_key == "EMPTY"


@pytest.mark.asyncio
async def test_vllm_provider_base_url_trailing_slash():
    """Test that trailing slash is removed from base_url."""
    config = {"base_url": "http://localhost:8001/", "timeout": 30.0}
    provider = VLLMProvider(name="vllm", config=config)
    assert provider.base_url == "http://localhost:8001"


@pytest.mark.asyncio
async def test_chat_completion_success(vllm_provider, sample_request):
    """Test successful chat completion."""
    mock_response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "facebook/opt-125m",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
    }
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()
    
    with patch("app.providers.vllm.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        response = await vllm_provider.chat_completion(sample_request, "test-request-id")
        
        assert response.id == "chatcmpl-123"
        assert response.model == "facebook/opt-125m"
        assert len(response.choices) == 1
        assert response.usage["total_tokens"] == 18


@pytest.mark.asyncio
async def test_chat_completion_http_error(vllm_provider, sample_request):
    """Test chat completion with HTTP error."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )
    
    with patch("app.providers.vllm.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        with pytest.raises(httpx.HTTPStatusError):
            await vllm_provider.chat_completion(sample_request, "test-id")


@pytest.mark.asyncio
async def test_chat_completion_timeout(vllm_provider, sample_request):
    """Test chat completion with timeout."""
    with patch("app.providers.vllm.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        with pytest.raises(httpx.TimeoutException):
            await vllm_provider.chat_completion(sample_request, "test-id")


@pytest.mark.asyncio
async def test_health_check_success(vllm_provider):
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    
    with patch("app.providers.vllm.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        health = await vllm_provider.health_check()
        
        assert isinstance(health, ProviderHealth)
        assert health.name == "vllm"
        assert health.healthy is True
        assert health.latency_ms >= 0
        assert health.error is None


@pytest.mark.asyncio
async def test_health_check_failure(vllm_provider):
    """Test health check failure."""
    with patch("app.providers.vllm.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        health = await vllm_provider.health_check()
        
        assert health.name == "vllm"
        assert health.healthy is False
        assert "Connection refused" in health.error
