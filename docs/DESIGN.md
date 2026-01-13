
## Purpose
This project demonstrates **SRE and platform engineering principles applied to AI inference**.

The focus is on:
- Reliability
- Cost control
- Safe operation
- Observability

not on model training or fine-tuning.

The project is intentionally scoped as a **portfolio-quality system**, not a production SaaS.

## Goals
- Expose a **single OpenAI-style API** for clients (`/v1/chat/completions`)
- Route requests to multiple inference backends /Support **multiple inference providers** behind that API
- Enforce **per-consumer quotas and rate limits**
- Apply **SRE reliability patterns** at the gateway layer
- Provide first-class observability and failure simulation

## Non-Goals (Explicit)
- User sign-up / authentication flows
- OAuth / JWT / SSO - pre generated api-keys for testing and simulation
- Billing, payments, or invoicing
- Model training or fine-tuning
- Full OpenAI API compatibility
- Prompt or response storage
- Frontend UI or dashboards

## Architecture Overview

The system is a **Python-based inference gateway** composed of the following layers:

### 1. API Layer
- FastAPI HTTP endpoints
- Request validation
- Extracts API keys
- OpenAI-compatible request schema
- Request ID generation and assignment
- Propagates context

### 2. Auth Layer (API Keys)
- Pre-generated API keys
- Each key maps to a logical “user”
- Keys identify the caller for:
  - Quotas
  - Rate limits
  - Observability attribution

No user registration or login is implemented.

### 3. Quota & Rate Limiting Layer
- Redis-backed counters
- Enforced per API key
- Supports:
  - Requests per minute
  - Tokens per minute / day
- Hard failure on exhaustion (`429` / `403`)

Redis is treated as **runtime state**, not a system of record.

### 4. Router / Orchestrator
All resilience logic lives here.

Responsibilities:
- Provider selection
- Weighted routing
- Deterministic pinning - simulate model preference selection & Crucial for incident reproduction
- Retries and timeouts
- Circuit breaking
- Backpressure and load shedding
- Chaos injection (fault simulation)
- Minimal operational guardrails - AI Safty

Providers are intentionally **thin and dumb**.

### 5. Provider Adapters
Adapters translate requests to provider-specific APIs.

Supported providers:
- OpenAI (external)
- vLLM (local, OpenAI-compatible)

Adapters:
- Do not retry
- Do not apply policy
- Do not enforce quotas

## Key Design Decisions

### Python + FastAPI
Chosen to:
- Optimize development speed
- Reduce boilerplate
- Maximize iteration with AI assistants
- Improve readability for reviewers

Architecture remains language-agnostic.

### Single public API
Clients integrate once.
All provider-specific differences are absorbed by the gateway.

### vLLM for Local Inference
Local inference is treated as **infrastructure**, not application logic.
vLLM provides:
- OpenAI-compatible API
- High-performance serving
- Reduced implementation complexity

### API Keys Instead of Full Auth
Pre-generated API keys allow:
- Per-user usage tracking
- Cost attribution
- Simple Postman-based testing

This avoids unnecessary identity complexity.

### Redis for Runtime State
Redis is used for:
- Rate limiting
- Token usage tracking
- Circuit breaker state

It is not used for persistence or analytics.

### Router-Centric Resilience
All failure-handling logic is centralized.
This avoids:
- Duplicated retries
- Conflicting policies
- Provider-specific behavior

## Observability
The system emits:
- Structured logs (JSON)
- Prometheus metrics
- Distributed traces (OpenTelemetry)

No prompts or responses are logged by default.

## Failure Modes Considered
- Provider outage
- Provider latency spikes
- Budget exhaustion
- Partial degradation
- Misconfiguration

Each is observable and recoverable.

## Known Limitations
- API keys are static
- Token estimation is approximate
- Chaos injection is non-production-safe
- Single-region deployment
## At 10× Scale (Out of Scope)
- Dynamic cost-aware routing
- Persistent usage analytics
- Multi-region routing
- Billing integration

