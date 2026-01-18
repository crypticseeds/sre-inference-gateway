# Provider Factory Documentation

## Overview

The `ProviderFactory` class provides a centralized factory pattern implementation for creating inference provider instances from configuration. It abstracts the complexity of provider instantiation, handles provider-specific initialization logic, and validates required configuration parameters.

## Module: `app.providers.factory`

### Purpose

The factory pattern enables:
- **Centralized Provider Creation**: Single point for instantiating all provider types
- **Configuration-Driven Instantiation**: Create providers from `ProviderConfig` objects
- **Type-Safe Provider Selection**: Automatic provider type detection and validation
- **Environment Variable Management**: Secure API key retrieval from environment
- **Provider-Specific Initialization**: Handles unique requirements for each provider type

### Key Features

- **Multiple Provider Support**: OpenAI, vLLM, and Mock providers
- **Automatic Configuration Validation**: Validates required parameters before instantiation
- **Environment Variable Integration**: Secure API key management via environment variables
- **Flexible Base URL Configuration**: Supports custom endpoints for different environments
- **Comprehensive Error Handling**: Clear error messages for configuration issues
- **Logging Integration**: Structured logging for provider creation events

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  ProviderFactory                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         create_provider(config)                   │  │
│  │         - Main factory method                     │  │
│  │         - Type detection and dispatch             │  │
│  │         - Configuration validation                │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Provider-Specific Methods                 │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  _create_openai_adapter()                   │ │  │
│  │  │  - API key validation                       │ │  │
│  │  │  - Base URL configuration                   │ │  │
│  │  │  - OpenAI-specific initialization           │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  _create_vllm_adapter()                     │ │  │
│  │  │  - Local/remote endpoint configuration      │ │  │
│  │  │  - vLLM-specific initialization             │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  Mock Provider Selection                    │ │  │
│  │  │  - Name-based mock provider selection       │ │  │
│  │  │  - Test environment support                 │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Class Reference

### `ProviderFactory`

**Static Factory Class**: Creates provider instances from configuration without requiring instantiation.

#### Class Methods

##### `create_provider(config: ProviderConfig) -> BaseProvider`

**Main factory method** that creates provider instances based on configuration type.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `config` | `ProviderConfig` | Yes | Provider configuration object containing all necessary parameters |

**Configuration Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | Required | Provider identifier for logging and metrics |
| `type` | `str` | Required | Provider type: "openai", "vllm", or "mock" |
| `base_url` | `str` | Provider-specific | API endpoint URL |
| `api_key_env` | `str` | "OPENAI_API_KEY" | Environment variable name for API key |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `max_retries` | `int` | `3` | Maximum retry attempts |
| `weight` | `float` | `1.0` | Routing weight for load balancing |
| `enabled` | `bool` | `True` | Whether provider is active |

**Returns:**

| Provider Type | Return Type | Description |
|---------------|-------------|-------------|
| "openai" | `OpenAIAdapter` | OpenAI API provider with authentication |
| "vllm" | `VLLMAdapter` | vLLM inference service provider |
| "mock" | `MockOpenAIAdapter` or `MockVLLMAdapter` | Mock provider for testing |

**Raises:**

| Exception | Condition | Description |
|-----------|-----------|-------------|
| `ValueError` | Unknown provider type | Provider type not in supported list |
| `ValueError` | Missing API key | Required environment variable not set |
| `ValueError` | Invalid configuration | Configuration validation failed |

**Example:**

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Create OpenAI provider
config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    api_key_env="OPENAI_API_KEY",
    base_url="https://api.openai.com/v1",
    timeout=30.0,
    max_retries=3,
    weight=0.7,
    enabled=True
)

provider = ProviderFactory.create_provider(config)

# Use the provider
from app.providers.base import ChatCompletionRequest

request = ChatCompletionRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

response = await provider.chat_completion(request, "req-123")
print(response.choices[0]["message"]["content"])
```

## Provider Type Details

### OpenAI Provider (`type="openai"`)

**Purpose**: Integrates with OpenAI's API for cloud-based inference.

**Requirements:**
- API key via environment variable
- Internet connectivity
- Valid OpenAI account with credits

**Configuration:**

```python
config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    api_key_env="OPENAI_API_KEY",  # Environment variable name
    base_url="https://api.openai.com/v1",  # Optional, defaults to OpenAI
    timeout=30.0,
    max_retries=3
)
```

**Environment Setup:**

```bash
# Set API key in environment
export OPENAI_API_KEY="sk-..."

