"""Test provider implementations."""

import pytest

from app.providers.base import ChatCompletionRequest
from app.providers.mock import MockOpenAIProvider, MockVLLMProvider
from app.providers.registry import ProviderRegistry


@pytest.fixture
def chat_request():
    """Create test chat request."""
    return ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}]
    )


@pytest.mark.asyncio
async def test_mock_openai_provider(chat_request):
    """Test mock OpenAI provider."""
    provider = MockOpenAIProvider("test_openai", {})
    request_id = "test-123"
    
    response = await provider.chat_completion(chat_request, request_id)
    
    assert response.id == request_id
    assert response.model == chat_request.model
    assert len(response.choices) == 1
    assert response.choices[0]["message"]["role"] == "assistant"
    assert "Mock OpenAI response" in response.choices[0]["message"]["content"]


@pytest.mark.asyncio
async def test_mock_vllm_provider(chat_request):
    """Test mock vLLM provider."""
    provider = MockVLLMProvider("test_vllm", {})
    request_id = "test-456"
    
    response = await provider.chat_completion(chat_request, request_id)
    
    assert response.id == request_id
    assert response.model == chat_request.model
    assert len(response.choices) == 1
    assert response.choices[0]["message"]["role"] == "assistant"
    assert "Mock vLLM response" in response.choices[0]["message"]["content"]


@pytest.mark.asyncio
async def test_provider_health_checks():
    """Test provider health checks."""
    openai_provider = MockOpenAIProvider("test_openai", {})
    vllm_provider = MockVLLMProvider("test_vllm", {})
    
    openai_health = await openai_provider.health_check()
    vllm_health = await vllm_provider.health_check()
    
    assert openai_health.healthy is True
    assert openai_health.name == "test_openai"
    assert openai_health.latency_ms == 100.0
    
    assert vllm_health.healthy is True
    assert vllm_health.name == "test_vllm"
    assert vllm_health.latency_ms == 200.0


def test_provider_registry():
    """Test provider registry."""
    from app.config.models import ProviderConfig
    
    registry = ProviderRegistry()
    
    # Initialize with mock providers
    mock_configs = [
        ProviderConfig(name="mock_openai", type="mock", enabled=True),
        ProviderConfig(name="mock_vllm", type="mock", enabled=True),
    ]
    
    registry.initialize_from_config(mock_configs)
    
    # Check providers are registered
    providers = registry.list_providers()
    assert "mock_openai" in providers
    assert "mock_vllm" in providers
    
    # Test getting providers
    openai_provider = registry.get_provider("mock_openai")
    assert openai_provider is not None
    assert openai_provider.name == "mock_openai"
    
    # Test non-existent provider
    non_existent = registry.get_provider("non_existent")
    assert non_existent is None