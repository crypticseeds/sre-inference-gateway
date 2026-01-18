# OpenAI Adapter Usage Examples

## Overview

This document provides comprehensive usage examples for the `OpenAIAdapter` class, covering common integration patterns, error handling, and best practices for production use.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration Patterns](#configuration-patterns)
- [Error Handling](#error-handling)
- [Integration Patterns](#integration-patterns)
- [Testing Examples](#testing-examples)
- [Production Patterns](#production-patterns)
- [Performance Optimization](#performance-optimization)

## Basic Usage

### Simple Chat Completion

```python
import asyncio
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

async def basic_example():
    # Initialize adapter
    adapter = OpenAIAdapter(
        name="openai-gpt4",
        config={"model": "gpt-4"},
        api_key="sk-your-api-key-here"
    )
    
    try:
        # Create request
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        # Execute request
        response = await adapter.chat_completion(request, "req-001")
        
        # Extract response
        content = response.choices[0]["message"]["content"]
        tokens_used = response.usage["total_tokens"]
        
        print(f"Response: {content}")
        print(f"Tokens used: {tokens_used}")
        
    finally:
        # Always clean up
        await adapter.close()

# Run example
asyncio.run(basic_example())
```

### Health Check Example

```python
async def health_check_example():
    adapter = OpenAIAdapter(
        name="openai",
        config={},
        api_key="sk-your-api-key-here"
    )
    
    try:
        health = await adapter.health_check()
        
        if health.healthy:
            print(f"✓ OpenAI is healthy")
            print(f"  Latency: {health.latency_ms:.2f}ms")
        else:
            print(f"✗ OpenAI is unhealthy")
            print(f"  Error: {health.error}")
            print(f"  Latency: {health.latency_ms:.2f}ms")
            
    finally:
        await adapter.close()
```

## Configuration Patterns

### Environment-Based Configuration

```python
import os
from app.providers.openai import OpenAIAdapter

def create_openai_adapter() -> OpenAIAdapter:
    """Create OpenAI adapter from environment variables."""
    return OpenAIAdapter(
        name=os.getenv("OPENAI_PROVIDER_NAME", "openai"),
        config={
            "model": os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo"),
            "priority": int(os.getenv("OPENAI_PRIORITY", "1"))
        },
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        timeout=float(os.getenv("OPENAI_TIMEOUT", "30.0")),
        max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3"))
    )

# Usage
adapter = create_openai_adapter()
```

### Configuration Model Integration

```python
from app.config.models import ProviderConfig
from app.providers.factory import ProviderFactory

async def config_model_example():
    # Define configuration
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
    
    # Create adapter via factory
    adapter = ProviderFactory.create_provider(config)
    
    try:
        # Use adapter
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        response = await adapter.chat_completion(request, "req-002")
        print(f"Response: {response.choices[0]['message']['content']}")
        
    finally:
        await adapter.close()
```

### Multiple Provider Configuration

```python
async def multiple_providers_example():
    # Create multiple adapters with different configurations
    adapters = {
        "gpt-4": OpenAIAdapter(
            name="openai-gpt4",
            config={"model": "gpt-4", "priority": 1},
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0,  # Longer timeout for GPT-4
            max_retries=5
        ),
        "gpt-3.5": OpenAIAdapter(
            name="openai-gpt35",
            config={"model": "gpt-3.5-turbo", "priority": 2},
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,
            max_retries=3
        )
    }
    
    try:
        # Use different adapters for different models
        gpt4_request = ChatCompletionRequest(
            model="gpt-4",
            messages=[{"role": "user", "content": "Complex reasoning task"}]
        )
        
        gpt35_request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Simple question"}]
        )
        
        # Execute requests
        gpt4_response = await adapters["gpt-4"].chat_completion(gpt4_request, "req-003")
        gpt35_response = await adapters["gpt-3.5"].chat_completion(gpt35_request, "req-004")
        
        print(f"GPT-4: {gpt4_response.choices[0]['message']['content']}")
        print(f"GPT-3.5: {gpt35_response.choices[0]['message']['content']}")
        
    finally:
        # Clean up all adapters
        for adapter in adapters.values():
            await adapter.close()
```

## Error Handling

### Comprehensive Error Handling

```python
import asyncio
from fastapi import HTTPException

async def error_handling_example():
    adapter = OpenAIAdapter(
        name="openai",
        config={},
        api_key="sk-your-api-key-here",
        max_retries=3
    )
    
    try:
        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        response = await adapter.chat_completion(request, "req-005")
        return response
        
    except HTTPException as e:
        if e.status_code == 400:
            print(f"Bad Request: {e.detail}")
            # Handle invalid request parameters
            return None
            
        elif e.status_code == 429:
            print(f"Rate Limited: {e.detail}")
            # Implement additional backoff
            await asyncio.sleep(60)
            return await adapter.chat_completion(request, "req-005-retry")
            
        elif e.status_code == 500:
            print(f"Authentication Error: {e.detail}")
            # Check API key configuration
            return None
            
        elif e.status_code == 502:
            print(f"Server Error: {e.detail}")
            # Try fallback provider or retry later
            return None
            
        elif e.status_code == 504:
            print(f"Timeout: {e.detail}")
            # Consider reducing request complexity
            return None
            
        else:
            print(f"Unexpected Error: {e.status_code} - {e.detail}")
            raise
            
    except Exception as e:
        print(f"Unexpected Exception: {e}")
        raise
        
    finally:
        await adapter.close()
```

### Retry with Custom Backoff

```python
async def custom_retry_example():
    adapter = OpenAIAdapter(
        name="openai",
        config={},
        api_key="sk-your-api-key-here",
        max_retries=1  # Use custom retry logic
    )
    
    async def retry_with_custom_backoff(request, request_id, max_attempts=5):
        for attempt in range(max_attempts):
            try:
                return await adapter.chat_completion(request, request_id)
                
            except HTTPException as e:
                if e.status_code in [429, 502, 504] and attempt < max_attempts - 1:
                    # Custom exponential backoff with jitter
                    base_delay = 2 ** attempt
                    jitter = random.uniform(0.5, 1.5)
                    delay = base_delay * jitter
                    
                    print(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise
        
        raise HTTPException(500, "All retry attempts failed")
    
    try:
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        response = await retry_with_custom_backoff(request, "req-006")
        print(f"Success: {response.choices[0]['message']['content']}")
        
    finally:
        await adapter.close()
```

## Integration Patterns

### FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

app = FastAPI()

# Dependency to provide OpenAI adapter
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

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    adapter: OpenAIAdapter = Depends(get_openai_adapter)
):
    """OpenAI-compatible chat completions endpoint."""
    try:
        response = await adapter.chat_completion(request, "api-request")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")

@app.get("/health/openai")
async def openai_health(
    adapter: OpenAIAdapter = Depends(get_openai_adapter)
):
    """OpenAI provider health check."""
    health = await adapter.health_check()
    if not health.healthy:
        raise HTTPException(503, health.error)
    return health
```

### Provider Registry Integration

```python
from app.providers.registry import ProviderRegistry

class OpenAIProviderManager:
    def __init__(self):
        self.registry = ProviderRegistry()
        self.adapters = {}
    
    async def initialize_providers(self):
        """Initialize multiple OpenAI adapters."""
        configs = [
            {
                "name": "openai-gpt4",
                "model": "gpt-4",
                "timeout": 60.0,
                "max_retries": 5
            },
            {
                "name": "openai-gpt35",
                "model": "gpt-3.5-turbo",
                "timeout": 30.0,
                "max_retries": 3
            }
        ]
        
        for config in configs:
            adapter = OpenAIAdapter(
                name=config["name"],
                config={"model": config["model"]},
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=config["timeout"],
                max_retries=config["max_retries"]
            )
            
            self.adapters[config["name"]] = adapter
            self.registry.register_provider(config["name"], adapter)
    
    async def get_provider(self, name: str) -> OpenAIAdapter:
        """Get provider by name."""
        return self.registry.get_provider(name)
    
    async def cleanup(self):
        """Clean up all adapters."""
        for adapter in self.adapters.values():
            await adapter.close()

# Usage
manager = OpenAIProviderManager()
await manager.initialize_providers()

try:
    gpt4_adapter = await manager.get_provider("openai-gpt4")
    response = await gpt4_adapter.chat_completion(request, "req-007")
finally:
    await manager.cleanup()
```

### Circuit Breaker Integration

```python
import time
from typing import Dict, Any

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class ResilientOpenAIAdapter:
    def __init__(self, adapter: OpenAIAdapter):
        self.adapter = adapter
        self.circuit_breaker = CircuitBreaker()
    
    async def chat_completion(self, request: ChatCompletionRequest, request_id: str):
        if self.circuit_breaker.is_open():
            raise HTTPException(503, "OpenAI service circuit breaker is open")
        
        try:
            response = await self.adapter.chat_completion(request, request_id)
            self.circuit_breaker.record_success()
            return response
            
        except HTTPException as e:
            if e.status_code >= 500:
                self.circuit_breaker.record_failure()
            raise
    
    async def close(self):
        await self.adapter.close()

# Usage
base_adapter = OpenAIAdapter(
    name="openai",
    config={},
    api_key=os.getenv("OPENAI_API_KEY")
)

resilient_adapter = ResilientOpenAIAdapter(base_adapter)

try:
    response = await resilient_adapter.chat_completion(request, "req-008")
finally:
    await resilient_adapter.close()
```

## Testing Examples

### Unit Test with Mocking

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

@pytest.fixture
async def openai_adapter():
    adapter = OpenAIAdapter(
        name="test-openai",
        config={},
        api_key="test-key"
    )
    yield adapter
    await adapter.close()

@pytest.mark.asyncio
async def test_chat_completion_success(openai_adapter):
    """Test successful chat completion."""
    # Mock response data
    mock_response_data = {
        "id": "chatcmpl-test123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gpt-3.5-turbo",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello!"},
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15
        }
    }
    
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data
    
    # Patch the HTTP client
    with patch.object(openai_adapter.client, "post", new=AsyncMock(return_value=mock_response)):
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        response = await openai_adapter.chat_completion(request, "test-123")
        
        assert response.id == "chatcmpl-test123"
        assert response.model == "gpt-3.5-turbo"
        assert len(response.choices) == 1
        assert response.choices[0]["message"]["content"] == "Hello!"
        assert response.usage["total_tokens"] == 15

@pytest.mark.asyncio
async def test_chat_completion_rate_limit(openai_adapter):
    """Test rate limit handling."""
    from fastapi import HTTPException
    
    # Mock rate limit response
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    
    with patch.object(openai_adapter.client, "post", new=AsyncMock()) as mock_post:
        mock_post.side_effect = [
            # First attempt: rate limited
            httpx.HTTPStatusError("Rate limited", request=None, response=mock_response),
            # Second attempt: rate limited
            httpx.HTTPStatusError("Rate limited", request=None, response=mock_response),
            # Third attempt: rate limited
            httpx.HTTPStatusError("Rate limited", request=None, response=mock_response)
        ]
        
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await openai_adapter.chat_completion(request, "test-rate-limit")
        
        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()
```

### Integration Test

```python
import os
import pytest
from app.providers.openai import OpenAIAdapter
from app.providers.base import ChatCompletionRequest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_integration():
    """Integration test with real OpenAI API (requires API key)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")
    
    adapter = OpenAIAdapter(
        name="integration-test",
        config={},
        api_key=api_key,
        timeout=30.0,
        max_retries=2
    )
    
    try:
        # Test chat completion
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'integration test successful'"}],
            max_tokens=10
        )
        
        response = await adapter.chat_completion(request, "integration-test")
        
        assert response.id is not None
        assert response.model == "gpt-3.5-turbo"
        assert len(response.choices) > 0
        assert response.usage["total_tokens"] > 0
        
        # Test health check
        health = await adapter.health_check()
        assert health.healthy is True
        assert health.latency_ms > 0
        
    finally:
        await adapter.close()
```

## Production Patterns

### Connection Pool Management

```python
import asyncio
from contextlib import asynccontextmanager

class OpenAIAdapterPool:
    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self.adapters = []
        self.available = asyncio.Queue()
        self.lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the adapter pool."""
        for i in range(self.pool_size):
            adapter = OpenAIAdapter(
                name=f"openai-pool-{i}",
                config={},
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=30.0,
                max_retries=3
            )
            self.adapters.append(adapter)
            await self.available.put(adapter)
    
    @asynccontextmanager
    async def get_adapter(self):
        """Get an adapter from the pool."""
        adapter = await self.available.get()
        try:
            yield adapter
        finally:
            await self.available.put(adapter)
    
    async def cleanup(self):
        """Clean up all adapters in the pool."""
        for adapter in self.adapters:
            await adapter.close()

# Usage
pool = OpenAIAdapterPool(pool_size=10)
await pool.initialize()

try:
    async with pool.get_adapter() as adapter:
        response = await adapter.chat_completion(request, "pool-req-001")
finally:
    await pool.cleanup()
```

### Monitoring and Observability

```python
import time
import logging
from prometheus_client import Counter, Histogram, Gauge

# Metrics
openai_requests_total = Counter(
    "openai_requests_total",
    "Total OpenAI requests",
    ["status", "model"]
)

openai_request_duration = Histogram(
    "openai_request_duration_seconds",
    "OpenAI request duration",
    ["model"]
)

openai_active_connections = Gauge(
    "openai_active_connections",
    "Active OpenAI connections"
)

class MonitoredOpenAIAdapter:
    def __init__(self, adapter: OpenAIAdapter):
        self.adapter = adapter
        self.logger = logging.getLogger(__name__)
    
    async def chat_completion(self, request: ChatCompletionRequest, request_id: str):
        start_time = time.time()
        openai_active_connections.inc()
        
        try:
            self.logger.info(
                "OpenAI request started",
                extra={
                    "request_id": request_id,
                    "model": request.model,
                    "provider": self.adapter.name
                }
            )
            
            response = await self.adapter.chat_completion(request, request_id)
            
            # Record success metrics
            duration = time.time() - start_time
            openai_requests_total.labels(status="success", model=request.model).inc()
            openai_request_duration.labels(model=request.model).observe(duration)
            
            self.logger.info(
                "OpenAI request completed",
                extra={
                    "request_id": request_id,
                    "model": request.model,
                    "tokens": response.usage["total_tokens"],
                    "duration": duration
                }
            )
            
            return response
            
        except HTTPException as e:
            # Record error metrics
            duration = time.time() - start_time
            status = "client_error" if 400 <= e.status_code < 500 else "server_error"
            openai_requests_total.labels(status=status, model=request.model).inc()
            openai_request_duration.labels(model=request.model).observe(duration)
            
            self.logger.error(
                "OpenAI request failed",
                extra={
                    "request_id": request_id,
                    "model": request.model,
                    "status_code": e.status_code,
                    "error": e.detail,
                    "duration": duration
                }
            )
            
            raise
            
        finally:
            openai_active_connections.dec()
    
    async def close(self):
        await self.adapter.close()

# Usage
base_adapter = OpenAIAdapter(
    name="openai",
    config={},
    api_key=os.getenv("OPENAI_API_KEY")
)

monitored_adapter = MonitoredOpenAIAdapter(base_adapter)

try:
    response = await monitored_adapter.chat_completion(request, "monitored-req-001")
finally:
    await monitored_adapter.close()
```

### Cost Tracking

```python
class CostTrackingOpenAIAdapter:
    # OpenAI pricing (as of 2024)
    PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03}
    }
    
    def __init__(self, adapter: OpenAIAdapter):
        self.adapter = adapter
        self.total_cost = 0.0
        self.request_costs = {}
    
    def calculate_cost(self, model: str, usage: dict) -> float:
        """Calculate request cost based on token usage."""
        if model not in self.PRICING:
            return 0.0
        
        pricing = self.PRICING[model]
        prompt_cost = (usage["prompt_tokens"] / 1000) * pricing["prompt"]
        completion_cost = (usage["completion_tokens"] / 1000) * pricing["completion"]
        
        return prompt_cost + completion_cost
    
    async def chat_completion(self, request: ChatCompletionRequest, request_id: str):
        response = await self.adapter.chat_completion(request, request_id)
        
        # Calculate and track cost
        cost = self.calculate_cost(request.model, response.usage)
        self.total_cost += cost
        self.request_costs[request_id] = {
            "model": request.model,
            "tokens": response.usage,
            "cost": cost,
            "timestamp": time.time()
        }
        
        print(f"Request {request_id}: ${cost:.4f} (Total: ${self.total_cost:.4f})")
        
        return response
    
    def get_cost_summary(self) -> dict:
        """Get cost summary by model."""
        summary = {}
        for req_id, data in self.request_costs.items():
            model = data["model"]
            if model not in summary:
                summary[model] = {"requests": 0, "cost": 0.0, "tokens": 0}
            
            summary[model]["requests"] += 1
            summary[model]["cost"] += data["cost"]
            summary[model]["tokens"] += data["tokens"]["total_tokens"]
        
        return summary
    
    async def close(self):
        await self.adapter.close()

# Usage
base_adapter = OpenAIAdapter(
    name="openai",
    config={},
    api_key=os.getenv("OPENAI_API_KEY")
)

cost_adapter = CostTrackingOpenAIAdapter(base_adapter)

try:
    # Make several requests
    for i in range(5):
        request = ChatCompletionRequest(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Request {i}"}]
        )
        await cost_adapter.chat_completion(request, f"cost-req-{i}")
    
    # Print cost summary
    summary = cost_adapter.get_cost_summary()
    print(f"Cost Summary: {summary}")
    
finally:
    await cost_adapter.close()
```

## Performance Optimization

### Request Batching

```python
import asyncio
from typing import List

class BatchingOpenAIAdapter:
    def __init__(self, adapter: OpenAIAdapter, batch_size: int = 5, batch_timeout: float = 1.0):
        self.adapter = adapter
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.batch_lock = asyncio.Lock()
    
    async def chat_completion(self, request: ChatCompletionRequest, request_id: str):
        # For demonstration - in practice, you'd need to modify the request structure
        # to support batching at the OpenAI API level
        async with self.batch_lock:
            future = asyncio.Future()
            self.pending_requests.append((request, request_id, future))
            
            if len(self.pending_requests) >= self.batch_size:
                await self._process_batch()
            else:
                # Schedule batch processing after timeout
                asyncio.create_task(self._process_batch_after_timeout())
            
            return await future
    
    async def _process_batch_after_timeout(self):
        await asyncio.sleep(self.batch_timeout)
        async with self.batch_lock:
            if self.pending_requests:
                await self._process_batch()
    
    async def _process_batch(self):
        if not self.pending_requests:
            return
        
        batch = self.pending_requests.copy()
        self.pending_requests.clear()
        
        # Process requests concurrently
        tasks = []
        for request, request_id, future in batch:
            task = asyncio.create_task(
                self._execute_single_request(request, request_id, future)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_single_request(self, request, request_id, future):
        try:
            response = await self.adapter.chat_completion(request, request_id)
            future.set_result(response)
        except Exception as e:
            future.set_exception(e)
    
    async def close(self):
        await self.adapter.close()
```

### Connection Reuse

```python
class OptimizedOpenAIAdapter:
    def __init__(self, api_key: str, max_connections: int = 100):
        self.api_key = api_key
        
        # Optimized HTTP client configuration
        limits = httpx.Limits(
            max_keepalive_connections=max_connections,
            max_connections=max_connections,
            keepalive_expiry=30.0
        )
        
        self.client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Connection": "keep-alive"
            },
            http2=True  # Enable HTTP/2 for better performance
        )
    
    async def chat_completion(self, request: ChatCompletionRequest, request_id: str):
        # Implementation similar to OpenAIAdapter but with optimized client
        payload = request.model_dump(exclude_none=True)
        
        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        return ChatCompletionResponse(**data)
    
    async def close(self):
        await self.client.aclose()
```

## Related Documentation

- [OpenAI Adapter API Reference](OPENAI_ADAPTER_API.md) - Complete API documentation
- [OpenAI Adapter Signatures](OPENAI_ADAPTER_SIGNATURES.md) - Quick signature reference
- [Provider Implementation Guide](PROVIDERS.md) - Provider architecture
- [Configuration Models](CONFIG_MODELS_API.md) - Configuration system
- [Testing Documentation](TEST_REAL_PROVIDERS.md) - Testing patterns and examples

## Best Practices Summary

1. **Always clean up resources** with `await adapter.close()`
2. **Handle errors appropriately** based on status codes
3. **Use configuration models** for structured configuration
4. **Implement monitoring** for production deployments
5. **Consider cost tracking** for budget management
6. **Use connection pooling** for high-throughput scenarios
7. **Implement circuit breakers** for resilience
8. **Test with mocks** for unit tests and real API for integration tests