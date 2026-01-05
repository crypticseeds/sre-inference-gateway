# sre-inference-gateway

> Reliable and observable multi-provider LLM inference for experimentation and learning.

## About this project
This project demonstrates how to operate AI inference **reliably and safely**. The focus is **not model quality**, but on **reliability, cost-awareness, and controlled rollout**—the areas that most often cause incidents in real-world AI systems. It’s designed as a **portfolio project** to showcase SRE-inspired patterns for multi-provider inference, including retries, circuit breaking, weighted routing, chaos injection, and observability with Prometheus and OpenTelemetry.

⚠️ **Not production-ready** — intended to illustrate architecture, operational trade-offs, and reliability engineering principles.

## Key Features
- Single OpenAI-style API with multiple provider support (OpenAI, local Hugging Face)
- Router with weighted routing, failover, and deterministic request pinning
- Resilience patterns: retries, circuit breakers, chaos injection
- Observability: request tracing, Prometheus metrics, structured logs
- Hot-reloadable configuration and Kubernetes-ready deployment

## Learning Outcomes / Recruiter Signals
- Multi-provider inference gateway design
- Go-based microservices and concurrency patterns
- Reliability engineering (SRE) for AI workloads
- Observability and monitoring best practices
- Safe experimentation and failure testing
