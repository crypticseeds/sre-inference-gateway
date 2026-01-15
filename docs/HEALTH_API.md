# Health Check API Documentation

## Overview

The Health Check API provides comprehensive monitoring endpoints for the SRE Inference Gateway. It enables health monitoring, readiness checks, and provider status tracking with automatic caching and periodic updates.

## Module: `app.api.health`

### Purpose

Provides FastAPI endpoints for:
- Basic service health checks
- Detailed health status with provider monitoring
- Kubernetes readiness probes
- Individual provider health tracking
- Automatic health cache management

### Key Features

- **Automatic Health Caching**: Periodic provider health checks with configurable intervals
- **Provider Filtering**: Only reports health for enabled providers
- **Async Health Checks**: Non-blocking concurrent provider health monitoring
- **Kubernetes Integration**: Readiness endpoint for K8s liveness/readiness probes
- **Detailed Status**: Comprehensive health information including response times and errors

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Health Check Module                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Global Health Cache                       │  │
│  │  - _provider_health_cache: Dict[str, Dict]       │  │
│  │  - _last_health_check: float                     │  │
│  │  - _health_check_lock: asyncio.Lock              │  │
│  └──────────────────────────────────────────────────┘  │
│                          ▲                              │
│                          │                              │
│  ┌──────────────────────┴───────────────────────────┐  │
│  │    update_provider_health_cache()                 │  │
│  │    - Periodic updates (configurable interval)    │  │
│  │    - Concurrent health checks                    │  │
│  │    - Thread-safe with async lock                 │  │
│  └──────────────────────────────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Health Check Endpoints                    │  │
│  │  - GET /health                                    │  │
│  │  - GET /health/detailed                           │  │
│  │  - GET /ready                                     │  │
│  │  - GET /health/providers                          │  │
│  │  - GET /health/providers/{provider_name}          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Global State

### Health Cache

```python
_provider_health_cache: Dict[str, Dict] = {}
```

Stores health status for all providers. Each entry contains:
- `name`: Provider identifier
- `status`: "healthy", "unhealthy", or "unknown"
- `response_time`: Health check latency in seconds
- `error`: Error message if unhealthy
- `last_check`: Unix timestamp of last check

### Last Check Timestamp

```python
_last_health_check: float = 0
```

Unix timestamp of the last health cache update. Used to enforce check intervals.

### Health Check Lock

```python
_health_check_lock = asyncio.Lock()
```

Async lock to prevent concurrent health cache updates.

## Functions

### `check_provider_health(provider_name, health_url, timeout=5.0)`

Check health of a single provider by making an HTTP GET request to its health endpoint.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `provider_name` | `str` | Required | Provider identifier for logging and cache |
| `health_url` | `Optional[str]` | Required | Health check URL (None = assume healthy) |
| `timeout` | `float` | `5.0` | Request timeout in seconds |

#### Returns

`Dict` containing:
```python
{
    "name": str,              # Provider name
    "status": str,            # "healthy", "unhealthy", or "unknown"
    "response_time": float,   # Response time in seconds (None if failed)
    "error": Optional[str],   # Error message if unhealthy
    "last_check": float       # Unix timestamp
}
```

#### Example

```python
# Check OpenAI provider health
health = await check_provider_health(
    provider_name="openai-gpt4",
    health_url="https://api.openai.com/v1/models",
    timeout=5.0
)

if health["status"] == "healthy":
    print(f"Provider healthy: {health['response_time']:.2f}s")
else:
    print(f"Provider unhealthy: {health['error']}")
```

#### Behavior

- If `health_url` is `None`, assumes provider is healthy (response_time=0.0)
- Returns "healthy" status for HTTP 200 responses
- Returns "unhealthy" status for non-200 responses, timeouts, or errors
- Measures response time for all requests (including failures)

### `update_provider_health_cache()`

Update the global provider health cache by checking all enabled providers concurrently.

#### Parameters

None

