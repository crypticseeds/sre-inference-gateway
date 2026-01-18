# Provider Factory API Reference

## Module: `app.providers.factory`

### Classes

#### `ProviderFactory`

**Static factory class for creating provider instances from configuration.**

```python
class ProviderFactory:
    """Factory for creating provider instances from configuration."""
```

### Methods

#### `create_provider(config: ProviderConfig) -> BaseProvider`

**Main factory method for creating provider instances.**

```python
@staticmethod
def create_provider(config: ProviderConfig) -> BaseProvider:
    """Create provider instance from configuration.
    
    Args:
        config: Provider configuration containing:
            - name (str): Provider identifier
            - type (str): Provider type ("openai", "vllm", "mock")
            - base_url (str, optional): API base URL
            - api_key_env (str, optional): Environment variable for API key
            - timeout (float): Request timeout in seconds
            - max_retries (int): Maximum retry attempts
            - weight (float): Routing weight
            - enabled (bool): Whether provider is enabled
    
    Returns:
        BaseProvider: Configured provider instance:
            - OpenAIAdapter for "openai" type
            - VLLMAdapter for "vllm" type
            - MockOpenAIAdapter or MockVLLMAdapter for "mock" type
    
    Raises:
        ValueError: If provider type is unknown or configuration is invalid
    """
```

#### `_create_openai_adapter(config: ProviderConfig, provider_config: Dict[str, Any]) -> OpenAIAdapter`

**Internal method for creating OpenAI provider instances.**

```python
@staticmethod
def _create_openai_adapter(
    config: ProviderConfig, 
    provider_config: Dict[str, Any]
) -> OpenAIAdapter:
    """Create OpenAI provider instance with API key authentication.
    
    Args:
        config: Provider configuration object
        provider_config: Provider configuration as dictionary
    
    Returns:
        OpenAIAdapter: Configured OpenAI provider instance
    
    Raises:
        ValueError: If API key environment variable is not set
    """
```

#### `_create_vllm_adapter(config: ProviderConfig, provider_config: Dict[str, Any]) -> VLLMAdapter`

**Internal method for creating vLLM provider instances.**

```python
@staticmethod
def _create_vllm_adapter(
    config: ProviderConfig, 
    provider_config: Dict[str, Any]
) -> VLLMAdapter:
    """Create vLLM provider instance for local or remote inference.
    
    Args:
        config: Provider configuration object
        provider_config: Provider configuration as dictionary
    
    Returns:
        VLLMAdapter: Configured vLLM adapter instance
    """
```

### Type Definitions

#### Provider Type Mapping

| Provider Type | Return Type | Description |
|---------------|-------------|-------------|
| `"openai"` | `OpenAIAdapter` | OpenAI API provider with authentication |
| `"vllm"` | `VLLMAdapter` | vLLM inference service provider |
| `"mock"` | `MockOpenAIAdapter` or `MockVLLMAdapter` | Mock provider for testing |

#### Configuration Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `name` | `str` | - | Yes | Provider identifier |
| `type` | `str` | - | Yes | Provider type |
| `base_url` | `str` | Provider-specific | No | API endpoint URL |
| `api_key_env` | `str` | `"OPENAI_API_KEY"` | No | Environment variable for API key |
| `timeout` | `float` | `30.0` | No | Request timeout in seconds |
| `max_retries` | `int` | `3` | No | Maximum retry attempts |
| `weight` | `float` | `1.0` | No | Routing weight |
| `enabled` | `bool` | `True` | No | Whether provider is active |

### Usage Examples

#### Basic Usage

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Create OpenAI provider
config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    api_key_env="OPENAI_API_KEY"
)

provider = ProviderFactory.create_provider(config)
```

#### vLLM Provider

```python
# Create vLLM provider
config = ProviderConfig(
    name="vllm-local",
    type="vllm",
    base_url="http://localhost:8000/v1",
    timeout=60.0
)

provider = ProviderFactory.create_provider(config)
```

#### Mock Provider

```python
# Create mock provider
config = ProviderConfig(
    name="mock-openai-test",
    type="mock"
)

provider = ProviderFactory.create_provider(config)
```

### Error Handling

#### Common Exceptions

```python
# ValueError: Unknown provider type
try:
    config = ProviderConfig(name="test", type="unknown")
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Error: {e}")  # "Unknown provider type: unknown"

# ValueError: Missing API key
try:
    config = ProviderConfig(name="openai", type="openai", api_key_env="MISSING_KEY")
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Error: {e}")  # "OpenAI API key not found in environment variable: MISSING_KEY"
```

### Dependencies

#### Required Imports

```python
from app.config.models import ProviderConfig
from app.providers.base import BaseProvider
from app.providers.openai import OpenAIAdapter
from app.providers.vllm import VLLMAdapter
```

#### Optional Imports (Dynamic)

```python
# Imported dynamically to avoid circular imports
from app.providers.mock import MockOpenAIAdapter, MockVLLMAdapter
```

### Environment Variables

#### OpenAI Provider

```bash
# Required for OpenAI provider
export OPENAI_API_KEY="sk-..."

# Or custom environment variable
export CUSTOM_OPENAI_KEY="sk-..."
```

#### vLLM Provider

```bash
# No environment variables required
# vLLM providers connect directly to service endpoints
```

### Logging

The factory emits structured logs during provider creation:

```python
# Info logs for successful creation
logger.info(
    "Creating OpenAI adapter: name=%s, base_url=%s, timeout=%s",
    config.name, base_url, config.timeout
)

logger.info(
    "Creating vLLM adapter: name=%s, base_url=%s, timeout=%s", 
    config.name, base_url, config.timeout
)
```

### Related Types

#### ProviderConfig

```python
from app.config.models import ProviderConfig

config = ProviderConfig(
    name="provider-name",
    type="openai|vllm|mock",
    base_url="https://api.example.com/v1",
    api_key_env="API_KEY_ENV_VAR",
    timeout=30.0,
    max_retries=3,
    weight=1.0,
    enabled=True
)
```

#### BaseProvider

```python
from app.providers.base import BaseProvider, ChatCompletionRequest, ChatCompletionResponse

# All providers implement BaseProvider interface
provider: BaseProvider = ProviderFactory.create_provider(config)

# Common methods available on all providers
response: ChatCompletionResponse = await provider.chat_completion(request, "req-123")
health = await provider.health_check()
await provider.close()
```

### Mock Provider Selection Logic

The factory automatically selects the appropriate mock provider based on the provider name:

```python
# Name contains "openai" -> MockOpenAIAdapter
config = ProviderConfig(name="mock-openai-test", type="mock")
provider = ProviderFactory.create_provider(config)  # Returns MockOpenAIAdapter

# Name contains "vllm" -> MockVLLMAdapter  
config = ProviderConfig(name="mock-vllm-test", type="mock")
provider = ProviderFactory.create_provider(config)  # Returns MockVLLMAdapter

# Default -> MockOpenAIAdapter
config = ProviderConfig(name="test-provider", type="mock")
provider = ProviderFactory.create_provider(config)  # Returns MockOpenAIAdapter
```

### Thread Safety

The `ProviderFactory` is thread-safe:
- All methods are static
- No shared mutable state
- Environment variable access is thread-safe
- Provider instances are independent

### Performance

- **Factory method**: < 1ms execution time
- **Provider creation**: 1-5ms depending on type
- **Memory per provider**: 1-5MB depending on type
- **No caching**: Each call creates a new instance

For better performance in production, consider caching provider instances at the application level.