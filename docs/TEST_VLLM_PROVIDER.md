# vLLM Provider Tests Documentation

## Overview

The `tests/test_vllm_provider.py` module provides comprehensive unit tests for the vLLM provider adapter implementation. These tests validate the adapter's behavior, error handling, health checks, and integration with the vLLM inference service using mocked HTTP responses.

## Purpose

This test suite ensures:
- vLLM adapter correctly handles successful API responses
- Error conditions (timeouts, service unavailability, server errors) are properly handled
- Health checks accurately report provider status
- Adapter initialization and configuration work correctly
- Request/response translation functions properly

## Test Structure

### Test Classes

The module uses pytest fixtures and async test functions to validate the `VLLMAdapter` class functionality.

### Fixtures

#### `vllm_config()`

Creates a standard test configuration for vLLM provider.

**Returns:**
- `dict`: Configuration dictionary with:
  - timeout: 30.0 seconds

**Usage:**
```python
def test_example(vllm_config):
    adapter = VLLMAdapter("test", vllm_config, ...)
```

#### `vllm_provider(vllm_config)`

Creates a configured vLLM adapter instance for testing.

**Parameters:**
- `vllm_config` (dict): Configuration from vllm_config fixture

**Returns:**
- `VLLMAdapter`: Configured adapter instance with:
  - name: "vllm"
  - base_url: "http://localhost:8080/v1"
  - timeout: 30.0 seconds
  - max_retries: 3

**Usage:**
```python
def test_example(vllm_provider):
    response = await vllm_provider.chat_completion(request, "test-123")
```

#### `sample_request()`

Creates a standard test chat completion request.

**Returns:**
- `ChatCompletionRequest`: Test request with:
  - model: "facebook/opt-125m"
  - messages: Single user message "Hello, how are you?"
  - temperature: 0.7
  - max_tokens: 100

**Usage:**
```python
def test_example(sample_request):
    response = await adapter.chat_completion(sample_request, "test-123")
```

## Test Cases

### Initialization Tests

#### `test_vllm_provider_initialization(vllm_provider)`

**Purpose:** Verify vLLM adapter initialization with correct configuration.

**Test Flow:**
1. Create vLLM adapter using fixture
2. Assert all configuration parameters are set correctly

**Assertions:**
- Provider name matches expected value
- Base URL is correctly configured
- Timeout value is properly set
- Max retries value is correctly configured

**Example:**
```python
@pytest.mark.asyncio
async def test_vllm_provider_initialization(vllm_provider):
    assert vllm_provider.name == "vllm"
    assert vllm_provider.base_url == "http://localhost:8080/v1"
    assert vllm_provider.timeout == 30.0
    assert vllm_provider.max_retries == 3
```

#### `test_vllm_provider_base_url_trailing_slash()`

**Purpose:** Verify that trailing slashes are properly removed from base URLs.

**Test Flow:**
1. Create adapter with base URL containing trailing slash
2. Assert trailing slash is removed

**Assertions:**
- Base URL has trailing slash removed
- URL normalization works correctly

**Note:** There appears to be a bug in the current test - it expects `http://localhost:8001/v1` but creates with `http://localhost:8080/v1/`.

### Chat Completion Tests

#### `test_chat_completion_success(vllm_provider, sample_request)`

**Purpose:** Verify successful chat completion request handling.

**Test Flow:**
1. Create mock response with valid vLLM API response data
2. Mock httpx client POST method
3. Execute chat completion request
4. Assert response contains expected fields and values

**Mock Response Data:**
```python
{
    "id": "chatcmpl-123",
    "object": "chat.completion", 
    "created": 1234567890,
    "model": "facebook/opt-125m",
    "choices": [{
        "index": 0,
        "message": {"role": "assistant", "content": "Hello!"},
        "finish_reason": "stop"
    }],
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 8, 
        "total_tokens": 18
    }
}
```

**Assertions:**
- Response ID matches mock data
- Response model matches expected model
- Response contains exactly one choice
- Token usage statistics are correct

#### `test_chat_completion_http_error(vllm_provider, sample_request)`

**Purpose:** Verify handling of HTTP server errors (5xx status codes).

**Test Flow:**
1. Mock httpx response with 500 status code
2. Execute chat completion request
3. Assert HTTPException is raised with correct status code

**Assertions:**
- HTTPException is raised
- Exception status code is 502 (mapped from 500)
- Error handling works correctly

#### `test_chat_completion_timeout(vllm_provider, sample_request)`

**Purpose:** Verify timeout handling with proper exception mapping.

**Test Flow:**
1. Mock httpx client to raise TimeoutException
2. Execute chat completion request
3. Assert HTTPException is raised with timeout status code

**Assertions:**
- HTTPException is raised
- Exception status code is 504 (timeout)
- Timeout errors are properly handled

### Health Check Tests

#### `test_health_check_success(vllm_provider)`

**Purpose:** Verify health check reports healthy status for responsive service.

**Test Flow:**
1. Mock httpx GET request with 200 status
2. Execute health check
3. Assert health status indicates healthy service

