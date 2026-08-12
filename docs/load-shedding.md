# Load shedding

The gateway limits concurrent work with one global semaphore and one semaphore
per provider. Admission is immediate: requests never wait in a gateway queue.
Streaming requests hold both slots from provider establishment until the stream
finishes or the downstream connection closes.

```yaml
load_shedding:
  enabled: true
  global_max_in_flight: 200
  per_provider_max_in_flight: 100
```

The defaults are deliberately well above the 5-20 requests-per-second benchmark
load. Set `enabled: false` to bypass both limits. Configuration is applied when
the gateway starts.

When the global limit is full, the gateway returns `503` with
`Retry-After: 1`. A provider at capacity is excluded from routing like a provider
with an open circuit breaker, allowing another provider to serve the request. If
all eligible providers are full, the gateway returns the same `503` and retry
header. Clients decide whether and when to retry.

`gateway_shed_requests_total{scope="global|provider",provider="..."}` counts
rejections. The `provider` label is empty for global rejections and names the
saturated provider for provider-scoped rejections. Existing
`gateway_in_flight_requests{provider="..."}` continues to report active provider
work.
