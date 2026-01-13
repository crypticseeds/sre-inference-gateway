"""FastAPI dependencies for request processing."""

import uuid
from typing import Optional

from fastapi import Depends, Header, Request
from opentelemetry import trace

from app.config.settings import get_settings
from app.router.router import RequestRouter


def get_request_id(x_request_id: Optional[str] = Header(None)) -> str:
    """Get or generate request ID.
    
    Args:
        x_request_id: Optional request ID from header
        
    Returns:
        Request ID
    """
    if x_request_id:
        return x_request_id
    return f"req-{uuid.uuid4().hex[:16]}"


def get_provider_priority(
    x_provider_priority: Optional[str] = Header(None)
) -> Optional[str]:
    """Get provider priority from header.
    
    Args:
        x_provider_priority: Optional provider priority from header
        
    Returns:
        Provider priority or None
    """
    return x_provider_priority


def get_router() -> RequestRouter:
    """Get request router instance.
    
    Returns:
        RequestRouter instance
    """
    settings = get_settings()
    return RequestRouter(settings.provider_weights)


def setup_request_context(
    request: Request,
    request_id: str = Depends(get_request_id),
) -> None:
    """Setup request context for tracing.
    
    Args:
        request: FastAPI request object
        request_id: Request ID
    """
    # Add request ID to OpenTelemetry span
    span = trace.get_current_span()
    if span:
        span.set_attribute("request.id", request_id)
        span.set_attribute("request.method", request.method)
        span.set_attribute("request.url", str(request.url))
    
    # Store request ID in request state for access in handlers
    request.state.request_id = request_id