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

## Measured single-instance capacity (informal)

Measured 2026-08-16 on a MacBook (localhost, mock lane, single uvicorn worker,
`--log-level warning`, no `--reload`), llm-slo-bench ramp with bench-side
`max_in_flight: 400` so the bench never bottlenecks. 30s stages, 5s half-rate
warmup. Not comparable to the official README benchmark (different rates and
run shape); useful only as a capacity envelope for this deployment shape.

| Target rps | Result | TTFT p50 / p99 |
| --- | --- | --- |
| 100 | 2000/2000, zero errors | 105 / 147 ms |
| 200 | 4000/4000, zero errors | 114 / 168 ms |
| 250 | 5000/5000, zero errors, SLO breach | 125 / 292 ms |
| 300 | 5895/6000 (105 bench-side drops), no errors | 243 / 4223 ms |

Interpretation: the practical knee for one worker on this hardware is around
200-250 rps. Below it, latency is flat; at 250 rps every request still succeeds
but the p99 TTFT SLO (250 ms) breaches; at 300 rps the asyncio event loop
saturates and queueing collapses tail latency. The gateway's own load shedding
never fired at any rate (in-flight stayed under the 200 global cap because the
event loop, not admission, was the binding constraint). There is no configured
request-per-second limit - only the concurrency caps documented above. To scale
past the knee, run multiple uvicorn workers (the gateway keeps no cross-request
state) or lower `global_max_in_flight` so shedding engages before the loop
saturates and the 503+Retry-After contract, rather than tail latency, absorbs
the overload.
