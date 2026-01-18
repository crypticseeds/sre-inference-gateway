# vLLM Docker Compose Setup Guide

## Overview

The SRE Inference Gateway now includes a fully integrated vLLM service in Docker Compose, enabling local LLM inference with Hugging Face model support.

## Quick Start

### 1. Environment Configuration

Copy the environment template and configure your settings:

```bash
cp .env.example .env
```

Key vLLM environment variables:

```bash
# vLLM Configuration
VLLM_MODEL=google/gemma-3-270m          # Hugging Face model to load
VLLM_PORT=8080                          # vLLM service port
VLLM_HOST=0.0.0.0                       # Host binding
VLLM_MAX_MODEL_LEN=2048                 # Context window size (GPU) / 1024 (CPU)
VLLM_GPU_MEMORY_UTILIZATION=0.7         # GPU memory usage (0.0-1.0)
VLLM_TENSOR_PARALLEL_SIZE=1             # Multi-GPU parallelism
VLLM_TRUST_REMOTE_CODE=false            # Trust remote code in models
VLLM_ENABLE_GPU=true                    # Enable GPU acceleration

# vLLM CPU-specific optimizations (when VLLM_ENABLE_GPU=false)
VLLM_CPU_KVCACHE_SPACE=4                # KV cache space in GB
VLLM_CPU_OMP_THREADS_BIND=auto          # CPU thread binding strategy
VLLM_BLOCK_SIZE=32                      # Memory block size (multiples of 32)
VLLM_MAX_NUM_BATCHED_TOKENS=2048        # Batch size for throughput
VLLM_MAX_NUM_SEQS=64                    # Concurrent sequences

# Hugging Face Token (required for gated models)
HUGGING_FACE_HUB_TOKEN=your_token_here
```

### 2. Choose Your Configuration

The Docker Compose files provide two optimized configurations:

**Option 1: GPU-accelerated (Recommended)**
- Best performance for inference
- Requires NVIDIA GPU with Docker GPU support
- Optimized resource allocation: 2-3 CPUs, 3-4GB RAM
- GPU memory utilization: 70% (conservative for stability)

**Option 2: CPU-only**
- Compatible with any system
- Lower performance but no GPU required
- Optimized resource allocation: 2-3 CPUs, 2-3GB RAM
- Reduced context window for better CPU performance

### 3. Enable Your Preferred Configuration

Edit the Docker Compose files to uncomment your preferred option:

**For GPU acceleration:**
```bash
# In infra/docker-compose.yml and infra/docker-compose.prod.yml
# Comment out the CPU-only section and uncomment the GPU section
```

**For CPU-only:**
```bash
# In infra/docker-compose.yml and infra/docker-compose.prod.yml
# Keep the CPU-only section uncommented (default)
```

### 4. Start Services

**Development:**
```bash
cd infra
docker-compose up -d
```

**Production:**
```bash
cd infra
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. Verify vLLM Service

Check service health:
```bash
curl http://localhost:8080/health
```

Test inference:
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-3-270m",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

## Architecture

### Service Integration

- **Gateway Service**: Port 8000 (main API)
- **vLLM Service**: Port 8080 (inference)
- **Redis**: Port 6379 (state management)
- **Prometheus**: Port 9091 (metrics)
- **Grafana**: Port 3000 (dashboards)

### Docker Network

All services communicate via Docker's internal network:
- Gateway connects to vLLM at `http://vllm:8080/v1`
- No external network access required between services

### Persistent Storage

- **vLLM Cache**: `/root/.cache/huggingface` mounted as `vllm_cache` volume
- **Model Persistence**: Downloaded models persist between container restarts
- **Redis Data**: Persistent storage for rate limiting and quotas

## Configuration

### Model Selection

The vLLM service supports any Hugging Face model compatible with vLLM:

```bash
# Small models (good for testing)
VLLM_MODEL=google/gemma-3-270m
VLLM_MODEL=microsoft/DialoGPT-small

# Larger models (require more resources)
VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf
VLLM_MODEL=mistralai/Mistral-7B-Instruct-v0.1
```

### Resource Limits

**Development Environment:**

*GPU Configuration:*
- CPU: 2 cores limit
- Memory: 3GB limit  
- GPU: 1 NVIDIA GPU reserved
- GPU Memory: 70% utilization (conservative)
- Context Window: 2048 tokens

*CPU-only Configuration:*
- CPU: 2 cores limit, 1 core reserved
- Memory: 2GB limit, 1GB reserved
- Context Window: 1024 tokens (optimized for CPU)

