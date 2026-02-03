# Configuration Models Summary

## Overview

This document provides a comprehensive overview of all configuration models in the SRE Inference Gateway, including the recently added resilience patterns configuration. The configuration system uses Pydantic models for validation, type safety, and automatic documentation generation.

## Configuration Architecture

```
GatewayConfig (Root)
├── version: str
├── server: ServerConfig
├── providers: List[ProviderConfig]
├── health: HealthConfig
├── logging: LoggingConfig
├── metrics: MetricsConfig
├── resilience: ResilienceConfig (NEW)
├── max_request_size: int
└── request_timeout: float
```

## Configuration Models

### Core Models

#### `ProviderConfig`
Configures individual inference providers (OpenAI, vLLM, mock).

**Key Attributes:**
- `name`: Provider identifier
- `type`: Provider type (openai, vllm, mock)
- `weight`: Routing weight for load balancing
- `enabled`: Whether provider is active
- `timeout`: Request timeout in seconds
- `max_retries`: Maximum retry attempts

#### `ServerConfig`
Configures FastAPI server binding.

**Key Attributes:**
- `host`: Host address to bind (default: "0.0.0.0")
- `port`: Port number (default: 8000)
- `debug`: Debug mode flag (default: False)

#### `HealthConfig`
Configures provider health monitoring.

**Key Attributes:**
- `check_interval`: Time between health checks (default: 30.0s)
- `timeout`: Health check timeout (default: 5.0s)
- `retries`: Number of health check retries (default: 3)

#### `LoggingConfig`
Configures application logging.

**Key Attributes:**
- `level`: Log level (default: "INFO")
- `format`: Log format string

#### `MetricsConfig`
Configures Prometheus metrics collection.

**Key Attributes:**
- `enabled`: Enable metrics collection (default: True)
- `port`: Metrics server port (default: 9090)

### Resilience Models (NEW)

#### `CircuitBreakerConfig`
Configures circuit breaker pattern to prevent cascading failures.

**Key Attributes:**
- `failure_threshold`: Failures before opening circuit (default: 5)
- `recovery_timeout`: Time before attempting recovery (default: 60.0s)
- `expected_exception`: Exception type to trigger breaker (default: "Exception")

**Purpose:** Prevents overwhelming failing services by temporarily stopping requests after a threshold of failures.

#### `RetryConfig`
Configures retry logic with exponential backoff and jitter.

**Key Attributes:**
- `max_attempts`: Maximum retry attempts (default: 3)
- `min_wait`: Minimum wait time between retries (default: 1.0s)
- `max_wait`: Maximum wait time between retries (default: 10.0s)
- `exponential_base`: Backoff multiplier (default: 2.0)
- `jitter`: Add randomization to wait times (default: True)

**Purpose:** Handles transient failures gracefully with intelligent backoff strategies.

#### `ResilienceConfig`
Container for all resilience pattern configurations.

**Key Attributes:**
- `circuit_breaker`: CircuitBreakerConfig instance
- `retry`: RetryConfig instance

**Purpose:** Provides unified interface for configuring all resilience patterns.

### Root Model

#### `GatewayConfig`
Main configuration container that includes all other configuration models.

**Key Features:**
- Validates provider configurations (unique names, at least one enabled)
- Provides helper methods for provider management
- Includes request processing limits
- Integrates all subsystem configurations

## Configuration Examples

### Basic Configuration

```yaml
version: "1.0.0"
server:
  host: "0.0.0.0"
  port: 8000
providers:
  - name: "openai-gpt4"
    type: "openai"
    weight: 1.0
    enabled: true
```

### Production Configuration with Resilience

```yaml
version: "1.0.0"
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

providers:
  - name: "openai-gpt4"
    type: "openai"
    weight: 0.7
    enabled: true
    api_key_env: "OPENAI_API_KEY"
    timeout: 30.0
    max_retries: 3

  - name: "vllm-local"
    type: "vllm"
    weight: 0.3
    enabled: true
    base_url: "http://localhost:8000/v1"
    timeout: 60.0
    max_retries: 5

health:
  check_interval: 30.0
  timeout: 5.0
  retries: 3

logging:
  level: "INFO"

metrics:
  enabled: true
  port: 9090

resilience:
  circuit_breaker:
    failure_threshold: 3
    recovery_timeout: 45.0
    expected_exception: "HTTPException"
  retry:
    max_attempts: 4
    min_wait: 0.5
    max_wait: 20.0
    exponential_base: 1.8
    jitter: true

max_request_size: 1048576
request_timeout: 30.0
```

