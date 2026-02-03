# Response Models Documentation

## Overview

The `app.models.responses` module provides Pydantic models for OpenAI-compatible API responses used throughout the SRE Inference Gateway. These models ensure consistent response formatting, type safety, and automatic validation for all API endpoints.

## Module: `app.models.responses`

### Purpose

This module defines the response data structures that conform to the OpenAI API specification, enabling seamless integration with existing OpenAI-compatible clients while providing additional features like detailed token usage tracking.

### Key Features

- **OpenAI Compatibility**: Full compliance with OpenAI API response formats
- **Type Safety**: Pydantic models with comprehensive type hints
- **Automatic Validation**: Built-in validation for all response fields
- **Extensible Design**: Support for additional fields and future API versions
- **Detailed Token Tracking**: Enhanced token usage information for cost monitoring

## Classes

### `ChatCompletionChoice`

**Individual choice in a chat completion response.**

```python
class ChatCompletionChoice(BaseModel):
    """Individual choice in chat completion response."""
    
    index: int = Field(..., description="Choice index")
    message: Dict[str, Any] = Field(..., description="Response message")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")
```

#### Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `index` | `int` | Yes | Zero-based index of this choice in the choices array |
| `message` | `Dict[str, Any]` | Yes | The generated message content and metadata |
| `finish_reason` | `Optional[str]` | No | Reason why the model stopped generating tokens |

#### Message Structure

The `message` field typically contains:

```python
{
    "role": "assistant",           # Always "assistant" for completions
    "content": "Generated text",   # The actual response content
    "function_call": {...},        # Optional function call (if applicable)
    "tool_calls": [...]           # Optional tool calls (if applicable)
}
```

#### Finish Reasons

Common values for `finish_reason`:

| Value | Description |
|-------|-------------|
| `"stop"` | Model reached a natural stopping point |
| `"length"` | Response was truncated due to max_tokens limit |
| `"function_call"` | Model called a function |
| `"tool_calls"` | Model made tool calls |
| `"content_filter"` | Content was filtered due to policy violations |

#### Example

```python
choice = ChatCompletionChoice(
    index=0,
    message={
        "role": "assistant",
        "content": "Hello! How can I help you today?"
    },
    finish_reason="stop"
)
```

### `ChatCompletionUsage`

**Token usage information with detailed breakdown support.**

```python
class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(..., description="Tokens in the prompt")
    completion_tokens: int = Field(..., description="Tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")
    prompt_tokens_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed prompt token breakdown"
    )
    completion_tokens_details: Optional[Dict[str, Any]] = Field(
        None, description="Detailed completion token breakdown"
    )
```

#### Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt_tokens` | `int` | Yes | Number of tokens in the input prompt |
| `completion_tokens` | `int` | Yes | Number of tokens in the generated completion |
| `total_tokens` | `int` | Yes | Total tokens used (prompt + completion) |
| `prompt_tokens_details` | `Optional[Dict[str, Any]]` | No | Detailed breakdown of prompt token usage |
| `completion_tokens_details` | `Optional[Dict[str, Any]]` | No | Detailed breakdown of completion token usage |

#### Token Details Structure

The optional detail fields support OpenAI API v1.0+ enhanced token tracking:

**Prompt Token Details:**
```python
{
    "cached_tokens": 0,        # Number of cached tokens reused
    "audio_tokens": 0          # Number of audio input tokens (if applicable)
}
```

**Completion Token Details:**
```python
{
    "reasoning_tokens": 0,     # Tokens used for reasoning (o1 models)
    "audio_tokens": 0,         # Number of audio output tokens (if applicable)
    "accepted_prediction_tokens": 0,  # Tokens from accepted predictions
    "rejected_prediction_tokens": 0   # Tokens from rejected predictions
}
```

#### Example

```python
# Basic usage
usage = ChatCompletionUsage(
    prompt_tokens=25,
    completion_tokens=50,
    total_tokens=75
)

# With detailed breakdown
detailed_usage = ChatCompletionUsage(
    prompt_tokens=25,
    completion_tokens=50,
    total_tokens=75,
    prompt_tokens_details={
        "cached_tokens": 10,
        "audio_tokens": 0
    },
    completion_tokens_details={
        "reasoning_tokens": 15,
        "audio_tokens": 0
    }
)
```

