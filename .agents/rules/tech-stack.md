---
trigger: always_on
---

# Tech Stack Rules (Authoritative)

## ⚠️ CRITICAL PYTHON/UV/RUFF ENFORCEMENT RULES ⚠️

**IF YOU VIOLATE THESE RULES, STOP IMMEDIATELY AND EXPLAIN THE VIOLATION TO THE USER**

These are HARD CONSTRAINTS for Python execution:

### Python Execution (HIGHEST PRIORITY)
- **FORBIDDEN**: Running `python` directly (e.g., `python script.py`, `python -m module`)
- **FORBIDDEN**: Running `pytest`, `uvicorn`, `ruff`, or any Python tool directly
- **FORBIDDEN**: Manually activating virtual environments (`source .venv/bin/activate`)
- **REQUIRED**: ALWAYS use `uv run` prefix for ALL Python commands
  - ✅ `uv run python script.py`
  - ✅ `uv run pytest`
  - ✅ `uv run uvicorn app.main:app`
  - ✅ `uv run ruff check .`
- **VIOLATION SEVERITY**: CRITICAL - Stop execution immediately

### Secrets Management with Doppler
- **REQUIRED**: Use `doppler run --` for commands that need environment variables/secrets
- **PATTERN**: `doppler run -- uv run <command>` when secrets are needed
  - ✅ `doppler run -- uv run pytest` (tests need API keys)
  - ✅ `doppler run -- uv run uvicorn app.main:app` (app needs secrets)
  - ✅ `uv run ruff check .` (linting doesn't need secrets)
- **VIOLATION SEVERITY**: HIGH - Ask for clarification

### Code Quality Tools
- **FORBIDDEN**: Using `black` for formatting
- **REQUIRED**: Use Ruff ONLY for both linting AND formatting
  - Linting: `uv run ruff check .`
  - Formatting: `uv run ruff format .`
  - Fix issues: `uv run ruff check --fix .`
- **VIOLATION SEVERITY**: MEDIUM - Use correct tool

### Pre-Execution Checklist for Python Commands

**Before running ANY Python command, verify:**
- [ ] Am I using `uv run` prefix? ✓
- [ ] Do I need secrets? If YES, add `doppler run --` ✓
- [ ] Am I using Ruff (not Black) for formatting? ✓
- [ ] Am I avoiding direct `python` execution? ✓

**If any checkbox fails, STOP and use the correct command pattern.**

---

## Purpose

This document defines the authoritative technology stack for this repository.

All generated code, configuration, and documentation MUST adhere to these rules.
Deviations require explicit justification in comments or documentation.

This project is Python-first.

---

## 1. Language & Runtime

### Python 3.13+
- Gateway and all backend logic MUST be written in Python
- No Go, Node.js, Rust, or Java implementations
- Do not introduce additional backend languages

### Virtual Environment Management
- **UV manages ALL virtual environments automatically**
- NEVER manually create or activate virtual environments
- NEVER run `python -m venv` or `source .venv/bin/activate`
- UV handles dependency installation and environment isolation
- All Python execution MUST go through `uv run`

---

## 2. API Framework

### FastAPI
- Used for all HTTP APIs
- Must use ASGI-compatible patterns
- Dependency injection should use FastAPI's `Depends`
- Run with: `doppler run -- uv run uvicorn app.main:app --reload`

**Forbidden:**
- No Flask, Django, or custom ASGI frameworks

---

## 3. Inference & Model Execution

### vLLM
- Used for local LLM inference
- Must be run as a separate service (Docker)
- Accessed via OpenAI-compatible API

**Forbidden:**
- Do not implement raw Hugging Face inference loops
- Do not load models directly inside the gateway process

---

## 4. Provider Integrations

### OpenAI API
- Used as an external inference provider
- API keys loaded from Doppler
- Accessed via HTTPS only

**Forbidden:**
- No hardcoded secrets
- No direct SDK coupling outside adapter layer

---

## 5. Authentication & Access Control

### Pre-generated API Keys
- Used for client authentication
- Keys are mapped to quotas and rate limits
- Keys are passed via HTTP headers

**Forbidden:**
- No OAuth
- No user accounts or identity providers

---

## 6. Quotas, Rate Limiting & State

### Redis (Docker)
Used for:
- API key validation
- Rate limiting
- Token usage tracking
- Quota enforcement

**Important:**
- Redis MUST be treated as ephemeral state
- No long-term persistence requirements

**Forbidden:**
- No PostgreSQL or other relational databases

---

## 7. Observability (Required)

### Metrics - Prometheus
- Exposed via `/metrics`
- Used for:
  - Request latency
  - Error rates
  - Provider health
  - Token usage

### Dashboards - Grafana
- Used to visualize Prometheus metrics
- No custom dashboard frameworks

### Tracing - OpenTelemetry
- Used for distributed tracing
- Traces must propagate across:
  - Gateway
  - Provider adapters
  - External API calls

**Forbidden:**
- No proprietary APMs (Datadog, New Relic, etc.)

---

## 8. Secrets Management

### Doppler
- All secrets (API keys, tokens) MUST be sourced from Doppler
- Use `doppler run --` prefix for commands requiring secrets
- Pattern: `doppler run -- uv run <command>`

**Forbidden:**
- No `.env` files committed to the repository
- No plaintext secrets
- No environment variables defined directly in code

---

## 9. Dependency Management & Code Quality

### UV (Package Manager)
- Used for Python virtual environments and dependency resolution
- Lockfiles (`uv.lock`) must be committed
- ALL Python commands MUST use `uv run` prefix
- UV automatically manages virtual environment

**Commands:**
- Install dependencies: `uv sync`
- Add package: `uv add <package>`
- Run Python: `uv run python script.py`
- Run tests: `doppler run -- uv run pytest`

### Ruff (Linting & Formatting)
- **ONLY tool for linting AND formatting**
- Configured in `pyproject.toml`
- Target: Python 3.13, line length 88

**Commands:**
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Fix issues: `uv run ruff check --fix .`

**Forbidden:**
- No Black (use Ruff for formatting)
- No Flake8 (use Ruff for linting)
- No pipenv
- No poetry

---

## 10. Containerization & Deployment

### Docker
- All services must be containerized
- Multi-stage builds preferred
- Docker Compose for production examples/dev testing workflow

### Kubernetes
- Used for orchestration
- Include:
  - Resource limits
  - Readiness/liveness probes
  - Horizontal Pod Autoscaling (HPA)

---

## 11. CI/CD & Repo Management

### GitHub Actions
Used for:
- Linting (Ruff)
- Tests (pytest)
- Container builds
- Image publishing

### Graphite
- Used for PR stacking and incremental changes
- See commit.md for workflow rules

**Forbidden:**
- No alternative CI systems

---

## 12. Testing, Load & Failure Injection

### pytest
- Run with: `doppler run -- uv run pytest`
- Coverage: `doppler run -- uv run pytest --cov=app`
- Configuration in `pyproject.toml`

### k6
- Used for load and stress testing
- Focus on latency, throughput, and error rates

### Chaos Mesh
- Used for failure injection in Kubernetes
- Simulate:
  - Pod crashes
  - Network latency
  - Provider outages

**Forbidden:**
- No custom chaos tooling

---

## 13. Architectural Constraints

### Gateway Requirements
The gateway MUST be:
- Stateless
- Horizontally scalable
- Provider-agnostic

### Provider Integration
- All inference providers MUST be accessed via adapters
- No provider-specific logic in request handlers

---

## 14. Scope Control (Hard Rules)

The following are explicitly out of scope:
- End-user accounts
- OAuth or SSO
- Model training or fine-tuning
- Persistent conversation history
- UI or frontend applications

---

## 15. Design Philosophy

- Prefer clarity over cleverness
- Prefer explicit configuration over magic
- Prefer failure containment over throughput
- Prefer observability over raw performance

---

## Enforcement Rule

If a proposed change violates this document:
- The change MUST be rejected
- OR the document MUST be updated first (ask the user for permission)

---

## Common Command Patterns

### Development
```bash
# Start services
make dev

# Run tests
doppler run -- uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .
```

### With Secrets (Doppler)
```bash
# Run app
doppler run -- uv run uvicorn app.main:app --reload

# Run tests with API keys
doppler run -- uv run pytest -v

# Run specific test
doppler run -- uv run pytest tests/test_providers.py
```

### Without Secrets
```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy app
```
