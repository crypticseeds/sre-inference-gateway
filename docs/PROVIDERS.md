# Provider Implementation Guide

This document provides comprehensive documentation for the inference provider system, including implementation details, usage examples, and integration patterns.

## Overview

The provider system abstracts different inference backends (OpenAI, vLLM, etc.) behind a common interface. This allows the gateway to route requests to multiple providers without coupling to specific implementations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BaseProvider (ABC)                    │
│  - chat_completion(request, request_id) -> response     │
│  - health_check() -> ProviderHealth                     │
│  - generate_request_id() -> str                         │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────┴────────┐  ┌──────┴───────┐  ┌───────┴────────┐
│ OpenAIProvider │  │  VLLMAdapter │  │  MockProvider  │
└────────────────┘  └──────────────┘  └────────────────┘
```

## Base Provider Interface

All providers must implement the `BaseProvider` abstract class:

```python
from abc import ABC, abstractmethod
from app.providers.base import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)

class CustomProvider(BaseProvider):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        # Initialize provider-specific resources
    
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        request_id: str
    ) -> ChatCompletionResponse:
        # Implement chat completion logic
        pass
    
    async def health_check(self) -> ProviderHealth:
        # Implement health check logic
        pass
```

## OpenAI Adapter

### Overview

The `OpenAIAdapter` integrates with the OpenAI API to handle chat completion requests. It includes automatic retry logic, exponential backoff, comprehensive error handling, and health monitoring.

### Initialization

```python
from app.providers.openai import OpenAIAdapter

adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={"model": "gpt-4", "priority": 1},
    api_key="sk-...",  # From Doppler in production
    base_url="https://api.openai.com/v1",
    timeout=30.0,
    max_retries=3
)
```

### Parameters

- **name** (str): Provider identifier for logging and metrics
- **config** (Dict[str, Any]): Provider configuration dictionary
- **api_key** (str): OpenAI API authentication key
- **base_url** (str): API base URL (default: `https://api.openai.com/v1`)
- **timeout** (float): Request timeout in seconds (default: 30.0)
- **max_retries** (int): Maximum retry attempts (default: 3)

### Chat Completion

```python
from app.providers.base import ChatCompletionRequest

# Create request
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ],
    temperature=0.7,
    max_tokens=150,
    top_p=1.0,
    frequency_penalty=0.0,
    presence_penalty=0.0
)

# Execute request
response = await provider.chat_completion(request, "req-abc123")

# Access response
print(response.choices[0]["message"]["content"])
print(f"Tokens used: {response.usage['total_tokens']}")
```

### Error Handling

The provider handles various error scenarios:

**Authentication Errors (401)**
```python
# Raises HTTPException with status 500
# Detail: "OpenAI API authentication failed"
```

**Invalid Requests (400)**
```python
# Raises HTTPException with status 400
# Detail: "Invalid request: <error message>"
```

**Rate Limits (429)**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 429
# Detail: "OpenAI API rate limit exceeded"
```

**Server Errors (5xx)**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 502
# Detail: "OpenAI API server error"
```

**Timeouts**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 504
# Detail: "OpenAI API request timeout"
```

### Retry Logic

The provider implements exponential backoff for transient failures:

1. **First attempt**: Immediate request
2. **Second attempt**: 1 second delay (2^0)
3. **Third attempt**: 2 second delay (2^1)
4. **Fourth attempt**: 4 second delay (2^2)

Client errors (4xx except 429) are not retried.

### Health Checks

```python
# Check provider health
health = await provider.health_check()

if health.healthy:
    print(f"Provider: {health.name}")
    print(f"Latency: {health.latency_ms:.2f}ms")
else:
    print(f"Provider unhealthy: {health.error}")
```

Health checks use the `/models` endpoint with a 5-second timeout.

### Resource Cleanup

```python
# Always close the adapter when done
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()
```

Or use as an async context manager (if implemented):

```python
async with OpenAIAdapter(...) as adapter:
    response = await adapter.chat_completion(request, "req-123")
