# Pydantic Models Documentation

This document provides comprehensive documentation for all Pydantic models used in the SRE Inference Gateway.

## Overview

The gateway uses Pydantic models for:
- Request validation and parsing
- Response serialization
- Data transfer between components
- Type safety and documentation

All models follow OpenAI API compatibility standards where applicable.

## Core Models

### ChatCompletionRequest

OpenAI-compatible chat completion request model.

**Location**: `app.providers.base.ChatCompletionRequest`

**Fields**:
- `model` (str): The model identifier (e.g., "gpt-3.5-turbo")
- `messages` (list[Dict[str, Any]]): Array of message objects
- `temperature` (Optional[float], default=1.0): Sampling temperature (0.0-2.0)
- `max_tokens` (Optional[int], default=None): Maximum tokens to generate
- `stream` (bool, default=False): Whether to stream responses
- `user` (Optional[str], default=None): User identifier for tracking

**Example**:
```python
from app.providers.base import ChatCompletionRequest

request = ChatCompletionRequest(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"}
    ],
    temperature=0.7,
    max_tokens=150
)
```

**Message Format**:
Each message in the `messages` array should have:
- `role` (str): One of "system", "user", or "assistant"
- `content` (str): The message content

### ChatCompletionResponse

OpenAI-compatible chat completion response model.

**Location**: `app.providers.base.ChatCompletionResponse`

**Fields**:
- `id` (str): Unique response identifier (format: "chatcmpl-{uuid}")
- `object` (str, default="chat.completion"): Response object type
- `created` (int): Unix timestamp of creation
- `model` (str): Model that generated the response
- `choices` (list[Dict[str, Any]]): Array of completion choices
- `usage` (Dict[str, int]): Token usage statistics

**Example**:
```python
from app.providers.base import ChatCompletionResponse
import time

response = ChatCompletionResponse(
    id="chatcmpl-7QyqpwdfhqwajicIEznoc6Q47XAyW",
    created=int(time.time()),
    model="gpt-3.5-turbo",
    choices=[{
        "index": 0,
        "message": {
            "role": "assistant",
            "content": "Hello! I'm doing well, thank you for asking."
        },
        "finish_reason": "stop"
    }],
    usage={
        "prompt_tokens": 20,
        "completion_tokens": 12,
        "total_tokens": 32
    }
)
```

**Choice Format**:
Each choice in the `choices` array contains:
- `index` (int): Choice index (usually 0)
- `message` (Dict): Message object with "role" and "content"
- `finish_reason` (str): Reason completion stopped ("stop", "length", etc.)

**Usage Format**:
The `usage` object contains:
- `prompt_tokens` (int): Tokens in the input prompt
- `completion_tokens` (int): Tokens in the generated completion
- `total_tokens` (int): Total tokens used (prompt + completion)

### ProviderHealth

Provider health status model for monitoring and diagnostics.

**Location**: `app.providers.base.ProviderHealth`

**Fields**:
- `name` (str): Provider name/identifier
- `healthy` (bool): Whether the provider is healthy
- `latency_ms` (Optional[float], default=None): Response latency in milliseconds
- `error` (Optional[str], default=None): Error message if unhealthy

**Example**:
```python
from app.providers.base import ProviderHealth

# Healthy provider
healthy_status = ProviderHealth(
    name="mock_openai",
    healthy=True,
    latency_ms=150.5
)

# Unhealthy provider
unhealthy_status = ProviderHealth(
    name="mock_vllm",
    healthy=False,
    error="Connection timeout after 30s"
)
```

## Usage Patterns

### Request Validation

```python
from fastapi import HTTPException
from app.providers.base import ChatCompletionRequest

async def chat_completion_endpoint(request: ChatCompletionRequest):
    """FastAPI automatically validates the request using Pydantic."""
    try:
        # Request is already validated by FastAPI + Pydantic
        return await process_chat_request(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Response Serialization

```python
from app.providers.base import ChatCompletionResponse
import time

def create_response(request_id: str, model: str, content: str) -> ChatCompletionResponse:
    """Create a standardized chat completion response."""
    return ChatCompletionResponse(
        id=request_id,
        created=int(time.time()),
        model=model,
        choices=[{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop"
        }],
        usage={
            "prompt_tokens": 0,  # Calculate actual values
            "completion_tokens": 0,
            "total_tokens": 0
        }
    )
```

### Health Check Aggregation

```python
from app.providers.base import ProviderHealth
from typing import List

async def aggregate_provider_health(providers: List[str]) -> List[ProviderHealth]:
    """Check health of all providers."""
    health_statuses = []
    
    for provider_name in providers:
        try:
            provider = get_provider(provider_name)
            health = await provider.health_check()
            health_statuses.append(health)
        except Exception as e:
            health_statuses.append(ProviderHealth(
                name=provider_name,
                healthy=False,
                error=str(e)
            ))
    
    return health_statuses
```

## Validation Rules

### Request Validation

- `model`: Must be a non-empty string
- `messages`: Must be a non-empty array
- `temperature`: Must be between 0.0 and 2.0 if provided
- `max_tokens`: Must be positive integer if provided
- `stream`: Currently only `false` is supported

### Response Validation

- `id`: Must follow format "chatcmpl-{uuid}"
- `created`: Must be valid Unix timestamp
- `choices`: Must contain at least one choice
- `usage`: All token counts must be non-negative integers

## Error Handling

Pydantic automatically validates all model fields and raises `ValidationError` for invalid data:

```python
from pydantic import ValidationError
from app.providers.base import ChatCompletionRequest

try:
    request = ChatCompletionRequest(
        model="",  # Invalid: empty string
        messages=[],  # Invalid: empty array
        temperature=3.0  # Invalid: > 2.0
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Handle validation errors appropriately
```

## Integration with FastAPI

FastAPI automatically uses these models for:
- Request body validation
- Response serialization
- OpenAPI schema generation
- Interactive API documentation

The models appear in the auto-generated API docs at `/docs` with full field descriptions and examples.

## Best Practices

1. **Always use type hints**: All model fields should have proper type annotations
2. **Provide defaults**: Use sensible defaults for optional fields
3. **Add field descriptions**: Use Pydantic's `Field()` for documentation
4. **Validate constraints**: Use Pydantic validators for complex validation rules
5. **Keep models focused**: Each model should have a single responsibility
6. **Use composition**: Prefer composition over inheritance for complex models

## Future Enhancements

Potential model improvements:
- Add field-level validation for message roles
- Implement custom validators for model names
- Add support for function calling parameters
- Extend health model with more detailed metrics
- Add request/response middleware models for observability