# Or use Doppler for secrets management
doppler secrets set OPENAI_API_KEY="sk-..."
```

**Features:**
- Bearer token authentication
- Automatic retry with exponential backoff
- Rate limit handling
- Comprehensive error mapping
- Health monitoring via `/models` endpoint

### vLLM Provider (`type="vllm"`)

**Purpose**: Connects to local or remote vLLM inference services.

**Requirements:**
- vLLM service running with OpenAI-compatible API
- Network access to vLLM endpoint
- No API key required

**Configuration:**

```python
# Local vLLM service
config = ProviderConfig(
    name="vllm-local",
    type="vllm",
    base_url="http://localhost:8000/v1",  # vLLM service endpoint
    timeout=60.0,  # Longer timeout for local inference
    max_retries=3
)

# Remote vLLM service
remote_config = ProviderConfig(
    name="vllm-remote",
    type="vllm",
    base_url="https://vllm.example.com/v1",
    timeout=90.0,
    max_retries=5
)
```

**Features:**
- OpenAI-compatible API integration
- No authentication required
- Service availability monitoring
- Configurable timeouts for inference workloads
- Support for local and remote deployments

### Mock Provider (`type="mock"`)

**Purpose**: Provides deterministic responses for testing and development.

**Requirements:**
- None (no external dependencies)

**Configuration:**

```python
# Mock OpenAI provider (auto-detected from name)
mock_openai_config = ProviderConfig(
    name="mock-openai-test",
    type="mock",
    weight=1.0
)

# Mock vLLM provider (auto-detected from name)
mock_vllm_config = ProviderConfig(
    name="mock-vllm-test",
    type="mock",
    weight=1.0
)

# Default mock (falls back to OpenAI mock)
default_mock_config = ProviderConfig(
    name="test-provider",
    type="mock"
)
```

**Provider Selection Logic:**
- Name contains "openai" → `MockOpenAIAdapter`
- Name contains "vllm" → `MockVLLMAdapter`
- Default → `MockOpenAIAdapter`

**Features:**
- Deterministic responses
- Simulated processing delays
- No external API calls
- Always reports healthy status
- Configurable mock responses

## Usage Patterns

### Basic Factory Usage

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Create provider from configuration
config = ProviderConfig(
    name="my-provider",
    type="openai",
    api_key_env="OPENAI_API_KEY"
)

provider = ProviderFactory.create_provider(config)

# Use provider
response = await provider.chat_completion(request, "req-123")
```

### Configuration from YAML

```yaml
# config.yaml
providers:
  - name: openai-gpt4
    type: openai
    api_key_env: OPENAI_API_KEY
    base_url: https://api.openai.com/v1
    timeout: 30.0
    max_retries: 3
    weight: 0.7
    enabled: true
  
  - name: vllm-local
    type: vllm
    base_url: http://localhost:8000/v1
    timeout: 60.0
    max_retries: 3
    weight: 0.3
    enabled: true
```

```python
import yaml
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Load configuration
with open("config.yaml") as f:
    config_data = yaml.safe_load(f)

# Create providers
providers = []
for provider_data in config_data["providers"]:
    config = ProviderConfig(**provider_data)
    provider = ProviderFactory.create_provider(config)
    providers.append(provider)
```

### Provider Registry Integration

```python
from app.providers.registry import ProviderRegistry
from app.providers.factory import ProviderFactory

# Initialize registry
registry = ProviderRegistry()

# Create and register providers from configuration
provider_configs = [
    ProviderConfig(name="openai", type="openai", api_key_env="OPENAI_API_KEY"),
    ProviderConfig(name="vllm", type="vllm", base_url="http://localhost:8000/v1"),
    ProviderConfig(name="mock", type="mock")
]

for config in provider_configs:
    provider = ProviderFactory.create_provider(config)
    registry.register_provider(config.name, provider)

# Use providers from registry
openai_provider = registry.get_provider("openai")
response = await openai_provider.chat_completion(request, "req-123")
```

### Environment-Specific Configuration

```python
import os
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Development environment
if os.getenv("ENVIRONMENT") == "development":
    config = ProviderConfig(
        name="dev-mock",
        type="mock",
        weight=1.0
    )
# Production environment
else:
    config = ProviderConfig(
        name="prod-openai",
        type="openai",
        api_key_env="OPENAI_API_KEY",
        timeout=30.0,
        max_retries=5
    )

provider = ProviderFactory.create_provider(config)
```

