# vLLM Docker setup

`infra/docker-compose.yml` contains an enabled CPU-only `vllm` service and a
commented GPU alternative. The CPU service builds
`services/vllm-inference`, publishes port 8080 by default, and persists the
Hugging Face cache in `vllm_cache`.

Start the CPU service directly:

```bash
REDIS_PASSWORD=local-dev-password \
GRAFANA_ADMIN_PASSWORD=local-dev-password \
docker compose -f infra/docker-compose.yml up -d vllm
```

The gateway does not auto-detect this service. To route requests to it, enable
the `vllm` provider in `config.yaml`, set a reachable `base_url`, and restart the
gateway. For a gateway process running on the host, the checked-in
`http://localhost:8080/v1` URL is appropriate. A gateway container on the Compose
network should use `http://vllm:8080/v1`.

The Compose vLLM service has no Docker health check. The vLLM adapter's own
health method requests `{base_url}/models`. The separate API health routes use
`health_check_url` when configured and otherwise report the enabled provider as
healthy without calling its adapter.

## GPU alternative

The GPU service block is commented. To use it, replace the CPU service with the
GPU block and provide a compatible NVIDIA container runtime. Do not define both
blocks with the same `vllm` service key.

## Limits

The repository does not establish production capacity, latency, or model-quality
claims for the CPU service. Resource limits in Compose are local defaults, not
benchmarked sizing guidance.