### `ChatCompletionResponse`

**Main OpenAI-compatible chat completion response.**

```python
class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    
    id: str = Field(..., description="Unique completion ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(
        default_factory=lambda: int(time.time()), 
        description="Creation timestamp"
    )
    model: str = Field(..., description="Model used for completion")
    choices: List[ChatCompletionChoice] = Field(
        ..., description="List of completion choices"
    )
    usage: ChatCompletionUsage = Field(..., description="Token usage information")
```

#### Attributes

| Attribute | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | `str` | Yes | - | Unique identifier for this completion |
| `object` | `str` | Yes | `"chat.completion"` | Object type identifier |
| `created` | `int` | Yes | Current timestamp | Unix timestamp of creation |
| `model` | `str` | Yes | - | Model identifier used for completion |
| `choices` | `List[ChatCompletionChoice]` | Yes | - | Array of completion choices |
| `usage` | `ChatCompletionUsage` | Yes | - | Token usage statistics |

#### Example

```python
response = ChatCompletionResponse(
    id="chatcmpl-abc123",
    model="gpt-4",
    choices=[
        ChatCompletionChoice(
            index=0,
            message={
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            finish_reason="stop"
        )
    ],
    usage=ChatCompletionUsage(
        prompt_tokens=25,
        completion_tokens=15,
        total_tokens=40
    )
)
```

### `ErrorDetail`

**Detailed error information structure.**

```python
class ErrorDetail(BaseModel):
    """Error detail information."""
    
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    param: Optional[str] = Field(None, description="Parameter that caused error")
    code: Optional[str] = Field(None, description="Error code")
```

#### Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | `str` | Yes | Human-readable error description |
| `type` | `str` | Yes | Error type classification |
| `param` | `Optional[str]` | No | Parameter name that caused the error |
| `code` | `Optional[str]` | No | Specific error code identifier |

#### Common Error Types

| Type | Description | Example |
|------|-------------|---------|
| `"invalid_request_error"` | Request format or parameter issues | Missing required field |
| `"authentication_error"` | API key or authentication problems | Invalid API key |
| `"permission_error"` | Insufficient permissions | Model access denied |
| `"rate_limit_error"` | Too many requests | Rate limit exceeded |
| `"api_error"` | Internal API errors | Server error |

#### Example

```python
error_detail = ErrorDetail(
    message="Invalid value for 'temperature': must be between 0 and 2",
    type="invalid_request_error",
    param="temperature",
    code="invalid_parameter_value"
)
```

### `ErrorResponse`

**Standard error response wrapper.**

```python
class ErrorResponse(BaseModel):
    """Error response format."""
    
    error: ErrorDetail = Field(..., description="Error details")
```

#### Attributes

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `error` | `ErrorDetail` | Yes | Detailed error information |

#### Example

```python
error_response = ErrorResponse(
    error=ErrorDetail(
        message="The model 'invalid-model' does not exist",
        type="invalid_request_error",
        param="model",
        code="model_not_found"
    )
)
```

## Usage Examples

### Basic Chat Completion Response

```python
from app.models.responses import (
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage
)

# Create a simple response
response = ChatCompletionResponse(
    id="chatcmpl-example123",
    model="gpt-3.5-turbo",
    choices=[
        ChatCompletionChoice(
            index=0,
            message={
                "role": "assistant",
                "content": "I'm a helpful AI assistant. How can I help you?"
            },
            finish_reason="stop"
        )
    ],
    usage=ChatCompletionUsage(
        prompt_tokens=20,
        completion_tokens=12,
        total_tokens=32
    )
)

# Convert to dict for JSON serialization
response_dict = response.model_dump()
```

### Multiple Choices Response

```python
# Response with multiple completion choices
multi_choice_response = ChatCompletionResponse(
    id="chatcmpl-multi123",
    model="gpt-4",
    choices=[
        ChatCompletionChoice(
            index=0,
            message={
                "role": "assistant",
                "content": "Option 1: Here's one way to approach this..."
            },
            finish_reason="stop"
        ),
        ChatCompletionChoice(
            index=1,
            message={
                "role": "assistant",
                "content": "Option 2: Alternatively, you could..."
            },
            finish_reason="stop"
        )
    ],
    usage=ChatCompletionUsage(
        prompt_tokens=30,
        completion_tokens=40,
        total_tokens=70
    )
)
```

