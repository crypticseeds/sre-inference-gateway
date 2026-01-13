"""Tests for health check endpoints."""

import time
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.api.health import (
    check_provider_health,
    update_provider_health_cache,
    _provider_health_cache,
    _last_health_check
)
from app.config.models import GatewayConfig, ProviderConfig


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_gateway_config():
    """Mock gateway configuration."""
    return GatewayConfig(
        providers=[
            ProviderConfig(
                name="test_provider_1",
                weight=0.6,
                enabled=True,
                health_check_url="http://localhost:8001/health"
            ),
            ProviderConfig(
                name="test_provider_2", 
                weight=0.4,
                enabled=True,
                health_check_url="http://localhost:8002/health"
            ),
            ProviderConfig(
                name="disabled_provider",
                weight=0.0,
                enabled=False,
                health_check_url="http://localhost:8003/health"
            )
        ]
    )


class TestProviderHealthCheck:
    """Test individual provider health checking."""
    
    @pytest.mark.asyncio
    async def test_healthy_provider(self):
        """Test health check for healthy provider."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await check_provider_health(
                "test_provider",
                "http://localhost:8000/health",
                timeout=5.0
            )
            
            assert result["name"] == "test_provider"
            assert result["status"] == "healthy"
            assert result["response_time"] is not None
            assert result["error"] is None
            assert "last_check" in result
    
    @pytest.mark.asyncio
    async def test_unhealthy_provider_http_error(self):
        """Test health check for provider returning HTTP error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await check_provider_health(
                "test_provider",
                "http://localhost:8000/health",
                timeout=5.0
            )
            
            assert result["name"] == "test_provider"
            assert result["status"] == "unhealthy"
            assert result["error"] == "HTTP 500"
    
    @pytest.mark.asyncio
    async def test_provider_timeout(self):
        """Test health check timeout."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
            
            result = await check_provider_health(
                "test_provider",
                "http://localhost:8000/health",
                timeout=1.0
            )
            
            assert result["name"] == "test_provider"
            assert result["status"] == "unhealthy"
            assert result["error"] == "Timeout"
    
    @pytest.mark.asyncio
    async def test_provider_connection_error(self):
        """Test health check connection error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await check_provider_health(
                "test_provider",
                "http://localhost:8000/health",
                timeout=5.0
            )
            
            assert result["name"] == "test_provider"
            assert result["status"] == "unhealthy"
            assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_provider_no_health_url(self):
        """Test health check for provider without health URL."""
        result = await check_provider_health(
            "test_provider",
            None,
            timeout=5.0
        )
        
        assert result["name"] == "test_provider"
        assert result["status"] == "healthy"
        assert result["response_time"] == 0.0
        assert result["error"] is None


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sre-inference-gateway"
        assert "timestamp" in data
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "mock_openai": {"name": "mock_openai", "status": "healthy"},
        "mock_vllm": {"name": "mock_vllm", "status": "healthy"}
    })
    def test_detailed_health_all_healthy(self, mock_update, client):
        """Test detailed health endpoint with all providers healthy."""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["providers"]["total"] == 2  # Default mock providers
        assert data["providers"]["healthy"] == 2
        assert data["providers"]["unhealthy"] == 0
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "mock_openai": {"name": "mock_openai", "status": "healthy"},
        "mock_vllm": {"name": "mock_vllm", "status": "unhealthy"}
    })
    def test_detailed_health_degraded(self, mock_update, client):
        """Test detailed health endpoint with some providers unhealthy."""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["providers"]["healthy"] == 1
        assert data["providers"]["unhealthy"] == 1
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "provider1": {"name": "provider1", "status": "unhealthy"},
        "provider2": {"name": "provider2", "status": "unhealthy"}
    })
    @patch('app.config.settings.get_gateway_config')
    def test_detailed_health_all_unhealthy(self, mock_get_config, mock_update, client):
        """Test detailed health endpoint with all providers unhealthy."""
        from app.config.models import GatewayConfig, ProviderConfig
        
        # Mock config with 2 providers to match the cache
        mock_config = GatewayConfig(
            providers=[
                ProviderConfig(name="provider1", enabled=True),
                ProviderConfig(name="provider2", enabled=True)
            ]
        )
        mock_get_config.return_value = mock_config
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["providers"]["healthy"] == 0
        assert data["providers"]["unhealthy"] == 2
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "mock_openai": {"name": "mock_openai", "status": "healthy"},
        "mock_vllm": {"name": "mock_vllm", "status": "healthy"}
    })
    def test_readiness_check_ready(self, mock_update, client):
        """Test readiness endpoint when providers are available."""
        # Use the default provider names that should be available
        response = client.get("/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert len(data["available_providers"]) > 0
        assert len(data["healthy_providers"]) > 0
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "mock_openai": {"name": "mock_openai", "status": "unhealthy"},
        "mock_vllm": {"name": "mock_vllm", "status": "unhealthy"}
    })
    def test_readiness_check_not_ready(self, mock_update, client):
        """Test readiness endpoint when no providers are healthy."""
        response = client.get("/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "not_ready"
        assert data["detail"]["healthy_count"] == 0
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "provider1": {"name": "provider1", "status": "healthy", "response_time": 0.1},
        "provider2": {"name": "provider2", "status": "unhealthy", "error": "Timeout"}
    })
    def test_provider_health_status(self, mock_update, client):
        """Test provider health status endpoint."""
        response = client.get("/health/providers")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["providers"]) == 2
        assert "last_updated" in data
        assert "timestamp" in data
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {
        "test_provider": {"name": "test_provider", "status": "healthy"}
    })
    def test_single_provider_health_found(self, mock_update, client):
        """Test single provider health endpoint for existing provider."""
        response = client.get("/health/providers/test_provider")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_provider"
        assert data["status"] == "healthy"
    
    @patch('app.api.health.update_provider_health_cache', new_callable=AsyncMock)
    @patch('app.api.health._provider_health_cache', {})
    def test_single_provider_health_not_found(self, mock_update, client):
        """Test single provider health endpoint for non-existing provider."""
        response = client.get("/health/providers/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestHealthCacheUpdate:
    """Test health cache update functionality."""
    
    @pytest.mark.asyncio
    @patch('app.api.health.get_gateway_config')
    @patch('app.api.health.check_provider_health')
    async def test_update_health_cache(self, mock_check_health, mock_get_config, mock_gateway_config):
        """Test updating provider health cache."""
        import app.api.health as health_module
        
        mock_get_config.return_value = mock_gateway_config
        
        # Mock health check results
        mock_check_health.side_effect = [
            {"name": "test_provider_1", "status": "healthy"},
            {"name": "test_provider_2", "status": "unhealthy"}
        ]
        
        # Clear cache and reset timestamp
        health_module._provider_health_cache.clear()
        health_module._last_health_check = 0
        
        await update_provider_health_cache()
        
        assert len(health_module._provider_health_cache) == 2
        assert "test_provider_1" in health_module._provider_health_cache
        assert "test_provider_2" in health_module._provider_health_cache
        assert health_module._provider_health_cache["test_provider_1"]["status"] == "healthy"
        assert health_module._provider_health_cache["test_provider_2"]["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    @patch('app.api.health.get_gateway_config')
    async def test_update_health_cache_skip_recent(self, mock_get_config, mock_gateway_config):
        """Test skipping health cache update when recently updated."""
        import app.api.health as health_module
        
        mock_get_config.return_value = mock_gateway_config
        
        # Set recent timestamp
        health_module._last_health_check = time.time()
        
        # Clear cache to verify it's not updated
        health_module._provider_health_cache.clear()
        
        await update_provider_health_cache()
        
        # Cache should still be empty since update was skipped
        assert len(health_module._provider_health_cache) == 0