---
trigger: always_on
---


Tech Stack Rules (Authoritative)

Purpose

This document defines the authoritative technology stack for this repository.

All generated code, configuration, and documentation MUST adhere to these rules.
Deviations require explicit justification in comments or documentation.

This project is Python-first.



1. Language & Runtime

- Python 3.13+

  - Gateway and all backend logic MUST be written in Python
  - No Go, Node.js, Rust, or Java implementations

- Do not introduce additional backend languages



2. API Framework

- FastAPI

  - Used for all HTTP APIs
  - Must use ASGI-compatible patterns
  - Dependency injection should use FastAPI’s `Depends`

- No Flask, Django, or custom ASGI frameworks



3. Inference & Model Execution

- vLLM

  - Used for local LLM inference
  - Must be run as a separate service (Docker)
  - Accessed via OpenAI-compatible API

- Do not implement raw Hugging Face inference loops

- Do not load models directly inside the gateway process



4. Provider Integrations

- OpenAI API

  - Used as an external inference provider
  - API keys loaded from Doppler
  - Accessed via HTTPS only

- No hardcoded secrets

- No direct SDK coupling outside adapter layer



5. Authentication & Access Control

- Pre-generated API keys

  - Used for client authentication
  - Keys are mapped to quotas and rate limits
  - Keys are passed via HTTP headers

- No OAuth

- No user accounts or identity providers



6. Quotas, Rate Limiting & State

- Redis (Docker)

  - Used for:

    - API key validation
    - Rate limiting
    - Token usage tracking
    - Quota enforcement

- Redis MUST be treated as ephemeral state

- No long-term persistence requirements

- No PostgreSQL or other relational databases



7. Observability (Required)

Metrics

- Prometheus

  - Exposed via `/metrics`
  - Used for:

    - Request latency
    - Error rates
    - Provider health
    - Token usage

Dashboards

- Grafana

  - Used to visualize Prometheus metrics
  - No custom dashboard frameworks

Tracing

- OpenTelemetry

  - Used for distributed tracing
  - Traces must propagate across:

    - Gateway
    - Provider adapters
    - External API calls

- No proprietary APMs (Datadog, New Relic, etc.)



8. Secrets Management

- Doppler

  - All secrets (API keys, tokens) MUST be sourced from Doppler
  - No `.env` files committed to the repository

- No plaintext secrets

- No environment variables defined directly in code



9. Dependency Management

- uv

  - Used for Python virtual environments and dependency resolution
  - Lockfiles must be committed
  - Ruff for formatting and linting

- No pipenv

- No poetry



10. Containerization & Deployment

- Docker

  - All services must be containerized
  - Multi-stage builds preferred
  - Docker Compose for production examples/dev testing workflow


- Kubernetes

  - Used for orchestration
  - Include:

    - Resource limits
    - Readiness/liveness probes
    - Horizontal Pod Autoscaling (HPA)



11. CI/CD & Repo Management

- GitHub Actions

  - Used for:

    - Linting
    - Tests
    - Container builds
    - Image publishing

- Graphite

  - Used for PR stacking and incremental changes

- No alternative CI systems



12. Testing, Load & Failure Injection

- k6

  - Used for load and stress testing
  - Focus on latency, throughput, and error rates

- Chaos Mesh

  - Used for failure injection in Kubernetes
  - Simulate:

    - Pod crashes
    - Network latency
    - Provider outages

- No custom chaos tooling



13. Architectural Constraints

- Gateway MUST be:

  - Stateless
  - Horizontally scalable
  - Provider-agnostic

- All inference providers MUST be accessed via adapters

- No provider-specific logic in request handlers



14. Scope Control (Hard Rules)

The following are explicitly out of scope:

- End-user accounts
- OAuth or SSO
- Model training or fine-tuning
- Persistent conversation history
- UI or frontend applications



15. Design Philosophy

- Prefer clarity over cleverness
- Prefer explicit configuration over magic
- Prefer failure containment over throughput
- Prefer observability over raw performance



Enforcement Rule

If a proposed change violates this document:

- The change MUST be rejected
- OR the document MUST be updated first, ask the user for permission
