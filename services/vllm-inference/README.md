# vLLM Local Inference Service

OpenAI-compatible local inference service powered by vLLM.

## Overview

This service provides local LLM inference using vLLM with an OpenAI-compatible API. It can be used as a drop-in replacement for OpenAI's API for supported models.

## Features

- OpenAI-compatible `/v1/chat/completions` endpoint
- GPU-accelerated inference with vLLM
- Model caching for faster startup
- Health check endpoint at `/health`
- Prometheus metrics support
- Kubernetes deployment with HPA

## Quick Start

### Docker Compose

```bash
# Start all services (from project root)
docker-compose up -d

# Start only vLLM service
docker-compose up -d vllm

# Check health
curl http://localhost:8080/health

# Test inference
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "facebook/opt-125m",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Kubernetes

```bash
# Deploy vLLM service
kubectl apply -f infra/k8s/vllm-service.yaml

# Check status
kubectl get pods -l app=vllm-inference
kubectl logs -l app=vllm-inference

# Port forward for testing
kubectl port-forward svc/vllm-inference 8080:8080
```

## Configuration

### Environment Variables

- `VLLM_MODEL`: Model to load (default: `facebook/opt-125m`)
- `VLLM_TENSOR_PARALLEL_SIZE`: Number of GPUs for tensor parallelism (default: `1`)
- `VLLM_GPU_MEMORY_UTILIZATION`: GPU memory utilization (default: `0.9`)
- `VLLM_MAX_MODEL_LEN`: Maximum sequence length (default: `2048`)
- `VLLM_TRUST_REMOTE_CODE`: Trust remote code in models (default: `false`)

### Supported Models

vLLM supports many popular models including:

- Llama 2 / Llama 3
- Mistral / Mixtral
- Phi-2 / Phi-3
- Qwen
- Gemma
- OPT (default for testing)

See [vLLM documentation](https://docs.vllm.ai/en/latest/models/supported_models.html) for full list.

## Gateway Integration

The vLLM service integrates with the Python gateway via the `VLLMProvider` adapter:

```python
from app.providers.vllm import VLLMProvider

# Initialize provider
provider = VLLMProvider(
    name="vllm",
    config={
        "base_url": "http://vllm-inference:8080",
        "timeout": 30.0
    }
)

# Use in gateway
response = await provider.chat_completion(request, request_id)
```

## Monitoring

### Health Check

```bash
curl http://localhost:8080/health
```

### Metrics

vLLM exposes Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8080/metrics
```

Key metrics:
- `vllm:num_requests_running` - Active requests
- `vllm:num_requests_waiting` - Queued requests
- `vllm:gpu_cache_usage_perc` - GPU cache utilization
- `vllm:time_to_first_token_seconds` - TTFT latency
- `vllm:time_per_output_token_seconds` - Token generation speed

## Resource Requirements

### Minimum (Testing)

- 1 GPU (8GB VRAM)
- 8GB RAM
- 2 CPU cores

### Production

- 1-2 GPUs (16GB+ VRAM each)
- 16GB RAM
- 4 CPU cores
- 50GB storage for model cache

## Troubleshooting

### Model Download Issues

Models are cached in `/root/.cache/huggingface`. Ensure:
- Sufficient disk space
- Network access to Hugging Face Hub
- Valid model name

### GPU Not Detected

Ensure:
- NVIDIA drivers installed
- `nvidia-docker2` installed
- GPU resources available in Kubernetes

### Out of Memory

Reduce:
- `VLLM_GPU_MEMORY_UTILIZATION` (try 0.8 or 0.7)
- `VLLM_MAX_MODEL_LEN` (reduce sequence length)
- Use smaller model

## Performance Tuning

### Tensor Parallelism

For multi-GPU setups:

```bash
VLLM_TENSOR_PARALLEL_SIZE=2  # Use 2 GPUs
```

### Batch Size

vLLM automatically batches requests. Monitor metrics to optimize.

### Model Selection

- Smaller models (OPT-125m, Phi-2): Fast, lower quality
- Medium models (Llama-7B, Mistral-7B): Balanced
- Large models (Llama-70B, Mixtral-8x7B): High quality, slower

## Security

- No authentication required by default (internal service)
- Use network policies in Kubernetes to restrict access
- Do not expose directly to internet
- Access via gateway with API key authentication
