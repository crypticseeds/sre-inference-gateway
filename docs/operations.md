# Operations

## No-key local development

Install dependencies and start the gateway with the two enabled mock providers:

```bash
uv sync
env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY -u GEMINI_API_KEY \
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`make dev` also starts Redis, Prometheus, and Grafana with Docker Compose before
running the gateway on the host. Doppler is optional. Note that the checked-in
Prometheus target is `gateway:8000`, while `make dev` does not start the Compose
gateway service; scrape the host process directly or run the gateway service in
the Compose network when using that configuration.

## Failover drill

Use the exact start, fail, restore, and breaker-observation commands in
[failover-drill.md](failover-drill.md). The drill requires
`FAILOVER_DRILL_ADMIN=1` and should bind only to loopback.

## Metrics

Prometheus text exposition is available at both paths:

```bash
curl -sS http://127.0.0.1:8000/metrics
curl -sS http://127.0.0.1:8000/v1/metrics
```

The metric inventory and semantics are in
[ARCHITECTURE.md](ARCHITECTURE.md#golden-signals).

## Go probe integration

The integration test builds `llm-slo-bench` from `git archive HEAD`, starts a
zero-key gateway on a free loopback port, and checks status, TTFT, content event
count, and usage:

```bash
LLM_SLO_BENCH_DIR=/path/to/llm-slo-bench \
  uv run pytest -q -m integration tests/test_streaming_probe.py -s
```

Without the override, the test searches beside the primary gateway checkout. It
skips when Go or the benchmark checkout is unavailable.

## CI

The Python job installs Python 3.13 dependencies, runs Ruff, and runs the normal
pytest suite. Integration tests are excluded from normal pytest by marker. A
second job checks out the private benchmark and runs the Go-probe test only when
`LLM_SLO_BENCH_TOKEN` is available; otherwise it records a skip summary.
