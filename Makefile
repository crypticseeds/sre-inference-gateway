.PHONY: help dev dev-stop dev-logs monitoring-up monitoring-down test test-cov lint format clean health status

DOPPLER_CMD := $(shell if command -v doppler >/dev/null 2>&1 && doppler run -- true >/dev/null 2>&1; then printf 'doppler run --'; fi)
REDIS_PASSWORD ?= local-dev-password
GRAFANA_ADMIN_PASSWORD ?= local-dev-password
export REDIS_PASSWORD GRAFANA_ADMIN_PASSWORD

# Default target
help:
	@echo "SRE Inference Gateway - Development Commands"
	@echo ""
	@echo "  make dev        - Start all services (Redis, Prometheus, Grafana, Gateway)"
	@echo "  make dev-stop   - Stop all services"
	@echo "  make dev-logs   - Tail logs from all services"
	@echo "  make monitoring-up   - Start Prometheus with Grafana Cloud remote write"
	@echo "  make monitoring-down - Stop Grafana Cloud Prometheus"
	@echo "  make status     - Show running containers"
	@echo "  make health     - Check gateway health endpoint"
	@echo ""
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo "  make lint       - Run linter (ruff)"
	@echo "  make format     - Format code (ruff)"
	@echo ""
	@echo "  make clean      - Stop services and remove volumes"

# Development
dev:
	@echo "Starting services..."
# 	$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml up -d redis prometheus grafana vllm
	$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml up -d redis prometheus grafana
	@echo "Waiting for services to start..."
	@sleep 5
	@echo ""
	@echo "Services running:"
	@echo "  Gateway:    http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo "  Prometheus: http://localhost:9091"
	@echo "  Grafana:    http://localhost:3000"
# 	@echo "  vLLM:       http://localhost:8080/v1"
	@echo ""
	@echo "Starting gateway..."
	$(DOPPLER_CMD) uv run run_dev.py

dev-stop:
	@echo "Stopping all services..."
	@echo "Stopping gateway..."
	@-pkill -f "uvicorn app.main:app" 2>/dev/null || true
	@echo "Stopping Docker services..."
	@$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml down
	@echo "Done."

dev-logs:
	$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml logs -f

monitoring-up:
	@command -v doppler >/dev/null 2>&1 || { echo "Error: doppler is required for monitoring-up." >&2; exit 1; }
	@doppler run --project sre-inference-gateway --config dev_personal -- true >/dev/null 2>&1 || { echo "Error: doppler run failed. Run 'doppler setup --project sre-inference-gateway --config dev_personal' and verify access." >&2; exit 1; }
	@env -u REDIS_PASSWORD -u GRAFANA_ADMIN_PASSWORD doppler run --project sre-inference-gateway --config dev_personal -- python3 -c 'import json, os, pathlib; names=("GRAFANA_CLOUD_PROMETHEUS_URL", "GRAFANA_CLOUD_PROMETHEUS_USERNAME", "GRAFANA_CLOUD_PROMETHEUS_TOKEN", "REDIS_PASSWORD", "GRAFANA_ADMIN_PASSWORD"); missing=[name for name in names if not os.environ.get(name)]; missing and (_ for _ in ()).throw(SystemExit("Missing Doppler secrets: " + ", ".join(missing))); source=pathlib.Path("infra/prometheus.grafana-cloud.template.yml").read_text(); source=source.replace("__GRAFANA_CLOUD_PROMETHEUS_URL__", json.dumps(os.environ[names[0]])).replace("__GRAFANA_CLOUD_PROMETHEUS_USERNAME__", json.dumps(os.environ[names[1]])).replace("__GRAFANA_CLOUD_PROMETHEUS_TOKEN__", json.dumps(os.environ[names[2]])); target=pathlib.Path("infra/prometheus.local.yml"); descriptor=os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.fchmod(descriptor, 0o600); file=os.fdopen(descriptor, "w"); file.write(source); file.close()'
	@env -u REDIS_PASSWORD -u GRAFANA_ADMIN_PASSWORD doppler run --project sre-inference-gateway --config dev_personal -- docker compose -f infra/docker-compose.yml -f infra/docker-compose.grafana-cloud.yml up -d prometheus

monitoring-down:
	@command -v doppler >/dev/null 2>&1 || { echo "Error: doppler is required for monitoring-down." >&2; exit 1; }
	@doppler run --project sre-inference-gateway --config dev_personal -- true >/dev/null 2>&1 || { echo "Error: doppler run failed. Run 'doppler setup --project sre-inference-gateway --config dev_personal' and verify access." >&2; exit 1; }
	@env -u REDIS_PASSWORD -u GRAFANA_ADMIN_PASSWORD doppler run --project sre-inference-gateway --config dev_personal -- docker compose -f infra/docker-compose.yml -f infra/docker-compose.grafana-cloud.yml stop prometheus

status:
	@$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml ps

health:
	@curl -s http://localhost:8000/v1/health | python -m json.tool || echo "Gateway not responding"

# Testing
test:
	$(DOPPLER_CMD) uv run pytest -v

test-cov:
	$(DOPPLER_CMD) uv run pytest -v --cov=app --cov-report=term-missing

# Code quality
lint:
	uv run ruff check .

format:
	uv run ruff format .

# Cleanup
clean:
	@echo "Stopping services and removing volumes..."
	$(DOPPLER_CMD) docker compose -f infra/docker-compose.yml down -v
	@echo "Removing Python cache..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done."