```

## vLLM Adapter

### Overview

The `VLLMAdapter` integrates with vLLM inference services that expose an OpenAI-compatible API. vLLM is a high-throughput and memory-efficient inference engine for LLMs. The adapter handles request translation, automatic retry logic, comprehensive error handling, and health monitoring.

### Initialization

```python
from app.providers.vllm import VLLMAdapter

# Local vLLM service
adapter = VLLMAdapter(
    name="vllm-local",
    config={"model": "llama-2-7b", "priority": 1},
    base_url="http://localhost:8000/v1",
    timeout=60.0,
    max_retries=3
)

# Remote vLLM service
remote_adapter = VLLMAdapter(
    name="vllm-remote",
    config={},
    base_url="https://vllm.example.com/v1",
    timeout=90.0
)
```

### Parameters

- **name** (str): Provider identifier for logging and metrics
- **config** (Dict[str, Any]): Provider configuration dictionary
- **base_url** (str): vLLM service base URL (default: `http://localhost:8000/v1`)
- **timeout** (float): Request timeout in seconds (default: 30.0)
- **max_retries** (int): Maximum retry attempts (default: 3)

### Chat Completion

```python
from app.providers.base import ChatCompletionRequest

# Create request
request = ChatCompletionRequest(
    model="llama-2-7b",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing"}
    ],
    temperature=0.7,
    max_tokens=200,
    top_p=0.9
)

# Execute request
response = await adapter.chat_completion(request, "req-xyz789")

# Access response
print(response.choices[0]["message"]["content"])
print(f"Tokens used: {response.usage['total_tokens']}")
```

### Error Handling

The adapter handles various error scenarios:

**Invalid Requests (400)**
```python
# Raises HTTPException with status 400
# Detail: "Invalid request: <error message>"
# No retry attempted
```

**Service Unavailable (503)**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 503
# Detail: "vLLM service unavailable"
```

**Server Errors (5xx)**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 502
# Detail: "vLLM service error"
```

**Timeouts**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 504
# Detail: "vLLM service request timeout"
```

**Network Errors**
```python
# Automatically retries with exponential backoff
# After max_retries, raises HTTPException with status 502
# Detail: "Failed to connect to vLLM service: <error>"
```

### Retry Logic

The adapter implements exponential backoff for transient failures:

1. **First attempt**: Immediate request
2. **Second attempt**: 1 second delay (2^0)
3. **Third attempt**: 2 second delay (2^1)
4. **Fourth attempt**: 4 second delay (2^2)

Client errors (400) are not retried.

### Health Checks

```python
# Check adapter health
health = await adapter.health_check()

if health.healthy:
    print(f"Adapter: {health.name}")
    print(f"Latency: {health.latency_ms:.2f}ms")
else:
    print(f"Adapter unhealthy: {health.error}")
```

Health checks use the `/models` endpoint with a 5-second timeout.

### Resource Cleanup

```python
# Always close the adapter when done
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()
```

Or use in application lifecycle:

```python
@app.on_event("shutdown")
async def shutdown_event():
    await adapter.close()
```

## Mock Providers

Mock providers are available for testing without external API calls:

```python
from app.providers.mock import MockOpenAIProvider, MockVLLMProvider

# Mock OpenAI provider
mock_openai = MockOpenAIProvider(
    name="mock-openai",
    config={"model": "gpt-3.5-turbo"}
)

# Mock vLLM provider
mock_vllm = MockVLLMProvider(
    name="mock-vllm",
    config={"model": "llama-2-7b"}
)

