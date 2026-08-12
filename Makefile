.PHONY: help dev dev-stop dev-logs test test-cov lint format clean health status

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
