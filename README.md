# SRE Inference Gateway

OpenAI-compatible API gateway with provider abstraction, built with Python 3.13+ and FastAPI.

## Features

- **OpenAI-Compatible API**: Single `/v1/chat/completions` endpoint
- **Provider Abstraction**: Support for multiple inference providers (OpenAI, vLLM)
- **Weighted Routing**: Configurable load balancing between providers
- **Deterministic Pinning**: Route requests to specific providers via headers
- **Request Tracing**: End-to-end request ID propagation with OpenTelemetry
- **Health Checks**: Operational readiness monitoring
- **Observability**: Prometheus metrics and distributed tracing

## Quick Start

### Development

1. **Install dependencies**:
   ```bash
   uv sync --extra dev
   ```

2. **Run tests**:
   ```bash
   uv run pytest tests/ -v
   ```

3. **Start development server**:
   ```bash
   python run_dev.py
   ```

4. **Test the API**:
   ```bash
   python test_gateway.py
   ```

### Docker

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Access services**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Metrics: http://localhost:9090/metrics
   - Prometheus: http://localhost:9091
   - Grafana: http://localhost:3000 (admin/admin)

## API Usage

### Basic Chat Completion

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello, world!"}
    ]
  }'
```

### Provider Routing

```bash
# Route to specific provider
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Provider-Priority: mock_openai" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello from OpenAI!"}
    ]
  }'
```

### Request ID Tracking

```bash
# Custom request ID
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-custom-request-123" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Track this request"}
    ]
  }'
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client        │───▶│  FastAPI Gateway │───▶│  Provider       │
│                 │    │                  │    │  (OpenAI/vLLM)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Observability   │
                       │  (Metrics/Traces)│
                       └──────────────────┘
```

## Configuration

The gateway uses Pydantic Settings for configuration:

- `DEBUG`: Enable debug mode (default: false)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `PORT`: Port to bind to (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `PROVIDER_WEIGHTS`: JSON object with provider weights

## Health Checks

- **Health**: `GET /v1/health` - Basic service health
- **Readiness**: `GET /v1/ready` - Service readiness with provider status

## Observability

- **Metrics**: Prometheus metrics on port 9090
- **Tracing**: OpenTelemetry distributed tracing
- **Logging**: Structured JSON logging

## Development

### Project Structure

```
app/
├── api/              # FastAPI routes and dependencies
├── config/           # Configuration management
├── observability/    # Metrics and tracing
├── providers/        # Provider abstractions
└── router/           # Request routing logic
tests/                # Test suite
```

### Tech Stack

- **Python 3.13+** with uv for dependency management
- **FastAPI** for HTTP API framework
- **OpenTelemetry** for distributed tracing
- **Prometheus** for metrics collection
- **Redis** for state management (future)
- **Docker** for containerization

## License

See [LICENSE](LICENSE) file.

Reliable and observable multi-provider LLM inference, built with SRE and platform engineering principles.

## About this project

This project demonstrates how to operate AI inference **reliably, safely, and cost-consciously** in production-like environments.

The focus is **not model quality**.  
Instead, it explores the operational challenges that most often cause real-world AI incidents:

- Provider outages
- Latency spikes
- Cost overruns
- Uncontrolled retries
- Poor observability

The gateway exposes a **single OpenAI-compatible API**, while routing requests across multiple inference backends such as **OpenAI** and **local vLLM**. All reliability, policy, and cost controls are centralized in the gateway.

⚠️ **Not production-ready** — this is a learning and portfolio project designed to showcase architecture, trade-offs, and SRE thinking.

## Key Features

- **Single OpenAI-style API**
  - Clients integrate once, regardless of backend provider

- **Multi-provider routing**
  - OpenAI (external)
  - vLLM (local or remote, OpenAI-compatible)

- **Reliability & resilience**
  - Weighted routing and failover
  - Timeouts and retries
  - Circuit breaking
  - Backpressure and load shedding
  - Chaos injection for failure testing

- **Cost control & quotas**
  - API key–based access
  - Redis-backed rate limits and token usage tracking
  - Budget enforcement before inference execution

- **Observability-first design**
  - Structured logs with request IDs
  - Prometheus metrics (latency, errors, usage)
  - Distributed tracing with OpenTelemetry

- **Minimal safety guardrails**
  - Response length limits
  - Banned-word filtering
  - Demonstrates operational safety awareness without overreach

- **Platform-ready**
  - Containerized with Docker
  - Kubernetes manifests (HPA, resource limits)
  - Hot-reloadable configuration

## Architecture Overview

At a high level:

- Clients send requests to a **single public API**
- The gateway enforces authentication, quotas, routing, and policy
- Requests are routed to OpenAI or vLLM
- Responses flow back through the gateway for accounting and observability

All reliability and control logic lives **inside the gateway**.  
Providers remain simple execution engines.

See:
- `docs/ARCHITECTURE.md` – diagrams and request lifecycle
- `docs/DESIGN.md` – goals, non-goals, and trade-offs

## What This Project Demonstrates

- SRE and platform engineering applied to AI workloads
- Designing control planes for inference systems
- Failure containment and blast-radius reduction
- Cost-aware AI system design
- Operational observability and incident analysis

## Non-goals

To keep scope realistic, this project intentionally does **not** implement:

- End-user accounts or OAuth
- Fine-tuning or model training
- Production-grade multi-tenancy
- Persistent caching or data storage

These are discussed as future considerations in `DESIGN.md`.

## Getting Started (Demo)

1. Run Redis (for quotas and rate limits)
2. Start the inference gateway
3. Start vLLM (optional local provider)
4. Send requests to `/v1/chat/completions`
5. Observe metrics and logs

## Documentation

- `DESIGN.md` – architectural decisions and trade-offs
- `ARCHITECTURE.md` – request and deployment diagrams
- `INCIDENT.md` – simulated outage and postmortem
- 
## License

MIT License - see [LICENSE](LICENSE) file for details.
## Author

Femi - [GitHub](https://github.com/crypticseeds)
