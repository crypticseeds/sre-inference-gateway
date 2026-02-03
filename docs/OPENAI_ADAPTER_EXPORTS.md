# OpenAI Adapter Module Exports

## Overview

This document provides a comprehensive reference for all exports from the `app.providers.openai` module, including classes, functions, and their usage patterns.

## Module Information

**Module Path**: `app.providers.openai`  
**Primary Export**: `OpenAIAdapter`  
**Dependencies**: `httpx`, `fastapi`, `app.providers.base`

## Exports

### Classes

#### `OpenAIAdapter`

**Type**: Class  
**Inherits**: `BaseProvider`  
**Purpose**: OpenAI API integration with retry logic and health monitoring

```python
from app.providers.openai import OpenAIAdapter

class OpenAIAdapter(BaseProvider):
    """OpenAI API adapter implementation."""
```

**Key Features**:
- OpenAI API integration with authentication
- Automatic retry with exponential backoff
- Comprehensive error handling and status code mapping
- Health monitoring via `/models` endpoint
- Resource management with proper cleanup
- Structured logging with request tracking

**Constructor Signature**:
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

**Public Methods**:
- `chat_completion(request, request_id)` → `ChatCompletionResponse`
- `health_check()` → `ProviderHealth`
- `close()` → `None`

**Usage Example**:
```python
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

# Initialize adapter
adapter = OpenAIAdapter(
    name="openai-gpt4",
    config={"model": "gpt-4"},
    api_key="sk-...",
    timeout=30.0,
    max_retries=3
)

# Create request
request = ChatCompletionRequest(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Execute request
response = await adapter.chat_completion(request, "req-123")

# Clean up
await adapter.close()
```

## Import Patterns

### Direct Import

```python
from app.providers.openai import OpenAIAdapter

adapter = OpenAIAdapter(...)
```

### Factory Pattern Import

```python
from app.providers.factory import ProviderFactory
from app.config.models import ProviderConfig

config = ProviderConfig(name="openai", type="openai", ...)
adapter = ProviderFactory.create_provider(config)
```

### Registry Pattern Import

```python
from app.providers.registry import ProviderRegistry

registry = ProviderRegistry()
registry.register_provider("openai", adapter)
provider = registry.get_provider("openai")
```

## Dependencies

### External Dependencies

```python
import asyncio          # Async sleep for retry backoff
import logging          # Structured logging
import time            # Timestamp generation and latency measurement
from typing import Any, Dict  # Type hints

import httpx           # Async HTTP client
from fastapi import HTTPException  # HTTP error responses
```

### Internal Dependencies

```python
from app.providers.base import (
    BaseProvider,           # Abstract base class
    ChatCompletionRequest,  # Request model
    ChatCompletionResponse, # Response model
    ProviderHealth,        # Health status model
)
```

## Module Constants

### Default Values

```python
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
HEALTH_CHECK_TIMEOUT = 5.0
```

### HTTP Status Codes

```python
# Success
HTTP_OK = 200

# Client Errors (no retry)
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401

# Rate Limiting (retry with backoff)
HTTP_TOO_MANY_REQUESTS = 429

# Server Errors (retry with backoff)
HTTP_INTERNAL_SERVER_ERROR = 500
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504
```

## Error Mappings

### OpenAI API → Gateway Mappings

| OpenAI Status | Gateway Status | Description | Retry |
|---------------|----------------|-------------|-------|
| 200 | 200 | Success | No |
| 400 | 400 | Bad Request | No |
| 401 | 500 | Auth Failed (mapped for security) | No |
| 429 | 429 | Rate Limited | Yes |
| 5xx | 502 | Server Error | Yes |
| Timeout | 504 | Gateway Timeout | Yes |
| Network | 502 | Bad Gateway | Yes |

## Configuration Integration

### Provider Configuration

```python
from app.config.models import ProviderConfig

config = ProviderConfig(
    name="openai-gpt4",
    type="openai",
    weight=0.7,
    enabled=True,
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
    timeout=30.0,
    max_retries=3
)
```

### Environment Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `OPENAI_API_KEY` | API authentication | - | Yes |
| `OPENAI_BASE_URL` | API endpoint | `https://api.openai.com/v1` | No |
| `OPENAI_TIMEOUT` | Request timeout | `30.0` | No |
| `OPENAI_MAX_RETRIES` | Retry attempts | `3` | No |

## Testing Integration

### Unit Test Imports

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest, ProviderHealth
```

### Mock Patterns

```python
# Mock HTTP client
with patch.object(adapter.client, "post", new=AsyncMock()) as mock_post:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {...}
    mock_post.return_value = mock_response
    
    response = await adapter.chat_completion(request, "test-id")
