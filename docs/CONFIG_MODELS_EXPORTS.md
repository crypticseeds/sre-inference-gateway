# Configuration Models - Exports and Integration

## Module Exports

The `app.config.models` module exports the following classes and types:

### Primary Configuration Classes

```python
from app.config.models import (
    # Main configuration container
    GatewayConfig,
    
    # Component configurations
    ProviderConfig,
    ServerConfig,
    HealthConfig,
    LoggingConfig,
    MetricsConfig,
    
    # Resilience pattern configurations
    ResilienceConfig,
    CircuitBreakerConfig,
    RetryConfig,
)
```

### Type Imports

```python
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
```

## Integration Points

### 1. Configuration Loading

```python
# app/config/settings.py
from app.config.models import GatewayConfig

class ConfigManager:
    def load_config(self) -> GatewayConfig:
        # Load and validate configuration
        return GatewayConfig(**config_data)
```

### 2. Provider Factory

```python
# app/providers/factory.py
from app.config.models import ProviderConfig

class ProviderFactory:
    @staticmethod
    def create_provider(config: ProviderConfig) -> BaseProvider:
        # Create provider instances from configuration
        pass
```

### 3. FastAPI Dependencies

```python
# app/api/dependencies.py
from app.config.models import GatewayConfig

def get_gateway_config() -> GatewayConfig:
    # Provide configuration to FastAPI endpoints
    pass
```

### 4. Health Monitoring

```python
# app/api/health.py
from app.config.models import HealthConfig

async def check_provider_health(config: HealthConfig):
    # Use health configuration for monitoring
    pass
```

### 5. Resilience Patterns

```python
# app/router/resilience.py
from app.config.models import ResilienceConfig

class ResilienceHandler:
    def __init__(self, config: ResilienceConfig):
        # Configure resilience patterns
        pass
```

## Configuration File Integration

### YAML Configuration

```yaml
# config.yaml
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

resilience:
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60.0
    expected_exception: "HTTPException"
  retry:
    max_attempts: 3
    min_wait: 1.0
    max_wait: 10.0
    exponential_base: 2.0
    jitter: true
```

### Environment Variables

```python
# Environment variable integration
import os
from app.config.models import GatewayConfig, ProviderConfig

def create_config_from_env() -> GatewayConfig:
    return GatewayConfig(
        server=ServerConfig(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        ),
        providers=[
            ProviderConfig(
                name="openai",
                type="openai",
                api_key_env="OPENAI_API_KEY",
                timeout=float(os.getenv("OPENAI_TIMEOUT", "30.0"))
            )
        ]
    )
```

## Testing Integration

### Unit Tests

```python
# tests/test_config.py
from app.config.models import GatewayConfig, ProviderConfig

def test_gateway_config():
    config = GatewayConfig(
        providers=[
            ProviderConfig(name="test", type="mock")
        ]
    )
    assert len(config.providers) == 1
```

### Validation Testing

```python
import pytest
from pydantic import ValidationError
from app.config.models import RetryConfig

def test_retry_config_validation():
    with pytest.raises(ValidationError):
        RetryConfig(min_wait=10.0, max_wait=5.0)  # Invalid: min > max
```

## Documentation Integration

### API Documentation

- **`docs/CONFIG_MODELS_API.md`** - Complete API reference with examples
- **`docs/CONFIG_MODELS_SIGNATURES.md`** - Quick reference for signatures
- **`docs/CONFIG_MODELS_SUMMARY.md`** - Overview and usage patterns
- **`docs/RESILIENCE_CONFIG.md`** - Detailed resilience configuration guide

### README Integration

The main README.md includes:
- Configuration overview
- Available configuration models
- Links to detailed documentation
- Usage examples

## Migration Guide

### From Legacy Configuration

If migrating from a legacy configuration system:

1. **Map old settings to new models**:
   ```python
   # Old way
   config = {
       "host": "0.0.0.0",
       "port": 8000,
       "providers": {...}
   }
   
   # New way
   config = GatewayConfig(
       server=ServerConfig(host="0.0.0.0", port=8000),
       providers=[ProviderConfig(...)]
   )
   ```

2. **Update validation logic**:
   ```python
   # Old way - manual validation
   if not config.get("providers"):
       raise ValueError("No providers configured")
   
   # New way - automatic validation
   config = GatewayConfig(**config_data)  # Validates automatically
   ```

3. **Update access patterns**:
   ```python
   # Old way - dictionary access
   port = config["server"]["port"]
   
   # New way - attribute access with type safety
   port = config.server.port
   ```

## Best Practices

### 1. Use Type Hints

```python
from app.config.models import GatewayConfig

def configure_app(config: GatewayConfig) -> None:
    """Configure application with full type safety."""
    pass
```

### 2. Validate Early

```python
def load_config(config_path: str) -> GatewayConfig:
    """Load and validate configuration at startup."""
    with open(config_path) as f:
        config_data = yaml.safe_load(f)
    
    try:
        return GatewayConfig(**config_data)
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
```

### 3. Use Factory Patterns

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

def create_providers(configs: List[ProviderConfig]) -> List[BaseProvider]:
    """Create provider instances from configurations."""
    return [
        ProviderFactory.create_provider(config)
        for config in configs
        if config.enabled
    ]
```

### 4. Environment-Specific Configuration

```python
import os
from app.config.models import GatewayConfig, LoggingConfig

def create_environment_config() -> GatewayConfig:
    """Create configuration based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        return GatewayConfig(
            logging=LoggingConfig(level="INFO"),
            server=ServerConfig(debug=False)
        )
    else:
        return GatewayConfig(
            logging=LoggingConfig(level="DEBUG"),
            server=ServerConfig(debug=True)
        )
```

## Summary

The configuration models provide:

- ✅ **Complete Type Safety**: Full Pydantic validation with Python type hints
- ✅ **Comprehensive Documentation**: Detailed API reference and usage examples
- ✅ **Integration Ready**: Seamless integration with all system components
- ✅ **Test Coverage**: Comprehensive unit tests for all models and validation
- ✅ **Migration Support**: Clear migration path from legacy configurations
- ✅ **Best Practices**: Documented patterns for common use cases

All exports are properly documented and tested, ensuring reliable configuration management across the entire SRE Inference Gateway system.