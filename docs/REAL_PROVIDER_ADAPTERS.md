# Real Provider Adapters - DEV-93

This document provides an overview of the real provider adapter implementations for the SRE Inference Gateway.

## Overview

The gateway supports multiple inference providers through a unified adapter interface. This allows seamless switching between providers while maintaining a consistent API for clients.

## Supported Providers

### OpenAI Provider
- **Type**: External cloud provider
- **API**: OpenAI Chat Completions API
- **Features**: 
  - Streaming and non-streaming responses
  - Token usage tracking
  - Error handling with retries
  - Health check support

### vLLM Provider  
- **Type**: Local/self-hosted inference
- **API**: OpenAI-compatible API
- **Features**:
  - Local model inference
  - Streaming support
  - Custom model configurations
  - Health monitoring

## Architecture

All providers implement the `BaseProvider` interface which ensures:
- Consistent request/response handling
- Unified error handling
- Standardized health checks
- Metrics collection compatibility

## Configuration

Providers are configured via `config.yaml` and can be enabled/disabled dynamically through hot-reload.

## Related Issues

- DEV-93: Real Provider Adapters implementation
- DEV-77: vLLM Local Inference Service

## See Also

- [PROVIDERS.md](./PROVIDERS.md) - Detailed provider documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture overview
