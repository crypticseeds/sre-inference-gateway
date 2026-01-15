"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import router as api_router
from app.api.health import router as health_router
from app.config.settings import (
    get_settings,
    get_gateway_config,
    start_config_watching,
    stop_config_watching,
)
from app.observability.metrics import setup_metrics
from app.observability.tracing import setup_tracing
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    logger.info(f"Starting SRE Inference Gateway v{settings.version}")
    
    # Setup metrics only (tracing is already setup in create_app)
    setup_metrics()
    
    # Initialize providers from configuration
    try:
        gateway_config = get_gateway_config()
        provider_registry.initialize_from_config(gateway_config.providers)
        logger.info(f"Initialized {len(provider_registry.list_providers())} providers")
    except Exception as e:
        logger.error(f"Failed to initialize providers: {e}")
        # Continue startup even if providers fail - allows health checks to report issues
    
    # Start configuration file watching for hot-reload (only if event loop is running)
    try:
        start_config_watching()
        logger.info("Started configuration file watching")
    except Exception as e:
        logger.warning(f"Could not start config watching: {e}")
    
    yield
    
    # Close all provider connections
    try:
        await provider_registry.close_all()
        logger.info("Closed all provider connections")
    except Exception as e:
        logger.warning(f"Error closing providers: {e}")
    
    # Stop configuration file watching
    try:
        stop_config_watching()
        logger.info("Stopped configuration file watching")
    except Exception as e:
        logger.warning(f"Error stopping config watching: {e}")
    
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
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with application information."""
        return {
            "app": "sre-inference-gateway",
            "version": settings.version,
            "docs": "/docs",
            "health": "/health",
            "developer": "Femi Akinlotan"
        }
    
    # Include API routes
    app.include_router(api_router, prefix="/v1")
    
    # Include health check routes (no prefix for standard health endpoints)
    app.include_router(health_router)
    
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