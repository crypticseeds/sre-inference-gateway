# Multi-stage Docker build for SRE Inference Gateway
FROM python:3.13-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies only. The project itself is not installed: the app runs
# from /app/app with `python -m app.main`, and building it as a package here
# would need README.md and the source in this stage.
RUN uv sync --frozen --no-dev --no-install-project

# Production stage
FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/

# Create non-root user with a fixed numeric UID/GID. Kubernetes runAsNonRoot
# can only verify a numeric USER, and the Helm chart sets runAsUser to match.
RUN groupadd -r -g 10001 gateway && useradd -r -u 10001 -g 10001 gateway
RUN chown -R 10001:10001 /app
USER 10001:10001

# Expose ports
EXPOSE 8000 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /app/.venv/bin/python -c "import httpx; httpx.get('http://localhost:8000/v1/health').raise_for_status()"

# Run application
CMD ["/app/.venv/bin/python", "-m", "app.main"]