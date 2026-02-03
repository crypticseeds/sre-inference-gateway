# Configuration Models API Documentation

## Overview

The `app.config.models` module provides Pydantic-based configuration models for the SRE Inference Gateway. These models define the structure, validation rules, and default values for all configuration aspects of the gateway, including providers, server settings, health checks, logging, metrics, and resilience patterns.

## Table of Contents

- [Module Overview](#module-overview)
- [Configuration Models](#configuration-models)
- [Validation Rules](#validation-rules)
- [Usage Examples](#usage-examples)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)

## Module Overview

**Module**: `app.config.models`

**Dependencies**:
- `pydantic`: Data validation and settings management
- `typing`: Type hints for better code documentation

**Key Features**:
- Comprehensive validation using Pydantic
- Type safety with Python type hints
- Default values for all optional fields
- Custom validation methods for complex rules
- Hierarchical configuration structure

## Configuration Models

### ProviderConfig

Configuration model for individual inference providers (OpenAI, vLLM, mock).

#### Class Definition

```python
class ProviderConfig(BaseModel):
    """Configuration for a single provider."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `name` | `str` | Required | - | Provider identifier for routing and logging |
| `type` | `str` | Required | - | Provider type: "openai", "vllm", or "mock" |
| `weight` | `float` | `1.0` | `>= 0.0` | Routing weight for load balancing |
| `enabled` | `bool` | `True` | - | Whether provider is active |
| `base_url` | `Optional[str]` | `None` | - | Provider API base URL |
| `api_key_env` | `Optional[str]` | `None` | - | Environment variable name for API key |
| `health_check_url` | `Optional[str]` | `None` | - | Health check endpoint URL |
| `timeout` | `float` | `30.0` | `> 0` | Request timeout in seconds |
| `max_retries` | `int` | `3` | `>= 0` | Maximum retry attempts |

#### Usage Examples

```python
from app.config.models import ProviderConfig

# Basic provider configuration
provider = ProviderConfig(
    name="openai-gpt4",
    type="openai"
)

# Full provider configuration
provider = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    weight=0.7,
    enabled=True,
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
    health_check_url="https://api.openai.com/v1/models",
    timeout=60.0,
    max_retries=5
)

# vLLM provider configuration
vllm_provider = ProviderConfig(
    name="vllm-local",
    type="vllm",
    weight=0.3,
    base_url="http://localhost:8000/v1",
    timeout=90.0
)
```

### ServerConfig

Configuration model for FastAPI server binding and behavior.

#### Class Definition

```python
class ServerConfig(BaseModel):
    """Server configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `host` | `str` | `"0.0.0.0"` | - | Host address to bind to |
| `port` | `int` | `8000` | `1-65535` | Port number to bind to |
| `debug` | `bool` | `False` | - | Enable debug mode |

#### Usage Examples

```python
from app.config.models import ServerConfig

# Default server configuration
server = ServerConfig()

# Custom server configuration
server = ServerConfig(
    host="127.0.0.1",
    port=9000,
    debug=True
)

# Production server configuration
prod_server = ServerConfig(
    host="0.0.0.0",
    port=8080,
    debug=False
)
```

### HealthConfig

Configuration model for provider health monitoring.

#### Class Definition

```python
class HealthConfig(BaseModel):
    """Health check configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `check_interval` | `float` | `30.0` | `> 0` | Health check interval in seconds |
| `timeout` | `float` | `5.0` | `> 0` | Health check timeout in seconds |
| `retries` | `int` | `3` | `>= 0` | Number of health check retries |

#### Usage Examples

```python
from app.config.models import HealthConfig

# Default health configuration
health = HealthConfig()

# Custom health configuration
health = HealthConfig(
    check_interval=60.0,
    timeout=10.0,
    retries=5
)

# Fast health checks for development
dev_health = HealthConfig(
    check_interval=10.0,
    timeout=2.0,
    retries=1
)
```

### LoggingConfig

Configuration model for application logging.

#### Class Definition

```python
class LoggingConfig(BaseModel):
    """Logging configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `level` | `str` | `"INFO"` | Valid log levels | Logging level |
| `format` | `str` | Standard format | - | Log format string |

#### Validation Methods

##### `validate_log_level(cls, v)`

Validates that the log level is one of the standard Python logging levels.

**Parameters**:
- `v` (str): Log level string

**Returns**:
- `str`: Normalized log level (uppercase)

**Raises**:
- `ValueError`: If log level is invalid

**Valid Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

#### Usage Examples

```python
from app.config.models import LoggingConfig

# Default logging configuration
logging = LoggingConfig()

# Custom logging configuration
logging = LoggingConfig(
    level="DEBUG",
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Case-insensitive level setting
logging = LoggingConfig(level="info")  # Normalized to "INFO"
```

### MetricsConfig

Configuration model for Prometheus metrics collection.

#### Class Definition

```python
class MetricsConfig(BaseModel):
    """Metrics configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `enabled` | `bool` | `True` | - | Enable metrics collection |
| `port` | `int` | `9090` | `1-65535` | Metrics server port |

#### Usage Examples

```python
from app.config.models import MetricsConfig

# Default metrics configuration
metrics = MetricsConfig()

# Custom metrics configuration
metrics = MetricsConfig(
    enabled=True,
    port=9091
)

# Disabled metrics for testing
test_metrics = MetricsConfig(enabled=False)
```

### CircuitBreakerConfig

Configuration model for circuit breaker resilience pattern.

#### Class Definition

```python
class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `failure_threshold` | `int` | `5` | `>= 1` | Number of failures before opening circuit |
| `recovery_timeout` | `float` | `60.0` | `> 0` | Time in seconds before attempting recovery |
| `expected_exception` | `str` | `"Exception"` | - | Exception type to trigger circuit breaker |

#### Usage Examples

```python
from app.config.models import CircuitBreakerConfig

# Default circuit breaker configuration
circuit_breaker = CircuitBreakerConfig()

# Aggressive circuit breaker for production
prod_circuit_breaker = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception="HTTPException"
)

# Lenient circuit breaker for development
dev_circuit_breaker = CircuitBreakerConfig(
    failure_threshold=10,
    recovery_timeout=15.0
)
```

### RetryConfig

Configuration model for retry logic with exponential backoff.

#### Class Definition

```python
class RetryConfig(BaseModel):
    """Retry configuration."""
```

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `max_attempts` | `int` | `3` | `>= 1` | Maximum retry attempts |
| `min_wait` | `float` | `1.0` | `> 0` | Minimum wait time between retries in seconds |
| `max_wait` | `float` | `10.0` | `> 0` | Maximum wait time between retries in seconds |
| `exponential_base` | `float` | `2.0` | `> 1` | Exponential backoff base multiplier |
| `jitter` | `bool` | `True` | - | Add random jitter to wait times |

#### Validation Methods

##### `validate_wait_bounds(self)`

Validates that `min_wait` is less than or equal to `max_wait`.

**Returns**:
- `self`: The validated instance

**Raises**:
- `ValueError`: If `min_wait > max_wait`

#### Usage Examples

```python
from app.config.models import RetryConfig

# Default retry configuration
retry = RetryConfig()

# Aggressive retry configuration
aggressive_retry = RetryConfig(
    max_attempts=5,
    min_wait=0.5,
    max_wait=30.0,
    exponential_base=1.5,
    jitter=True
)

# Conservative retry configuration
conservative_retry = RetryConfig(
    max_attempts=2,
    min_wait=2.0,
    max_wait=5.0,
    exponential_base=2.0,
    jitter=False
)
```

### ResilienceConfig

Configuration model combining circuit breaker and retry patterns.

#### Class Definition

```python
class ResilienceConfig(BaseModel):
    """Resilience patterns configuration."""
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `circuit_breaker` | `CircuitBreakerConfig` | `CircuitBreakerConfig()` | Circuit breaker configuration |
| `retry` | `RetryConfig` | `RetryConfig()` | Retry configuration |

#### Usage Examples

```python
from app.config.models import (
    ResilienceConfig,
    CircuitBreakerConfig,
    RetryConfig
)

# Default resilience configuration
resilience = ResilienceConfig()

# Custom resilience configuration
resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=45.0
    ),
    retry=RetryConfig(
        max_attempts=4,
        min_wait=0.5,
        max_wait=20.0
    )
)
```

### GatewayConfig

Main configuration model that combines all other configuration models.

#### Class Definition

```python
class GatewayConfig(BaseModel):
    """Main gateway configuration."""
```

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `version` | `str` | `"0.1.0"` | Application version |
| `server` | `ServerConfig` | `ServerConfig()` | Server configuration |
| `providers` | `List[ProviderConfig]` | Default mock providers | Provider configurations |
| `health` | `HealthConfig` | `HealthConfig()` | Health check configuration |
| `logging` | `LoggingConfig` | `LoggingConfig()` | Logging configuration |
| `metrics` | `MetricsConfig` | `MetricsConfig()` | Metrics configuration |
| `resilience` | `ResilienceConfig` | `ResilienceConfig()` | Resilience patterns configuration |
| `max_request_size` | `int` | `1048576` (1MB) | Maximum request size in bytes |
| `request_timeout` | `float` | `30.0` | Request timeout in seconds |

#### Validation Methods

##### `validate_providers(cls, v)`

Validates provider configurations to ensure:
- At least one provider is configured
- Provider names are unique
- At least one enabled provider has weight > 0

**Parameters**:
- `v` (List[ProviderConfig]): List of provider configurations

**Returns**:
- `List[ProviderConfig]`: Validated provider list

**Raises**:
- `ValueError`: If validation fails

#### Instance Methods

##### `get_provider_weights(self) -> Dict[str, float]`

Returns a dictionary mapping provider names to their weights for enabled providers with weight > 0.

**Returns**:
- `Dict[str, float]`: Provider name to weight mapping

**Example**:
```python
config = GatewayConfig(
    providers=[
        ProviderConfig(name="openai", type="openai", weight=0.7),
        ProviderConfig(name="vllm", type="vllm", weight=0.3),
        ProviderConfig(name="disabled", type="mock", weight=0.5, enabled=False)
    ]
)

weights = config.get_provider_weights()
# Returns: {"openai": 0.7, "vllm": 0.3}
```

##### `get_enabled_providers(self) -> List[ProviderConfig]`

Returns a list of enabled provider configurations.

**Returns**:
- `List[ProviderConfig]`: List of enabled providers

**Example**:
```python
config = GatewayConfig(
    providers=[
        ProviderConfig(name="openai", type="openai", enabled=True),
        ProviderConfig(name="vllm", type="vllm", enabled=True),
        ProviderConfig(name="disabled", type="mock", enabled=False)
    ]
)

enabled = config.get_enabled_providers()
# Returns: [ProviderConfig(name="openai", ...), ProviderConfig(name="vllm", ...)]
```

#### Usage Examples

```python
from app.config.models import (
    GatewayConfig,
    ProviderConfig,
    ServerConfig,
    ResilienceConfig,
    CircuitBreakerConfig,
    RetryConfig
)

# Default gateway configuration
config = GatewayConfig()

# Custom gateway configuration
config = GatewayConfig(
    version="1.0.0",
    server=ServerConfig(
        host="0.0.0.0",
        port=8080,
        debug=False
    ),
    providers=[
        ProviderConfig(
            name="openai-gpt4",
            type="openai",
            weight=0.7,
            api_key_env="OPENAI_API_KEY",
            timeout=60.0
        ),
        ProviderConfig(
            name="vllm-local",
            type="vllm",
            weight=0.3,
            base_url="http://localhost:8000/v1",
            timeout=90.0
        )
    ],
    resilience=ResilienceConfig(
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0
        ),
        retry=RetryConfig(
            max_attempts=5,
            min_wait=0.5,
            max_wait=20.0
        )
    ),
    max_request_size=2 * 1024 * 1024,  # 2MB
    request_timeout=60.0
)
```

## Validation Rules

### Provider Validation

1. **Non-empty providers list**: At least one provider must be configured
2. **Unique provider names**: No duplicate provider names allowed
3. **Active providers**: At least one enabled provider must have weight > 0

### Numeric Constraints

1. **Positive values**: All timeout, interval, and size values must be > 0
2. **Port ranges**: Ports must be between 1 and 65535
3. **Weight constraints**: Provider weights must be >= 0
4. **Retry constraints**: max_attempts >= 1, exponential_base > 1

### String Validation

1. **Log levels**: Must be valid Python logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
2. **Case normalization**: Log levels are normalized to uppercase

### Cross-field Validation

1. **Wait time bounds**: min_wait must be <= max_wait in RetryConfig

## Usage Examples

### Basic Configuration

```python
from app.config.models import GatewayConfig

# Create with defaults
config = GatewayConfig()

# Access nested configurations
print(f"Server port: {config.server.port}")
print(f"Log level: {config.logging.level}")
print(f"Circuit breaker threshold: {config.resilience.circuit_breaker.failure_threshold}")
```

### YAML Configuration Loading

```python
import yaml
from app.config.models import GatewayConfig

# Load from YAML
with open("config.yaml", "r") as f:
    config_data = yaml.safe_load(f)

config = GatewayConfig(**config_data)
```

### Environment-Specific Configurations

```python
# Development configuration
dev_config = GatewayConfig(
    server=ServerConfig(debug=True),
    logging=LoggingConfig(level="DEBUG"),
    resilience=ResilienceConfig(
        circuit_breaker=CircuitBreakerConfig(failure_threshold=10),
        retry=RetryConfig(max_attempts=5)
    )
)

# Production configuration
prod_config = GatewayConfig(
    server=ServerConfig(debug=False),
    logging=LoggingConfig(level="INFO"),
    resilience=ResilienceConfig(
        circuit_breaker=CircuitBreakerConfig(failure_threshold=3),
        retry=RetryConfig(max_attempts=3)
    )
)
```

### Configuration Validation

```python
from pydantic import ValidationError

try:
    # This will raise ValidationError
    invalid_config = GatewayConfig(
        providers=[],  # Empty providers list
        server=ServerConfig(port=0)  # Invalid port
    )
except ValidationError as e:
    print(f"Configuration errors: {e}")
```

## Integration Patterns

### With ConfigManager

```python
from app.config.settings import ConfigManager

manager = ConfigManager("config.yaml")
config = manager.load_config()  # Returns GatewayConfig instance
```

### With FastAPI Dependency Injection

```python
from fastapi import Depends
from app.config.models import GatewayConfig
from app.config.settings import get_gateway_config

@app.get("/status")
async def get_status(config: GatewayConfig = Depends(get_gateway_config)):
    return {
        "version": config.version,
        "providers": len(config.providers),
        "debug": config.server.debug
    }
```

### With Provider Factory

```python
from app.providers.factory import ProviderFactory

for provider_config in config.providers:
    if provider_config.enabled:
        provider = ProviderFactory.create_provider(provider_config)
```

## Best Practices

### 1. Use Type Hints

```python
from app.config.models import GatewayConfig

def configure_app(config: GatewayConfig) -> None:
    """Configure application with type safety."""
    pass
```

### 2. Validate Early

```python
from pydantic import ValidationError

def load_config(config_data: dict) -> GatewayConfig:
    """Load and validate configuration early."""
    try:
        return GatewayConfig(**config_data)
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
```

### 3. Use Environment-Specific Defaults

```python
import os

def create_config() -> GatewayConfig:
    """Create configuration with environment-specific defaults."""
    is_production = os.getenv("ENVIRONMENT") == "production"
    
    return GatewayConfig(
        server=ServerConfig(debug=not is_production),
        logging=LoggingConfig(level="INFO" if is_production else "DEBUG")
    )
```

### 4. Document Configuration Changes

```python
# When adding new configuration fields, update:
# 1. This documentation
# 2. Example configuration files
# 3. Tests in tests/test_config.py
# 4. Migration guides if breaking changes
```

### 5. Use Sensible Defaults

```python
# Provide defaults that work out of the box
class MyConfig(BaseModel):
    timeout: float = Field(default=30.0, gt=0)  # Reasonable default
    retries: int = Field(default=3, ge=0)       # Safe default
```

## See Also

- [Configuration Manager](../app/config/settings.py) - Configuration loading and management
- [Configuration Tests](../tests/test_config.py) - Comprehensive test suite
- [Resilience Configuration Guide](RESILIENCE_CONFIG.md) - Detailed resilience patterns documentation
- [Provider Implementation Guide](PROVIDERS.md) - Provider configuration usage
- [Environment Configuration](ENVIRONMENT.md) - Environment variable handling

## Summary

The configuration models provide:

- ✅ **Type Safety**: Full Pydantic validation with type hints
- ✅ **Comprehensive Coverage**: All system components configurable
- ✅ **Sensible Defaults**: Working out-of-the-box configuration
- ✅ **Validation**: Input validation with clear error messages
- ✅ **Flexibility**: Environment and use-case specific configuration
- ✅ **Documentation**: Extensive field descriptions and examples
- ✅ **Integration**: Seamless integration with other system components

These models form the foundation of the gateway's configuration system, ensuring type safety, validation, and maintainability across all configuration aspects.