**Production Environment:**

*GPU Configuration:*
- CPU: 3 cores limit, 2 cores reserved
- Memory: 4GB limit, 2GB reserved
- GPU: 1 NVIDIA GPU reserved
- GPU Memory: 70% utilization
- Context Window: 2048 tokens

*CPU-only Configuration:*
- CPU: 3 cores limit, 2 cores reserved  
- Memory: 3GB limit, 1.5GB reserved
- Context Window: 1024 tokens

### Model-Specific Resource Optimization

The configurations are optimized for small models like `google/gemma-3-270m`:

**Why These Limits?**
- Gemma 270M requires ~1GB RAM for model weights
- Additional ~1-2GB for inference overhead and context
- Conservative GPU memory usage prevents OOM errors
- CPU limits ensure other services have resources
- Reduced context window for CPU improves performance

### GPU Support

**Enable GPU (Recommended for Production):**
1. Uncomment the GPU configuration section in Docker Compose files
2. Comment out the CPU-only section
3. Ensure NVIDIA Docker runtime is installed
4. Set environment variables:
```bash
VLLM_ENABLE_GPU=true
VLLM_GPU_MEMORY_UTILIZATION=0.7  # Conservative 70%
VLLM_MAX_MODEL_LEN=2048
```

**CPU-only Mode (Default):**
1. Keep the CPU-only section uncommented (default)
2. Comment out the GPU configuration section
3. Set environment variables:
```bash
VLLM_ENABLE_GPU=false
VLLM_MAX_MODEL_LEN=1024  # Reduced for better CPU performance
```

**Switching Between Modes:**
```bash
# Stop services
docker-compose down

# Edit docker-compose.yml to switch configurations
# Uncomment desired section, comment out the other

# Restart services
docker-compose up -d
```

## Provider Configuration

The gateway automatically detects the vLLM service. To enable it:

1. Edit `config.yaml`:
```yaml
providers:
  - name: "vllm"
    type: "vllm"
    weight: 0.5
    enabled: true  # Change from false to true
    base_url: "http://vllm:8080/v1"  # Internal Docker network
```

2. Restart the gateway service:
```bash
docker-compose restart gateway
```

## Troubleshooting

### Common Issues

**vLLM service fails to start:**
- Check GPU availability: `nvidia-smi`
- Verify model name is correct
- Check Hugging Face token for gated models

**Gateway can't connect to vLLM:**
- Verify vLLM health: `curl http://localhost:8080/health`
- Check Docker network connectivity
- Ensure vLLM service is running: `docker-compose ps`

**Model download fails:**
- Verify Hugging Face token
- Check internet connectivity
- Ensure sufficient disk space for model cache

### Logs

View service logs:
```bash
# All services
docker-compose logs -f

# vLLM service only
docker-compose logs -f vllm

# Gateway service only
docker-compose logs -f gateway
```

### Health Checks

All services include health checks:
- **Gateway**: `http://localhost:8000/health`
- **vLLM**: `http://localhost:8080/health`
- **Redis**: Internal health check via Redis CLI

## Performance Tuning

### Resource Optimization by Model Size

**Small Models (< 1B parameters):**
```bash
# Examples: google/gemma-3-270m, microsoft/DialoGPT-small
VLLM_MODEL=google/gemma-3-270m
VLLM_MAX_MODEL_LEN=1024          # CPU: 1024, GPU: 2048
# Use CPU-only configuration for cost efficiency
```

**Medium Models (1B-7B parameters):**
```bash
# Examples: meta-llama/Llama-2-7b-chat-hf
VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf
VLLM_MAX_MODEL_LEN=4096
# Requires GPU configuration with increased memory limits
```

### GPU Memory Tuning

Conservative GPU memory utilization prevents OOM errors:
```bash
VLLM_GPU_MEMORY_UTILIZATION=0.7  # 70% - recommended for stability
VLLM_GPU_MEMORY_UTILIZATION=0.8  # 80% - higher utilization, more risk
VLLM_GPU_MEMORY_UTILIZATION=0.9  # 90% - maximum, may cause OOM
```

### CPU Performance Optimization

For CPU-only inference, vLLM provides several optimization parameters:

**KV Cache Management:**
```bash
VLLM_CPU_KVCACHE_SPACE=4                # 4GB for development
VLLM_CPU_KVCACHE_SPACE=6                # 6GB for production
# Larger values support more concurrent requests and longer contexts
# Must fit within NUMA node memory capacity
```

