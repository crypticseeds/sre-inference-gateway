# Resilience Patterns Tests Documentation

## Overview

The `tests/test_resilience.py` module provides comprehensive unit tests for the resilience patterns implementation in the SRE Inference Gateway. This test suite validates circuit breaker functionality, retry logic with exponential backoff, combined resilience patterns, registry management, and Prometheus metrics integration.

## Purpose

This test suite ensures:
- Circuit breaker patterns correctly handle failure thresholds and state transitions
- Retry logic properly classifies exceptions and implements exponential backoff
- Combined resilience patterns work together seamlessly
- Registry classes manage instances correctly per provider
- Prometheus metrics are properly recorded for observability
- Error handling and recovery scenarios work as expected

## Test Structure

### Test Classes

| Class | Description | Focus Area |
|-------|-------------|------------|
| `TestCircuitBreaker` | Circuit breaker functionality | State management, failure detection, recovery |
| `TestRetryHandler` | Retry logic and exception classification | Exponential backoff, retryable vs non-retryable errors |
| `TestResilienceHandler` | Combined resilience patterns | Integration of circuit breaker and retry logic |
| `TestRegistries` | Registry pattern implementation | Instance management, provider isolation |
| `TestConvenienceFunctions` | Utility functions | High-level resilience execution |
| `TestMetricsIntegration` | Prometheus metrics | Observability and monitoring |

## Fixtures

### Circuit Breaker Fixtures

#### `circuit_breaker_config()`

Creates a test configuration for circuit breaker testing.

**Returns:**
- `CircuitBreakerConfig`: Test configuration with:
  - `failure_threshold`: 3 failures before opening
  - `recovery_timeout`: 1.0 second recovery window
  - `expected_exception`: "Exception" type

**Usage:**
```python
def test_example(circuit_breaker_config):
    assert circuit_breaker_config.failure_threshold == 3
```

#### `circuit_breaker(circuit_breaker_config)`

Creates a circuit breaker instance with unique provider name.

**Parameters:**
- `circuit_breaker_config`: Circuit breaker configuration fixture

**Returns:**
- `CircuitBreaker`: Instance with unique provider name (UUID-based)

**Usage:**
```python
@pytest.mark.asyncio
async def test_example(circuit_breaker):
    result = await circuit_breaker.call(some_function)
```

### Retry Handler Fixtures

#### `retry_config()`

Creates a test configuration for retry handler testing.

**Returns:**
- `RetryConfig`: Test configuration with:
  - `max_attempts`: 3 retry attempts
  - `min_wait`: 0.1 second minimum wait
  - `max_wait`: 1.0 second maximum wait
  - `exponential_base`: 2.0 backoff multiplier
  - `jitter`: False (disabled for predictable tests)

#### `retry_handler(retry_config)`

Creates a retry handler instance with unique provider name.

**Parameters:**
- `retry_config`: Retry configuration fixture

**Returns:**
- `RetryHandler`: Instance with unique provider name (UUID-based)

### Resilience Handler Fixtures

#### `resilience_config()`

Creates a combined resilience configuration for testing.

**Returns:**
- `ResilienceConfig`: Configuration combining:
  - Circuit breaker with 2 failure threshold, 0.5s recovery
  - Retry with 2 max attempts, 0.1-0.5s wait range, no jitter

#### `resilience_handler(resilience_config)`

Creates a resilience handler instance combining circuit breaker and retry.

**Parameters:**
- `resilience_config`: Combined resilience configuration

**Returns:**
- `ResilienceHandler`: Instance managing both patterns

## Test Cases

### TestCircuitBreaker

#### State Management Tests

##### `test_circuit_breaker_closed_state(circuit_breaker)`

**Purpose:** Verify circuit breaker starts in closed state.

**Test Flow:**
1. Create circuit breaker instance
2. Check initial state properties
3. Assert closed state and negated open/half-open states

**Assertions:**
- `circuit_breaker.is_closed` is True
- `circuit_breaker.is_open` is False
- `circuit_breaker.is_half_open` is False

##### `test_successful_call(circuit_breaker)`

**Purpose:** Verify successful function execution through circuit breaker.

**Test Flow:**
1. Define async success function returning "success"
2. Execute function through circuit breaker
3. Verify result and state remain healthy

**Assertions:**
- Function result equals "success"
- Circuit breaker remains closed
- Failure count resets to 0

##### `test_circuit_breaker_opens_after_failures(circuit_breaker)`

**Purpose:** Verify circuit breaker opens after threshold failures.