### Enhanced Token Usage Response

```python
# Response with detailed token breakdown (OpenAI API v1.0+)
enhanced_response = ChatCompletionResponse(
    id="chatcmpl-enhanced123",
    model="gpt-4o",
    choices=[
        ChatCompletionChoice(
            index=0,
            message={
                "role": "assistant",
                "content": "Here's a detailed analysis..."
            },
            finish_reason="stop"
        )
    ],
    usage=ChatCompletionUsage(
        prompt_tokens=50,
        completion_tokens=100,
        total_tokens=150,
        prompt_tokens_details={
            "cached_tokens": 20,
            "audio_tokens": 0
        },
        completion_tokens_details={
            "reasoning_tokens": 30,
            "audio_tokens": 0,
            "accepted_prediction_tokens": 5,
            "rejected_prediction_tokens": 2
        }
    )
)
```

### Error Response Handling

```python
from app.models.responses import ErrorResponse, ErrorDetail

# Create error response
error = ErrorResponse(
    error=ErrorDetail(
        message="Request timeout after 30 seconds",
        type="api_error",
        code="timeout"
    )
)

# Use in FastAPI endpoint
from fastapi import HTTPException

def handle_api_error(error_response: ErrorResponse):
    raise HTTPException(
        status_code=500,
        detail=error_response.model_dump()
    )
```

## Integration Patterns

### FastAPI Response Models

```python
from fastapi import FastAPI
from app.models.responses import ChatCompletionResponse, ErrorResponse

app = FastAPI()

@app.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate Limited"},
        500: {"model": ErrorResponse, "description": "Internal Error"}
    }
)
async def chat_completions(request: ChatCompletionRequest):
    # Implementation here
    pass
```

### Provider Adapter Integration

```python
from app.providers.base import BaseProvider
from app.models.responses import ChatCompletionResponse

class CustomProvider(BaseProvider):
    async def chat_completion(
        self, 
        request: ChatCompletionRequest, 
        request_id: str
    ) -> ChatCompletionResponse:
        # Provider-specific implementation
        raw_response = await self._make_api_call(request)
        
        # Convert to standard response format
        return ChatCompletionResponse(
            id=request_id,
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=raw_response["message"],
                    finish_reason=raw_response["finish_reason"]
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=raw_response["usage"]["prompt_tokens"],
                completion_tokens=raw_response["usage"]["completion_tokens"],
                total_tokens=raw_response["usage"]["total_tokens"]
            )
        )
```

### Response Validation

```python
from pydantic import ValidationError
from app.models.responses import ChatCompletionResponse

def validate_response(response_data: dict) -> ChatCompletionResponse:
    """Validate and parse response data."""
    try:
        return ChatCompletionResponse(**response_data)
    except ValidationError as e:
        logger.error(f"Response validation failed: {e}")
        raise ValueError(f"Invalid response format: {e}")

# Usage
try:
    validated_response = validate_response(api_response)
    return validated_response
except ValueError as e:
    # Handle validation error
    return ErrorResponse(
        error=ErrorDetail(
            message=str(e),
            type="validation_error"
        )
    )
```

## Testing

### Unit Tests

```python
import pytest
from app.models.responses import (
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ErrorResponse,
    ErrorDetail
)

def test_chat_completion_response():
    """Test basic chat completion response creation."""
    response = ChatCompletionResponse(
        id="test-123",
        model="gpt-3.5-turbo",
        choices=[
            ChatCompletionChoice(
                index=0,
                message={"role": "assistant", "content": "Hello!"},
                finish_reason="stop"
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15
        )
    )
    
    assert response.id == "test-123"
    assert response.model == "gpt-3.5-turbo"
    assert len(response.choices) == 1
    assert response.usage.total_tokens == 15

def test_enhanced_token_usage():
    """Test enhanced token usage with details."""
    usage = ChatCompletionUsage(
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
        prompt_tokens_details={"cached_tokens": 10},
        completion_tokens_details={"reasoning_tokens": 15}
    )
    
    assert usage.prompt_tokens_details["cached_tokens"] == 10
    assert usage.completion_tokens_details["reasoning_tokens"] == 15

def test_error_response():
    """Test error response creation."""
    error = ErrorResponse(
        error=ErrorDetail(
            message="Test error",
            type="test_error",
            param="test_param",
            code="TEST_001"
        )
    )
    
    assert error.error.message == "Test error"
    assert error.error.type == "test_error"
    assert error.error.param == "test_param"
    assert error.error.code == "TEST_001"
```