#### Returns

`None` (updates global cache in-place)

#### Behavior

1. Acquires async lock to prevent concurrent updates
2. Checks if update is needed based on `health.check_interval` config
3. Retrieves all enabled providers from configuration
4. Launches concurrent health checks using `asyncio.gather()`
5. Updates `_provider_health_cache` with results
6. Updates `_last_health_check` timestamp
7. Logs update completion

#### Example

```python
# Manually trigger health cache update
await update_provider_health_cache()

# Access cached health data
for provider_name, health in _provider_health_cache.items():
    print(f"{provider_name}: {health['status']}")
```

#### Configuration

Controlled by `GatewayConfig.health` settings:
- `check_interval`: Minimum seconds between updates (default: 30)
- `timeout`: Health check timeout in seconds (default: 5.0)

## API Endpoints

### `GET /health`

Basic health check endpoint for simple service availability monitoring.

#### Request

```bash
curl http://localhost:8000/v1/health
```

#### Response

```json
{
  "status": "healthy",
  "service": "sre-inference-gateway",
  "timestamp": 1705234567.89
}
```

#### Status Codes

- `200 OK`: Service is running

#### Use Cases

- Simple uptime monitoring
- Load balancer health checks
- Basic service availability

### `GET /health/detailed`

Detailed health check with provider status and configuration information.

#### Request

```bash
curl http://localhost:8000/v1/health/detailed
```

#### Response

```json
{
  "status": "healthy",
  "service": "sre-inference-gateway",
  "timestamp": 1705234567.89,
  "providers": {
    "total": 2,
    "healthy": 2,
    "unhealthy": 0,
    "details": [
      {
        "name": "openai-gpt4",
        "status": "healthy",
        "response_time": 0.234,
        "error": null,
        "last_check": 1705234560.12
      },
      {
        "name": "vllm-local",
        "status": "healthy",
        "response_time": 0.045,
        "error": null,
        "last_check": 1705234560.15
      }
    ]
  },
  "configuration": {
    "version": "1.0.0",
    "health_check_interval": 30,
    "last_health_check": 1705234560.12
  }
}
```

#### Status Codes

- `200 OK`: Health check completed

#### Overall Status Values

| Status | Condition |
|--------|-----------|
| `healthy` | All enabled providers are healthy |
| `degraded` | Some providers are healthy, some unhealthy |
| `unhealthy` | No providers are healthy or no providers configured |

#### Behavior

- Triggers health cache update if interval has elapsed
- Only includes enabled providers in response
- Filters provider details to match enabled providers
- Calculates overall status based on enabled provider health

#### Use Cases

- Comprehensive service monitoring
- Dashboard health displays
- Debugging provider issues
- Capacity planning

### `GET /ready`

Readiness check endpoint for Kubernetes liveness/readiness probes.

#### Request

```bash
curl http://localhost:8000/v1/ready
```

#### Response (Ready)

```json
{
  "status": "ready",
  "available_providers": ["openai-gpt4", "vllm-local"],
  "healthy_providers": ["openai-gpt4", "vllm-local"],
  "provider_count": 2,
  "healthy_count": 2,
  "timestamp": 1705234567.89
}
```

#### Response (Not Ready)

```json
{
  "status": "not_ready",
  "available_providers": ["openai-gpt4", "vllm-local"],
  "healthy_providers": [],
  "provider_count": 2,
  "healthy_count": 0,
  "timestamp": 1705234567.89
}
```

#### Status Codes

- `200 OK`: Service is ready (at least one healthy provider)
- `503 Service Unavailable`: Service is not ready (no healthy providers)

#### Behavior

- Returns 503 if no healthy providers are available
- Uses health cache to determine provider health
- Falls back to router's available providers if cache is empty
- Triggers health cache update before checking

#### Use Cases

- Kubernetes readiness probes
- Load balancer backend health
- Traffic routing decisions
- Auto-scaling triggers

#### Kubernetes Integration

