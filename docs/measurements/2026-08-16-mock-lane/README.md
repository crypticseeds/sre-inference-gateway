# Official mock-lane run: llm-slo-bench against the gateway (2026-08-16)

The v0.1.0 benchmark quoted in the main README. Recorded here so the gateway repo holds its own methodology; the README previously pointed to llm-slo-bench, which only ever published the summary table.

## Setup

| | |
|---|---|
| Gateway | `bf319e6`, single uvicorn worker on localhost (macOS) |
| Load generator | llm-slo-bench `fe41627`, same host |
| Providers | Mock lane only (`mock_openai`, `mock_vllm`): SSE chunks on a fixed 50 ms cadence, zero keys, zero network |
| Bench admission | `max_in_flight: 4` in the bench config (a client-side cap, not a gateway limit) |
| SLO gate | p99 semantic TTFT <= 250 ms |

Because the mocks have no inference and no network, these numbers isolate gateway overhead. Semantic TTFT is client-measured (first non-empty content delta) and includes the mocks' synthetic first-chunk delay; it is an end-to-end streaming number through the gateway, not a model benchmark.

## Runs

| Run | Load shape | Result | TTFT p50 / p99 | Chunk ITL p50 / p99 |
| --- | --- | --- | --- | --- |
| Ramp | 10 s @ 5 rps, then 20 s @ 10 rps | 175/175 success, 0 errors, 0 drops | 112.4 / 135.9 ms | 50.9 / 54.9 ms |
| Failover drill | 45 s @ 8 rps, one provider killed at t = 12 s | 180/180 success, zero client-visible errors | 114.6 / 140.4 ms | 51.0 / 61.2 ms |
| Headroom | 30 s @ 20 rps | 226/226 started succeeded; 74 dropped by the bench-side `max_in_flight=4` cap | 110.3 / 144.6 ms | 50.9 / 59.3 ms |

The failover drill used the env-gated admin controls (`FAILOVER_DRILL_ADMIN=1`); the procedure is in [failover-drill.md](../../failover-drill.md).

## Findings

- SLO gate passed on every run; worst p99 TTFT 144.6 ms.
- Failover: the circuit breaker opened about 1.4 s after the kill and re-closed 13.7 s after the kill, 1.8 s after the provider was restored. Clients saw uninterrupted 200s from the surviving provider.
- Highest sustained zero-drop stage: 10 rps. The headroom run's drops are a bench-side cap, not gateway shedding.
- Chunk ITL p50 of about 51 ms against the mock's fixed 50 ms cadence puts per-chunk gateway overhead around 1 ms at these rates.

## What was not kept

The raw llm-slo-bench summaries (JSON, HTML, JSONL) and the bench configs for these runs were treated as scratch output and never committed, so the table above is the complete surviving record. The circuit-breaker timeline comes from the epochs recorded at the time (llm-slo-bench commit `87d6d8e` corrected the re-close interval to 1.8 s post-restore).

## Related

- [Single-instance capacity (informal)](../../load-shedding.md#measured-single-instance-capacity-informal): a separate 2026-08-16 run at 100-300 rps with a different shape; not comparable to this table.
- [2026-10-18 real-backend run](../2026-10-18-vllm-modal/README.md): the same bench against vLLM on Modal, direct vs through the gateway.
