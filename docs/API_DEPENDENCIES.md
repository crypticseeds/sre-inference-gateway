# API Dependencies Documentation

This document provides comprehensive documentation for the FastAPI dependencies used in the SRE Inference Gateway.

## Overview

The `app.api.dependencies` module contains FastAPI dependency functions that handle:
- Request ID generation and propagation
- Provider routing configuration
- Request context setup for observability
- Header-based parameter extraction

All dependencies follow FastAPI's dependency injection pattern and can be used with the `Depends()` function.

## Dependencies

### get_request_id

Extracts or generates a unique request ID for tracing and logging purposes.

**Signature**:
```python
def get_request_id(x_request_id: Optional[str] = Header(None)) -> str
```

**Parameters**:
- `x_request_id` (Optional[str]): Request ID from the `X-Request-ID` header. If not provided, a new UUID-based ID is generated.

**Returns**:
- `str`: A unique request ID in the format `req-{16-char-hex}` (generated) or the provided header value.

**Usage Example**:
```python
from fastapi import Depends, FastAPI
from app.api.dependencies import get_request_id

app = FastAPI()

@app.get("/example")
async def example_endpoint(request_id: str = Depends(get_request_id)):
    return {"request_id": request_id}
```

**Header Usage**:
```bash
# With custom request ID
curl -H "X-Request-ID: my-custom-id-123" http://localhost:8000/v1/health

# Without header (auto-generated)
curl http://localhost:8000/v1/health
```

### get_provider_priority

Extracts provider priority from request headers for deterministic routing.

**Signature**:
```python
def get_provider_priority(x_provider_priority: Optional[str] = Header(None)) -> Optional[str]
```

**Parameters**:
- `x_provider_priority` (Optional[str]): Provider name from the `X-Provider-Priority` header.

**Returns**:
- `Optional[str]`: Provider name for deterministic routing, or `None` for weighted routing.

**Usage Example**:
```python
from fastapi import Depends
from app.api.dependencies import get_provider_priority

@app.post("/chat/completions")
async def chat_completion(
    provider_priority: Optional[str] = Depends(get_provider_priority)
):
    if provider_priority:
        print(f"Using specific provider: {provider_priority}")
    else:
        print("Using weighted routing")
```

**Header Usage**:
```bash
# Route to specific provider
curl -H "X-Provider-Priority: mock_openai" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [...]}' \
     http://localhost:8000/v1/chat/completions

# Use weighted routing (no header)
curl -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [...]}' \
     http://localhost:8000/v1/chat/completions
```

**Supported Providers**:
- `mock_openai`: Mock OpenAI provider
- `mock_vllm`: Mock vLLM provider
- Additional providers as configured in `PROVIDER_WEIGHTS`

### get_router

Creates and configures a RequestRouter instance with current settings.

**Signature**:
```python
def get_router() -> RequestRouter
```

**Parameters**: None

**Returns**:
- `RequestRouter`: Configured router instance with provider weights from settings.

**Usage Example**:
```python
from fastapi import Depends
from app.api.dependencies import get_router
from app.router.router import RequestRouter

@app.post("/chat/completions")
async def chat_completion(
    request_router: RequestRouter = Depends(get_router)
):
    provider = request_router.select_provider()
    return await provider.chat_completion(request)
```

**Configuration**:
The router is configured using the `PROVIDER_WEIGHTS` environment variable:
```bash
export PROVIDER_WEIGHTS='{"mock_openai": 0.7, "mock_vllm": 0.3}'
```

### setup_request_context

Sets up request context for distributed tracing and observability.

**Signature**:
```python
def setup_request_context(
    request: Request,
    request_id: str = Depends(get_request_id),
) -> None
```

**Parameters**:
- `request` (Request): FastAPI request object
- `request_id` (str): Request ID from `get_request_id` dependency

**Returns**:
- `None`: This dependency performs side effects only

**Side Effects**:
1. Adds request metadata to the current OpenTelemetry span:
   - `request.id`: Unique request identifier
   - `request.method`: HTTP method (GET, POST, etc.)
   - `request.url`: Full request URL
2. Stores request ID in `request.state.request_id` for handler access