```yaml
readinessProbe:
  httpGet:
    path: /v1/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /v1/health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### `GET /health/providers`

Get detailed health status for all providers.

#### Request

```bash
curl http://localhost:8000/v1/health/providers
```

#### Response

```json
{
  "providers": [
    {
      "name": "openai-gpt4",
      "status": "healthy",
      "response_time": 0.234,
      "error": null,
      "last_check": 1705234560.12
    },
    {
      "name": "vllm-local",
      "status": "unhealthy",
      "response_time": 5.001,
      "error": "Timeout",
      "last_check": 1705234560.15
    }
  ],
  "last_updated": 1705234560.12,
  "timestamp": 1705234567.89
}
```

#### Status Codes

- `200 OK`: Provider health data returned

#### Use Cases

- Provider-specific monitoring
- Debugging provider issues
- Health trend analysis
- Alert configuration

### `GET /health/providers/{provider_name}`

Get health status for a specific provider.

#### Request

```bash
curl http://localhost:8000/v1/health/providers/openai-gpt4
```

#### Response

```json
{
  "name": "openai-gpt4",
  "status": "healthy",
  "response_time": 0.234,
  "error": null,
  "last_check": 1705234560.12
}
```

#### Status Codes

- `200 OK`: Provider health data returned
- `404 Not Found`: Provider not found in cache

#### Error Response

```json
{
  "detail": "Provider 'unknown-provider' not found"
}
```

#### Use Cases

- Single provider monitoring
- Provider-specific alerts
- Debugging specific provider issues

## Configuration

### Health Check Settings

Configured in `app/config/settings.py`:

```python
class HealthConfig(BaseModel):
    check_interval: int = 30  # Seconds between health checks
    timeout: float = 5.0      # Health check timeout in seconds
```

### Provider Health URLs

Configured per provider in `config.yaml`:

```yaml
providers:
  - name: openai-gpt4
    type: openai
    enabled: true
    health_check_url: https://api.openai.com/v1/models
  
  - name: vllm-local
    type: vllm
    enabled: true
    health_check_url: http://localhost:8000/v1/models
```

## Usage Examples

### Basic Health Monitoring

```python
import httpx
import asyncio

async def monitor_gateway():
    """Monitor gateway health every 10 seconds."""
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get("http://localhost:8000/v1/health/detailed")
            data = response.json()
            
            print(f"Status: {data['status']}")
            print(f"Healthy providers: {data['providers']['healthy']}/{data['providers']['total']}")
            
            await asyncio.sleep(10)

asyncio.run(monitor_gateway())
```

### Provider-Specific Monitoring

```python
async def check_provider(provider_name: str):
    """Check specific provider health."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://localhost:8000/v1/health/providers/{provider_name}"
            )
            health = response.json()
            
            if health["status"] == "healthy":
                print(f"✓ {provider_name} is healthy ({health['response_time']:.3f}s)")
            else:
                print(f"✗ {provider_name} is unhealthy: {health['error']}")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"Provider {provider_name} not found")

await check_provider("openai-gpt4")
```

### Readiness Check with Retry

```python
async def wait_for_ready(max_attempts: int = 10, delay: float = 2.0):
    """Wait for gateway to become ready."""
    async with httpx.AsyncClient() as client:
        for attempt in range(max_attempts):
            try:
                response = await client.get("http://localhost:8000/v1/ready")
                if response.status_code == 200:
                    print("Gateway is ready!")
                    return True
            except httpx.RequestError:
                pass
            
            print(f"Attempt {attempt + 1}/{max_attempts}: Not ready, waiting...")
            await asyncio.sleep(delay)
    
    print("Gateway did not become ready")
    return False

await wait_for_ready()
```

### Health Dashboard

```python
async def health_dashboard():
    """Display comprehensive health dashboard."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/v1/health/detailed")
        data = response.json()
        
        print("=" * 60)
        print(f"SRE Inference Gateway Health Dashboard")
        print("=" * 60)
        print(f"Overall Status: {data['status'].upper()}")
        print(f"Service: {data['service']}")
        print(f"Version: {data['configuration']['version']}")
        print()
        print(f"Providers: {data['providers']['healthy']}/{data['providers']['total']} healthy")
        print()
        
        for provider in data['providers']['details']:
            status_icon = "✓" if provider['status'] == "healthy" else "✗"
            print(f"{status_icon} {provider['name']}")
            print(f"  Status: {provider['status']}")
            if provider['response_time']:
                print(f"  Response Time: {provider['response_time']:.3f}s")
            if provider['error']:
                print(f"  Error: {provider['error']}")
            print()

