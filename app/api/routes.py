"""FastAPI routes for the inference gateway."""

import logging

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.api.completions import router as completions_router

logger = logging.getLogger(__name__)
router = APIRouter()

# Include completions routes
router.include_router(completions_router)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.

    Returns:
        Prometheus metrics in text format
    """
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
