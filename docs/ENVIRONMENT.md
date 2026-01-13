# Environment Configuration

This document describes the environment variables used by the SRE Inference Gateway.

## Required Environment Variables

### Production Deployment

The following environment variables **MUST** be set for production deployments:

```bash
# Redis Authentication
REDIS_PASSWORD=your_secure_redis_password_here

# Grafana Admin Access
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_admin_password_here
```

## Optional Environment Variables

### Application Settings

```bash
# Application Configuration
DEBUG=false                    # Enable debug mode (default: false)
LOG_LEVEL=INFO                # Logging level (default: INFO)
HOST=0.0.0.0                  # Host to bind to (default: 0.0.0.0)
PORT=8000                     # Port to bind to (default: 8000)

# Metrics Configuration
METRICS_PORT=9090             # Prometheus metrics port (default: 9090)
                              # Note: Metrics are served via /v1/metrics on main port
```

### Request Processing

```bash
MAX_REQUEST_SIZE=1048576      # Maximum request size in bytes (default: 1MB)
REQUEST_TIMEOUT=30.0          # Request timeout in seconds (default: 30.0)
HEALTH_CHECK_INTERVAL=30.0    # Health check interval (default: 30.0)
```

### Provider Configuration

```bash
# Provider weights as JSON (default: equal weights for mock providers)
PROVIDER_WEIGHTS='{"mock_openai": 0.5, "mock_vllm": 0.5}'
```

## Deployment Configurations

### Development

For local development, copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
# Edit .env with your local settings
```

### Production with Docker Compose

Use environment variable substitution:

```bash
# Set required variables
export REDIS_PASSWORD="your_secure_password"
export GRAFANA_ADMIN_PASSWORD="your_secure_grafana_password"

# Optional: Override defaults
export DEBUG=false
export LOG_LEVEL=WARN

# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

Use Kubernetes secrets and ConfigMaps:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gateway-secrets
type: Opaque
stringData:
  redis-password: "your_secure_password"
  grafana-admin-password: "your_secure_grafana_password"
```

## Security Best Practices

1. **Never commit secrets to version control**
2. **Use Doppler or similar secret management in production**
3. **Rotate passwords regularly**
4. **Use strong, unique passwords for each service**
5. **Limit Redis access to internal networks only**
6. **Use TLS/SSL for all external communications**

## Environment Variable Precedence

1. Doppler (production)
2. Environment variables
3. `.env` file (development only)
4. Default values in code