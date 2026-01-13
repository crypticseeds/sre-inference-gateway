# SRE Inference Gateway - Python Migration Roadmap

This document outlines the roadmap and tasks for migrating the SRE Inference Gateway to a Python-native architecture.
Original Go-based issues have been refactored to align with the Python stack (FastAPI, Pydantic, uv, Python 3.13+).

## Stage 1: Core Foundation (The Big Shift)

### DEV-64: Foundation Epic
**Status**: In Progress
**Goal**: Establish the Python 3.13+ project structure with FastAPI and uv.
**Acceptance Criteria**:
- [ ] Initialize project using `uv init` with Python 3.13+.
- [ ] Set up `pyproject.toml` with core dependencies:
  - `fastapi`
  - `uvicorn`
  - `pydantic[email]`
  - `pydantic-settings`
  - `httpx` (for provider calls)
- [ ] Create directory structure adhering to `python.md`:
  - `app/` (main, api, auth, router, providers, observability)
  - `infra/`
  - `docs/`
- [ ] Configure `ruff` for linting and formatting.

### DEV-65: API Handler
**Status**: Todo
**Goal**: Implement the main entry point and request handling.
**Dependencies**: DEV-64
**Acceptance Criteria**:
- [ ] Implement `app/main.py` with `FastAPI`.
- [ ] Define Pydantic models for OpenAI-compatible request/response schemas in `app/api/models.py`.
- [ ] Implement basic health check endpoint (`/health`).
- [ ] Ensure proper error handling and JSON validation.

### DEV-66: Router Logic
**Status**: Todo
**Goal**: Implement the routing logic for multi-provider support.
**Dependencies**: DEV-65
**Acceptance Criteria**:
- [ ] Create `app/router/router.py`.
- [ ] Define `Provider` Abstract Base Class (ABC) in `app/providers/base.py`.
- [ ] Implement weighted routing logic using Python's `random.choices`.
- [ ] Support provider selection based on configured weights.

### DEV-67: Configuration Management
**Status**: Todo
**Goal**: Implement type-safe configuration.
**Dependencies**: DEV-64
**Acceptance Criteria**:
- [ ] Implement `Pydantic Settings` in `app/config.py`.
- [ ] Map environment variables to config fields.
- [ ] **Secrets Management**: Ensure integration specifically with **Doppler** for loading API keys and secrets (as per tech stack rules).
- [ ] Support loading configuration from `.env` or structured files if needed (dev mode only).
- [ ] Replace legacy Go `viper` or standard yaml concepts with idiomatic Pydantic.

## Stage 2: Resilience (The SRE Part)

### DEV-68: Resilience Epic
**Status**: Todo
**Goal**: Implement SRE patterns to improve system reliability.

### DEV-69: Circuit Breakers
**Status**: Todo
**Goal**: Prevent cascading failures using circuit breakers.
**Dependencies**: DEV-66
**Acceptance Criteria**:
- [ ] Implement circuit breaker pattern (using `pycircuitbreaker` or custom decorator in `app/router/resilience.py`).
- [ ] Wrap provider calls with circuit breaker logic.
- [ ] Configurable thresholds (failure count, recovery timeout).

### DEV-73: Metrics & Observability
**Status**: Todo
**Goal**: Instrument the application for monitoring.
**Acceptance Criteria**:
- [ ] Integrate `prometheus-fastapi-instrumentator`.
- [ ] Expose standard RED metrics (Rate, Errors, Duration) at `/metrics`.
- [ ] Ensure request IDs are propagated in logs and traces.

### DEV-XX: vLLM Adapter (vLLM)
**Status**: Todo
**Goal**: Support local inference using vLLM.
**Acceptance Criteria**:
- [ ] Create `app/providers/vllm.py` implementing the Provider ABC.
- [ ] Implement HTTP client logic to call local vLLM instance.
- [ ] Ensure compatibility with OpenAI schema.

## Future / Post-MVP

### DEV-94: Streaming Support
**Status**: Backlog
**Goal**: Support internal logic for streaming but defer full implementation.
**Acceptance Criteria**:
- [ ] Support `stream: true` parameter in valid request models (Pydantic).
- [ ] Toggle feature via config settings (default off/mock implementation initially).
- [ ] Full SSE implementation deferred to Post-MVP.

### Incident Remediation (from INCIDENT.md)
**Status**: Backlog
**Goal**: Address action items from simulated incidents.
- [ ] **Warm-up Hook**: Add mechanism to warm up local providers to prevent cold-start latency.
- [ ] **Latency SLO Alerts**: Configure alerts for latency breaches (Platform task).
- [ ] **Provider Health Scoring**: Improve logic for determining provider health beyond simple availability.
