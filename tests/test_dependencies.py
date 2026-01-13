"""Test FastAPI dependencies."""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from opentelemetry.trace import Span

from app.api.dependencies import (
    get_request_id,
    get_provider_priority,
    get_router,
    setup_request_context,
)
from app.router.router import RequestRouter


class TestGetRequestId:
    """Test get_request_id dependency."""
    
    def test_with_custom_header(self):
        """Test request ID extraction from header."""
        custom_id = "custom-request-123"
        result = get_request_id(custom_id)
        assert result == custom_id
    
    def test_without_header(self):
        """Test request ID generation when no header provided."""
        result = get_request_id(None)
        assert result.startswith("req-")
        assert len(result) == 20  # "req-" + 16 hex chars
    
    def test_generated_ids_are_unique(self):
        """Test that generated IDs are unique."""
        id1 = get_request_id(None)
        id2 = get_request_id(None)
        assert id1 != id2


class TestGetProviderPriority:
    """Test get_provider_priority dependency."""
    
    def test_with_provider_header(self):
        """Test provider priority extraction from header."""
        provider = "mock_openai"
        result = get_provider_priority(provider)
        assert result == provider
    
    def test_without_header(self):
        """Test provider priority when no header provided."""
        result = get_provider_priority(None)
        assert result is None
    
    def test_with_empty_header(self):
        """Test provider priority with empty header."""
        result = get_provider_priority("")
        assert result == ""


class TestGetRouter:
    """Test get_router dependency."""
    
    @patch('app.api.dependencies.get_settings')
    def test_router_creation(self, mock_get_settings):
        """Test router creation with settings."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.provider_weights = {"mock_openai": 0.5, "mock_vllm": 0.5}
        mock_get_settings.return_value = mock_settings
        
        router = get_router()
        
        assert isinstance(router, RequestRouter)
        assert router.provider_weights == {"mock_openai": 0.5, "mock_vllm": 0.5}
    
    @patch('app.api.dependencies.get_settings')
    def test_router_with_different_weights(self, mock_get_settings):
        """Test router creation with different provider weights."""
        # Mock settings with different weights
        mock_settings = Mock()
        mock_settings.provider_weights = {"mock_openai": 0.8, "mock_vllm": 0.2}
        mock_get_settings.return_value = mock_settings
        
        router = get_router()
        
        assert isinstance(router, RequestRouter)
        # Weights should be normalized
        assert abs(sum(router.provider_weights.values()) - 1.0) < 0.001


class TestSetupRequestContext:
    """Test setup_request_context dependency."""
    
    @patch('app.api.dependencies.trace.get_current_span')
    def test_with_recording_span(self, mock_get_span):
        """Test context setup with recording span."""
        # Mock span
        mock_span = Mock(spec=Span)
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = "http://localhost:8000/v1/chat/completions"
        mock_request.state = Mock()
        
        request_id = "test-request-123"
        
        # Call function
        setup_request_context(mock_request, request_id)
        
        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("request.id", request_id)
        mock_span.set_attribute.assert_any_call("request.method", "POST")
        mock_span.set_attribute.assert_any_call(
            "request.url", 
            "http://localhost:8000/v1/chat/completions"
        )
        
        # Verify request state was set
        assert mock_request.state.request_id == request_id
    
    @patch('app.api.dependencies.trace.get_current_span')
    def test_with_non_recording_span(self, mock_get_span):
        """Test context setup with non-recording span."""
        # Mock non-recording span
        mock_span = Mock(spec=Span)
        mock_span.is_recording.return_value = False
        mock_get_span.return_value = mock_span
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        
        request_id = "test-request-456"
        
        # Call function
        setup_request_context(mock_request, request_id)
        
        # Verify span attributes were NOT set
        mock_span.set_attribute.assert_not_called()
        
        # Verify request state was still set
        assert mock_request.state.request_id == request_id
    
    @patch('app.api.dependencies.trace.get_current_span')
    def test_with_no_span(self, mock_get_span):
        """Test context setup when no span is available."""
        # Mock no span
        mock_get_span.return_value = None
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        
        request_id = "test-request-789"
        
        # Should not raise exception
        setup_request_context(mock_request, request_id)
        
        # Verify request state was set
        assert mock_request.state.request_id == request_id


class TestDependencyIntegration:
    """Test dependencies working together."""
    
    @patch('app.api.dependencies.get_settings')
    @patch('app.api.dependencies.trace.get_current_span')
    def test_full_dependency_chain(self, mock_get_span, mock_get_settings):
        """Test all dependencies working together."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.provider_weights = {"mock_openai": 1.0}
        mock_get_settings.return_value = mock_settings
        
        mock_span = Mock(spec=Span)
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span
        
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url = "http://localhost:8000/v1/chat/completions"
        mock_request.state = Mock()
        
        # Call dependencies in order
        request_id = get_request_id("custom-id")
        provider_priority = get_provider_priority("mock_openai")
        router = get_router()
        setup_request_context(mock_request, request_id)
        
        # Verify results
        assert request_id == "custom-id"
        assert provider_priority == "mock_openai"
        assert isinstance(router, RequestRouter)
        assert mock_request.state.request_id == request_id
        
        # Verify span was configured
        mock_span.set_attribute.assert_any_call("request.id", request_id)