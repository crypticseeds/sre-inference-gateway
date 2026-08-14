# SSE streaming

`POST /v1/chat/completions` returns an OpenAI-compatible SSE response when the
request sets `"stream": true`. The gateway selects a provider through the same
weighted or `X-Provider-Priority` routing path as non-streaming requests and
uses the provider resilience wrapper while establishing the upstream stream.

The gateway accepts both `max_tokens` and `max_completion_tokens`. It forwards
`stream_options` unchanged, including `{"include_usage": true}`. Provider SSE
transport chunks are flushed immediately without application buffering or byte
rewriting, preserving multi-line `data:` events and the final `data: [DONE]`
sentinel. Streaming responses use `Content-Type: text/event-stream`, are not
compressed, and include `X-Accel-Buffering: no` for compatible reverse proxies.
`X-Served-By` identifies the provider whose stream was successfully established,
including the survivor selected after pre-header failover.

## Mock streaming

The no-key `mock_openai` provider is configured in `config.yaml`:

```yaml
model: "mock-model"
stream_chunk_delay: 0.05
stream_content_chunks: 3
```

`stream_chunk_delay` is the delay in seconds before each event. Keep it below
the probe's default five-second idle timeout. `stream_content_chunks` controls
the number of non-empty `delta.content` events and must be at least two. When
`stream_options.include_usage` is true, the mock sends a final usage chunk
before `[DONE]`.

## Failure behavior

Failures while establishing an upstream stream use the existing resilience,
retry, and circuit-breaker behavior and return an HTTP error before response
streaming starts. If a provider fails after bytes have been sent, the gateway
logs the failure, closes the upstream response and downstream stream cleanly,
and does not retry or synthesize an SSE error event. The client receives no
`[DONE]`, so clients such as `llm-slo-bench` report a truncated-stream failure
instead of accepting partial output or receiving duplicate retried content.

## Verification

Run the normal suite, including in-process streaming tests:

```bash
make test
```

Run the automated Go-probe integration test:

```bash
uv run pytest -v -m integration tests/test_streaming_probe.py
```

The test discovers `llm-slo-bench` beside the primary gateway checkout. Set
`LLM_SLO_BENCH_DIR=<path-to-llm-slo-bench>` to override that location. The test
skips cleanly when Go or the benchmark checkout is unavailable. It builds a
temporary `git archive HEAD` snapshot so unrelated uncommitted benchmark work
cannot alter the reference probe or make the gateway test nondeterministic.
