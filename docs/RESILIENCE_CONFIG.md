# Resilience Configuration Documentation

## Overview

The SRE Inference Gateway includes comprehensive resilience patterns to handle failures gracefully and maintain service availability. This document covers the configuration models for circuit breakers and retry mechanisms that were added to enhance system reliability.

## Table of Contents

- [Configuration Models](#configuration-models)
- [Circuit Breaker Configuration](#circuit-breaker-configuration)
- [Retry Configuration](#retry-configuration)
- [Resilience Configuration](#resilience-configuration)
- [Usage Examples](#usage-examples)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)

## Configuration Models

### CircuitBreakerConfig

**Module**: `app.config.models`

**Purpose**: Configures circuit breaker behavior to prevent cascading failures by temporarily stopping requests to failing services.

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `failure_threshold` | `int` | `5` | `>= 1` | Number of consecutive failures before opening the circuit |
| `recovery_timeout` | `float` | `60.0` | `> 0` | Time in seconds before attempting to close the circuit |
| `expected_exception` | `str` | `"Exception"` | - | Exception type that triggers circuit breaker |

#### Example

```python
from app.config.models import CircuitBreakerConfig

# Default configuration
circuit_breaker = CircuitBreakerConfig()

# Custom configuration
circuit_breaker = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception="HTTPException"
)
```

#### Validation Rules

- `failure_threshold` must be at least 1
- `recovery_timeout` must be greater than 0
- `expected_exception` should be a valid exception class name

### RetryConfig

**Module**: `app.config.models`

**Purpose**: Configures retry behavior with exponential backoff and jitter for handling transient failures.

#### Attributes

| Attribute | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `max_attempts` | `int` | `3` | `>= 1` | Maximum number of retry attempts |
| `min_wait` | `float` | `1.0` | `> 0` | Minimum wait time between retries in seconds |
| `max_wait` | `float` | `10.0` | `> 0` | Maximum wait time between retries in seconds |
| `exponential_base` | `float` | `2.0` | `> 1` | Base multiplier for exponential backoff |
| `jitter` | `bool` | `True` | - | Whether to add random jitter to wait times |

#### Example

```python
from app.config.models import RetryConfig

# Default configuration
retry = RetryConfig()

# Custom configuration for aggressive retries
retry = RetryConfig(
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

#### Validation Rules

- `max_attempts` must be at least 1
- `min_wait` must be greater than 0
- `max_wait` must be greater than 0
- `exponential_base` must be greater than 1

#### Retry Timing Calculation

The retry mechanism calculates wait times using exponential backoff:

```python
base_wait = min_wait * (exponential_base ** attempt)
actual_wait = min(base_wait, max_wait)

if jitter:
    actual_wait = actual_wait * (0.5 + random.random() * 0.5)
```

**Example timing with default settings:**

| Attempt | Base Wait | Capped Wait | With Jitter (range) |
|---------|-----------|-------------|---------------------|
| 1 | 1.0s | 1.0s | 0.5s - 1.0s |
| 2 | 2.0s | 2.0s | 1.0s - 2.0s |
| 3 | 4.0s | 4.0s | 2.0s - 4.0s |
| 4 | 8.0s | 8.0s | 4.0s - 8.0s |
| 5 | 16.0s | 10.0s (capped) | 5.0s - 10.0s |

### ResilienceConfig

**Module**: `app.config.models`

**Purpose**: Container for all resilience pattern configurations, providing a unified interface for circuit breaker and retry settings.

#### Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `circuit_breaker` | `CircuitBreakerConfig` | `CircuitBreakerConfig()` | Circuit breaker configuration |
| `retry` | `RetryConfig` | `RetryConfig()` | Retry configuration |

#### Example

```python
from app.config.models import (
    ResilienceConfig,
    CircuitBreakerConfig,
    RetryConfig
)

# Default configuration
resilience = ResilienceConfig()

# Custom configuration
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

## Usage Examples

### Basic Configuration

```python
from app.config.models import GatewayConfig, ResilienceConfig

# Gateway with default resilience settings
config = GatewayConfig()
print(f"Circuit breaker threshold: {config.resilience.circuit_breaker.failure_threshold}")
print(f"Max retry attempts: {config.resilience.retry.max_attempts}")
```

### YAML Configuration

```yaml
# config.yaml
resilience:
  circuit_breaker:
    failure_threshold: 3
    recovery_timeout: 30.0
    expected_exception: "HTTPException"
  retry:
    max_attempts: 5
    min_wait: 0.5
    max_wait: 15.0
    exponential_base: 1.8
    jitter: true
```

### Environment-Specific Configurations

```python
# Development environment - more aggressive retries
dev_resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=10,  # Higher threshold for dev
        recovery_timeout=30.0
    ),
    retry=RetryConfig(
        max_attempts=5,
        min_wait=0.1,
        max_wait=5.0
    )
)

# Production environment - conservative settings
prod_resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,   # Lower threshold for prod
        recovery_timeout=60.0
    ),
    retry=RetryConfig(
        max_attempts=3,
        min_wait=1.0,
        max_wait=30.0
    )
)
```

## Integration Patterns

### Provider-Specific Resilience

```python
from app.config.models import ProviderConfig, ResilienceConfig

# Different resilience settings per provider type
openai_resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception="HTTPException"
    ),
    retry=RetryConfig(
        max_attempts=3,
        min_wait=1.0,
        max_wait=10.0
    )
)

vllm_resilience = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0
    ),
    retry=RetryConfig(
        max_attempts=5,
        min_wait=0.5,
        max_wait=20.0
    )
)
```

### Configuration Validation

```python
from pydantic import ValidationError

try:
    # Invalid configuration - failure_threshold too low
    invalid_config = CircuitBreakerConfig(failure_threshold=0)
except ValidationError as e:
    print(f"Validation error: {e}")

try:
    # Invalid configuration - exponential_base too low
    invalid_retry = RetryConfig(exponential_base=0.5)
except ValidationError as e:
    print(f"Validation error: {e}")
```

### Dynamic Configuration Updates

```python
from app.config.settings import ConfigManager

# Load configuration
manager = ConfigManager("config.yaml")
config = manager.load_config()

# Update resilience settings
config.resilience.circuit_breaker.failure_threshold = 7
config.resilience.retry.max_attempts = 4

# Validate updated configuration
try:
    updated_config = GatewayConfig(**config.model_dump())
    print("Configuration updated successfully")
except ValidationError as e:
    print(f"Invalid configuration: {e}")
```

## Best Practices

### 1. Environment-Appropriate Settings

```python
# Development: More lenient settings for debugging
dev_settings = {
    "circuit_breaker": {
        "failure_threshold": 10,
        "recovery_timeout": 15.0
    },
    "retry": {
        "max_attempts": 5,
        "min_wait": 0.1
    }
}

# Production: Conservative settings for stability
prod_settings = {
    "circuit_breaker": {
        "failure_threshold": 3,
        "recovery_timeout": 60.0
    },
    "retry": {
        "max_attempts": 3,
        "min_wait": 1.0
    }
}
```

### 2. Service-Specific Tuning

```python
# External APIs: Higher tolerance for failures
external_api_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=120.0
    ),
    retry=RetryConfig(
        max_attempts=4,
        max_wait=30.0
    )
)

# Internal services: Lower tolerance
internal_service_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=30.0
    ),
    retry=RetryConfig(
        max_attempts=2,
        max_wait=10.0
    )
)
```

### 3. Monitoring and Observability

```python
# Configuration with monitoring in mind
monitored_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception="HTTPException"  # Specific exception for metrics
    ),
    retry=RetryConfig(
        max_attempts=3,
        jitter=True  # Helps prevent thundering herd
    )
)
```

### 4. Testing Configurations

```python
# Test environment: Fast failures for quick feedback
test_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=5.0
    ),
    retry=RetryConfig(
        max_attempts=2,
        min_wait=0.1,
        max_wait=1.0,
        jitter=False  # Deterministic for testing
    )
)
```

### 5. Configuration Validation

```python
def validate_resilience_config(config: ResilienceConfig) -> bool:
    """Validate resilience configuration for production use."""
    
    # Check circuit breaker settings
    if config.circuit_breaker.failure_threshold < 2:
        raise ValueError("Failure threshold too low for production")
    
    if config.circuit_breaker.recovery_timeout < 30.0:
        raise ValueError("Recovery timeout too short for production")
    
    # Check retry settings
    if config.retry.max_attempts > 5:
        raise ValueError("Too many retry attempts may cause delays")
    
    if config.retry.max_wait > 60.0:
        raise ValueError("Max wait time too long for user experience")
    
    return True

# Usage
try:
    validate_resilience_config(prod_resilience)
    print("Configuration is production-ready")
except ValueError as e:
    print(f"Configuration issue: {e}")
```

## Configuration Examples by Use Case

### High-Availability Service

```python
ha_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0
    ),
    retry=RetryConfig(
        max_attempts=5,
        min_wait=0.5,
        max_wait=15.0,
        exponential_base=1.5,
        jitter=True
    )
)
```

### Batch Processing

```python
batch_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=300.0  # Longer recovery for batch jobs
    ),
    retry=RetryConfig(
        max_attempts=10,
        min_wait=5.0,
        max_wait=120.0,
        exponential_base=1.2,
        jitter=True
    )
)
```

### Real-Time API

```python
realtime_config = ResilienceConfig(
    circuit_breaker=CircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout=15.0  # Quick recovery for real-time
    ),
    retry=RetryConfig(
        max_attempts=2,
        min_wait=0.1,
        max_wait=2.0,
        exponential_base=2.0,
        jitter=False  # Predictable timing
    )
)
```

## Related Documentation

- [Configuration Models](../app/config/models.py) - Complete configuration model definitions
- [Provider Implementation Guide](PROVIDERS.md) - Provider-specific resilience patterns
- [Health Check API](HEALTH_API.md) - Health monitoring integration
- [Architecture Overview](ARCHITECTURE.md) - System resilience architecture

## Summary

The resilience configuration models provide:

- ✅ **Circuit Breaker Configuration**: Prevents cascading failures with configurable thresholds
- ✅ **Retry Configuration**: Handles transient failures with exponential backoff and jitter
- ✅ **Unified Interface**: Single configuration point for all resilience patterns
- ✅ **Validation**: Comprehensive input validation with meaningful error messages
- ✅ **Flexibility**: Environment and service-specific configuration support
- ✅ **Best Practices**: Built-in defaults following industry standards

These configurations enable the gateway to maintain high availability and graceful degradation under various failure scenarios while providing operators with fine-grained control over resilience behavior.