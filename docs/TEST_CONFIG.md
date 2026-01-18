# Configuration Tests Documentation

## Overview

The `tests/test_config.py` module provides comprehensive unit tests for the SRE Inference Gateway configuration system. Tests validate Pydantic models, YAML configuration loading, and backward compatibility with legacy settings.

## Purpose

This test suite ensures:
- Configuration models correctly validate input data
- Default values are applied when optional fields are omitted
- Invalid configurations are rejected with appropriate errors
- YAML configuration files are parsed correctly
- The ConfigManager handles file operations and hot-reload
- Settings class maintains backward compatibility

## Test Structure

### Test Classes

| Class | Description |
|-------|-------------|
| `TestProviderConfig` | Tests for provider configuration model |
| `TestServerConfig` | Tests for server binding configuration |
| `TestHealthConfig` | Tests for health check configuration |
| `TestLoggingConfig` | Tests for logging configuration |
| `TestGatewayConfig` | Tests for main gateway configuration |
| `TestConfigManager` | Tests for YAML configuration loading |
| `TestSettingsBackwardCompatibility` | Tests for legacy settings compatibility |

## Configuration Models Tested

### ProviderConfig

Configuration for inference providers (OpenAI, vLLM, mock).

| Attribute | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Provider identifier |
| `type` | `str` | Required | Provider type (openai, vllm, mock) |
| `weight` | `float` | `1.0` | Must be >= 0 |
| `enabled` | `bool` | `True` | Whether provider is active |
| `base_url` | `str` | `None` | Provider API base URL |
| `api_key_env` | `str` | `None` | Environment variable for API key |
| `health_check_url` | `str` | `None` | Health endpoint URL |
| `timeout` | `float` | `30.0` | Must be > 0 |
| `max_retries` | `int` | `3` | Must be >= 0 |

### ServerConfig

Configuration for FastAPI server binding.

| Attribute | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `host` | `str` | `"0.0.0.0"` | Host address |
| `port` | `int` | `8000` | Range: 1-65535 |
| `debug` | `bool` | `False` | Debug mode flag |

### HealthConfig

Configuration for provider health checks.

| Attribute | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `check_interval` | `float` | `30.0` | Must be > 0 |
| `timeout` | `float` | `5.0` | Must be > 0 |
| `retries` | `int` | `3` | Must be >= 0 |

### LoggingConfig

Configuration for application logging.

| Attribute | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `level` | `str` | `"INFO"` | Valid: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `format` | `str` | Standard format | Log format string |

### GatewayConfig

Main gateway configuration container.

| Attribute | Type | Default |
|-----------|------|---------|
| `version` | `str` | `"0.1.0"` |
| `server` | `ServerConfig` | Default ServerConfig |
| `providers` | `List[ProviderConfig]` | Default mock providers |
| `health` | `HealthConfig` | Default HealthConfig |
| `logging` | `LoggingConfig` | Default LoggingConfig |
| `metrics` | `MetricsConfig` | Default MetricsConfig |

**Validation Rules:**
- At least one provider must be configured
- Provider names must be unique
- At least one enabled provider must have weight > 0

## Test Cases

### TestProviderConfig

#### `test_valid_provider_config`

Verifies that ProviderConfig accepts valid parameters.

```python
config = ProviderConfig(
    name="test_provider",
    type="mock",
    weight=0.5,
    enabled=True,
    health_check_url="http://localhost:8080/health",
    timeout=30.0,
)
```

#### `test_provider_config_defaults`

Verifies default values when only required fields provided.

```python
config = ProviderConfig(name="test_provider", type="mock")
assert config.weight == 1.0
assert config.enabled is True
```

#### `test_invalid_weight`

Verifies negative weights are rejected.

```python
with pytest.raises(ValidationError):
    ProviderConfig(name="test", type="mock", weight=-1.0)
```

### TestServerConfig

#### `test_valid_server_config`

Verifies valid server configuration.

```python
config = ServerConfig(host="127.0.0.1", port=9000, debug=True)
```

#### `test_invalid_port`

Verifies invalid ports are rejected.

```python
with pytest.raises(ValidationError):
    ServerConfig(port=0)  # Below minimum

with pytest.raises(ValidationError):
    ServerConfig(port=70000)  # Above maximum
```

### TestHealthConfig

#### `test_valid_health_config`

Verifies valid health configuration.

```python
config = HealthConfig(check_interval=60.0, timeout=10.0, retries=5)
```

#### `test_invalid_values`

Verifies invalid values are rejected.

```python
with pytest.raises(ValidationError):
    HealthConfig(check_interval=0)  # Must be > 0

with pytest.raises(ValidationError):
    HealthConfig(timeout=-1)  # Must be > 0

with pytest.raises(ValidationError):
    HealthConfig(retries=-1)  # Must be >= 0
```

### TestLoggingConfig

#### `test_valid_log_levels`

Verifies all standard log levels are accepted.

```python
for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    config = LoggingConfig(level=level)
    assert config.level == level
```

#### `test_case_insensitive_log_level`

Verifies log levels are normalized to uppercase.

```python
config = LoggingConfig(level="info")
assert config.level == "INFO"
```

#### `test_invalid_log_level`

Verifies invalid log levels are rejected.