# Use like real providers
response = await mock_openai.chat_completion(request, "test-123")
```

Mock providers:
- Return deterministic responses
- Simulate processing delays (100-200ms)
- Always report healthy status
- Include mock token usage

## Provider Factory

The provider factory creates provider instances from configuration, abstracting the complexity of provider initialization.

### Factory Usage

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

# Create OpenAI provider from config
openai_config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    api_key_env="OPENAI_API_KEY",
    base_url="https://api.openai.com/v1",
    timeout=30.0,
    max_retries=3,
    weight=0.7,
    enabled=True
)

openai_provider = ProviderFactory.create_provider(openai_config)

# Create vLLM provider from config
vllm_config = ProviderConfig(
    name="vllm-local",
    type="vllm",
    base_url="http://localhost:8000/v1",
    timeout=60.0,
    max_retries=3,
    weight=0.3,
    enabled=True
)

vllm_provider = ProviderFactory.create_provider(vllm_config)

# Create mock provider for testing
mock_config = ProviderConfig(
    name="mock-openai-test",
    type="mock",
    weight=1.0,
    enabled=True
)

mock_provider = ProviderFactory.create_provider(mock_config)
```

### Supported Provider Types

The factory supports three provider types:

**OpenAI (`type="openai"`)**
- Requires API key via environment variable
- Defaults to `https://api.openai.com/v1` if base_url not specified
- API key environment variable defaults to `OPENAI_API_KEY`

**vLLM (`type="vllm"`)**
- No API key required
- Defaults to `http://localhost:8000/v1` if base_url not specified
- Expects OpenAI-compatible endpoint

**Mock (`type="mock"`)**
- No API key or base URL required
- Auto-selects MockOpenAIProvider or MockVLLMProvider based on name
- If name contains "openai", uses MockOpenAIProvider
- If name contains "vllm", uses MockVLLMProvider
- Otherwise defaults to MockOpenAIProvider

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

# Load config from YAML
with open("config.yaml") as f:
    config_data = yaml.safe_load(f)

# Create providers from config
providers = []
for provider_data in config_data["providers"]:
    config = ProviderConfig(**provider_data)
    provider = ProviderFactory.create_provider(config)
    providers.append(provider)
```

### Error Handling

```python
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig

# Missing API key for OpenAI
try:
    config = ProviderConfig(
        name="openai",
        type="openai",
        api_key_env="MISSING_KEY"
    )
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Error: {e}")
    # Error: OpenAI API key not found in environment variable: MISSING_KEY

# Unknown provider type
try:
    config = ProviderConfig(
        name="unknown",
        type="unknown_type"
    )
    provider = ProviderFactory.create_provider(config)
except ValueError as e:
    print(f"Error: {e}")
    # Error: Unknown provider type: unknown_type
```

## Provider Registry

The provider registry manages multiple providers and handles routing:

```python
from app.providers.registry import ProviderRegistry

# Create registry
registry = ProviderRegistry()

# Register providers
registry.register("openai-gpt4", openai_provider)
registry.register("vllm-local", vllm_provider)

# Get provider by name
provider = registry.get("openai-gpt4")

# List all providers
providers = registry.list_providers()

# Check all provider health
health_status = await registry.health_check_all()
```

## Integration with Gateway

### Dependency Injection

```python
from fastapi import Depends
from app.api.dependencies import get_provider_registry

@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    registry: ProviderRegistry = Depends(get_provider_registry)
):
    provider = registry.get("openai-gpt4")
    response = await provider.chat_completion(request, "req-123")
    return response
```

### Request Routing

```python
from app.router.router import RequestRouter

# Create router with weighted providers
router = RequestRouter(
    providers={
        "openai-gpt4": openai_provider,
        "vllm-local": vllm_provider
    },
    weights={
        "openai-gpt4": 0.7,
        "vllm-local": 0.3
    }
)

# Route request
provider = router.select_provider(request)
response = await provider.chat_completion(request, request_id)
```

## Observability

### Logging

All providers emit structured logs:

```python
# Debug logs
logger.debug(f"OpenAI request attempt 1/3: request_id={request_id}, model=gpt-4")

# Info logs
logger.info(f"OpenAI request successful: request_id={request_id}, elapsed=245.32ms")

# Warning logs
logger.warning(f"OpenAI API error (attempt 2/3): 429 - Rate limit exceeded")

