"""Test main application."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint displays application information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "sre-inference-gateway"
    assert data["version"] == "0.1.0"
    assert data["developer"] == "Femi Akinlotan"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sre-inference-gateway"


@patch("app.api.health.update_provider_health_cache", new_callable=AsyncMock)
@patch(
    "app.api.health._provider_health_cache",
    {
        "mock_openai": {"name": "mock_openai", "status": "healthy"},
        "mock_vllm": {"name": "mock_vllm", "status": "healthy"},
    },
)
@patch("app.router.router.provider_registry")
def test_readiness_endpoint(mock_registry, mock_update, client):
    """Test readiness endpoint."""
    # Mock the provider registry to return providers
    mock_registry.get_provider.side_effect = lambda name: (
        MagicMock() if name in ["mock_openai", "mock_vllm"] else None
    )

    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "available_providers" in data
    assert "provider_count" in data


@patch("app.router.router.provider_registry")
def test_chat_completions_endpoint(mock_registry, client):
    """Test chat completions endpoint."""
    # Setup mock provider with async chat_completion method
    mock_provider = MagicMock()
    mock_provider.name = "mock_openai"
    mock_provider.chat_completion = AsyncMock(
        return_value=MagicMock(
            id="test-id",
            object="chat.completion",
            created=1234567890,
            model="gpt-3.5-turbo",
            choices=[
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
    )

    mock_registry.get_provider.side_effect = lambda name: (
        mock_provider if name in ["mock_openai", "mock_vllm"] else None
    )

    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello, world!"}],
    }

    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert "object" in data
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert "usage" in data
