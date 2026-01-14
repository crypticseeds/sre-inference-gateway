"""Test request router."""

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


def test_deterministic_routing():
    """Test deterministic provider selection."""
    weights = {"mock_openai": 0.5, "mock_vllm": 0.5}
    router = RequestRouter(weights)
    
    # Test valid provider priority
    provider = router.select_provider("mock_openai")
    assert provider is not None
    assert provider.name == "mock_openai"
    
    # Test invalid provider priority (should fall back to weighted)
    provider = router.select_provider("non_existent")
    assert provider is not None  # Should still get a provider via weighted selection


def test_weighted_routing():
    """Test weighted provider selection."""
    weights = {"mock_openai": 1.0, "mock_vllm": 0.0}
    router = RequestRouter(weights)
    
    # With 100% weight to mock_openai, should always select it
    for _ in range(10):
        provider = router.select_provider()
        assert provider is not None
        assert provider.name == "mock_openai"


def test_available_providers():
    """Test getting available providers."""
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