```python
with pytest.raises(ValidationError):
    LoggingConfig(level="INVALID")
```

### TestGatewayConfig

#### `test_valid_gateway_config`

Verifies valid gateway configuration with multiple providers.

```python
config = GatewayConfig(
    version="1.0.0",
    providers=[
        ProviderConfig(name="provider1", type="mock", weight=0.7),
        ProviderConfig(name="provider2", type="mock", weight=0.3),
    ],
)
assert config.get_provider_weights() == {"provider1": 0.7, "provider2": 0.3}
```

#### `test_default_providers`

Verifies default mock providers are created.

```python
config = GatewayConfig()
assert len(config.providers) == 2
# Contains mock_openai and mock_vllm
```

#### `test_duplicate_provider_names`

Verifies duplicate names are rejected.

```python
with pytest.raises(ValidationError):
    GatewayConfig(
        providers=[
            ProviderConfig(name="duplicate", type="mock"),
            ProviderConfig(name="duplicate", type="mock"),
        ]
    )
```

#### `test_no_providers`

Verifies empty provider list is rejected.

```python
with pytest.raises(ValidationError):
    GatewayConfig(providers=[])
```

#### `test_all_providers_disabled`

Verifies all-disabled configuration is rejected.

```python
with pytest.raises(ValidationError):
    GatewayConfig(
        providers=[
            ProviderConfig(name="p1", type="mock", enabled=False),
            ProviderConfig(name="p2", type="mock", enabled=False),
        ]
    )
```

#### `test_all_weights_zero`

Verifies zero-weight configuration is rejected.

```python
with pytest.raises(ValidationError):
    GatewayConfig(
        providers=[
            ProviderConfig(name="p1", type="mock", weight=0.0),
            ProviderConfig(name="p2", type="mock", weight=0.0),
        ]
    )
```

#### `test_get_enabled_providers`

Verifies `get_enabled_providers()` filters correctly.

```python
config = GatewayConfig(
    providers=[
        ProviderConfig(name="enabled1", type="mock", enabled=True),
        ProviderConfig(name="disabled", type="mock", enabled=False),
        ProviderConfig(name="enabled2", type="mock", enabled=True),
    ]
)
enabled = config.get_enabled_providers()
assert len(enabled) == 2
```

### TestConfigManager

#### `test_load_default_config`

Verifies default config when file doesn't exist.

```python
manager = ConfigManager("nonexistent.yaml")
config = manager.load_config()
assert config.version == "0.1.0"
```

#### `test_load_yaml_config`

Verifies YAML file loading.

```python
config_data = {
    "version": "2.0.0",
    "server": {"host": "127.0.0.1", "port": 9000},
    "providers": [{"name": "test", "type": "mock"}],
}
# Write to temp file and load
```

#### `test_invalid_yaml`

Verifies invalid YAML raises error.

```python
# Write invalid YAML to file
with pytest.raises(yaml.YAMLError):
    manager.load_config()
```

#### `test_invalid_config_data`

Verifies invalid config data raises ValidationError.

```python
config_data = {"providers": []}  # Invalid: empty
with pytest.raises(ValidationError):
    manager.load_config()
```

### TestSettingsBackwardCompatibility

#### `test_settings_from_gateway_config`

Verifies Settings.from_gateway_config() conversion.

```python
gateway_config = GatewayConfig(
    version="1.5.0",
    server=ServerConfig(host="192.168.1.1", port=9000, debug=True),
    providers=[
        ProviderConfig(name="provider1", type="mock", weight=0.8),
        ProviderConfig(name="provider2", type="mock", weight=0.2),
    ],
)
settings = Settings.from_gateway_config(gateway_config)
assert settings.version == "1.5.0"
assert settings.provider_weights == {"provider1": 0.8, "provider2": 0.2}
```

## Running Tests

### Run All Configuration Tests

```bash
pytest tests/test_config.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_config.py::TestProviderConfig -v
pytest tests/test_config.py::TestGatewayConfig -v
```

### Run Specific Test

```bash
pytest tests/test_config.py::TestProviderConfig::test_valid_provider_config -v
```

### Run with Coverage

```bash
pytest tests/test_config.py --cov=app.config --cov-report=html
```

## Test Dependencies

### Required Packages

- `pytest`: Test framework
- `pydantic`: Data validation (tested models)
- `pyyaml`: YAML parsing
- `tempfile`: Temporary file handling (stdlib)

### No External Dependencies

All tests run without external services or API calls.

## Related Documentation

- [Configuration Models](../app/config/models.py) - Pydantic model definitions
- [Settings Module](../app/config/settings.py) - ConfigManager and Settings classes
- [Provider Implementation Guide](PROVIDERS.md) - Provider configuration usage
- [Environment Configuration](ENVIRONMENT.md) - Environment variable handling

## Summary

The configuration test suite provides comprehensive coverage for:

- ✅ All configuration model validation
- ✅ Default value verification
- ✅ Invalid input rejection
- ✅ YAML file loading and parsing
- ✅ ConfigManager lifecycle
- ✅ Settings backward compatibility
- ✅ Provider weight calculations
- ✅ Enabled provider filtering

All tests are designed to run quickly without external dependencies, making them suitable for CI/CD pipelines.