**Usage Example**:
```python
from fastapi import Depends, Request
from app.api.dependencies import setup_request_context

@app.post("/chat/completions")
async def chat_completion(
    request: Request,
    _: None = Depends(setup_request_context)
):
    # Request context is now set up
    request_id = request.state.request_id
    # OpenTelemetry span has request metadata
    return {"request_id": request_id}
```

**Observability Integration**:
- **Tracing**: Adds structured attributes to OpenTelemetry spans
- **Logging**: Request ID available via `request.state.request_id`
- **Metrics**: Request metadata available for metric labeling

## Dependency Chain Example

Complete example showing how dependencies work together:

```python
from fastapi import APIRouter, Depends, Request
from typing import Optional

from app.api.dependencies import (
    get_request_id,
    get_provider_priority,
    get_router,
    setup_request_context,
)
from app.router.router import RequestRouter

router = APIRouter()

@router.post("/chat/completions")
async def create_chat_completion(
    request: Request,
    chat_request: ChatCompletionRequest,
    request_id: str = Depends(get_request_id),
    provider_priority: Optional[str] = Depends(get_provider_priority),
    request_router: RequestRouter = Depends(get_router),
    _: None = Depends(setup_request_context),
):
    """Complete endpoint with all dependencies."""
    # All context is now available:
    # - request_id: unique identifier
    # - provider_priority: optional routing hint
    # - request_router: configured router
    # - OpenTelemetry span: has request metadata
    # - request.state.request_id: accessible in middleware
    
    provider = request_router.select_provider(provider_priority)
    return await provider.chat_completion(chat_request, request_id)
```

## Error Handling

### Invalid Provider Priority

If an invalid provider name is specified in `X-Provider-Priority`:
- The router will log a warning
- Fallback to weighted routing occurs automatically
- No error is returned to the client

### Missing Dependencies

Dependencies are designed to be resilient:
- `get_request_id`: Always returns a valid ID (generated if not provided)
- `get_provider_priority`: Returns `None` if header not present
- `get_router`: Uses default weights if configuration is invalid
- `setup_request_context`: Safely handles missing OpenTelemetry context

## Testing Dependencies

### Unit Testing

```python
import pytest
from fastapi.testclient import TestClient
from app.api.dependencies import get_request_id, get_provider_priority

def test_get_request_id_with_header():
    """Test request ID extraction from header."""
    request_id = get_request_id("custom-id-123")
    assert request_id == "custom-id-123"

def test_get_request_id_generated():
    """Test request ID generation."""
    request_id = get_request_id(None)
    assert request_id.startswith("req-")
    assert len(request_id) == 20  # "req-" + 16 hex chars

def test_get_provider_priority():
    """Test provider priority extraction."""
    priority = get_provider_priority("mock_openai")
    assert priority == "mock_openai"
    
    priority = get_provider_priority(None)
    assert priority is None
```

### Integration Testing

```python
def test_dependencies_integration():
    """Test dependencies in FastAPI context."""
    with TestClient(app) as client:
        # Test with custom headers
        response = client.post(
            "/v1/chat/completions",
            headers={
                "X-Request-ID": "test-123",
                "X-Provider-Priority": "mock_openai"
            },
            json={"model": "gpt-3.5-turbo", "messages": [...]}
        )
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "test-123"
```

## Best Practices

1. **Always use dependencies for request context**: Don't manually extract headers in handlers
2. **Chain dependencies appropriately**: Use `setup_request_context` last to ensure all context is available
3. **Handle optional values gracefully**: Dependencies should work with or without headers
4. **Test dependency behavior**: Unit test each dependency function independently
5. **Use type hints**: All dependencies include proper type annotations for IDE support

## Integration with Observability

The dependencies integrate seamlessly with the observability stack:

- **OpenTelemetry**: Request metadata automatically added to spans
- **Prometheus**: Request IDs available for metric correlation
- **Logging**: Structured logging with request context
- **Distributed Tracing**: Request IDs propagate across service boundaries

## Configuration

Dependencies respect the following environment variables:

- `PROVIDER_WEIGHTS`: JSON object defining provider routing weights
- OpenTelemetry configuration (via standard environment variables)
- FastAPI configuration (debug mode, etc.)

See `docs/ENVIRONMENT.md` for complete configuration reference.