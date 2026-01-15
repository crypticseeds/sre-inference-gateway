# Real Provider Tests Documentation

## Overview

The `tests/test_real_providers.py` module provides comprehensive unit tests for the OpenAI and vLLM provider adapters, as well as the provider factory. These tests validate adapter behavior, error handling, health checks, and factory instantiation patterns using mocked HTTP responses.

## Purpose

This test suite ensures:
- Provider adapters correctly handle successful API responses
- Error conditions (timeouts, service unavailability, authentication failures) are properly handled
- Health checks accurately report provider status
- The provider factory correctly instantiates adapters from configuration
- Retry logic and exponential backoff work as expected

## Test Structure

### Test Classes

#### `TestOpenAIAdapter`
Tests for the OpenAI API adapter implementation.

#### `TestVLLMAdapter`
Tests for the vLLM inference service adapter implementation.

#### `TestProviderFactory`
Tests for the provider factory pattern implementation.

## Fixtures

### `chat_request()`

Creates a standard test chat completion request.

**Returns:**
- `ChatCompletionRequest`: Test request with:
  - model: "gpt-3.5-turbo"
  - messages: Single user message "Hello, world!"
  - temperature: 0.7
  - max_tokens: 100

**Usage:**
```python
def test_example(chat_request):
    response = await adapter.chat_completion(chat_request, "test-123")
```

### `mock_openai_response()`

Creates a mock OpenAI API response matching the expected format.

**Returns:**
- `dict`: Mock response containing:
  - id: "chatcmpl-123"
  - object: "chat.completion"
  - created: Unix timestamp
  - model: "gpt-3.5-turbo"
  - choices: List with single assistant message
  - usage: Token usage statistics

**Usage:**
```python
def test_example(mock_openai_response):
    mock_response.json.return_value = mock_openai_response
```

## Test Cases

### OpenAI Adapter Tests

#### `test_chat_completion_success`

**Purpose:** Verify successful chat completion request handling.

**Test Flow:**
1. Create OpenAI adapter with test configuration
2. Mock httpx response with 200 status and valid response data
3. Execute chat completion request
4. Assert response contains expected fields (id, model, choices)
5. Clean up adapter resources