### Multiple Provider Setup

```python
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig

# Create multiple providers for load balancing
providers = {}

# Primary OpenAI provider
openai_config = ProviderConfig(
    name="openai-primary",
    type="openai",
    api_key_env="OPENAI_API_KEY",
    weight=0.7
)
providers["openai"] = ProviderFactory.create_provider(openai_config)

# Fallback vLLM provider
vllm_config = ProviderConfig(
    name="vllm-fallback",
    type="vllm",
    base_url="http://localhost:8000/v1",
    weight=0.3
)
providers["vllm"] = ProviderFactory.create_provider(vllm_config)

# Use providers with routing logic
def select_provider(providers, request):
    # Implement routing logic here
    return providers["openai"]  # Simple example

provider = select_provider(providers, request)
response = await provider.chat_completion(request, "req-123")
```

## Error Handling

### Common Error Scenarios

#### Missing API Key

```python
try:
    config = ProviderConfig(
        name="openai",
        type="openai",
        api_key_env="MISSING_KEY"
    )
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Configuration error: {e}")
    # Output: Configuration error: OpenAI API key not found in environment variable: MISSING_KEY
```

#### Unknown Provider Type

```python
try:
    config = ProviderConfig(
        name="unknown",
        type="unsupported_type"
    )
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Provider error: {e}")
    # Output: Provider error: Unknown provider type: unsupported_type
```

#### Invalid Configuration

```python
try:
    # Invalid configuration (negative timeout)
    config = ProviderConfig(
        name="invalid",
        type="openai",
        timeout=-1.0  # Invalid value
    )
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Validation error: {e}")
```

### Error Handling Best Practices

```python
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig
import logging

logger = logging.getLogger(__name__)

def create_provider_safely(config_data):
    """Create provider with comprehensive error handling."""
    try:
        # Validate configuration
        config = ProviderConfig(**config_data)
        
        # Create provider
        provider = ProviderFactory.create_provider(config)
        
        logger.info(f"Successfully created provider: {config.name}")
        return provider
        
    except ValueError as e:
        logger.error(f"Provider creation failed: {e}")
        # Return mock provider as fallback
        fallback_config = ProviderConfig(
            name=f"fallback-{config_data.get('name', 'unknown')}",
            type="mock"
        )
        return ProviderFactory.create_provider(fallback_config)
        
    except Exception as e:
        logger.error(f"Unexpected error creating provider: {e}")
        raise
```

## Testing

### Unit Testing

```python
import pytest
import os
from unittest.mock import patch
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig
from app.providers.openai import OpenAIAdapter
from app.providers.vllm import VLLMAdapter
from app.providers.mock import MockOpenAIAdapter, MockVLLMAdapter

class TestProviderFactory:
    """Test provider factory functionality."""
    
    def test_create_openai_provider(self):
        """Test OpenAI provider creation."""
        config = ProviderConfig(
            name="test-openai",
            type="openai",
            api_key_env="TEST_OPENAI_KEY"
        )
        
        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "test-key"}):
            provider = ProviderFactory.create_provider(config)
        
        assert isinstance(provider, OpenAIAdapter)
        assert provider.name == "test-openai"
    
    def test_create_vllm_provider(self):
        """Test vLLM provider creation."""
        config = ProviderConfig(
            name="test-vllm",
            type="vllm",
            base_url="http://localhost:8000/v1"
        )
        
        provider = ProviderFactory.create_provider(config)
        
        assert isinstance(provider, VLLMAdapter)
        assert provider.name == "test-vllm"
    
    def test_create_mock_openai_provider(self):
        """Test mock OpenAI provider creation."""
        config = ProviderConfig(
            name="mock-openai-test",
            type="mock"
        )
        
        provider = ProviderFactory.create_provider(config)
        
        assert isinstance(provider, MockOpenAIAdapter)
        assert provider.name == "mock-openai-test"
    
    def test_create_mock_vllm_provider(self):
        """Test mock vLLM provider creation."""
        config = ProviderConfig(
            name="mock-vllm-test",
            type="mock"
        )
        
        provider = ProviderFactory.create_provider(config)
        
        assert isinstance(provider, MockVLLMAdapter)
        assert provider.name == "mock-vllm-test"
    
    def test_unknown_provider_type(self):
        """Test error handling for unknown provider type."""
        config = ProviderConfig(
            name="unknown",
            type="unknown_type"
        )
        
        with pytest.raises(ValueError, match="Unknown provider type"):
            ProviderFactory.create_provider(config)
    
    def test_missing_api_key(self):
        """Test error handling for missing API key."""
        config = ProviderConfig(
            name="openai",
            type="openai",
            api_key_env="MISSING_KEY"
        )
        
        with pytest.raises(ValueError, match="API key not found"):
            ProviderFactory.create_provider(config)
```