**Test Flow:**
1. Define async function that always raises Exception
2. Execute function 3 times (matching failure threshold)
3. Verify circuit opens and subsequent calls fail fast

**Assertions:**
- Circuit breaker transitions to open state
- Failure count reaches threshold (3)
- Next call raises `CircuitBreakerOpenException`

#### Recovery Tests

##### `test_circuit_breaker_half_open_recovery(circuit_breaker)`

**Purpose:** Verify circuit breaker recovery through half-open state.

**Test Flow:**
1. Open circuit by triggering threshold failures
2. Wait for recovery timeout (1.1 seconds)
3. Execute successful function
4. Verify circuit closes and resets

**Assertions:**
- Circuit opens after failures
- After timeout, successful call closes circuit
- Failure count resets to 0

##### `test_circuit_breaker_half_open_failure(circuit_breaker)`

**Purpose:** Verify circuit breaker re-opens on half-open failure.

**Test Flow:**
1. Open circuit by triggering threshold failures
2. Wait for recovery timeout
3. Execute failing function in half-open state
4. Verify circuit re-opens

**Assertions:**
- Circuit opens initially
- After timeout, failure re-opens circuit

#### State Information Test

##### `test_circuit_breaker_state_info(circuit_breaker)`

**Purpose:** Verify circuit breaker state information accuracy.

**Test Flow:**
1. Get state information dictionary
2. Verify all state properties match expected values

**Assertions:**
- Provider name matches circuit breaker's provider name
- State is "CLOSED"
- Failure count is 0
- Failure threshold is 3
- Recovery timeout is 1.0

### TestRetryHandler

#### Basic Retry Tests

##### `test_successful_call_no_retry(retry_handler)`

**Purpose:** Verify successful calls don't trigger retries.

**Test Flow:**
1. Define async success function
2. Execute through retry handler
3. Verify immediate success without retries

**Assertions:**
- Function result equals "success"
- No retry attempts made

##### `test_retry_on_retryable_exception(retry_handler)`

**Purpose:** Verify retry logic for retryable exceptions.

**Test Flow:**
1. Define function that fails twice, then succeeds
2. Execute through retry handler
3. Verify retries occur and eventual success

**Assertions:**
- Function eventually succeeds
- Call count reaches 3 (initial + 2 retries)

##### `test_no_retry_on_non_retryable_exception(retry_handler)`

**Purpose:** Verify non-retryable exceptions don't trigger retries.

**Test Flow:**
1. Define function that raises ValueError (non-retryable)
2. Execute through retry handler
3. Verify immediate failure without retries

**Assertions:**
- `NonRetryableException` is raised
- Call count is 1 (no retries)

##### `test_retry_exhaustion(retry_handler)`

**Purpose:** Verify retry exhaustion after max attempts.

**Test Flow:**
1. Define function that always raises ConnectionError
2. Execute through retry handler
3. Verify retries exhaust and original exception propagates

**Assertions:**
- Original `ConnectionError` is raised
- Call count equals max_attempts (3)

#### Exception Classification Tests

##### `test_classify_http_exception_4xx()`

**Purpose:** Verify HTTP 4xx exceptions are not retryable.

**Test Flow:**
1. Create HTTPException instances with 400 and 404 status codes
2. Test classification function
3. Verify both return False (not retryable)

**Assertions:**
- 400 Bad Request is not retryable
- 404 Not Found is not retryable

##### `test_classify_http_exception_5xx()`

**Purpose:** Verify HTTP 5xx exceptions are retryable.

**Test Flow:**
1. Create HTTPException instances with 500 and 503 status codes
2. Test classification function
3. Verify both return True (retryable)

**Assertions:**
- 500 Internal Server Error is retryable
- 503 Service Unavailable is retryable

##### `test_classify_network_exceptions()`

**Purpose:** Verify network exceptions are retryable.

**Test Flow:**
1. Create network-related exception instances
2. Test classification function
3. Verify all return True (retryable)

**Assertions:**
- `ConnectionError` is retryable
- `TimeoutError` is retryable
- `asyncio.TimeoutError` is retryable

##### `test_classify_non_retryable_exceptions()`

**Purpose:** Verify non-retryable exceptions.

**Test Flow:**
1. Create various non-retryable exception instances
2. Test classification function
3. Verify all return False (not retryable)

**Assertions:**
- `ValueError` is not retryable
- `TypeError` is not retryable
- `NonRetryableException` is not retryable

### TestResilienceHandler

#### Combined Pattern Tests

##### `test_successful_execution(resilience_handler)`

**Purpose:** Verify successful execution with combined resilience patterns.

