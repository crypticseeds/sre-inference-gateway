# Monitoring

The gateway exposes Prometheus metrics at `/metrics` and `/v1/metrics`. The
checked-in Prometheus configuration scrapes a gateway started on the host by
`make dev` and can forward samples to Grafana Cloud using a local, ignored copy.

## Metric inventory

| Metric | Type and labels | Operational meaning |
| --- | --- | --- |
| `gateway_requests_total` | Counter: `provider`, `model`, `stream`, `status_class` | Completed provider attempts and request rate. Failover legs count separately. |
| `gateway_failures_total` | Counter: `provider`, `error_type` | Establishment, mid-stream truncation, and client 4xx failures. |
| `gateway_request_duration_seconds` | Histogram: `provider`, `stream` | Full provider-attempt duration; streams include iterator lifetime. |
| `gateway_stream_first_byte_seconds` | Histogram: `provider` | Gateway time to first forwarded transport chunk. This is TTFB and a gateway-side TTFT proxy, not token-aware client TTFT. |
| `gateway_stream_interchunk_seconds` | Histogram: `provider` | Gateway-observed interval between forwarded transport chunks. This is an ITL proxy; chunks can split or combine SSE events and model tokens. It differs from the benchmark's client-side chunk ITL. |
| `gateway_in_flight_requests` | Gauge: `provider` | Active provider work, including stream iteration. |
| `gateway_shed_requests_total` | Counter: `scope`, `provider` | Requests rejected by concurrency admission. |
| `circuit_breaker_state` | Gauge: `provider` | Breaker state: 0 closed, 1 open, 2 half-open. |
| `gateway_tokens_total` | Counter: `provider`, `model`, `type` | Provider-reported prompt and completion tokens. No client-side estimation. |
| `gateway_cost_usd_total` | Counter: `provider`, `model` | Cumulative USD cost calculated from provider-reported usage and configured prices. |
| `gateway_unpriced_requests_total` | Counter: `provider`, `model`, `reason` | Successful requests lacking usable usage or pricing. |

## Local scrape check

Start the no-key gateway, send a streaming request, and inspect its exposition:

```bash
make dev
curl -sS http://localhost:8000/metrics
```

Prometheus runs at <http://localhost:9091>. Its target is
`host.docker.internal:8000`, which works with recent Docker Desktop and Colima.
If an older Colima installation cannot resolve that name, copy the config and
use Colima's default host IP, `192.168.5.2:8000`. If the gateway itself runs as a
Compose service, use `gateway:8000` instead.

## Grafana Cloud remote write

1. Sign in at grafana.com and open the target stack.
2. Open **Prometheus**, then **Details**, and copy the remote-write URL, instance ID, and an API token with metrics-publish permission.
3. Add the three Grafana Cloud secrets to Doppler project
   `sre-inference-gateway`, config `dev_personal`. The two Compose secrets should
   already be present:

   - `GRAFANA_CLOUD_PROMETHEUS_URL`
   - `GRAFANA_CLOUD_PROMETHEUS_USERNAME`
   - `GRAFANA_CLOUD_PROMETHEUS_TOKEN`
   - `REDIS_PASSWORD`
   - `GRAFANA_ADMIN_PASSWORD`

4. Configure Doppler once and start Prometheus:

```bash
doppler setup --project sre-inference-gateway --config dev_personal
make monitoring-up
```

`make monitoring-up` renders the ignored `infra/prometheus.local.yml` with mode
`600` and starts Prometheus with `REDIS_PASSWORD` and
`GRAFANA_ADMIN_PASSWORD` supplied by `doppler run`. Stop it with
`make monitoring-down`. No secret values need to be exported or printed.

<details>
<summary>Manual fallback</summary>

Copy `infra/prometheus.yml` to `infra/prometheus.local.yml`, uncomment
`remote_write`, replace its endpoint, username, and password placeholders, and
set mode `600`. Then run the two-file Docker Compose command shown by
`make -n monitoring-up` with all required Compose variables supplied securely.
The local file is gitignored; never put credentials in a tracked file.

</details>

Prometheus continues to retain local samples while forwarding them to Grafana
Cloud. Check **Prometheus > Explore** in the stack and query `up` to confirm data
arrival.

## Dashboard import

1. In the Grafana Cloud stack, open **Dashboards > New > Import**.
2. Upload `infra/grafana/gateway-dashboard.json`.
3. Select the stack's hosted Prometheus datasource when prompted for
   `DS_PROMETHEUS`.
4. Import the dashboard and choose a time range containing gateway traffic.

All rate and histogram panels use Grafana's `$__rate_interval`, so they adapt to
the selected range and scrape interval.