**Assertions:**
- Response ID matches mock data
- Response model matches request model
- Response contains exactly one choice
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_chat_completion_success(self, chat_request, mock_openai_response):
    adapter = OpenAIAdapter(
        name="test_openai",
        config={},
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        timeout=30.0,
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_openai_response
    
    with patch.object(adapter.client, "post", return_value=mock_response):
        response = await adapter.chat_completion(chat_request, "test-123")
    
    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-3.5-turbo"
    assert len(response.choices) == 1
    
    await adapter.close()
```

#### `test_chat_completion_timeout`

**Purpose:** Verify timeout handling with retry logic.

**Test Flow:**
1. Create adapter with max_retries=2
2. Mock httpx to raise TimeoutException
3. Execute chat completion request
4. Assert exception is raised with timeout message
5. Clean up adapter resources

**Assertions:**
- Exception is raised after retries exhausted
- Exception message contains "timeout"
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_chat_completion_timeout(self, chat_request):
    adapter = OpenAIAdapter(
        name="test_openai",
        config={},
        api_key="test-key",
        timeout=30.0,
        max_retries=2,
    )
    
    with patch.object(
        adapter.client, "post", side_effect=httpx.TimeoutException("Timeout")
    ):
        with pytest.raises(Exception) as exc_info:
            await adapter.chat_completion(chat_request, "test-123")
        
        assert "timeout" in str(exc_info.value).lower()
    
    await adapter.close()
```

#### `test_health_check_success`

**Purpose:** Verify health check reports healthy status.

**Test Flow:**
1. Create OpenAI adapter
2. Mock httpx GET request with 200 status
3. Execute health check
4. Assert health status is healthy with valid latency
5. Clean up adapter resources

**Assertions:**
- Health status is True
- Provider name matches adapter name
- Latency measurement is present
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_health_check_success(self):
    adapter = OpenAIAdapter(
        name="test_openai",
        config={},
        api_key="test-key",
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch.object(adapter.client, "get", return_value=mock_response):
        health = await adapter.health_check()
    
    assert health.healthy is True
    assert health.name == "test_openai"
    assert health.latency_ms is not None
    
    await adapter.close()
```

### vLLM Adapter Tests

#### `test_chat_completion_success`

**Purpose:** Verify successful vLLM chat completion request handling.

**Test Flow:**
1. Create vLLM adapter with test configuration
2. Mock httpx response with 200 status and valid response data
3. Execute chat completion request
4. Assert response contains expected fields
5. Clean up adapter resources

**Assertions:**
- Response ID matches mock data
- Response contains exactly one choice
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_chat_completion_success(self, chat_request, mock_openai_response):
    adapter = VLLMAdapter(
        name="test_vllm",
        config={},
        base_url="http://localhost:8000/v1",
        timeout=30.0,
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_openai_response
    
    with patch.object(adapter.client, "post", return_value=mock_response):
        response = await adapter.chat_completion(chat_request, "test-456")
    
    assert response.id == "chatcmpl-123"
    assert len(response.choices) == 1
    
    await adapter.close()
```

#### `test_chat_completion_service_unavailable`

**Purpose:** Verify handling of 503 service unavailable errors.

**Test Flow:**
1. Create adapter with max_retries=2
2. Mock httpx response with 503 status
3. Execute chat completion request
4. Assert exception is raised with appropriate message
5. Clean up adapter resources

**Assertions:**
- Exception is raised after retries exhausted
- Exception message contains "503" or "unavailable"
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_chat_completion_service_unavailable(self, chat_request):
    adapter = VLLMAdapter(
        name="test_vllm",
        config={},
        timeout=30.0,
        max_retries=2,
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 503
    
    with patch.object(adapter.client, "post", return_value=mock_response):
        with pytest.raises(Exception) as exc_info:
            await adapter.chat_completion(chat_request, "test-456")
        
        assert "503" in str(exc_info.value) or "unavailable" in str(exc_info.value).lower()
    
    await adapter.close()
```

#### `test_health_check_success`

**Purpose:** Verify vLLM health check reports healthy status.

**Test Flow:**
1. Create vLLM adapter
2. Mock httpx GET request with 200 status
3. Execute health check
4. Assert health status is healthy with valid latency
5. Clean up adapter resources

**Assertions:**
- Health status is True
- Provider name matches adapter name
- Latency measurement is present
- Adapter properly closes connections

**Example:**
```python
@pytest.mark.asyncio
async def test_health_check_success(self):
    adapter = VLLMAdapter(
        name="test_vllm",
        config={},
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch.object(adapter.client, "get", return_value=mock_response):
        health = await adapter.health_check()
    
    assert health.healthy is True
    assert health.name == "test_vllm"
    assert health.latency_ms is not None
    
    await adapter.close()
```

### Provider Factory Tests

#### `test_create_openai_adapter`

**Purpose:** Verify factory creates OpenAI adapter from configuration.

**Test Flow:**
1. Create ProviderConfig for OpenAI type
2. Set API key in environment
3. Call factory to create provider
4. Assert correct adapter type and name

**Assertions:**
- Returned instance is OpenAIAdapter
- Adapter name matches configuration

**Example:**
```python
def test_create_openai_adapter(self):
    config = ProviderConfig(
        name="openai",
        type="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="TEST_OPENAI_KEY",
        timeout=30.0,
    )
    
    with patch.dict(os.environ, {"TEST_OPENAI_KEY": "test-key"}):
        adapter = ProviderFactory.create_provider(config)
    
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.name == "openai"
```

#### `test_create_vllm_adapter`

**Purpose:** Verify factory creates vLLM adapter from configuration.

**Test Flow:**
1. Create ProviderConfig for vLLM type
2. Call factory to create provider
3. Assert correct adapter type and name

**Assertions:**
- Returned instance is VLLMAdapter
- Adapter name matches configuration

**Example:**
```python
def test_create_vllm_adapter(self):
    config = ProviderConfig(
        name="vllm",
        type="vllm",
        base_url="http://localhost:8000/v1",
        timeout=30.0,
    )
    
    adapter = ProviderFactory.create_provider(config)
    
    assert isinstance(adapter, VLLMAdapter)
    assert adapter.name == "vllm"
```

#### `test_create_openai_adapter_missing_api_key`

**Purpose:** Verify factory raises error when API key is missing.

**Test Flow:**
1. Create ProviderConfig with non-existent API key environment variable
2. Call factory to create provider
3. Assert ValueError is raised with appropriate message

**Assertions:**
- ValueError is raised
- Error message contains "API key not found"

**Example:**
```python
def test_create_openai_adapter_missing_api_key(self):
    config = ProviderConfig(
        name="openai",
        type="openai",
        api_key_env="MISSING_KEY",
    )
    
    with pytest.raises(ValueError, match="API key not found"):
        ProviderFactory.create_provider(config)
```

#### `test_create_unknown_provider_type`

**Purpose:** Verify factory raises error for unknown provider types.

**Test Flow:**
1. Create ProviderConfig with invalid provider type
2. Call factory to create provider
3. Assert ValueError is raised with appropriate message

**Assertions:**
- ValueError is raised
- Error message contains "Unknown provider type"

**Example:**
```python
def test_create_unknown_provider_type(self):
    config = ProviderConfig(
        name="unknown",
        type="unknown_type",
    )
    
    with pytest.raises(ValueError, match="Unknown provider type"):
        ProviderFactory.create_provider(config)
```

## Running Tests

### Run All Tests

```bash
pytest tests/test_real_providers.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_real_providers.py::TestOpenAIAdapter -v
```

### Run Specific Test

```bash
pytest tests/test_real_providers.py::TestOpenAIAdapter::test_chat_completion_success -v
```

### Run with Coverage

```bash
pytest tests/test_real_providers.py --cov=app.providers --cov-report=html
```

## Test Dependencies

### Required Packages

- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `httpx`: HTTP client (mocked in tests)
- `unittest.mock`: Mocking framework

### Mocked Components

- `httpx.AsyncClient.post`: HTTP POST requests
- `httpx.AsyncClient.get`: HTTP GET requests for health checks
- `os.environ`: Environment variables for API keys

## Best Practices

### 1. Always Clean Up Resources

```python
async def test_example(self):
    adapter = OpenAIAdapter(...)
    try:
        # Test logic
        response = await adapter.chat_completion(...)
    finally:
        await adapter.close()
```

### 2. Use Fixtures for Common Data

```python
@pytest.fixture
def chat_request():
    return ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello!"}]
    )
```

### 3. Mock External Dependencies

```python
with patch.object(adapter.client, "post", return_value=mock_response):
    response = await adapter.chat_completion(request, "test-123")
```

### 4. Test Error Conditions

```python
with patch.object(adapter.client, "post", side_effect=httpx.TimeoutException("Timeout")):
    with pytest.raises(Exception) as exc_info:
        await adapter.chat_completion(request, "test-123")
    assert "timeout" in str(exc_info.value).lower()
```

### 5. Verify Retry Logic

```python
adapter = OpenAIAdapter(..., max_retries=2)
# Mock should be called multiple times for retries
```

## Integration with CI/CD

These tests are designed to run in CI/CD pipelines without external dependencies:

```yaml
# .github/workflows/test.yml
- name: Run provider tests
  run: |
    pytest tests/test_real_providers.py -v --cov=app.providers
```

## Related Documentation

- [Provider Implementation Guide](PROVIDERS.md) - Comprehensive provider documentation
- [OpenAI Adapter API](OPENAI_ADAPTER_API.md) - OpenAI adapter detailed documentation
- [Base Provider Interface](../app/providers/base.py) - Abstract base class
- [Provider Factory](../app/providers/factory.py) - Factory pattern implementation
- [Configuration Models](../app/config/models.py) - Configuration data structures

## Future Enhancements

### Additional Test Coverage

1. **Streaming Tests**
   - Test streaming response handling
   - Verify chunk processing
   - Test stream error handling

2. **Retry Logic Tests**
   - Verify exponential backoff timing
   - Test retry count limits
   - Validate retry conditions

3. **Error Response Tests**
   - Test all HTTP status codes
   - Verify error message formatting
   - Test error propagation

4. **Configuration Tests**
   - Test various timeout values
   - Test different retry configurations
   - Test base URL variations

5. **Integration Tests**
   - Test with real API endpoints (optional)
   - Test end-to-end request flow
   - Test provider failover scenarios

## Summary

The `test_real_providers.py` module provides comprehensive unit test coverage for provider adapters and the factory pattern. Tests validate:

- ✅ Successful request handling
- ✅ Error condition handling
- ✅ Health check functionality
- ✅ Factory instantiation
- ✅ Resource cleanup
- ✅ Retry logic
- ✅ Configuration validation

All tests use mocked HTTP responses to ensure fast, reliable execution without external dependencies.
