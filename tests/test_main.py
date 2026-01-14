"""Test main application."""

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
    assert data["App"] == "sre-inference-gateway"
    assert data["Version"] == "0.1.0"
    assert data["Developer"] == "Femi Akinlotan"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


def test_health_endpoint(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "sre-inference-gateway"


def test_readiness_endpoint(client):
    """Test readiness endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "available_providers" in data
    assert "provider_count" in data


def test_chat_completions_endpoint(client):
    """Test chat completions endpoint."""
    request_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, world!"}
        ]
    }
    
    response = client.post("/v1/chat/completions", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert "object" in data
    assert data["object"] == "chat.completion"
    assert "choices" in data
    assert "usage" in data