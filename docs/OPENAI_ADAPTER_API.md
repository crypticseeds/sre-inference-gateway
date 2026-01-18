# OpenAI Adapter API Documentation

## Overview

The `OpenAIAdapter` class provides a production-ready integration with the OpenAI API, implementing the `BaseProvider` interface for seamless integration with the SRE Inference Gateway. This adapter handles authentication, request/response translation, automatic retries with exponential backoff, comprehensive error handling, and health monitoring.

## Table of Contents

- [Class Reference](#class-reference)
- [Initialization](#initialization)
- [Methods](#methods)
- [Error Handling](#error-handling)
- [Usage Examples](#usage-examples)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)

## Class Reference

### `OpenAIAdapter`

**Module**: `app.providers.openai`

**Inherits**: `BaseProvider` (from `app.providers.base`)

**Purpose**: Adapts the OpenAI API to the internal provider interface, enabling the gateway to route requests to OpenAI while maintaining consistent error handling, retry logic, and observability.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Provider identifier for logging and metrics |
| `config` | `Dict[str, Any]` | Provider configuration dictionary |
| `api_key` | `str` | OpenAI API authentication key |
| `base_url` | `str` | OpenAI API base URL |
| `timeout` | `float` | Request timeout in seconds |
| `max_retries` | `int` | Maximum retry attempts for failed requests |
| `client` | `httpx.AsyncClient` | Async HTTP client for API requests |

## Initialization

### `__init__(name, config, api_key, base_url, timeout, max_retries)`

Initialize an OpenAI adapter instance with authentication and configuration.

#### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `name` | `str` | - | Yes | Provider identifier for logging and metrics tracking |
| `config` | `Dict[str, Any]` | - | Yes | Provider configuration dictionary |
| `api_key` | `str` | - | Yes | OpenAI API key for authentication |
| `base_url` | `str` | `"https://api.openai.com/v1"` | No | OpenAI API base URL |
| `timeout` | `float` | `30.0` | No | Request timeout in seconds |
| `max_retries` | `int` | `3` | No | Maximum retry attempts for transient failures |

#### Example

```python
from app.providers.openai import OpenAIAdapter

# Basic initialization
adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={"model": "gpt-4", "priority": 1},
    api_key="sk-..."
)

# Custom configuration
adapter = OpenAIAdapter(
    name="openai-gpt35",
    config={"model": "gpt-3.5-turbo"},
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    timeout=60.0,
    max_retries=5
)
```

#### Notes

- The `api_key` is passed via the `Authorization: Bearer` header
- The `base_url` should point to the OpenAI API v1 endpoint
- Timeout applies to both chat completion and health check requests
- Max retries only apply to transient failures (429, 5xx, timeouts, network errors)

## Methods

### `chat_completion(request, request_id)`

Process a chat completion request via the OpenAI API with automatic retry logic.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request` | `ChatCompletionRequest` | Yes | Chat completion request object |
| `request_id` | `str` | Yes | Unique identifier for request tracking |

#### Request Object (`ChatCompletionRequest`)

```python
class ChatCompletionRequest(BaseModel):
    model: str                              # Model identifier (e.g., "gpt-4")
    messages: list[Dict[str, Any]]          # Conversation messages
    temperature: Optional[float] = 1.0      # Sampling temperature (0.0-2.0)
    max_tokens: Optional[int] = None        # Maximum tokens to generate
    top_p: Optional[float] = 1.0            # Nucleus sampling (0.0-1.0)
    frequency_penalty: Optional[float] = 0.0  # Frequency penalty (-2.0-2.0)
    presence_penalty: Optional[float] = 0.0   # Presence penalty (-2.0-2.0)
    stream: bool = False                    # Whether to stream responses
    user: Optional[str] = None              # User identifier
```

#### Returns

`ChatCompletionResponse` object containing:

```python
class ChatCompletionResponse(BaseModel):
    id: str                          # Completion identifier
    object: str                      # "chat.completion"
    created: int                     # Unix timestamp
    model: str                       # Model used
    choices: list[Dict[str, Any]]    # Generated completions
    usage: Dict[str, int]            # Token usage statistics
```

#### Raises

| Exception | Status Code | Description | Retry? |
|-----------|-------------|-------------|--------|
| `HTTPException` | 400 | Invalid request format or parameters | No |
| `HTTPException` | 401 | Authentication failed (invalid API key) | No |
| `HTTPException` | 429 | Rate limit exceeded | Yes |
| `HTTPException` | 500 | Internal provider error | No |
| `HTTPException` | 502 | OpenAI server error or connection failure | Yes |
| `HTTPException` | 504 | Request timeout | Yes |

#### Example

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
    max_tokens=150
)

# Execute request
try:
    response = await adapter.chat_completion(request, "req-abc123")
    
    # Access response data
    content = response.choices[0]["message"]["content"]
    tokens_used = response.usage["total_tokens"]
    
    print(f"Response: {content}")
    print(f"Tokens: {tokens_used}")
    
except HTTPException as e:
    print(f"Error {e.status_code}: {e.detail}")
```

#### Retry Behavior

The adapter implements exponential backoff for transient failures:

| Attempt | Delay | Conditions |
|---------|-------|------------|
| 1 | 0s | Immediate request |
| 2 | 1s | After 429, 5xx, timeout, or network error |
| 3 | 2s | After second failure |
| 4 | 4s | After third failure |

**Client errors (4xx except 429) are NOT retried.**

#### Logging

The method emits structured logs at various levels:

```python
# DEBUG: Request attempts
logger.debug(
    f"OpenAI request attempt {attempt + 1}/{max_retries}: "
    f"request_id={request_id}, model={model}"
)

# INFO: Successful requests
logger.info(
    f"OpenAI request successful: request_id={request_id}, "
    f"elapsed={elapsed_ms:.2f}ms"
)

# WARNING: Retry attempts (HTTP errors and timeouts)
logger.warning(
    f"OpenAI API error (attempt {attempt + 1}/{max_retries}): "
    f"{status_code} - {error_text}"
)

# ERROR: Network/connection failures (with full context)
logger.error(
    f"OpenAI request error (attempt {attempt + 1}/{max_retries}): {error}. "
    f"Request ID: {request_id}, Elapsed: {elapsed_ms:.2f}ms"
)

# ERROR: Unexpected provider errors
logger.error(
    f"OpenAI provider error: {error}. "
    f"Request ID: {request_id}, Elapsed: {elapsed_ms:.2f}ms"
)
```

### `health_check()`

Check OpenAI API health and measure response latency.

#### Parameters

None

#### Returns

`ProviderHealth` object containing:

```python
class ProviderHealth(BaseModel):
    name: str                      # Provider identifier
    healthy: bool                  # Health status
    latency_ms: Optional[float]    # Response latency in milliseconds
    error: Optional[str]           # Error message if unhealthy
```

#### Example

```python
# Check health
health = await adapter.health_check()

if health.healthy:
    print(f"✓ {health.name} is healthy")
    print(f"  Latency: {health.latency_ms:.2f}ms")
else:
    print(f"✗ {health.name} is unhealthy")
    print(f"  Error: {health.error}")
    print(f"  Latency: {health.latency_ms:.2f}ms")
```

#### Implementation Details

- Uses the `/models` endpoint for health checks
- Shorter timeout (5 seconds) than regular requests
- Single attempt (no retries)
- Measures latency even for failed checks
- Returns unhealthy status on any exception

#### Use Cases

```python
# Periodic health monitoring
async def monitor_openai():
    while True:
        health = await adapter.health_check()
        if not health.healthy:
            logger.error(f"OpenAI unhealthy: {health.error}")
            # Trigger alert or failover
        await asyncio.sleep(30)

# Pre-request health check
async def safe_completion(request, request_id):
    health = await adapter.health_check()
    if not health.healthy:
        raise HTTPException(503, "Provider unavailable")
    return await adapter.chat_completion(request, request_id)
```

### `close()`

Close the HTTP client connection and release resources.

#### Parameters

None

#### Returns

None

#### Example

```python
# Manual cleanup
adapter = OpenAIAdapter(...)
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()

# Application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    await adapter.close()
```

#### Notes

- Should be called when the adapter is no longer needed
- Releases connection pools and other resources
- After calling `close()`, the adapter should not be used for further requests
- Create a new adapter instance if needed after closing

## Error Handling

### Error Response Format

All errors are raised as `HTTPException` with the following structure:

```python
HTTPException(
    status_code=<int>,
    detail=<str>
)
```

### Error Categories

#### Authentication Errors (401)

```python
# Raised when API key is invalid or missing
HTTPException(
    status_code=500,  # Mapped to 500 to hide auth details
    detail="OpenAI API authentication failed"
)
```

**Cause**: Invalid or expired API key

**Resolution**: Verify API key in environment variables

**Retry**: No

#### Invalid Request (400)

```python
# Raised when request format or parameters are invalid
HTTPException(
    status_code=400,
    detail="Invalid request: <error message from OpenAI>"
)
```

**Cause**: Malformed request, invalid parameters, or unsupported model

**Resolution**: Check request format and parameter values

**Retry**: No

#### Rate Limit (429)

```python
# Raised after max retries with rate limiting
HTTPException(
    status_code=429,
    detail="OpenAI API rate limit exceeded"
)
```

**Cause**: Too many requests to OpenAI API

**Resolution**: Implement backoff or reduce request rate

**Retry**: Yes (automatic with exponential backoff)

#### Server Error (502)

```python
# Raised after max retries with server errors
HTTPException(
    status_code=502,
    detail="OpenAI API server error"
)
```

**Cause**: OpenAI service issues or network problems

**Resolution**: Wait and retry, or failover to another provider

**Retry**: Yes (automatic with exponential backoff)

#### Timeout (504)

```python
# Raised after max retries with timeouts
HTTPException(
    status_code=504,
    detail="OpenAI API request timeout"
)
```

**Cause**: Request exceeded timeout duration

**Resolution**: Increase timeout or reduce request complexity

**Retry**: Yes (automatic with exponential backoff)

### Error Handling Example

```python
from fastapi import HTTPException

async def handle_completion(request, request_id):
    try:
        response = await adapter.chat_completion(request, request_id)
        return response
        
    except HTTPException as e:
        if e.status_code == 429:
            # Rate limited - implement backoff
            logger.warning("Rate limited, backing off")
            await asyncio.sleep(60)
            return await handle_completion(request, request_id)
            
        elif e.status_code == 502:
            # Server error - try fallback provider
            logger.error("OpenAI unavailable, using fallback")
            return await fallback_provider.chat_completion(request, request_id)
            
        elif e.status_code == 400:
            # Client error - don't retry
            logger.error(f"Invalid request: {e.detail}")
            raise
            
        else:
            # Unknown error
            logger.error(f"Unexpected error: {e.status_code} - {e.detail}")
            raise
```

## Usage Examples

### Basic Usage

```python
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

# Initialize adapter
adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={},
    api_key="sk-..."
)

# Create request
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Execute
response = await adapter.chat_completion(request, "req-123")
print(response.choices[0]["message"]["content"])

# Cleanup
await adapter.close()
```

### With Context Manager Pattern

```python
class OpenAIAdapterContext:
    def __init__(self, **kwargs):
        self.adapter = OpenAIAdapter(**kwargs)
    
    async def __aenter__(self):
        return self.adapter
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.adapter.close()

# Usage
async with OpenAIAdapterContext(
    name="openai",
    config={},
    api_key="sk-..."
) as adapter:
    response = await adapter.chat_completion(request, "req-123")
```

### With Provider Factory

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory
import os

# Create config
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

# Set API key in environment
os.environ["OPENAI_API_KEY"] = "sk-..."

# Create adapter via factory
adapter = ProviderFactory.create_provider(config)

# Use adapter
response = await adapter.chat_completion(request, "req-123")
```

### With Provider Registry

```python
from app.providers.registry import ProviderRegistry

# Create registry
registry = ProviderRegistry()

# Register adapter
registry.register_provider("openai-gpt4", adapter)

# Get adapter by name
provider = registry.get_provider("openai-gpt4")

# Use adapter
response = await provider.chat_completion(request, "req-123")
```

### Streaming Responses (Future)

```python
# Note: Streaming is not yet implemented
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True  # Will be supported in future version
)

# Future implementation will yield chunks
async for chunk in adapter.chat_completion_stream(request, "req-123"):
    print(chunk.choices[0]["delta"]["content"], end="")
```

## Integration Patterns

### FastAPI Dependency Injection

```python
from fastapi import Depends, FastAPI
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

app = FastAPI()

# Dependency function
async def get_openai_adapter() -> OpenAIAdapter:
    adapter = OpenAIAdapter(
        name="openai",
        config={},
        api_key=os.getenv("OPENAI_API_KEY")
    )
    try:
        yield adapter
    finally:
        await adapter.close()

# Endpoint using dependency
@app.post("/v1/chat/completions")
async def chat_completion(
    request: ChatCompletionRequest,
    adapter: OpenAIAdapter = Depends(get_openai_adapter)
):
    response = await adapter.chat_completion(request, "req-123")
    return response
```

### Request Router Integration

```python
from app.router.router import RequestRouter

# Create router with multiple providers
router = RequestRouter(
    providers={
        "openai-gpt4": openai_adapter,
        "vllm-local": vllm_adapter
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

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60):
        self.failures = 0
        self.threshold = threshold
        self.timeout = timeout
        self.opened_at = None
    
    def is_open(self):
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.timeout:
            self.reset()
            return False
        return True
    
    def record_failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.time()
    
    def reset(self):
        self.failures = 0
        self.opened_at = None
    
    async def call(self, adapter, request, request_id):
        if self.is_open():
            raise HTTPException(503, "Circuit breaker open")
        
        try:
            response = await adapter.chat_completion(request, request_id)
            self.reset()
            return response
        except HTTPException as e:
            if e.status_code >= 500:
                self.record_failure()
            raise

# Usage
breaker = CircuitBreaker()
response = await breaker.call(adapter, request, "req-123")
```

## Best Practices

### 1. Always Clean Up Resources

```python
# Bad - resource leak
adapter = OpenAIAdapter(...)
response = await adapter.chat_completion(request, "req-123")

# Good - proper cleanup
adapter = OpenAIAdapter(...)
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()
```

### 2. Use Appropriate Timeouts

```python
# Interactive use - shorter timeout
interactive_adapter = OpenAIAdapter(..., timeout=15.0)

# Batch processing - longer timeout
batch_adapter = OpenAIAdapter(..., timeout=60.0)

# Complex requests - very long timeout
complex_adapter = OpenAIAdapter(..., timeout=120.0)
```

### 3. Configure Retries Based on Use Case

```python
# Real-time API - fewer retries
realtime_adapter = OpenAIAdapter(..., max_retries=2)

# Background jobs - more retries
background_adapter = OpenAIAdapter(..., max_retries=5)

# Critical requests - maximum retries
critical_adapter = OpenAIAdapter(..., max_retries=10)
```

### 4. Implement Health Monitoring

```python
async def monitor_adapter_health(adapter, interval=30):
    """Monitor adapter health periodically."""
    while True:
        health = await adapter.health_check()
        
        if not health.healthy:
            logger.error(
                f"Adapter {adapter.name} unhealthy: {health.error}"
            )
            # Trigger alert or disable provider
        else:
            logger.info(
                f"Adapter {adapter.name} healthy: "
                f"{health.latency_ms:.2f}ms"
            )
        
        await asyncio.sleep(interval)
```

### 5. Handle Errors Gracefully

```python
async def safe_completion(adapter, request, request_id):
    """Execute completion with comprehensive error handling."""
    try:
        return await adapter.chat_completion(request, request_id)
        
    except HTTPException as e:
        if e.status_code == 429:
            # Rate limited - exponential backoff
            logger.warning("Rate limited, implementing backoff")
            await asyncio.sleep(60)
            return await safe_completion(adapter, request, request_id)
            
        elif e.status_code >= 500:
            # Server error - try fallback
            logger.error("Server error, using fallback")
            return await fallback_provider.chat_completion(
                request, request_id
            )
            
        else:
            # Client error - don't retry
            logger.error(f"Client error: {e.detail}")
            raise
```

### 6. Use Structured Logging

```python
import structlog

logger = structlog.get_logger()

async def logged_completion(adapter, request, request_id):
    """Execute completion with structured logging."""
    logger.info(
        "starting_completion",
        request_id=request_id,
        model=request.model,
        provider=adapter.name
    )
    
    try:
        response = await adapter.chat_completion(request, request_id)
        
        logger.info(
            "completion_success",
            request_id=request_id,
            tokens=response.usage["total_tokens"]
        )
        
        return response
        
    except HTTPException as e:
        logger.error(
            "completion_failed",
            request_id=request_id,
            status_code=e.status_code,
            detail=e.detail
        )
        raise
```

### 7. Implement Request Validation

```python
def validate_request(request: ChatCompletionRequest):
    """Validate request before sending to OpenAI."""
    # Check message count
    if len(request.messages) == 0:
        raise HTTPException(400, "Messages cannot be empty")
    
    # Check message roles
    valid_roles = {"system", "user", "assistant"}
    for msg in request.messages:
        if msg["role"] not in valid_roles:
            raise HTTPException(400, f"Invalid role: {msg['role']}")
    
    # Check token limits
    if request.max_tokens and request.max_tokens > 4096:
        raise HTTPException(400, "max_tokens exceeds limit")
    
    # Check temperature range
    if request.temperature < 0 or request.temperature > 2:
        raise HTTPException(400, "temperature must be between 0 and 2")

# Usage
validate_request(request)
response = await adapter.chat_completion(request, request_id)
```

### 8. Implement Cost Tracking

```python
class CostTracker:
    """Track OpenAI API costs."""
    
    PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002}
    }
    
    def calculate_cost(self, model, usage):
        """Calculate request cost."""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        prompt_cost = (usage["prompt_tokens"] / 1000) * pricing["prompt"]
        completion_cost = (usage["completion_tokens"] / 1000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    async def tracked_completion(self, adapter, request, request_id):
        """Execute completion with cost tracking."""
        response = await adapter.chat_completion(request, request_id)
        
        cost = self.calculate_cost(request.model, response.usage)
        
        logger.info(
            "completion_cost",
            request_id=request_id,
            model=request.model,
            tokens=response.usage["total_tokens"],
            cost_usd=cost
        )
        
        return response
```

## See Also

- [Provider Implementation Guide](PROVIDERS.md) - Comprehensive provider documentation
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [Provider Factory](../app/providers/factory.py) - Factory pattern implementation
- [Provider Registry](../app/providers/registry.py) - Provider management
- [vLLM Adapter](../app/providers/vllm.py) - Alternative provider implementation