**Test Flow:**
1. Define async success function
2. Execute through resilience handler
3. Verify successful execution without pattern activation

**Assertions:**
- Function result equals "success"
- No resilience patterns triggered

##### `test_retry_then_success(resilience_handler)`

**Purpose:** Verify retry logic with eventual success.

**Test Flow:**
1. Define function that fails once, then succeeds
2. Execute through resilience handler
3. Verify retry occurs and eventual success

**Assertions:**
- Function eventually succeeds
- Call count is 2 (initial failure + retry success)

##### `test_circuit_breaker_opens_after_failures(resilience_handler)`

**Purpose:** Verify circuit breaker opens after repeated failures.

**Test Flow:**
1. Define function that always raises ConnectionError
2. Execute multiple times to trigger circuit breaker
3. Verify progression from retry exhaustion to circuit opening

**Assertions:**
- First call: 502 (retry exhaustion)
- Second call: 502 (retry exhaustion, opens circuit)
- Third call: 503 (circuit breaker open, fail fast)

#### Error Handling Tests

##### `test_non_retryable_error_handling(resilience_handler)`

**Purpose:** Verify non-retryable error handling.

**Test Flow:**
1. Define function that raises ValueError
2. Execute through resilience handler
3. Verify immediate failure with 500 status

**Assertions:**
- HTTPException with status code 500 is raised

##### `test_http_4xx_error_handling(resilience_handler)`

**Purpose:** Verify HTTP 4xx error pass-through.

**Test Flow:**
1. Define function that raises HTTPException(400)
2. Execute through resilience handler
3. Verify error passes through unchanged

**Assertions:**
- HTTPException with status code 400 is raised

### TestRegistries

#### Registry Pattern Tests

##### `test_circuit_breaker_registry()`

**Purpose:** Verify circuit breaker registry instance management.

**Test Flow:**
1. Get circuit breaker for same provider twice
2. Get circuit breaker for different provider
3. Verify instance reuse and isolation

**Assertions:**
- Same provider returns same instance
- Different providers get different instances

##### `test_retry_registry()`

**Purpose:** Verify retry registry instance management.

**Test Flow:**
1. Get retry handler for same provider twice
2. Get retry handler for different provider
3. Verify instance reuse and isolation

**Assertions:**
- Same provider returns same instance
- Different providers get different instances

##### `test_resilience_registry()`

**Purpose:** Verify resilience registry instance management.

**Test Flow:**
1. Get resilience handler for same provider twice
2. Get resilience handler for different provider
3. Verify instance reuse and isolation

**Assertions:**
- Same provider returns same instance
- Different providers get different instances

### TestConvenienceFunctions

#### Utility Function Tests

##### `test_execute_with_resilience_function()`

**Purpose:** Verify convenience function for resilience execution.

**Test Flow:**
1. Define async success function
2. Execute using convenience function
3. Verify successful execution

**Assertions:**
- Function result equals "success"

##### `test_execute_with_resilience_failure()`

**Purpose:** Verify convenience function failure handling.

**Test Flow:**
1. Define function that raises ConnectionError
2. Configure single retry attempt
3. Execute and verify failure handling

**Assertions:**
- HTTPException with status code 502 is raised

### TestMetricsIntegration

#### Prometheus Metrics Tests

##### `test_circuit_breaker_metrics(circuit_breaker)`

**Purpose:** Verify circuit breaker metrics recording.

**Test Flow:**
1. Mock Prometheus metrics
2. Execute function through circuit breaker
3. Verify metrics are called

**Assertions:**
- State gauge labels method is called
- Calls counter labels method is called

##### `test_retry_metrics(retry_handler)`

**Purpose:** Verify retry metrics recording.

**Test Flow:**
1. Mock Prometheus metrics
2. Execute function through retry handler
3. Verify metrics are called

**Assertions:**
- Attempts counter labels method is called
- Duration histogram labels method is called

##### `test_resilience_metrics(resilience_handler)`

**Purpose:** Verify resilience metrics recording.

**Test Flow:**
1. Mock Prometheus metrics
2. Execute function through resilience handler
3. Verify metrics are called

**Assertions:**
- Calls counter labels method is called
- Duration histogram labels method is called

## Running Tests

### Run All Resilience Tests

```bash
doppler run -- uv run pytest tests/test_resilience.py -v
```

### Run Specific Test Class

```bash
doppler run -- uv run pytest tests/test_resilience.py::TestCircuitBreaker -v
doppler run -- uv run pytest tests/test_resilience.py::TestRetryHandler -v
doppler run -- uv run pytest tests/test_resilience.py::TestResilienceHandler -v
```