### Integration Testing

```python
import pytest
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig
from app.providers.base import ChatCompletionRequest

@pytest.mark.asyncio
async def test_factory_integration():
    """Test factory integration with actual provider usage."""
    # Create mock provider for testing
    config = ProviderConfig(
        name="integration-test",
        type="mock"
    )
    
    provider = ProviderFactory.create_provider(config)
    
    # Test provider functionality
    request = ChatCompletionRequest(
        model="test-model",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    
    response = await provider.chat_completion(request, "test-123")
    
    assert response.id == "test-123"
    assert len(response.choices) == 1
    assert "Hello!" in response.choices[0]["message"]["content"]
    
    # Test health check
    health = await provider.health_check()
    assert health.healthy is True
    assert health.name == "integration-test"
```

## Performance Considerations

### Factory Method Performance

The factory method is lightweight and performs minimal work:

1. **Configuration Validation**: O(1) - Simple type checking
2. **Provider Type Detection**: O(1) - String comparison
3. **Environment Variable Lookup**: O(1) - OS environment access
4. **Provider Instantiation**: O(1) - Constructor call

**Typical Performance:**
- Factory method execution: < 1ms
- Provider instantiation: 1-5ms
- Total creation time: < 10ms

### Memory Usage

Each provider instance maintains:
- HTTP client connection pool
- Configuration dictionary
- Logging instance
- Provider-specific state

**Estimated Memory per Provider:**
- OpenAI Provider: ~2-5MB
- vLLM Provider: ~2-5MB
- Mock Provider: ~1MB

### Optimization Tips

```python
# Cache providers to avoid recreation
provider_cache = {}

def get_or_create_provider(config):
    """Get cached provider or create new one."""
    cache_key = f"{config.name}-{config.type}"
    
    if cache_key not in provider_cache:
        provider_cache[cache_key] = ProviderFactory.create_provider(config)
    
    return provider_cache[cache_key]

# Reuse providers across requests
provider = get_or_create_provider(config)
```

## Security Considerations

### API Key Management

```python
# ✅ GOOD: Use environment variables
config = ProviderConfig(
    name="secure-openai",
    type="openai",
    api_key_env="OPENAI_API_KEY"  # Environment variable name
)

# ❌ BAD: Hardcode API keys
config = ProviderConfig(
    name="insecure-openai",
    type="openai",
    api_key="sk-hardcoded-key"  # Never do this!
)
```

### Environment Variable Security

```bash
# Use Doppler for secrets management
doppler secrets set OPENAI_API_KEY="sk-..."

# Or use secure environment variable management
export OPENAI_API_KEY="sk-..."
```

### Configuration Validation

The factory validates all configuration parameters to prevent:
- Injection attacks via malformed URLs
- Invalid timeout values that could cause hangs
- Missing required parameters that could cause runtime errors

## Related Documentation

- [Provider Implementation Guide](PROVIDERS.md) - Comprehensive provider documentation
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [OpenAI Adapter](OPENAI_ADAPTER_API.md) - OpenAI provider detailed documentation
- [Configuration Models](../app/config/models.py) - Configuration data structures
- [Provider Registry](../app/providers/registry.py) - Provider management

## Summary

The `ProviderFactory` provides a robust, type-safe way to create inference providers from configuration. Key benefits:

- ✅ **Centralized Creation**: Single point for all provider instantiation
- ✅ **Configuration-Driven**: Create providers from structured configuration
- ✅ **Type Safety**: Automatic provider type detection and validation
- ✅ **Security**: Secure API key management via environment variables
- ✅ **Flexibility**: Support for multiple provider types and configurations
- ✅ **Error Handling**: Comprehensive validation and error reporting
- ✅ **Testing Support**: Mock providers for development and testing
- ✅ **Performance**: Lightweight factory method with minimal overhead

The factory pattern enables clean separation between configuration and implementation, making the system more maintainable and testable.