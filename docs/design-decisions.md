# Design decisions

This record separates current behavior from approved follow-up work.

## Explicit failover opt-out

Pre-header failover masks provider outages by design, which is useful for
resilience but misleading during provider verification. `X-No-Failover: 1` (or
case-insensitive `true`) exposes the selected provider's error while leaving
production failover enabled.

## Mid-stream failure

### Current behavior

After a streaming response is established, upstream bytes are passed through
unchanged. If the provider fails during iteration, the gateway logs the failure,
records `mid_stream_truncation`, closes the upstream response, and ends the
downstream body without a synthetic event or `[DONE]`.

The HTTP status is already committed, so it cannot be changed to an error. A
client that requires `[DONE]` can identify the result as truncated rather than
accepting partial output as complete.

### Approved hardening plan

[DEV-124](https://linear.app/devopsfoundry/issue/DEV-124/mid-stream-failure-hardening-in-band-error-event-cb-stream-accounting)
tracks four layers of post-benchmark hardening:

1. Emit a terminal SSE error object containing the request ID before closing.
2. Detect `[DONE]` with a bounded rolling tail and record stream completion or
   truncation in circuit-breaker accounting.
3. Add an upstream idle timeout, with optional SSE keepalive comments, to bound
   stalled stream resource use.
4. Document the client retry contract around the terminal error, request ID, and
   existing establishment-time failover.

None of these layers is implemented today.

### Rejected: mid-stream provider switchover

The gateway will not splice a second provider's output onto a partial stream.
The providers may produce different continuations, so the final content would
have ambiguous provenance. Replaying context can duplicate tokens already sent.
Both providers can bill for overlapping generation. A benchmark would measure a
synthetic composite response rather than either provider's behavior. Those costs
outweigh concealing a visible truncation.

## Provider-attempt metric semantics

Gateway traffic and latency metrics count provider attempts, not only incoming
client requests. A request that fails over contributes one failed leg and one
successful leg with separate provider labels.

This is deliberate. Provider capacity, latency, and error rates are properties
of work actually sent to each backend. Collapsing both legs into one client
request would hide the load and latency cost of a failing provider. OpenTelemetry
FastAPI spans provide separate request-level trace visibility.

## Circuit breaker and streams

The circuit breaker currently accounts for stream establishment only. Returning
the byte iterator records breaker success; later iteration runs outside the
resilience wrapper. A mid-stream provider failure increments
`gateway_failures_total{error_type="mid_stream_truncation"}` but does not change
breaker state.

This is a known blind spot, not an assertion that the provider remained healthy.
DEV-124 will move completion accounting to the stream lifecycle by detecting the
terminal `[DONE]` sentinel.

## Drill-tuned resilience defaults

Checked-in `config.yaml` uses a circuit-breaker threshold of 2, a five-second
recovery timeout, and one outer resilience attempt. These values make failure,
OPEN-state routing exclusion, and HALF_OPEN recovery observable in a short local
drill.

Provider adapters retain their own configured retry behavior. Avoiding extra
gateway retries keeps benchmark latency attributable: an unhealthy first choice
fails over promptly instead of hiding repeated waits inside one provider leg.
This makes benchmark tail latency reflect the configured failover policy instead
of additional gateway retry waits hidden inside one provider leg.

## Doppler-optional Makefile

Make targets use `doppler run --` only when the CLI exists and can successfully
run a probe command. Otherwise they execute directly. Mock providers require no
credentials, and local Redis and Grafana passwords have development defaults.

This keeps Doppler available for contributors who use it without making a
secret manager a prerequisite for mock requests, tests, or the failover drill.

## Shed instead of queue

The gateway rejects excess concurrency immediately instead of placing requests
in an internal queue. Queueing under overload consumes resources, destroys tail
latency, and hides provider saturation. A fast `503` with `Retry-After: 1` keeps
the overload signal visible and lets the client decide whether and when to retry.

Provider saturation is an eligibility condition during routing, like an open
circuit breaker. This preserves healthy-provider fallback without admitting more
work to the saturated provider. Streaming requests retain their global and
provider admission slots for the complete downstream stream lifetime.

## Gateway inter-chunk latency

`gateway_stream_interchunk_seconds` measures elapsed time between consecutive
transport chunks forwarded by the gateway. It does not parse SSE events or model
tokens, so it is a gateway-observed proxy for inter-token latency (ITL), not the
benchmark's client-observed chunk ITL. This distinction preserves byte-faithful,
unparsed stream forwarding while making gateway-observed chunk cadence visible.
Because the timestamp is taken when iteration resumes, downstream backpressure
can contribute to the measured interval.
