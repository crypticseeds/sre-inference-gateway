"""Test real provider adapters (OpenAI and vLLM).

This module provides comprehensive unit tests for the OpenAI and vLLM provider
adapters, as well as the provider factory. Tests validate adapter behavior,
error handling, health checks, and factory instantiation patterns using mocked
HTTP responses.

Test Coverage:
    - OpenAI adapter chat completion (success and error cases)
    - OpenAI adapter health checks
    - OpenAI adapter timeout and retry logic
    - vLLM adapter chat completion (success and error cases)
    - vLLM adapter health checks
    - vLLM adapter service unavailability handling
    - Provider factory instantiation from configuration
    - Provider factory error handling

Key Features:
    - All tests use mocked HTTP responses (no external API calls)
    - Async test support via pytest-asyncio
    - Proper resource cleanup in all test cases
    - Comprehensive error condition testing
    - Factory pattern validation

Example Usage:
    Run all tests:
        pytest tests/test_real_providers.py -v

    Run specific test class:
        pytest tests/test_real_providers.py::TestOpenAIAdapter -v

    Run with coverage:
        pytest tests/test_real_providers.py --cov=app.providers

Fixtures:
    - chat_request: Standard test chat completion request
    - mock_openai_response: Mock OpenAI API response data

Test Classes:
    - TestOpenAIAdapter: Tests for OpenAI adapter implementation
    - TestVLLMAdapter: Tests for vLLM adapter implementation
    - TestProviderFactory: Tests for provider factory pattern

Note:
    These tests are designed to run without external dependencies and are
    suitable for CI/CD pipelines. All HTTP requests are mocked using
    unittest.mock.
"""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.config.models import ProviderConfig
from app.providers.base import ChatCompletionRequest
from app.providers.factory import ProviderFactory
from app.providers.openai import OpenAIAdapter
from app.providers.vllm import VLLMAdapter  # pylint: disable=no-name-in-module


@pytest.fixture
def chat_request():
    """Create test chat request.

    Returns:
        ChatCompletionRequest: Test request with standard parameters:
            - model: "gpt-3.5-turbo"
            - messages: Single user message "Hello, world!"
            - temperature: 0.7
            - max_tokens: 100

    Example:
        ```python
        def test_example(chat_request):
            response = await adapter.chat_completion(chat_request, "test-123")
            assert response.model == "gpt-3.5-turbo"
        ```
    """
    return ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, world!"}],
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def mock_openai_response():
    """Create mock OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello! How can I help?"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


class TestOpenAIAdapter:
    """Test OpenAI adapter implementation."""

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, chat_request, mock_openai_response):  # pylint: disable=redefined-outer-name
        """Test successful OpenAI chat completion."""
        adapter = OpenAIAdapter(
            name="test_openai",
            config={},
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            timeout=30.0,
        )

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openai_response

        with patch.object(adapter.client, "post", return_value=mock_response):
            response = await adapter.chat_completion(chat_request, "test-123")

        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-3.5-turbo"
        assert len(response.choices) == 1

        await adapter.close()

    @pytest.mark.asyncio
    async def test_chat_completion_timeout(self, chat_request):  # pylint: disable=redefined-outer-name
        """Test OpenAI timeout handling."""
        adapter = OpenAIAdapter(
            name="test_openai",
            config={},
            api_key="test-key",
            timeout=30.0,
            max_retries=2,
        )

        with patch.object(
            adapter.client, "post", side_effect=httpx.TimeoutException("Timeout")
        ):
            with pytest.raises(Exception) as exc_info:
                await adapter.chat_completion(chat_request, "test-123")

            assert "timeout" in str(exc_info.value).lower()

        await adapter.close()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test OpenAI health check success."""
        adapter = OpenAIAdapter(
            name="test_openai",
            config={},
            api_key="test-key",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(adapter.client, "get", return_value=mock_response):
            health = await adapter.health_check()

        assert health.healthy is True
        assert health.name == "test_openai"
        assert health.latency_ms is not None

        await adapter.close()


class TestVLLMAdapter:
    """Test vLLM adapter implementation."""

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, chat_request, mock_openai_response):  # pylint: disable=redefined-outer-name
        """Test successful vLLM chat completion."""
        adapter = VLLMAdapter(
            name="test_vllm",
            config={},
            base_url="http://localhost:8000/v1",
            timeout=30.0,
        )

        # Mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openai_response

        with patch.object(adapter.client, "post", return_value=mock_response):
            response = await adapter.chat_completion(chat_request, "test-456")

        assert response.id == "chatcmpl-123"
        assert len(response.choices) == 1

        await adapter.close()

    @pytest.mark.asyncio
    async def test_chat_completion_service_unavailable(self, chat_request):  # pylint: disable=redefined-outer-name
        """Test vLLM service unavailable handling."""
        adapter = VLLMAdapter(
            name="test_vllm",
            config={},
            timeout=30.0,
            max_retries=2,
        )

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(adapter.client, "post", return_value=mock_response):
            with pytest.raises(Exception) as exc_info:
                await adapter.chat_completion(chat_request, "test-456")

            assert (
                "503" in str(exc_info.value)
                or "unavailable" in str(exc_info.value).lower()
            )

        await adapter.close()

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test vLLM health check success."""
        adapter = VLLMAdapter(
            name="test_vllm",
            config={},
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(adapter.client, "get", return_value=mock_response):
            health = await adapter.health_check()

        assert health.healthy is True
        assert health.name == "test_vllm"
        assert health.latency_ms is not None

        await adapter.close()


class TestProviderFactory:
    """Test provider factory."""

    def test_create_openai_adapter(self):
        """Test creating OpenAI adapter from config."""
        config = ProviderConfig(
            name="openai",
            type="openai",
            base_url="https://api.openai.com/v1",
            api_key_env="TEST_OPENAI_KEY",
            timeout=30.0,
        )

        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "test-key"}):
            adapter = ProviderFactory.create_provider(config)

        assert isinstance(adapter, OpenAIAdapter)
        assert adapter.name == "openai"

    def test_create_vllm_adapter(self):
        """Test creating vLLM adapter from config."""
        config = ProviderConfig(
            name="vllm",
            type="vllm",
            base_url="http://localhost:8000/v1",
            timeout=30.0,
        )

        adapter = ProviderFactory.create_provider(config)

        assert isinstance(adapter, VLLMAdapter)
        assert adapter.name == "vllm"

    def test_create_openai_adapter_missing_api_key(self):
        """Test OpenAI adapter creation fails without API key."""
        config = ProviderConfig(
            name="openai",
            type="openai",
            api_key_env="MISSING_KEY",
        )

        with pytest.raises(ValueError, match="API key not found"):
            ProviderFactory.create_provider(config)

    def test_create_unknown_provider_type(self):
        """Test factory raises error for unknown provider type."""
        config = ProviderConfig(
            name="unknown",
            type="unknown_type",
        )

        with pytest.raises(ValueError, match="Unknown provider type"):
            ProviderFactory.create_provider(config)