**Thread Binding Optimization:**
```bash
VLLM_CPU_OMP_THREADS_BIND=auto          # Automatic NUMA-aware binding (recommended)
VLLM_CPU_OMP_THREADS_BIND=0-7           # Bind to specific CPU cores
VLLM_CPU_OMP_THREADS_BIND=nobind        # Disable binding (use OMP_NUM_THREADS)
```

**Batch Processing Optimization:**
```bash
VLLM_BLOCK_SIZE=32                      # Use multiples of 32 (32, 64, 96, 128)
VLLM_MAX_NUM_BATCHED_TOKENS=2048        # Balance throughput vs latency
VLLM_MAX_NUM_SEQS=64                    # Concurrent request handling
```

**Performance Tuning Guidelines:**
- **Higher throughput**: Increase `VLLM_MAX_NUM_BATCHED_TOKENS` and `VLLM_MAX_NUM_SEQS`
- **Lower latency**: Decrease batch sizes and sequence limits
- **Memory optimization**: Adjust `VLLM_CPU_KVCACHE_SPACE` based on available RAM
- **NUMA systems**: Use `auto` thread binding for optimal performance

### Context Window Optimization

Balance between capability and resource usage:
```bash
# Small context - faster, less memory
VLLM_MAX_MODEL_LEN=512

# Medium context - balanced (recommended for CPU)
VLLM_MAX_MODEL_LEN=1024

# Large context - slower, more memory (GPU recommended)
VLLM_MAX_MODEL_LEN=2048

# Very large context - GPU required
VLLM_MAX_MODEL_LEN=4096
```

## Resource Optimization Philosophy

### Why Optimized Resource Limits?

The configurations are specifically tuned for efficient resource usage:

**Memory Efficiency:**
- Gemma 270M model: ~1GB for weights + ~1-2GB inference overhead
- Total requirement: ~2-3GB (not 8GB!)
- Leaves resources available for other services and applications

**CPU Efficiency:**
- 2-3 CPU cores sufficient for small model inference
- Prevents resource starvation of other containers
- Allows multiple services to coexist on same host

**GPU Efficiency:**
- 70% GPU memory utilization prevents OOM crashes
- Conservative approach ensures stability under load
- Allows GPU sharing with other workloads if needed

**Context Window Optimization:**
- CPU: 1024 tokens - optimal for CPU performance
- GPU: 2048 tokens - balanced capability vs. resources
- Prevents excessive memory usage for typical use cases

### Resource Scaling Guidelines

**When to Increase Resources:**
- Using larger models (> 1B parameters)
- High concurrent request volume
- Longer context requirements
- Production workloads with strict SLAs

**When Current Limits Are Sufficient:**
- Development and testing
- Small to medium models (< 1B parameters)
- Low to moderate request volume
- Shared development environments

**Resource Monitoring:**
```bash
# Monitor container resource usage
docker stats

# Check vLLM service logs for memory warnings
docker-compose logs vllm
```

## Security

### Docker Security for vLLM CPU

When using CPU-only vLLM, certain NUMA optimizations may require additional Docker capabilities:

**For optimal CPU performance (optional):**
```bash
# Add to docker-compose.yml if you encounter NUMA warnings
services:
  vllm:
    cap_add:
      - SYS_NICE
    # Alternative: use --privileged=true (not recommended for production)
```

**Kubernetes Security Context:**
```yaml
# Add to vLLM pod spec for NUMA optimizations
securityContext:
  capabilities:
    add:
      - SYS_NICE
```

**Note:** These capabilities are only needed for advanced NUMA optimizations. The default configuration works without additional privileges.

### Token Management

- Store Hugging Face tokens in `.env` (not committed)
- Use Doppler for production secret management
- Rotate tokens regularly

### Network Security

- vLLM service only exposed on localhost by default
- Internal Docker network for service communication
- No external API keys required for vLLM

## Next Steps

1. **Enable Provider**: Update `config.yaml` to enable vLLM provider
2. **Test Integration**: Send requests through the gateway
3. **Monitor Performance**: Use Grafana dashboards for metrics
4. **Scale Resources**: Adjust GPU/CPU limits based on usage

For advanced configuration, see:
- [Provider Configuration](PROVIDERS.md)
- [Kubernetes Deployment](../infra/k8s/vllm-service.yaml)
- [Performance Monitoring](HEALTH_API.md)