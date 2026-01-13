"""Application settings using Pydantic Settings."""

import logging
from functools import lru_cache
from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Provider Configuration
    provider_weights: Dict[str, float] = Field(
        default_factory=lambda: {"mock_openai": 0.5, "mock_vllm": 0.5},
        description="Provider routing weights"
    )
    
    # Request Processing
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum request size in bytes"
    )
    request_timeout: float = Field(
        default=30.0,
        description="Request timeout in seconds"
    )
    
    # Health Check
    health_check_interval: float = Field(
        default=30.0,
        description="Health check interval in seconds"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


def setup_logging() -> None:
    """Setup application logging."""
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )