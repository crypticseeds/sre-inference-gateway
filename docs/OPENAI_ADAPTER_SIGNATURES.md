# OpenAI Adapter API Signatures

## Overview

This document provides the complete API signatures for the `OpenAIAdapter` class, including all methods, parameters, return types, and exceptions. This serves as a quick reference for developers integrating with the OpenAI provider.

## Module Information

**Module**: `app.providers.openai`  
**Class**: `OpenAIAdapter`  
**Inherits**: `BaseProvider`  
**Import**: `from app.providers.openai import OpenAIAdapter`

## Class Signature

```python
class OpenAIAdapter(BaseProvider):
    """OpenAI API adapter implementation.
    
    This provider integrates with the OpenAI API to handle chat completion
    requests. It includes retry logic, error handling, and health monitoring.
    """
```

## Constructor

```python
def __init__(
    self,
    name: str,
    config: Dict[str, Any],
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    timeout: float = 30.0,
    max_retries: int = 3,
) -> None
```

### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `name` | `str` | - | ✓ | Provider identifier for logging and metrics |
| `config` | `Dict[str, Any]` | - | ✓ | Provider configuration dictionary |
| `api_key` | `str` | - | ✓ | OpenAI API key for authentication |
| `base_url` | `str` | `"https://api.openai.com/v1"` | ✗ | OpenAI API base URL |
| `timeout` | `float` | `30.0` | ✗ | Request timeout in seconds |
| `max_retries` | `int` | `3` | ✗ | Maximum retry attempts for failed requests |

### Raises

| Exception | Condition |
|-----------|-----------|
| `ValueError` | If `max_retries` is less than 1 |

## Public Methods

### chat_completion

```python
async def chat_completion(
    self,
    request: ChatCompletionRequest,
    request_id: str
) -> ChatCompletionResponse
```

**Inherited from BaseProvider** - Wraps `_chat_completion_impl` with resilience patterns.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request` | `ChatCompletionRequest` | ✓ | Chat completion request object |
| `request_id` | `str` | ✓ | Unique identifier for request tracking |

#### Returns

| Type | Description |
|------|-------------|
| `ChatCompletionResponse` | Response containing model output, usage stats, and metadata |

#### Raises

| Exception | Status Code | Description |
|-----------|-------------|-------------|
| `HTTPException` | 400 | Invalid request format or parameters |
| `HTTPException` | 429 | Rate limit exceeded after retries |
| `HTTPException` | 500 | Authentication failed (mapped from 401) |
| `HTTPException` | 502 | Server error or connection failure after retries |
| `HTTPException` | 504 | Request timeout after retries |

### health_check

```python
async def health_check(self) -> ProviderHealth
```

**Inherited from BaseProvider** - Wraps `_health_check_impl` with resilience patterns.

#### Returns

| Type | Description |
|------|-------------|
| `ProviderHealth` | Health status object with latency and error information |

### close

```python
async def close(self) -> None
```

#### Description

Closes the HTTP client connection and releases resources.

## Private Implementation Methods

### _chat_completion_impl

```python
async def _chat_completion_impl(
    self,
    request: ChatCompletionRequest,
    request_id: str,
) -> ChatCompletionResponse
```

**Internal implementation** - Called by the public `chat_completion` method after resilience patterns are applied.

#### Implementation Details

- Converts `ChatCompletionRequest` to OpenAI API payload
- Implements exponential backoff retry logic
- Handles HTTP status codes: 200, 400, 401, 429, 5xx
- Maps authentication errors (401) to internal server errors (500)
- Parses OpenAI response and converts to `ChatCompletionResponse`
- Returns usage data as a simple dictionary for performance

#### Retry Behavior

| Condition | Retry | Backoff |
|-----------|-------|---------|
| 200 OK | No | - |
| 400 Bad Request | No | - |
| 401 Unauthorized | No | - |
| 429 Rate Limited | Yes | Exponential (2^attempt) |
| 5xx Server Error | Yes | Exponential (2^attempt) |
| Timeout | Yes | Exponential (2^attempt) |
| Network Error | Yes | Exponential (2^attempt) |

### _health_check_impl

```python
async def _health_check_impl(self) -> ProviderHealth
```

**Internal implementation** - Called by the public `health_check` method after resilience patterns are applied.

#### Implementation Details

- Uses OpenAI `/models` endpoint for health checks
- 5-second timeout (shorter than regular requests)
- Single attempt (no retries)
- Measures latency even for failed checks
- Returns unhealthy status on any exception

## Data Models

### ChatCompletionRequest

```python
class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Dict[str, Any]]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stream: bool = False
    user: Optional[str] = None