await health_dashboard()
```

## Monitoring Integration

### Prometheus Metrics

Health check data can be exposed as Prometheus metrics:

```python
from prometheus_client import Gauge

provider_health_gauge = Gauge(
    'provider_health_status',
    'Provider health status (1=healthy, 0=unhealthy)',
    ['provider_name']
)

async def update_health_metrics():
    """Update Prometheus metrics from health cache."""
    for provider_name, health in _provider_health_cache.items():
        status_value = 1 if health['status'] == 'healthy' else 0
        provider_health_gauge.labels(provider_name=provider_name).set(status_value)
```

### Grafana Dashboard

Query examples for Grafana:

```promql
# Provider health status
provider_health_status{provider_name="openai-gpt4"}

# Number of healthy providers
sum(provider_health_status)

# Provider health over time
rate(provider_health_status[5m])
```

## Best Practices

### 1. Configure Appropriate Check Intervals

```yaml
# config.yaml
health:
  check_interval: 30  # Balance between freshness and load
  timeout: 5.0        # Prevent hanging health checks
```

### 2. Use Readiness Probes in Kubernetes

```yaml
readinessProbe:
  httpGet:
    path: /v1/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### 3. Monitor Provider Health Trends

Track provider health over time to identify patterns and issues.

### 4. Set Up Alerts

Configure alerts for:
- Overall gateway health degradation
- Individual provider failures
- Prolonged unhealthy states

### 5. Filter Disabled Providers

The recent update ensures only enabled providers appear in health reports, reducing noise.

## Troubleshooting

### Issue: Health Cache Not Updating

**Symptoms**: Stale health data, `last_health_check` not changing

**Solutions**:
- Check `health.check_interval` configuration
- Verify providers have valid `health_check_url` configured
- Check logs for health check errors

### Issue: All Providers Showing Unhealthy

**Symptoms**: `/ready` returns 503, all providers marked unhealthy

**Solutions**:
- Verify provider services are running
- Check network connectivity to provider endpoints
- Increase `health.timeout` if providers are slow
- Check provider health URLs are correct

### Issue: Provider Not Appearing in Health Checks

**Symptoms**: Provider missing from `/health/detailed` response

**Solutions**:
- Verify provider is enabled in configuration
- Check provider is registered in provider registry
- Ensure provider has `health_check_url` configured

## Related Documentation

- [API Dependencies](API_DEPENDENCIES.md) - FastAPI dependency injection
- [Provider Implementation Guide](PROVIDERS.md) - Provider architecture
- [Architecture Overview](ARCHITECTURE.md) - System architecture
- [Configuration Guide](ENVIRONMENT.md) - Configuration management

## Summary

The Health Check API provides comprehensive monitoring capabilities for the SRE Inference Gateway with:

- ✅ Multiple health check endpoints for different use cases
- ✅ Automatic health caching with configurable intervals
- ✅ Provider-specific health tracking
- ✅ Kubernetes readiness probe support
- ✅ Concurrent health checks for performance
- ✅ Filtering of disabled providers (recent enhancement)
- ✅ Detailed error reporting and response time tracking

The recent update ensures that only enabled providers appear in health reports, improving clarity and reducing confusion when providers are temporarily disabled.
