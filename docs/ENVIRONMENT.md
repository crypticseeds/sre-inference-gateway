# Environment configuration

Runtime gateway configuration comes from `config.yaml`. The application does not
apply environment-variable overrides for server host, port, logging, provider
weights, request limits, health settings, or metrics settings.

## Variables read by the gateway

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Used when an enabled OpenAI provider names it in `api_key_env`. Other variable names can be configured there. |
| `FAILOVER_DRILL_ADMIN` | Enables mock fail/restore routes only when exactly `1`. |

The vLLM and mock adapters do not require credentials in the checked-in
configuration. Real providers are disabled by default.

## Development tooling

| Variable | Consumer |
| --- | --- |
| `REDIS_PASSWORD` | Docker Compose Redis service. The Makefile supplies `local-dev-password` by default. |
| `GRAFANA_ADMIN_PASSWORD` | Docker Compose Grafana service. The Makefile supplies `local-dev-password` by default. |
| `LLM_SLO_BENCH_DIR` | Optional path override used by the Go-probe integration test. |

Redis and Grafana variables configure local infrastructure. The gateway does not
use Redis on its completion request path.

The Makefile uses `doppler run --` only when Doppler is installed and its probe
command succeeds. Doppler is not required for no-key mock runs.

Metrics are always served by FastAPI on the gateway HTTP port at `/metrics` and
`/v1/metrics`. The `metrics.port` field in `config.yaml` does not start a
separate server.