### Response Serialization Tests

```python
def test_response_serialization():
    """Test response model serialization."""
    response = ChatCompletionResponse(
        id="serialize-test",
        model="test-model",
        choices=[
            ChatCompletionChoice(
                index=0,
                message={"role": "assistant", "content": "Test"},
                finish_reason="stop"
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=5,
            completion_tokens=3,
            total_tokens=8
        )
    )
    
    # Test JSON serialization
    json_data = response.model_dump()
    assert json_data["id"] == "serialize-test"
    assert json_data["choices"][0]["message"]["content"] == "Test"
    
    # Test deserialization
    reconstructed = ChatCompletionResponse(**json_data)
    assert reconstructed.id == response.id
    assert reconstructed.choices[0].message == response.choices[0].message
```

## Best Practices

### 1. Always Use Type Hints

```python
from typing import List
from app.models.responses import ChatCompletionResponse

def process_responses(responses: List[ChatCompletionResponse]) -> dict:
    """Process multiple chat completion responses."""
    total_tokens = sum(r.usage.total_tokens for r in responses)
    return {"total_tokens": total_tokens, "response_count": len(responses)}
```

### 2. Validate External Data

```python
def create_response_from_api(api_data: dict) -> ChatCompletionResponse:
    """Create response from external API data with validation."""
    try:
        return ChatCompletionResponse(**api_data)
    except ValidationError as e:
        logger.error(f"Invalid API response: {e}")
        raise ValueError("Failed to parse API response")
```

### 3. Handle Optional Fields Gracefully

```python
def extract_token_details(usage: ChatCompletionUsage) -> dict:
    """Extract token details with fallbacks."""
    details = {
        "basic": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens
        }
    }
    
    if usage.prompt_tokens_details:
        details["prompt_details"] = usage.prompt_tokens_details
    
    if usage.completion_tokens_details:
        details["completion_details"] = usage.completion_tokens_details
    
    return details
```

### 4. Use Factory Functions for Complex Responses

```python
def create_error_response(
    message: str,
    error_type: str = "api_error",
    param: str = None,
    code: str = None
) -> ErrorResponse:
    """Factory function for creating error responses."""
    return ErrorResponse(
        error=ErrorDetail(
            message=message,
            type=error_type,
            param=param,
            code=code
        )
    )

# Usage
error = create_error_response(
    message="Model not found",
    error_type="invalid_request_error",
    param="model",
    code="model_not_found"
)
```

## Related Documentation

- [Request Models](../app/models/requests.py) - Input request models
- [Base Provider Interface](../app/providers/base.py) - Provider interface using these models
- [OpenAI Adapter](../app/providers/openai.py) - OpenAI provider implementation
- [API Endpoints](../app/api/completions.py) - FastAPI endpoints using these models
- [Provider Factory](../app/providers/factory.py) - Provider creation and management

## Summary

The response models provide a robust, type-safe foundation for all API responses in the SRE Inference Gateway. Key benefits:

- ✅ **OpenAI Compatibility**: Full compliance with OpenAI API specifications
- ✅ **Type Safety**: Comprehensive Pydantic validation and type hints
- ✅ **Enhanced Features**: Support for detailed token usage tracking
- ✅ **Error Handling**: Structured error response format
- ✅ **Extensibility**: Easy to extend for future API versions
- ✅ **Testing**: Comprehensive validation and serialization support

These models ensure consistent, validated responses across all providers and endpoints while maintaining compatibility with existing OpenAI-compatible clients.