### Environment-Specific Configurations

#### Development
```yaml
resilience:
  circuit_breaker:
    failure_threshold: 10  # Higher threshold for dev
    recovery_timeout: 15.0
  retry:
    max_attempts: 5
    min_wait: 0.1
    max_wait: 5.0
```

#### Production
```yaml
resilience:
  circuit_breaker:
    failure_threshold: 3   # Lower threshold for prod
    recovery_timeout: 60.0
  retry:
    max_attempts: 3
    min_wait: 1.0
    max_wait: 30.0
```

## Validation Rules

### Provider Validation
- At least one provider must be configured
- Provider names must be unique
- At least one enabled provider must have weight > 0

### Resilience Validation
- `failure_threshold` must be >= 1
- `recovery_timeout` must be > 0
- `max_attempts` must be >= 1
- `min_wait` and `max_wait` must be > 0
- `exponential_base` must be > 1

### Server Validation
- `port` must be between 1 and 65535
- `host` must be a valid address

## Usage Patterns

### Programmatic Configuration

```python
from app.config.models import (
    GatewayConfig,
    ResilienceConfig,
    CircuitBreakerConfig,
    RetryConfig
)

# Create custom resilience configuration
resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0
    ),
    retry=RetryConfig(
        max_attempts=3,
        jitter=True
    )
)

# Create gateway configuration
config = GatewayConfig(
    version="2.0.0",
    resilience=resilience
)
```

### YAML Configuration Loading

```python
from app.config.settings import ConfigManager

manager = ConfigManager("config.yaml")
config = manager.load_config()

# Access resilience settings
print(f"Circuit breaker threshold: {config.resilience.circuit_breaker.failure_threshold}")
print(f"Max retry attempts: {config.resilience.retry.max_attempts}")
```

### Configuration Validation

```python
from pydantic import ValidationError

try:
    config = GatewayConfig(**config_data)
    print("Configuration is valid")
except ValidationError as e:
    print(f"Configuration errors: {e}")
```

## Testing

The configuration system includes comprehensive test coverage:

- **Unit Tests**: Individual model validation
- **Integration Tests**: YAML loading and parsing
- **Validation Tests**: Error condition handling
- **Default Tests**: Verify default values

### Running Configuration Tests

```bash
# Run all configuration tests
uv run pytest tests/test_config.py -v

# Run resilience-specific tests
uv run pytest tests/test_config.py -k "CircuitBreaker or Retry or Resilience" -v

# Run with coverage
uv run pytest tests/test_config.py --cov=app.config
```

## Best Practices

### 1. Environment-Specific Settings
Use different configurations for development, staging, and production environments.

### 2. Validation First
Always validate configuration before using it in production.

### 3. Sensible Defaults
Rely on built-in defaults for most settings, override only when necessary.

### 4. Documentation
Document any custom configuration values and their rationale.

### 5. Testing
Test configuration changes in non-production environments first.

## Related Documentation

- [Resilience Configuration Guide](RESILIENCE_CONFIG.md) - Detailed resilience patterns documentation
- [Provider Implementation Guide](PROVIDERS.md) - Provider-specific configuration
- [Health Check API](HEALTH_API.md) - Health monitoring configuration
- [Architecture Overview](ARCHITECTURE.md) - System configuration architecture

## Migration Guide

### Adding Resilience Configuration to Existing Deployments

If you have existing configuration files, the resilience settings are optional and will use sensible defaults:

```yaml
# Existing configuration - no changes needed
version: "1.0.0"
providers:
  - name: "openai"
    type: "openai"
    weight: 1.0

# Resilience settings will use defaults:
# - failure_threshold: 5
# - recovery_timeout: 60.0
# - max_attempts: 3
# - exponential backoff with jitter
```

To customize resilience settings, add the `resilience` section to your configuration file.

## Summary

The configuration system provides:

- ✅ **Type Safety**: Pydantic models with validation
- ✅ **Comprehensive Coverage**: All system components configurable
- ✅ **Resilience Patterns**: Built-in circuit breaker and retry logic
- ✅ **Environment Flexibility**: Easy customization per environment
- ✅ **Validation**: Comprehensive input validation with clear error messages
- ✅ **Testing**: Full test coverage for all configuration models
- ✅ **Documentation**: Extensive documentation and examples
- ✅ **Backward Compatibility**: Existing configurations continue to work

The addition of resilience configuration models enhances the gateway's ability to handle failures gracefully while maintaining high availability and performance.