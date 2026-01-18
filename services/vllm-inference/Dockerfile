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
CMD sh -c "python -m vllm.entrypoints.openai.api_server \
    --host \${VLLM_HOST:-0.0.0.0} \
    --port \${VLLM_PORT:-8080} \
    --model \${VLLM_MODEL:?VLLM_MODEL is required} \
    --tensor-parallel-size \${VLLM_TENSOR_PARALLEL_SIZE:-1} \
    \$([ \"\${VLLM_ENABLE_GPU}\" = \"false\" ] && echo \"--device cpu\" || echo \"\") \
    \$([ -n \"\${VLLM_GPU_MEMORY_UTILIZATION}\" ] && [ \"\${VLLM_ENABLE_GPU}\" != \"false\" ] && echo \"--gpu-memory-utilization \${VLLM_GPU_MEMORY_UTILIZATION}\") \
    \$([ -n \"\${VLLM_MAX_MODEL_LEN}\" ] && echo \"--max-model-len \${VLLM_MAX_MODEL_LEN}\") \
    \$([ \"\${VLLM_TRUST_REMOTE_CODE}\" = \"true\" ] && echo \"--trust-remote-code\")"
