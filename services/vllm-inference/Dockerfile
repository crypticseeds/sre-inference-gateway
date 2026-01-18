FROM vllm/vllm-openai:latest

# Set working directory
WORKDIR /app

# Create model cache directory with proper permissions
RUN mkdir -p /root/.cache/huggingface && \
    chmod 755 /root/.cache/huggingface

# Expose vLLM API port (will be set via environment variable)
EXPOSE ${VLLM_PORT:-8080}

# Start vLLM server with OpenAI-compatible API
# All configuration is now environment-driven with no hardcoded defaults
CMD sh -c "vllm serve \
    \$([ \"\${VLLM_ENABLE_GPU}\" = \"false\" ] && echo \"--device cpu\") \
    \${VLLM_MODEL:?VLLM_MODEL is required} \
    --host \${VLLM_HOST:-0.0.0.0} \
    --port \${VLLM_PORT:-8080} \
    --tensor-parallel-size \${VLLM_TENSOR_PARALLEL_SIZE:-1} \
    \$([ -n \"\${VLLM_GPU_MEMORY_UTILIZATION}\" ] && [ \"\${VLLM_ENABLE_GPU}\" != \"false\" ] && echo \"--gpu-memory-utilization \${VLLM_GPU_MEMORY_UTILIZATION}\") \
    \$([ -n \"\${VLLM_MAX_MODEL_LEN}\" ] && echo \"--max-model-len \${VLLM_MAX_MODEL_LEN}\") \
    \$([ \"\${VLLM_TRUST_REMOTE_CODE}\" = \"true\" ] && echo \"--trust-remote-code\")"



# # Use Python base image for CPU-only vLLM
# FROM python:3.12-slim

# # Set working directory
# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     git \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# # Install uv for fast package management
# RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# ENV PATH="/root/.local/bin:$PATH"

# # Install vLLM CPU version from wheels
# RUN uv pip install --system --extra-index-url https://wheels.vllm.ai/cpu vllm

# # Create model cache directory with proper permissions
# RUN mkdir -p /root/.cache/huggingface && \
#     chmod 755 /root/.cache/huggingface

# # Expose vLLM API port (will be set via environment variable)
# EXPOSE ${VLLM_PORT:-8080}

# # Start vLLM server with OpenAI-compatible API
# # All configuration is now environment-driven with no hardcoded defaults
# CMD sh -c "vllm serve \
#     --device cpu \
#     \${VLLM_MODEL:?VLLM_MODEL is required} \
#     --host \${VLLM_HOST:-0.0.0.0} \
#     --port \${VLLM_PORT:-8080} \
#     --dtype bfloat16 \
#     \$([ -n \"\${VLLM_MAX_MODEL_LEN}\" ] && echo \"--max-model-len \${VLLM_MAX_MODEL_LEN}\") \
#     \$([ \"\${VLLM_TRUST_REMOTE_CODE}\" = \"true\" ] && echo \"--trust-remote-code\")"
