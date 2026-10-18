# Real-backend run: gateway in front of vLLM on Modal (2026-10-18)

First run of the gateway against a real model instead of the mock lane. The same llm-slo-bench ramp was run twice against the same vLLM server, once directly and once through the gateway, so the difference is the gateway's cost on a real streaming workload.

## Setup

| | |
|---|---|
| Backend | vLLM 0.21.0, `Qwen/Qwen3-8B` BF16 served as `qwen3-8b`, one NVIDIA A10 on Modal us-east (`--enforce-eager --max-num-seqs 16`) |
| Gateway | `origin/main` @ `1a07d70` plus the `fix/forward-messages-without-null-name` change (without it every request to vLLM fails with a 400; see below). Uvicorn, one worker, `127.0.0.1:8000`, [`gateway-config.yaml`](gateway-config.yaml): `vllm` at weight 1.0, mocks at weight 0 |
| Load generator | llm-slo-bench `d94f17f`, [`slo-bench-gateway.yaml`](slo-bench-gateway.yaml) |
| Host | Raspberry Pi (arm64). Gateway and load generator on the same host; Modal reached over the public internet |
| Load | Linear ramp 0 -> 0.5 -> 1 -> 2 req/s over three 2-minute stages, `max_in_flight: 8`, 20-token prompt, `max_completion_tokens: 128`. 300 arrivals |

The direct run used the identical config with `base_url` pointed at Modal. It ran at 18:03, the gateway run at 18:51; network conditions between the two were not controlled.

## Results

Both runs: 300/300 success, 0 errors, 0 dropped, both SLO gates passed (exit 0).

| Client-side metric (ms) | Direct | Through gateway | Difference |
|---|---|---|---|
| TTFB min / p50 / p99 | 96.3 / 98.9 / 155.1 | 182.7 / 201.3 / 435.5 | +86 / +102 / +280 |
| Semantic TTFT min / p50 / p99 | 147.5 / 194.0 / 247.8 | 232.4 / 295.7 / 528.9 | +85 / +102 / +281 |
| Semantic TTFT mean | 195.3 | 302.5 | +107 |
| Chunk ITL p50 / p99 | 36.8 / 49.1 | 37.2 / 42.0 | +0.4 / -7.1 |
| Request duration p50 | 2791 | 2906 | +115 |
| Generation tokens/s per request (mean) | 27.7 | 27.5 | -0.2 |

Raw summaries: [`ramp-gateway.json`](ramp-gateway.json), [`ramp-gateway.html`](ramp-gateway.html), [`ramp-gateway.jsonl`](ramp-gateway.jsonl). The direct run lives in [inference-engineering `observability/artifacts/`](https://github.com/crypticseeds/inference-engineering/tree/main/observability/artifacts).

## Findings

1. **Streaming passthrough is free.** Chunk ITL and tokens/s are unchanged through the gateway. Once bytes flow, the byte-faithful SSE path adds nothing measurable.
2. **The gateway adds a flat ~100 ms to the first token, at every percentile including the minimum**, and more in the tail (+281 ms at p99).
3. **The 100 ms is on the gateway-to-Modal hop, not in gateway code.** The gateway's own `gateway_stream_first_byte_seconds{provider="vllm"}` (timer starts just before the upstream call, stops at the first body chunk) averaged 89.845 s / 300 = **299.5 ms**. The client's TTFT through the gateway averaged **302.5 ms**. Admission, routing, and Python request handling together cost about 3 ms; the upstream request itself took about 100 ms longer than the same request sent directly from the Go client.
4. **Bug found:** the API layer forwarded `"name": null` on every message, which vLLM 0.21 rejects with a 400. Mock providers ignore the field, so the existing suite never caught it. Fixed on `fix/forward-messages-without-null-name`.

## Working hypothesis (not yet proven)

A constant cost of about one to two network round trips on every request, including the fastest, looks like **per-request connection setup** (TCP + TLS) on the gateway's upstream hop:

- llm-slo-bench's Go client (`internal/loadgen/loadgen.go`, `newHTTPClient`) uses a plain `http.Transport`: Go attempts HTTP/2 when the server offers it, keeps up to `max_in_flight` idle connections per host, and never expires them (`IdleConnTimeout` unset).
- The vLLM adapter's `httpx.AsyncClient` speaks HTTP/1.1 (no `http2=True`) with default pool limits, and drops idle connections after 5 s (`keepalive_expiry`). At the ramp's early rates (under 0.5 req/s) gaps between requests exceed 5 s.
- Whether Modal's endpoint negotiated HTTP/2 with the Go client, and how often httpx reused a connection, were not recorded.

This needs to be confirmed before changing anything: count upstream TCP connects per request (httpx trace extension or connection-pool logging), then compare.

## Not measured

- Gateway behaviour at saturation, and failover against a real backend.
- A placement where gateway and backend share a region (the production shape); see the roadmap item.
