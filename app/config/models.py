"""Configuration models using Pydantic."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    name: str = Field(..., description="Provider name")
    type: str = Field(..., description="Provider type (openai, vllm, mock)")
    weight: float = Field(default=1.0, ge=0.0, description="Routing weight")
    enabled: bool = Field(default=True, description="Whether provider is enabled")
    base_url: Optional[str] = Field(default=None, description="Provider base URL")
    api_key_env: Optional[str] = Field(
        default=None, description="Environment variable name for API key"
    )
    health_check_url: Optional[str] = Field(
        default=None, description="Health check endpoint URL"
    )
    timeout: float = Field(default=30.0, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, ge=1, le=65535, description="Port to bind to")
    debug: bool = Field(default=False, description="Enable debug mode")


class HealthConfig(BaseModel):
    """Health check configuration."""

    check_interval: float = Field(
        default=30.0, gt=0, description="Health check interval in seconds"
    )
    timeout: float = Field(
        default=5.0, gt=0, description="Health check timeout in seconds"
    )
    retries: int = Field(default=3, ge=0, description="Number of health check retries")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Logging level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    enabled: bool = Field(default=True, description="Enable metrics collection")
    port: int = Field(default=9090, ge=1, le=65535, description="Metrics server port")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(
        default=5, ge=1, description="Number of failures before opening circuit"
    )
    recovery_timeout: float = Field(
        default=60.0, gt=0, description="Time in seconds before attempting recovery"
    )
    expected_exception: str = Field(
        default="Exception", description="Exception type to trigger circuit breaker"
    )


class RetryConfig(BaseModel):
    """Retry configuration."""

    max_attempts: int = Field(default=3, ge=1, description="Maximum retry attempts")
    min_wait: float = Field(
        default=1.0, gt=0, description="Minimum wait time between retries in seconds"
    )
    max_wait: float = Field(
        default=10.0, gt=0, description="Maximum wait time between retries in seconds"
    )
    exponential_base: float = Field(
        default=2.0, gt=1, description="Exponential backoff base multiplier"
    )
    jitter: bool = Field(default=True, description="Add random jitter to wait times")

    @model_validator(mode="after")
    def validate_wait_bounds(self):
        """Validate that min_wait <= max_wait."""
        if self.min_wait > self.max_wait:
            raise ValueError(
                f"min_wait ({self.min_wait}) must be less than or equal to max_wait ({self.max_wait})"
            )
        return self


class ResilienceConfig(BaseModel):
    """Resilience patterns configuration."""

    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)


class GatewayConfig(BaseModel):
    """Main gateway configuration."""

    version: str = Field(default="0.1.0", description="Application version")
    server: ServerConfig = Field(default_factory=ServerConfig)
    providers: List[ProviderConfig] = Field(
        default_factory=lambda: [
            ProviderConfig(name="mock_openai", type="mock", weight=0.5),
            ProviderConfig(name="mock_vllm", type="mock", weight=0.5),
        ],
        description="Provider configurations",
    )
    health: HealthConfig = Field(default_factory=HealthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)

    # Request processing
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        gt=0,
        description="Maximum request size in bytes",
    )
    request_timeout: float = Field(
        default=30.0, gt=0, description="Request timeout in seconds"
    )

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v):
        """Validate provider configurations."""
        if not v:
            raise ValueError("At least one provider must be configured")

        # Check for duplicate provider names
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("Provider names must be unique")

        # Check that at least one provider has weight > 0
        total_weight = sum(p.weight for p in v if p.enabled)
        if total_weight <= 0:
            raise ValueError("At least one enabled provider must have weight > 0")

        return v

    def get_provider_weights(self) -> Dict[str, float]:
        """Get provider weights as a dictionary."""
        return {p.name: p.weight for p in self.providers if p.enabled and p.weight > 0}

    def get_enabled_providers(self) -> List[ProviderConfig]:
        """Get list of enabled providers."""
        return [p for p in self.providers if p.enabled]
