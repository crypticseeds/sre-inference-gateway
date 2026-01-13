"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import router as api_router
from app.config.settings import get_settings
from app.observability.metrics import setup_metrics
from app.observability.tracing import setup_tracing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting SRE Inference Gateway v{settings.version}")
    
    # Setup metrics only (tracing is already setup in create_app)
    setup_metrics()
    
    yield
    
    logger.info("Shutting down SRE Inference Gateway")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Setup tracing before instrumentation
    setup_tracing()
    
    app = FastAPI(
        title="SRE Inference Gateway",
        description="OpenAI-compatible API gateway with provider abstraction",
        version=settings.version,
        lifespan=lifespan,
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/v1")
    
    # Setup OpenTelemetry instrumentation after tracing is configured
    FastAPIInstrumentor.instrument_app(app)
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )