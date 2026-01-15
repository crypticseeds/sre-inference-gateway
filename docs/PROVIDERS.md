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
│ OpenAIProvider │  │ VLLMProvider │  │  MockProvider  │
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

## OpenAI Provider

### Overview

The `OpenAIProvider` integrates with the OpenAI API to handle chat completion requests. It includes automatic retry logic, exponential backoff, comprehensive error handling, and health monitoring.

### Initialization

```python
from app.providers.openai import OpenAIProvider

provider = OpenAIProvider(
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
# Always close the provider when done
try:
    response = await provider.chat_completion(request, "req-123")
finally:
    await provider.close()
```

Or use as an async context manager (if implemented):

```python
async with OpenAIProvider(...) as provider:
    response = await provider.chat_completion(request, "req-123")
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
provider = OpenAIProvider(...)
response = await provider.chat_completion(request, "req-123")

# Good
provider = OpenAIProvider(...)
try:
    response = await provider.chat_completion(request, "req-123")
finally:
    await provider.close()
```

### 2. Use Appropriate Timeouts

```python
# Short timeout for health checks
health = await provider.health_check()  # 5s timeout

# Longer timeout for completions
provider = OpenAIProvider(..., timeout=30.0)
```

### 3. Configure Retries Based on Use Case

```python
# Interactive use: fewer retries
interactive_provider = OpenAIProvider(..., max_retries=2)

# Batch processing: more retries
batch_provider = OpenAIProvider(..., max_retries=5)
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
from app.providers.openai import OpenAIProvider

@pytest.mark.asyncio
async def test_openai_chat_completion():
    provider = OpenAIProvider(
        name="test-openai",
        config={},
        api_key="test-key"
    )
    
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello"}]
    )
    
    # Mock httpx client
    with patch.object(provider.client, 'post') as mock_post:
        mock_post.return_value.json.return_value = {
            "id": "chatcmpl-123",
            "created": 1234567890,
            "model": "gpt-3.5-turbo",
            "choices": [{"message": {"content": "Hi!"}}],
            "usage": {"total_tokens": 10}
        }
        
        response = await provider.chat_completion(request, "test-123")
        assert response.id == "chatcmpl-123"
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_real_api():
    provider = OpenAIProvider(
        name="openai-test",
        config={},
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    request = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'test'"}],
        max_tokens=5
    )
    
    response = await provider.chat_completion(request, "integration-test")
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
