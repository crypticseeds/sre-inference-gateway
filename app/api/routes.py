"""FastAPI routes for the inference gateway."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from opentelemetry import trace
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api.dependencies import (
    get_provider_priority,
    get_request_id,
    get_router,
    setup_request_context,
)
from app.providers.base import ChatCompletionRequest, ChatCompletionResponse
from app.router.router import RequestRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_completions(
    request: Request,
    chat_request: ChatCompletionRequest,
    request_id: str = Depends(get_request_id),
    provider_priority: Optional[str] = Depends(get_provider_priority),
    request_router: RequestRouter = Depends(get_router),
    _: None = Depends(setup_request_context),
) -> ChatCompletionResponse:
    """Handle chat completion requests.
    
    Args:
        request: FastAPI request object
        chat_request: Chat completion request
        request_id: Request ID
        provider_priority: Optional provider priority
        request_router: Request router instance
        
    Returns:
        Chat completion response
        
    Raises:
        HTTPException: If no providers available or provider error
    """
    span = trace.get_current_span()
    
    try:
        # Select provider
        provider = request_router.select_provider(provider_priority)
        if not provider:
            logger.error(f"No available providers for request {request_id}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No inference providers available"
            )
        
        # Add provider info to span
        if span:
            span.set_attribute("provider.name", provider.name)
            span.set_attribute("chat.model", chat_request.model)
            span.set_attribute("chat.stream", chat_request.stream)
        
        logger.info(
            f"Processing request {request_id} with provider {provider.name} "
            f"for model {chat_request.model}"
        )
        
        # Process request
        response = await provider.chat_completion(chat_request, request_id)
        
        logger.info(f"Completed request {request_id} successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        if span:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.
    
    Returns:
        Health status
    """
    return {"status": "healthy", "service": "sre-inference-gateway"}


@router.get("/ready")
async def readiness_check(
    request_router: RequestRouter = Depends(get_router)
) -> dict:
    """Readiness check endpoint.
    
    Args:
        request_router: Request router instance
        
    Returns:
        Readiness status with available providers
        
    Raises:
        HTTPException: If no providers are available (503 Service Unavailable)
    """
    available_providers = request_router.get_available_providers()
    
    response_data = {
        "status": "ready" if available_providers else "not_ready",
        "available_providers": available_providers,
        "provider_count": len(available_providers),
    }
    
    # Return 503 if no providers are available
    if not available_providers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response_data
        )
    
    return response_data


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Returns:
        Prometheus metrics in text format
    """
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )