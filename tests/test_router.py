"""Test request router."""

from unittest.mock import MagicMock, patch

import pytest

from app.router.router import RequestRouter


def test_router_initialization():
    """Test router initialization."""
    weights = {"mock_openai": 0.6, "mock_vllm": 0.4}
    router = RequestRouter(weights)

    # Weights should be normalized
    assert abs(sum(router.provider_weights.values()) - 1.0) < 1e-10


def test_router_validation():
    """Test router weight validation."""
    # Empty weights should raise error
    with pytest.raises(ValueError, match="Provider weights cannot be empty"):
        RequestRouter({})

    # Zero weights should raise error
    with pytest.raises(ValueError, match="Total provider weights must be positive"):
        RequestRouter({"mock_openai": 0.0, "mock_vllm": 0.0})


@patch("app.router.router.provider_registry")
def test_deterministic_routing(mock_registry):
    """Test deterministic provider selection."""
    # Setup mock providers
    mock_openai = MagicMock()
    mock_openai.name = "mock_openai"
    mock_vllm = MagicMock()
    mock_vllm.name = "mock_vllm"

    mock_registry.get_provider.side_effect = lambda name: {
        "mock_openai": mock_openai,
        "mock_vllm": mock_vllm,
    }.get(name)

    weights = {"mock_openai": 0.5, "mock_vllm": 0.5}
    router = RequestRouter(weights)

    # Test valid provider priority
    provider = router.select_provider("mock_openai")
    assert provider is not None
    assert provider.name == "mock_openai"

    # Test invalid provider priority (should fall back to weighted)
    provider = router.select_provider("non_existent")
    assert provider is not None  # Should still get a provider via weighted selection


@patch("app.router.router.provider_registry")
def test_weighted_routing(mock_registry):
    """Test weighted provider selection."""
    # Setup mock provider
    mock_openai = MagicMock()
    mock_openai.name = "mock_openai"

    mock_registry.get_provider.side_effect = lambda name: (
        mock_openai if name == "mock_openai" else None
    )

    weights = {"mock_openai": 1.0, "mock_vllm": 0.0}
    router = RequestRouter(weights)

    # With 100% weight to mock_openai, should always select it
    for _ in range(10):
        provider = router.select_provider()
        assert provider is not None
        assert provider.name == "mock_openai"


@patch("app.router.router.provider_registry")
def test_available_providers(mock_registry):
    """Test getting available providers."""
    # Setup mock providers - only mock_openai and mock_vllm exist
    mock_openai = MagicMock()
    mock_openai.name = "mock_openai"
    mock_vllm = MagicMock()
    mock_vllm.name = "mock_vllm"

    mock_registry.get_provider.side_effect = lambda name: {
        "mock_openai": mock_openai,
        "mock_vllm": mock_vllm,
    }.get(name)

    weights = {"mock_openai": 0.5, "mock_vllm": 0.5, "non_existent": 0.0}
    router = RequestRouter(weights)

    available = router.get_available_providers()
    assert "mock_openai" in available
    assert "mock_vllm" in available
    assert "non_existent" not in available  # Not in registry


def test_update_weights():
    """Test updating router weights."""
    weights = {"mock_openai": 0.5, "mock_vllm": 0.5}
    router = RequestRouter(weights)

    new_weights = {"mock_openai": 0.8, "mock_vllm": 0.2}
    router.update_weights(new_weights)

    # Check weights are updated and normalized
    assert abs(router.provider_weights["mock_openai"] - 0.8) < 1e-10
    assert abs(router.provider_weights["mock_vllm"] - 0.2) < 1e-10
