FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Environment variables for vLLM configuration
ENV VLLM_HOST=0.0.0.0
ENV VLLM_PORT=8001
ENV VLLM_MODEL=facebook/opt-125m
ENV VLLM_TENSOR_PARALLEL_SIZE=1
ENV VLLM_GPU_MEMORY_UTILIZATION=0.9

# Create model cache directory
RUN mkdir -p /root/.cache/huggingface

# Expose vLLM API port
EXPOSE 8001

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD sh -c 'curl -fS --max-time 5 http://localhost:${VLLM_PORT:-8001}/health || exit 1'

# Start vLLM server with OpenAI-compatible API
CMD ["sh", "-c", "python -m vllm.entrypoints.openai.api_server \
    --host ${VLLM_HOST} \
    --port ${VLLM_PORT} \
    --model ${VLLM_MODEL} \
    --tensor-parallel-size ${VLLM_TENSOR_PARALLEL_SIZE} \
    --gpu-memory-utilization ${VLLM_GPU_MEMORY_UTILIZATION}"]