# Error logs
logger.error(f"OpenAI health check failed: Connection timeout")
```

### Metrics

Providers should expose Prometheus metrics:

```python
from app.observability.metrics import (
    provider_request_duration,
    provider_request_total,
    provider_error_total
)

# Record request duration
with provider_request_duration.labels(provider=self.name, model=request.model).time():
    response = await self.chat_completion(request, request_id)

# Increment request counter
provider_request_total.labels(provider=self.name, model=request.model).inc()

# Record errors
provider_error_total.labels(provider=self.name, error_type="timeout").inc()
```

### Tracing

Providers propagate OpenTelemetry traces:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def chat_completion(self, request, request_id):
    with tracer.start_as_current_span(
        "openai.chat_completion",
        attributes={
            "provider.name": self.name,
            "request.id": request_id,
            "request.model": request.model
        }
    ):
        # Execute request
        response = await self.client.post(...)
        return response
```

## Best Practices

### 1. Always Handle Cleanup

```python
# Bad
adapter = OpenAIAdapter(...)
response = await adapter.chat_completion(request, "req-123")

# Good
adapter = OpenAIAdapter(...)
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()
```

### 2. Use Appropriate Timeouts

```python
# Short timeout for health checks
health = await adapter.health_check()  # 5s timeout

# Longer timeout for completions
adapter = OpenAIAdapter(..., timeout=30.0)
```

### 3. Configure Retries Based on Use Case

```python
# Interactive use: fewer retries
interactive_adapter = OpenAIAdapter(..., max_retries=2)

# Batch processing: more retries
batch_adapter = OpenAIAdapter(..., max_retries=5)
```

### 4. Monitor Provider Health

```python
# Periodic health checks
async def monitor_providers():
    while True:
        for provider in registry.list_providers():
            health = await provider.health_check()
            if not health.healthy:
                logger.error(f"Provider {provider.name} unhealthy: {health.error}")
        await asyncio.sleep(30)
```

### 5. Implement Circuit Breaking

```python
# Track failures and disable unhealthy providers
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60):
        self.failures = 0
        self.threshold = threshold
        self.timeout = timeout
        self.opened_at = None
    
    async def call(self, provider, request, request_id):
        if self.is_open():
            raise HTTPException(503, "Circuit breaker open")
        
        try:
            response = await provider.chat_completion(request, request_id)
            self.reset()
            return response
        except Exception as e:
            self.record_failure()
            raise
```

## Testing

### Unit Tests

```python
import pytest
from app.providers.openai import OpenAIAdapter

@pytest.mark.asyncio
async def test_openai_chat_completion():
    adapter = OpenAIAdapter(
        name="test-openai",
        config={},
        api_key="test-key"
    )
    
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    # Mock httpx client
    with patch.object(adapter.client, 'post') as mock_post:
        mock_post.return_value.json.return_value = {
            "id": "chatcmpl-123",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": [{"message": {"content": "Hi!"}}],
            "usage": {"total_tokens": 10}
        }
        
        response = await adapter.chat_completion(request, "test-123")
        assert response.id == "chatcmpl-123"
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_real_api():
    adapter = OpenAIAdapter(
        name="openai-test",
        config={},
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'test'"}],
        max_tokens=5
    )
    
    response = await adapter.chat_completion(request, "integration-test")
    assert "test" in response.choices[0]["message"]["content"].lower()
```

## Future Enhancements

- **Streaming support**: Implement SSE for streaming responses
- **Caching**: Add response caching for identical requests
- **Load balancing**: Implement advanced routing strategies
- **Cost tracking**: Track per-request costs and budgets
- **A/B testing**: Support model comparison and evaluation

## Related Documentation

- `app/providers/base.py` - Base provider interface
- `app/providers/openai.py` - OpenAI provider implementation
- `app/providers/registry.py` - Provider registry
- `docs/ARCHITECTURE.md` - System architecture
- `docs/API_DEPENDENCIES.md` - FastAPI integration patterns