### Run Specific Test

```bash
doppler run -- uv run pytest tests/test_resilience.py::TestCircuitBreaker::test_circuit_breaker_opens_after_failures -v
```

### Run with Coverage

```bash
doppler run -- uv run pytest tests/test_resilience.py --cov=app.router --cov-report=html
```

## Test Dependencies

### Required Packages

- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `unittest.mock`: Mocking framework for metrics
- `fastapi`: HTTPException class
- `asyncio`: Async utilities

### Mocked Components

- `app.router.circuit_breaker.circuit_breaker_state_gauge`: Prometheus gauge
- `app.router.circuit_breaker.circuit_breaker_calls_total`: Prometheus counter
- `app.router.retry.retry_attempts_total`: Prometheus counter
- `app.router.retry.retry_duration_seconds`: Prometheus histogram
- `app.router.resilience.resilience_calls_total`: Prometheus counter
- `app.router.resilience.resilience_duration_seconds`: Prometheus histogram

## Key Testing Patterns

### 1. Async Test Decoration

```python
@pytest.mark.asyncio
async def test_async_functionality():
    result = await some_async_function()
    assert result == expected_value
```

### 2. Exception Testing

```python
with pytest.raises(SpecificException) as exc_info:
    await function_that_should_fail()
assert exc_info.value.status_code == expected_code
```

### 3. State Verification

```python
# Before action
assert circuit_breaker.is_closed

# Perform action
await circuit_breaker.call(failing_function)

# After action
assert circuit_breaker.is_open
```

### 4. Metrics Mocking

```python
with patch("module.metric_name") as mock_metric:
    await function_that_records_metrics()
    mock_metric.labels.assert_called()
```

### 5. Unique Provider Names

```python
import uuid
provider_name = f"test_provider_{uuid.uuid4().hex[:8]}"
```

## Best Practices

### 1. Use Fixtures for Configuration

```python
@pytest.fixture
def config():
    return ConfigClass(
        param1=test_value1,
        param2=test_value2
    )
```

### 2. Test State Transitions

```python
# Test initial state
assert handler.initial_state

# Trigger transition
await handler.trigger_transition()

# Test final state
assert handler.final_state
```

### 3. Verify Call Counts

```python
call_count = 0

async def counting_function():
    nonlocal call_count
    call_count += 1
    # Function logic

await handler.execute(counting_function)
assert call_count == expected_count
```

### 4. Test Error Propagation

```python
with pytest.raises(ExpectedException) as exc_info:
    await handler.execute(failing_function)
assert "expected message" in str(exc_info.value)
```

### 5. Mock External Dependencies

```python
with patch("external.dependency") as mock_dep:
    mock_dep.return_value = expected_value
    result = await function_using_dependency()
    assert result == expected_result
```

## Integration with CI/CD

These tests are designed for CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run resilience tests
  run: |
    doppler run -- uv run pytest tests/test_resilience.py -v --cov=app.router
```

## Related Documentation

- [Resilience Configuration Guide](RESILIENCE_CONFIG.md) - Configuration options
- [Circuit Breaker Implementation](../app/router/circuit_breaker.py) - Circuit breaker code
- [Retry Handler Implementation](../app/router/retry.py) - Retry logic code
- [Resilience Handler Implementation](../app/router/resilience.py) - Combined patterns
- [Configuration Models](../app/config/models.py) - Configuration classes

## Future Enhancements

### Additional Test Coverage

1. **Timing Tests**
   - Verify exponential backoff timing
   - Test recovery timeout accuracy
   - Validate jitter randomization

2. **Concurrency Tests**
   - Test multiple concurrent requests
   - Verify thread safety
   - Test registry isolation

3. **Configuration Tests**
   - Test various configuration combinations
   - Verify configuration validation
   - Test edge case configurations

4. **Integration Tests**
   - Test with real provider adapters
   - Test end-to-end resilience flows
   - Test metrics collection accuracy

5. **Performance Tests**
   - Measure resilience pattern overhead
   - Test high-throughput scenarios
   - Verify memory usage patterns

## Summary

The `test_resilience.py` module provides comprehensive test coverage for resilience patterns:

- ✅ Circuit breaker state management and transitions
- ✅ Retry logic with exponential backoff
- ✅ Exception classification and handling
- ✅ Combined resilience pattern integration
- ✅ Registry pattern implementation
- ✅ Prometheus metrics integration
- ✅ Error handling and recovery scenarios
- ✅ Async operation support

All tests use mocked dependencies and unique provider names to ensure isolation and reliability in CI/CD environments.