**Assertions:**
- Health status is True
- Provider name matches adapter name
- Latency measurement is present and non-negative
- No error message is present

**Example:**
```python
@pytest.mark.asyncio
async def test_health_check_success(vllm_provider):
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch.object(vllm_provider.client, "get", return_value=mock_response):
        health = await vllm_provider.health_check()
    
    assert isinstance(health, ProviderHealth)
    assert health.name == "vllm"
    assert health.healthy is True
    assert health.latency_ms >= 0
    assert health.error is None
```

#### `test_health_check_failure(vllm_provider)`

**Purpose:** Verify health check reports unhealthy status for connection failures.

**Test Flow:**
1. Mock httpx client to raise ConnectError
2. Execute health check
3. Assert health status indicates unhealthy service with error details

**Assertions:**
- Health status is False
- Provider name matches adapter name
- Error message contains connection failure details
- Latency measurement is still captured

## Running Tests

### Run All vLLM Provider Tests

```bash
doppler run -- uv run pytest tests/test_vllm_provider.py -v
```

### Run Specific Test

```bash
doppler run -- uv run pytest tests/test_vllm_provider.py::test_chat_completion_success -v
```

### Run with Coverage

```bash
doppler run -- uv run pytest tests/test_vllm_provider.py --cov=app.providers.vllm --cov-report=html
```

## Test Dependencies

### Required Packages

- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `httpx`: HTTP client (mocked in tests)
- `unittest.mock`: Mocking framework (MagicMock, patch, AsyncMock)

### Mocked Components

- `httpx.AsyncClient.post`: HTTP POST requests for chat completions
- `httpx.AsyncClient.get`: HTTP GET requests for health checks
- HTTP responses and exceptions for error testing

## Integration with CI/CD

These tests are designed to run in CI/CD pipelines without external dependencies:

```yaml
# .github/workflows/test.yml
- name: Run vLLM provider tests
  run: |
    doppler run -- uv run pytest tests/test_vllm_provider.py -v --cov=app.providers.vllm
```

## Known Issues

### Base URL Trailing Slash Test Bug

The test `test_vllm_provider_base_url_trailing_slash()` contains a bug:

**Current Code:**
```python
provider = VLLMAdapter(
    name="vllm", config={}, base_url="http://localhost:8080/v1/", timeout=30.0
)
assert provider.base_url == "http://localhost:8001/v1"  # Wrong port!
```

**Expected Fix:**
```python
assert provider.base_url == "http://localhost:8080/v1"  # Correct port
```

This test should verify that the trailing slash is removed while preserving the correct port number.

## Best Practices

### 1. Use Fixtures for Common Setup

```python
@pytest.fixture
def vllm_provider():
    return VLLMAdapter(
        name="test-vllm",
        config={},
        base_url="http://localhost:8080/v1",
        timeout=30.0
    )
```

### 2. Mock External Dependencies

```python
with patch.object(adapter.client, "post", return_value=mock_response):
    response = await adapter.chat_completion(request, "test-123")
```

### 3. Test Error Conditions

```python
with patch.object(adapter.client, "post", side_effect=httpx.TimeoutException("Timeout")):
    with pytest.raises(HTTPException) as exc_info:
        await adapter.chat_completion(request, "test-123")
    assert exc_info.value.status_code == 504
```

### 4. Validate Response Structure

```python
assert response.id == "chatcmpl-123"
assert len(response.choices) == 1
assert response.usage["total_tokens"] == 18
```

### 5. Test Health Check Scenarios

```python
# Test both success and failure scenarios
async def test_health_check_success(vllm_provider):
    # Mock successful response
    
async def test_health_check_failure(vllm_provider):
    # Mock connection error
```

## Related Documentation

- [vLLM Provider Implementation](../app/providers/vllm.py) - Main provider implementation
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [Real Provider Tests](TEST_REAL_PROVIDERS.md) - Comprehensive provider test documentation
- [Provider Implementation Guide](PROVIDERS.md) - Provider architecture overview

## Future Enhancements

### Additional Test Coverage

1. **Retry Logic Tests**
   - Test exponential backoff timing
   - Verify retry count limits
   - Test retry conditions (503, 5xx errors)

2. **Request Validation Tests**
   - Test invalid request parameters
   - Test model validation
   - Test message format validation

3. **Configuration Tests**
   - Test various timeout values
   - Test different retry configurations
   - Test base URL variations

4. **Streaming Tests** (when implemented)
   - Test streaming response handling
   - Verify chunk processing
   - Test stream error handling

5. **Integration Tests**
   - Test with real vLLM endpoints (optional)
   - Test end-to-end request flow
   - Test provider failover scenarios

## Summary

The `test_vllm_provider.py` module provides comprehensive unit test coverage for the vLLM provider adapter. Tests validate:

- ✅ Adapter initialization and configuration
- ✅ Successful request handling
- ✅ Error condition handling (timeouts, server errors)
- ✅ Health check functionality
- ✅ HTTP response parsing
- ✅ Exception mapping and error propagation

All tests use mocked HTTP responses to ensure fast, reliable execution without external dependencies, making them suitable for CI/CD pipelines.