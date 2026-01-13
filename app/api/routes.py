"""FastAPI routes for the inference gateway."""

import logging

from fastapi import APIRouter, Depends, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api.completions import router as completions_router
from app.api.dependencies import get_router
from app.router.router import RequestRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# Include completions routes
router.include_router(completions_router)

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
    from fastapi import HTTPException, status
    
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