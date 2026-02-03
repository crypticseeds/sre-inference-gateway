# vLLM CPU Limitations and Requirements

## Current Status

The vLLM provider adapter code is fully implemented and tested. However, running the actual vLLM inference service on CPU has significant limitations.

## Issues Encountered

### 1. Docker Image Compatibility
- The official `vllm/vllm-openai:latest` image is GPU-only
- It fails with: `RuntimeError: Failed to infer device type` when no GPU is present
- The image tries to load CUDA libraries (`libcuda.so.1`) which don't exist in CPU-only environments

### 2. CPU Installation Requirements
- vLLM CPU support requires installing from CPU-specific wheels: `https://wheels.vllm.ai/cpu`
- The installation is very large (>20GB of dependencies including torch, CUDA libraries, etc.)
- Building from source requires significant disk space and time

### 3. Resource Requirements
According to vLLM documentation:
- CPU inference requires substantial memory (recommended: 32GB+ RAM)
- Model loading alone can take several GB
- Performance is significantly slower than GPU (10-100x slower)
- Recommended to use smaller models (< 1B parameters) for CPU

## Recommended Solutions

### Option 1: Use Mock Provider (Current)
For development and testing without actual inference:
```yaml
# config.yaml
providers:
  mock_vllm:
    type: mock
    enabled: true
    base_url: "http://localhost:8080/v1"
```

### Option 2: Use GPU-Enabled System
If you have access to a GPU system:
```bash
# Use the official GPU image
docker run --runtime nvidia --gpus all \
    -p 8080:8080 \
    vllm/vllm-openai:latest \
    --model google/gemma-2-2b-it
```

### Option 3: Use External vLLM Service
Point to a remote vLLM instance:
```yaml
# config.yaml
providers:
  vllm:
    type: vllm
    enabled: true
    base_url: "https://your-vllm-service.com/v1"
```

### Option 4: Build CPU Image (Advanced)
If you need CPU inference and have sufficient resources:

1. Ensure you have at least 30GB free disk space
2. Use the CPU-specific Dockerfile:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install vLLM CPU version
RUN uv pip install --system --extra-index-url https://wheels.vllm.ai/cpu vllm

# Create cache directory
RUN mkdir -p /root/.cache/huggingface

EXPOSE 8080

CMD vllm serve --device cpu \
    ${VLLM_MODEL} \
    --host 0.0.0.0 \
    --port 8080 \
    --dtype bfloat16
```

3. Build with sufficient resources:
```bash
docker build -t vllm-cpu -f services/vllm-inference/Dockerfile.cpu .
```

4. Run with a small model:
```bash
doppler run -- docker-compose up vllm
# With VLLM_MODEL=google/gemma-2-2b-it or smaller
```

## Testing Without vLLM Service

The vLLM provider adapter can be tested without a running service:

```bash
# Run unit tests (mocked)
doppler run -- uv run pytest tests/test_vllm_provider.py -v

# Test with mock provider
doppler run -- uv run pytest tests/test_providers.py -v -k mock
```

## Production Recommendations

For production use:
1. **Use GPU**: vLLM is designed for GPU inference
2. **External Service**: Use managed vLLM services (e.g., Anyscale, Modal, RunPod)
3. **Alternative**: Consider lighter inference engines for CPU (e.g., llama.cpp, ONNX Runtime)

## References

- [vLLM CPU Installation Guide](https://docs.vllm.ai/en/latest/getting_started/installation/cpu/)
- [vLLM Docker Documentation](https://docs.vllm.ai/en/latest/deployment/docker/)
- [Supported Models on CPU](https://docs.vllm.ai/en/latest/models/hardware_supported_models/cpu/)
