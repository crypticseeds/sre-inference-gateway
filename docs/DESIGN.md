# Design scope

This gateway is a portfolio implementation of provider routing, resilience, SSE
passthrough, and observability. It is not a production SaaS.

Implemented behavior is documented in [ARCHITECTURE.md](ARCHITECTURE.md).
Operational judgment and rejected designs are recorded in
[design-decisions.md](design-decisions.md).

## Goals

- Expose one OpenAI-style chat completions endpoint.
- Route to OpenAI-compatible real and mock providers.
- Demonstrate weighted and preferred-provider routing.
- Fail over on provider 5xx responses before response headers.
- Expose circuit-breaker, retry, streaming, and golden-signal behavior.
- Support repeatable no-key local drills and benchmark integration.

## Non-goals and current omissions

- Authentication, API keys for gateway clients, and identity management.
- Quotas, rate limiting, billing, and token accounting.
- Redis-backed application state. Redis is present in local infrastructure but is
  not on the completion request path.
- Content moderation, output guardrails, or response-length enforcement.
- Backpressure, admission control, and load shedding.
- General chaos injection. The only runtime failure control is the env-gated
  mock-provider fail/restore drill.
- Full OpenAI API compatibility.
- Prompt or response persistence.
- Mid-stream provider switchover.
- Multi-region operation or persistent circuit-breaker state.

Provider adapters translate requests and contain provider-specific error and
retry behavior. Gateway-level retries and circuit breaking wrap those adapters,
so resilience is not exclusively router-owned.
