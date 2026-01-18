# Configuration Models - Function and Class Signatures

## Quick Reference

This document provides a quick reference for all classes, methods, and their signatures in the `app.config.models` module.

## Class Signatures

### ProviderConfig

```python
class ProviderConfig(BaseModel):
    name: str
    type: str
    weight: float = 1.0
    enabled: bool = True
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    health_check_url: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
```

### ServerConfig

```python
class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
```

### HealthConfig

```python
class HealthConfig(BaseModel):
    check_interval: float = 30.0
    timeout: float = 5.0
    retries: int = 3
```

### LoggingConfig

```python
class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str
```

### MetricsConfig

```python
class MetricsConfig(BaseModel):
    enabled: bool = True
    port: int = 9090
```

### CircuitBreakerConfig

```python
class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: str = "Exception"
```

### RetryConfig

```python
class RetryConfig(BaseModel):
    max_attempts: int = 3
    min_wait: float = 1.0
    max_wait: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    @model_validator(mode='after')
    def validate_wait_bounds(self) -> 'RetryConfig'
```

### ResilienceConfig

```python
class ResilienceConfig(BaseModel):
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
```

### GatewayConfig

```python
class GatewayConfig(BaseModel):
    version: str = "0.1.0"
    server: ServerConfig = Field(default_factory=ServerConfig)
    providers: List[ProviderConfig] = Field(default_factory=lambda: [...])
    health: HealthConfig = Field(default_factory=HealthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    max_request_size: int = 1048576
    request_timeout: float = 30.0
    
    @field_validator("providers")
    @classmethod
    def validate_providers(cls, v: List[ProviderConfig]) -> List[ProviderConfig]
    
    def get_provider_weights(self) -> Dict[str, float]
    def get_enabled_providers(self) -> List[ProviderConfig]
```

## Method Signatures

### LoggingConfig.validate_log_level

```python
@field_validator("level")
@classmethod
def validate_log_level(cls, v: str) -> str:
    """Validate log level against standard Python logging levels.
    
    Args:
        v: Log level string (case-insensitive)
        
    Returns:
        Normalized log level (uppercase)
        
    Raises:
        ValueError: If log level is invalid
    """
```

### RetryConfig.validate_wait_bounds

```python
@model_validator(mode='after')
def validate_wait_bounds(self) -> 'RetryConfig':
    """Validate that min_wait <= max_wait.
    
    Returns:
        Self instance after validation
        
    Raises:
        ValueError: If min_wait > max_wait
    """
```

### GatewayConfig.validate_providers

```python
@field_validator("providers")
@classmethod
def validate_providers(cls, v: List[ProviderConfig]) -> List[ProviderConfig]:
    """Validate provider configurations.
    
    Args:
        v: List of provider configurations
        
    Returns:
        Validated provider list
        
    Raises:
        ValueError: If validation fails (empty list, duplicate names, no active providers)
    """
```

### GatewayConfig.get_provider_weights

```python
def get_provider_weights(self) -> Dict[str, float]:
    """Get provider weights as a dictionary.
    
    Returns:
        Dictionary mapping provider names to weights for enabled providers with weight > 0
    """
```

### GatewayConfig.get_enabled_providers

```python
def get_enabled_providers(self) -> List[ProviderConfig]:
    """Get list of enabled providers.
    
    Returns:
        List of provider configurations where enabled=True
    """
```

## Import Statements

```python
from app.config.models import (
    GatewayConfig,
    ProviderConfig,
    ServerConfig,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    CircuitBreakerConfig,
    RetryConfig,
    ResilienceConfig,
)
```

## Usage Patterns

### Basic Instantiation

```python
# With defaults
config = GatewayConfig()

# With custom values
config = GatewayConfig(
    version="1.0.0",
    server=ServerConfig(port=8080),
    providers=[
        ProviderConfig(name="openai", type="openai"),
        ProviderConfig(name="vllm", type="vllm")
    ]
)
```

### Validation Handling

```python
from pydantic import ValidationError

try:
    config = GatewayConfig(**config_data)
except ValidationError as e:
    print(f"Configuration errors: {e}")
```

### Accessing Nested Configuration

```python
config = GatewayConfig()

# Access nested values
port = config.server.port
log_level = config.logging.level
circuit_threshold = config.resilience.circuit_breaker.failure_threshold

# Use helper methods
weights = config.get_provider_weights()
enabled_providers = config.get_enabled_providers()
```

## Field Constraints Summary

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| `ProviderConfig.weight` | `float` | `>= 0.0` | Non-negative routing weight |
| `ProviderConfig.timeout` | `float` | `> 0` | Positive timeout value |
| `ProviderConfig.max_retries` | `int` | `>= 0` | Non-negative retry count |
| `ServerConfig.port` | `int` | `1-65535` | Valid port range |
| `HealthConfig.check_interval` | `float` | `> 0` | Positive interval |
| `HealthConfig.timeout` | `float` | `> 0` | Positive timeout |
| `HealthConfig.retries` | `int` | `>= 0` | Non-negative retry count |
| `MetricsConfig.port` | `int` | `1-65535` | Valid port range |
| `CircuitBreakerConfig.failure_threshold` | `int` | `>= 1` | At least one failure |
| `CircuitBreakerConfig.recovery_timeout` | `float` | `> 0` | Positive timeout |
| `RetryConfig.max_attempts` | `int` | `>= 1` | At least one attempt |
| `RetryConfig.min_wait` | `float` | `> 0` | Positive wait time |
| `RetryConfig.max_wait` | `float` | `> 0` | Positive wait time |
| `RetryConfig.exponential_base` | `float` | `> 1` | Greater than 1 for exponential growth |
| `GatewayConfig.max_request_size` | `int` | `> 0` | Positive size limit |
| `GatewayConfig.request_timeout` | `float` | `> 0` | Positive timeout |

## Validation Rules Summary

1. **Provider Validation**:
   - At least one provider must be configured
   - Provider names must be unique
   - At least one enabled provider must have weight > 0

2. **Log Level Validation**:
   - Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
   - Case-insensitive input, normalized to uppercase

3. **Wait Time Validation**:
   - `min_wait` must be <= `max_wait` in RetryConfig

4. **Port Validation**:
   - Server and metrics ports must be in range 1-65535

5. **Positive Value Validation**:
   - All timeout, interval, and size values must be > 0
   - Retry attempts and failure thresholds must be >= 1