```

### ChatCompletionResponse

```python
class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Dict[str, Any]]
    usage: Dict[str, int]  # Simple dictionary format
```

### ProviderHealth

```python
class ProviderHealth(BaseModel):
    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
```

## Usage Examples

### Basic Initialization

```python
from app.providers.openai import OpenAIAdapter

adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={"model": "gpt-4"},
    api_key="sk-...",
    timeout=30.0,
    max_retries=3
)
```

### Chat Completion

```python
from app.providers.base import ChatCompletionRequest

request = ChatCompletionRequest(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=100
)

response = await adapter.chat_completion(request, "req-123")
content = response.choices[0]["message"]["content"]
tokens = response.usage["total_tokens"]
```

### Health Check

```python
health = await adapter.health_check()
if health.healthy:
    print(f"Healthy: {health.latency_ms}ms")
else:
    print(f"Unhealthy: {health.error}")
```

### Resource Cleanup

```python
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()
```

## Error Handling

### Exception Hierarchy

```
HTTPException
├── 400 Bad Request (client errors, no retry)
├── 429 Too Many Requests (rate limits, retry with backoff)
├── 500 Internal Server Error (auth failures, no retry)
├── 502 Bad Gateway (server/network errors, retry with backoff)
└── 504 Gateway Timeout (timeouts, retry with backoff)
```

### Error Response Format

All errors are raised as `HTTPException` with:

```python
HTTPException(
    status_code: int,
    detail: str
)
```

## Configuration Integration

### With Provider Factory

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    api_key_env="OPENAI_API_KEY",
    timeout=30.0,
    max_retries=3
)

adapter = ProviderFactory.create_provider(config)
```

### With Environment Variables

```python
import os

adapter = OpenAIAdapter(
    name="openai",
    config={},
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=float(os.getenv("OPENAI_TIMEOUT", "30.0")),
    max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3"))
)
```

## Performance Characteristics

### Timeouts

| Operation | Default Timeout | Configurable |
|-----------|----------------|--------------|
| Chat Completion | 30.0s | Yes (constructor) |
| Health Check | 5.0s | No (hardcoded) |

### Retry Timing

| Attempt | Delay | Total Time |
|---------|-------|------------|
| 1 | 0s | 0s |
| 2 | 1s | 1s |
| 3 | 2s | 3s |
| 4 | 4s | 7s |

### Memory Usage

- HTTP client connection pool: ~1MB
- Request/response objects: ~10KB per request
- Retry state: ~1KB per request

## Thread Safety

- ✅ **Thread-safe**: Multiple coroutines can use the same adapter instance
- ✅ **Async-safe**: All methods are properly async
- ⚠️ **Resource cleanup**: Must call `close()` to prevent resource leaks

## Related Documentation

- [OpenAI Adapter API Reference](OPENAI_ADAPTER_API.md) - Comprehensive API documentation
- [Provider Implementation Guide](PROVIDERS.md) - Provider architecture overview
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [Provider Factory](PROVIDER_FACTORY.md) - Factory pattern documentation
- [Configuration Models](CONFIG_MODELS_API.md) - Configuration system

## Changelog

### Recent Changes

- **Usage Data Simplification**: Usage information is now returned as a simple dictionary instead of a Pydantic model instance for improved performance
- **Merge Conflict Resolution**: Resolved merge conflicts in error handling logic
- **Defensive Error Handling**: Added RuntimeError as a safety net for unreachable code paths

See [OpenAI Adapter Changelog](OPENAI_ADAPTER_CHANGELOG.md) for detailed change history.