```

### Test Fixtures

```python
@pytest.fixture
async def openai_adapter():
    adapter = OpenAIAdapter(
        name="test-openai",
        config={},
        api_key="test-key"
    )
    yield adapter
    await adapter.close()
```

## Performance Characteristics

### Resource Usage

| Resource | Usage | Notes |
|----------|-------|-------|
| Memory | ~1MB base + ~10KB per request | HTTP client pool + request objects |
| CPU | Low | Async I/O bound operations |
| Network | Variable | Depends on request/response size |
| File Descriptors | 1-10 | HTTP connection pool |

### Timing Characteristics

| Operation | Typical Time | Max Time |
|-----------|--------------|----------|
| Initialization | <1ms | 10ms |
| Chat Completion | 500ms-5s | 30s (timeout) |
| Health Check | 50ms-500ms | 5s (timeout) |
| Cleanup | <10ms | 100ms |

## Logging Integration

### Log Levels

```python
# DEBUG: Request attempts and detailed flow
logger.debug("OpenAI request attempt %d/%d", attempt, max_retries)

# INFO: Successful operations and timing
logger.info("OpenAI request successful: elapsed=%.2fms", elapsed_ms)

# WARNING: Retryable errors
logger.warning("OpenAI API error (attempt %d/%d): %d", attempt, max_retries, status_code)

# ERROR: Non-retryable errors and failures
logger.error("OpenAI request error: %s", error)
```

### Structured Logging

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "openai_request_completed",
    request_id=request_id,
    model=request.model,
    tokens=response.usage["total_tokens"],
    elapsed_ms=elapsed_ms
)
```

## Metrics Integration

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

# Request counters
openai_requests_total = Counter(
    "openai_requests_total",
    "Total OpenAI API requests",
    ["status", "model"]
)

# Latency histogram
openai_request_duration = Histogram(
    "openai_request_duration_seconds",
    "OpenAI API request duration",
    ["model"]
)
```

## FastAPI Integration

### Dependency Injection

```python
from fastapi import Depends

async def get_openai_adapter() -> OpenAIAdapter:
    adapter = OpenAIAdapter(...)
    try:
        yield adapter
    finally:
        await adapter.close()

@app.post("/completions")
async def completions(
    request: ChatCompletionRequest,
    adapter: OpenAIAdapter = Depends(get_openai_adapter)
):
    return await adapter.chat_completion(request, "req-123")
```

## Best Practices

### Resource Management

```python
# Good: Use try/finally
adapter = OpenAIAdapter(...)
try:
    response = await adapter.chat_completion(request, "req-123")
finally:
    await adapter.close()

# Better: Use async context manager (if implemented)
async with OpenAIAdapter(...) as adapter:
    response = await adapter.chat_completion(request, "req-123")
```

### Error Handling

```python
from fastapi import HTTPException

try:
    response = await adapter.chat_completion(request, "req-123")
except HTTPException as e:
    if e.status_code == 429:
        # Handle rate limiting
        await asyncio.sleep(60)
        response = await adapter.chat_completion(request, "req-123")
    else:
        raise
```

### Configuration

```python
# Good: Use environment variables
import os

adapter = OpenAIAdapter(
    name="openai",
    config={},
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=float(os.getenv("OPENAI_TIMEOUT", "30.0"))
)

# Better: Use configuration models
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

config = ProviderConfig(
    name="openai",
    type="openai",
    api_key_env="OPENAI_API_KEY"
)
adapter = ProviderFactory.create_provider(config)
```

## Related Documentation

- [OpenAI Adapter API Reference](OPENAI_ADAPTER_API.md) - Complete API documentation
- [OpenAI Adapter Signatures](OPENAI_ADAPTER_SIGNATURES.md) - Quick signature reference
- [Provider Implementation Guide](PROVIDERS.md) - Provider architecture
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [Provider Factory](PROVIDER_FACTORY.md) - Factory pattern usage
- [Configuration Models](CONFIG_MODELS_API.md) - Configuration system

## Version History

### Current Version
- **Usage Data Simplification**: Returns usage as dictionary for performance
- **Enhanced Error Handling**: Improved error mapping and retry logic
- **Comprehensive Logging**: Structured logging with request tracking
- **Resource Management**: Proper HTTP client lifecycle management

### Previous Versions
- Initial implementation with Pydantic usage models
- Basic retry logic without exponential backoff
- Simple error handling without status code mapping

See [OpenAI Adapter Changelog](OPENAI_ADAPTER_CHANGELOG.md) for detailed version history.