# Streaming failover drill

The default `config.yaml` enables `mock_openai` and `mock_vllm` with equal,
nonzero weights. Both serve `mock-model`, support streaming, and require no
keys. Real providers are disabled by default.

The runtime failure control is intentionally limited to registered mock
providers. It affects new requests and fails during stream establishment,
before response headers. It is suitable for the local benchmark drill and must
not be exposed on a public deployment. The endpoints return 404 unless the
gateway starts with `FAILOVER_DRILL_ADMIN=1`; bind the drill process to
`127.0.0.1` as shown below.

## Start the gateway with no keys

```bash
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u GEMINI_API_KEY \
  FAILOVER_DRILL_ADMIN=1 \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, send an unpinned streaming request. Repeating this command
shows weighted routing across both mocks:

```bash
curl -sS -N http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"failover drill"}],"stream":true}'
```

For a compact loop that prints the serving mock reconstructed from SSE chunks:

```bash
for i in 1 2 3 4 5 6; do
  curl -sS -N http://127.0.0.1:8000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"mock-model\",\"messages\":[{\"role\":\"user\",\"content\":\"request $i\"}],\"stream\":true}" \
    | tr -d '\n' | grep -o 'Mock[^"}]*' | tr -d '\n'
  printf '\n'
done
```

## Kill and restore mock_openai

Kill only `mock_openai` while the request loop or benchmark is running:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/providers/mock_openai/fail
```

New requests that first select `mock_openai` fail over before response headers
to `mock_vllm`. After two failed requests the `mock_openai` circuit opens and
routing skips it. Requests continue to return complete HTTP 200 SSE streams
from `mock_vllm`; the response header `X-Served-By: mock_vllm` makes the survivor
visible.
`X-Failed-Providers: mock_openai` explicitly marks that response as degraded
because a provider failed and was skipped.

Restore the mock:

```bash
curl -sS -X POST http://127.0.0.1:8000/admin/providers/mock_openai/restore
```

An OPEN circuit remains open until the five-second recovery timeout. The next
request that selects or pins `mock_openai` becomes the half-open probe. A
successful probe closes the circuit and both mocks resume serving:

```bash
sleep 5
curl -sS -N http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'X-Provider-Priority: mock_openai' \
  -d '{"model":"mock-model","messages":[{"role":"user","content":"recovery probe"}],"stream":true}'
```

## Observe circuit-breaker state

Query all breakers or one provider:

```bash
curl -sS http://127.0.0.1:8000/health/circuit-breakers
curl -sS http://127.0.0.1:8000/health/circuit-breakers/mock_openai
```

The same endpoints are available under `/v1`. Prometheus state is exposed at
`/v1/metrics` as `circuit_breaker_state{provider="mock_openai"}` with values 0
(closed), 1 (open), and 2 (half-open). Logs emit
`event=circuit_breaker_transition` with provider, previous state, and next
state, plus `event=provider_failover` for a pre-header fallback.

## Client-visible behavior

The mock kill mode fails at stream establishment, so the gateway can fall
through to the survivor before returning headers. With at least one healthy
provider, the benchmark sees complete HTTP 200 streams, although requests that
first hit the failed provider may have slightly higher time to first byte.
Do not send `X-No-Failover` during the drill because the drill depends on this
fallback behavior.

For real providers, a failure before response headers can also fall through to
another provider. A provider failure after SSE bytes have started cannot be
failed over safely: the response ends without `[DONE]`, and the benchmark
reports a truncated-stream failure. Such mid-stream failures do not increment
the circuit breaker; this is the accepted streaming limitation.
