"""Tests for configuration system.

This module provides comprehensive unit tests for the configuration system,
including Pydantic models for provider, server, health, logging, resilience,
and gateway configurations, as well as the ConfigManager and Settings classes.

Test Coverage:
    - ProviderConfig: Provider configuration validation and defaults
    - ServerConfig: Server binding configuration validation
    - HealthConfig: Health check configuration validation
    - LoggingConfig: Logging level validation and case handling
    - CircuitBreakerConfig: Circuit breaker configuration validation
    - RetryConfig: Retry configuration validation and constraints
    - ResilienceConfig: Combined resilience patterns configuration
    - GatewayConfig: Full gateway configuration with provider management
    - ConfigManager: YAML configuration loading and hot-reload
    - Settings: Backward compatibility with legacy settings format

Key Features:
    - Pydantic validation testing for all configuration models
    - Default value verification
    - Invalid input rejection testing
    - YAML file loading and parsing
    - Configuration manager lifecycle testing
    - Resilience patterns configuration testing

Example Usage:
    Run all configuration tests:
        pytest tests/test_config.py -v

    Run specific test class:
        pytest tests/test_config.py::TestProviderConfig -v
        pytest tests/test_config.py::TestResilienceConfig -v

    Run with coverage:
        pytest tests/test_config.py --cov=app.config

Test Classes:
    - TestProviderConfig: Tests for ProviderConfig model
    - TestServerConfig: Tests for ServerConfig model
    - TestHealthConfig: Tests for HealthConfig model
    - TestLoggingConfig: Tests for LoggingConfig model
    - TestCircuitBreakerConfig: Tests for CircuitBreakerConfig model
    - TestRetryConfig: Tests for RetryConfig model
    - TestResilienceConfig: Tests for ResilienceConfig model
    - TestGatewayConfig: Tests for GatewayConfig model
    - TestGatewayConfigWithResilience: Tests for GatewayConfig resilience integration
    - TestConfigManager: Tests for ConfigManager class
    - TestSettingsBackwardCompatibility: Tests for Settings class

Note:
    These tests use temporary files for YAML configuration testing and
    clean up resources after each test. All tests are designed to run
    without external dependencies.
"""

import os
import tempfile
from pathlib import Path

import yaml
import pytest
from pydantic import ValidationError

from app.config.models import (
    GatewayConfig,
    ProviderConfig,
    ServerConfig,
    HealthConfig,
    LoggingConfig,
    CircuitBreakerConfig,
    RetryConfig,
    ResilienceConfig,
)
from app.config.settings import ConfigManager, Settings


class TestProviderConfig:
    """Test provider configuration model.

    Tests validation, defaults, and constraints for the ProviderConfig
    Pydantic model used to configure inference providers.

    Attributes Tested:
        - name (str): Provider identifier (required)
        - type (str): Provider type - openai, vllm, mock (required)
        - weight (float): Routing weight (default: 1.0, must be >= 0)
        - enabled (bool): Whether provider is active (default: True)
        - health_check_url (str, optional): Health endpoint URL
        - timeout (float): Request timeout in seconds (default: 30.0)
    """

    def test_valid_provider_config(self):
        """Test valid provider configuration.

        Verifies that a ProviderConfig can be created with all valid
        parameters and that values are correctly assigned.

        Test Parameters:
            - name: "test_provider"
            - type: "mock"
            - weight: 0.5
            - enabled: True
            - health_check_url: "http://localhost:8080/health"
            - timeout: 30.0

        Assertions:
            - All provided values are correctly stored
            - No validation errors are raised
        """
        config = ProviderConfig(
            name="test_provider",
            type="mock",
            weight=0.5,
            enabled=True,
            health_check_url="http://localhost:8080/health",
            timeout=30.0,
        )

        assert config.name == "test_provider"
        assert config.weight == 0.5
        assert config.enabled is True
        assert config.health_check_url == "http://localhost:8080/health"
        assert config.timeout == 30.0

    def test_provider_config_defaults(self):
        """Test provider configuration defaults.

        Verifies that ProviderConfig uses correct default values when
        only required fields (name, type) are provided.

        Expected Defaults:
            - weight: 1.0
            - enabled: True
            - health_check_url: None
            - timeout: 30.0
        """
        config = ProviderConfig(name="test_provider", type="mock")

        assert config.name == "test_provider"
        assert config.weight == 1.0
        assert config.enabled is True
        assert config.health_check_url is None
        assert config.timeout == 30.0

    def test_invalid_weight(self):
        """Test invalid weight validation.

        Verifies that negative weights are rejected by Pydantic validation.
        Weight must be >= 0.0 per the model constraint.

        Raises:
            ValidationError: When weight is negative (-1.0)
        """
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", type="mock", weight=-1.0)


class TestServerConfig:
    """Test server configuration model.

    Tests validation and constraints for the ServerConfig Pydantic model
    used to configure the FastAPI server binding.

    Attributes Tested:
        - host (str): Host address to bind (default: "0.0.0.0")
        - port (int): Port number (default: 8000, range: 1-65535)
        - debug (bool): Debug mode flag (default: False)
    """

    def test_valid_server_config(self):
        """Test valid server configuration.

        Verifies that ServerConfig accepts valid host, port, and debug values.

        Test Parameters:
            - host: "127.0.0.1"
            - port: 9000
            - debug: True
        """
        config = ServerConfig(host="127.0.0.1", port=9000, debug=True)

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True

    def test_invalid_port(self):
        """Test invalid port validation.

        Verifies that ports outside the valid range (1-65535) are rejected.

        Invalid Values Tested:
            - port=0: Below minimum (1)
            - port=70000: Above maximum (65535)

        Raises:
            ValidationError: For each invalid port value
        """
        with pytest.raises(ValidationError):
            ServerConfig(port=0)

        with pytest.raises(ValidationError):
            ServerConfig(port=70000)


class TestHealthConfig:
    """Test health configuration model.

    Tests validation and constraints for the HealthConfig Pydantic model
    used to configure provider health check behavior.

    Attributes Tested:
        - check_interval (float): Interval between checks (default: 30.0, must be > 0)
        - timeout (float): Health check timeout (default: 5.0, must be > 0)
        - retries (int): Number of retry attempts (default: 3, must be >= 0)
    """

    def test_valid_health_config(self):
        """Test valid health configuration.

        Verifies that HealthConfig accepts valid check_interval, timeout,
        and retries values.

        Test Parameters:
            - check_interval: 60.0
            - timeout: 10.0
            - retries: 5
        """
        config = HealthConfig(check_interval=60.0, timeout=10.0, retries=5)

        assert config.check_interval == 60.0
        assert config.timeout == 10.0
        assert config.retries == 5

    def test_invalid_values(self):
        """Test invalid health config values.

        Verifies that invalid values are rejected by Pydantic validation.

        Invalid Values Tested:
            - check_interval=0: Must be > 0
            - timeout=-1: Must be > 0
            - retries=-1: Must be >= 0

        Raises:
            ValidationError: For each invalid value
        """
        with pytest.raises(ValidationError):
            HealthConfig(check_interval=0)

        with pytest.raises(ValidationError):
            HealthConfig(timeout=-1)

        with pytest.raises(ValidationError):
            HealthConfig(retries=-1)


class TestLoggingConfig:
    """Test logging configuration model.

    Tests validation and case handling for the LoggingConfig Pydantic model
    used to configure application logging behavior.

    Attributes Tested:
        - level (str): Log level (default: "INFO", validated against standard levels)
        - format (str): Log format string (default: standard format)

    Valid Log Levels:
        DEBUG, INFO, WARNING, ERROR, CRITICAL
    """

    def test_valid_log_levels(self):
        """Test valid log levels.

        Verifies that all standard Python logging levels are accepted.

        Valid Levels Tested:
            - DEBUG
            - INFO
            - WARNING
            - ERROR
            - CRITICAL
        """
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_case_insensitive_log_level(self):
        """Test case insensitive log level.

        Verifies that log levels are normalized to uppercase regardless
        of input case.

        Test Input: "info" (lowercase)
        Expected Output: "INFO" (uppercase)
        """
        config = LoggingConfig(level="info")
        assert config.level == "INFO"

    def test_invalid_log_level(self):
        """Test invalid log level.

        Verifies that invalid log level strings are rejected.

        Invalid Value Tested: "INVALID"

        Raises:
            ValidationError: When log level is not a valid Python log level
        """
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestGatewayConfig:
    """Test gateway configuration model.

    Tests validation, defaults, and helper methods for the GatewayConfig
    Pydantic model, which is the main configuration container for the
    SRE Inference Gateway.

    Attributes Tested:
        - version (str): Application version (default: "0.1.0")
        - server (ServerConfig): Server binding configuration
        - providers (List[ProviderConfig]): Provider configurations
        - health (HealthConfig): Health check configuration
        - logging (LoggingConfig): Logging configuration
        - metrics (MetricsConfig): Metrics configuration

    Validation Rules:
        - At least one provider must be configured
        - Provider names must be unique
        - At least one enabled provider must have weight > 0

    Helper Methods Tested:
        - get_provider_weights(): Returns dict of provider weights
        - get_enabled_providers(): Returns list of enabled providers
    """

    def test_valid_gateway_config(self):
        """Test valid gateway configuration.

        Verifies that GatewayConfig accepts valid configuration with
        multiple providers and correctly calculates provider weights.

        Test Configuration:
            - version: "1.0.0"
            - providers: 2 mock providers with weights 0.7 and 0.3
        """
        config = GatewayConfig(
            version="1.0.0",
            providers=[
                ProviderConfig(name="provider1", type="mock", weight=0.7),
                ProviderConfig(name="provider2", type="mock", weight=0.3),
            ],
        )

        assert config.version == "1.0.0"
        assert len(config.providers) == 2
        assert config.get_provider_weights() == {"provider1": 0.7, "provider2": 0.3}

    def test_default_providers(self):
        """Test default provider configuration.

        Verifies that GatewayConfig creates default mock providers when
        no providers are explicitly configured.

        Expected Defaults:
            - mock_openai: Mock OpenAI provider
            - mock_vllm: Mock vLLM provider
        """
        config = GatewayConfig()

        assert len(config.providers) == 2
        provider_names = [p.name for p in config.providers]
        assert "mock_openai" in provider_names
        assert "mock_vllm" in provider_names

    def test_duplicate_provider_names(self):
        """Test validation of duplicate provider names.

        Verifies that duplicate provider names are rejected.

        Raises:
            ValidationError: When two providers have the same name
        """
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="duplicate", type="mock", weight=0.5),
                    ProviderConfig(name="duplicate", type="mock", weight=0.5),
                ]
            )

    def test_no_providers(self):
        """Test validation when no providers configured.

        Verifies that an empty provider list is rejected.

        Raises:
            ValidationError: When providers list is empty
        """
        with pytest.raises(ValidationError):
            GatewayConfig(providers=[])

    def test_all_providers_disabled(self):
        """Test validation when all providers disabled.

        Verifies that configuration is rejected when all providers
        are disabled (no enabled provider with weight > 0).

        Raises:
            ValidationError: When all providers are disabled
        """
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="provider1", type="mock", enabled=False),
                    ProviderConfig(name="provider2", type="mock", enabled=False),
                ]
            )

    def test_all_weights_zero(self):
        """Test validation when all weights are zero.

        Verifies that configuration is rejected when all enabled
        providers have zero weight.

        Raises:
            ValidationError: When total weight of enabled providers is 0
        """
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="provider1", type="mock", weight=0.0),
                    ProviderConfig(name="provider2", type="mock", weight=0.0),
                ]
            )

    def test_get_enabled_providers(self):
        """Test getting enabled providers.

        Verifies that get_enabled_providers() returns only providers
        with enabled=True.

        Test Configuration:
            - enabled1: enabled=True
            - disabled: enabled=False
            - enabled2: enabled=True

        Expected Result: [enabled1, enabled2]
        """
        config = GatewayConfig(
            providers=[
                ProviderConfig(name="enabled1", type="mock", enabled=True),
                ProviderConfig(name="disabled", type="mock", enabled=False),
                ProviderConfig(name="enabled2", type="mock", enabled=True),
            ]
        )

        enabled = config.get_enabled_providers()
        assert len(enabled) == 2
        enabled_names = [p.name for p in enabled]
        assert "enabled1" in enabled_names
        assert "enabled2" in enabled_names
        assert "disabled" not in enabled_names


class TestConfigManager:
    """Test configuration manager.

    Tests the ConfigManager class which handles YAML configuration file
    loading, parsing, and hot-reload functionality.

    Key Features Tested:
        - Default configuration when file doesn't exist
        - YAML file loading and parsing
        - Invalid YAML handling
        - Invalid configuration data handling

    Note:
        Tests use temporary files that are cleaned up after each test.
    """

    def test_load_default_config(self):
        """Test loading default configuration when file doesn't exist.

        Verifies that ConfigManager returns default GatewayConfig when
        the specified configuration file doesn't exist.

        Expected Behavior:
            - Returns GatewayConfig instance
            - Version is "0.1.0" (default)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.yaml"
            manager = ConfigManager(str(config_path))

            config = manager.load_config()
            assert isinstance(config, GatewayConfig)
            assert config.version == "0.1.0"

    def test_load_yaml_config(self):
        """Test loading configuration from YAML file.

        Verifies that ConfigManager correctly parses YAML configuration
        files and creates GatewayConfig instances.

        Test YAML Content:
            - version: "2.0.0"
            - server: custom host, port, debug settings
            - providers: single test provider with type "mock"
        """
        config_data = {
            "version": "2.0.0",
            "server": {"host": "127.0.0.1", "port": 9000, "debug": True},
            "providers": [
                {
                    "name": "test_provider",
                    "type": "mock",
                    "weight": 1.0,
                    "enabled": True,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()

            assert config.version == "2.0.0"
            # pylint: disable=no-member
            assert config.server.host == "127.0.0.1"
            assert config.server.port == 9000
            assert config.server.debug is True
            # pylint: enable=no-member
            assert len(config.providers) == 1
            assert config.providers[0].name == "test_provider"
        finally:
            os.unlink(config_path)

    def test_invalid_yaml(self):
        """Test handling of invalid YAML.

        Verifies that ConfigManager raises yaml.YAMLError when the
        configuration file contains invalid YAML syntax.

        Invalid Content: "invalid: yaml: content: ["

        Raises:
            yaml.YAMLError: When YAML parsing fails
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            with pytest.raises(yaml.YAMLError):
                manager.load_config()
        finally:
            os.unlink(config_path)

    def test_invalid_config_data(self):
        """Test handling of invalid configuration data.

        Verifies that ConfigManager raises ValidationError when the
        YAML content is valid but violates configuration constraints.

        Invalid Configuration: Empty providers list

        Raises:
            ValidationError: When configuration validation fails
        """
        config_data = {
            "providers": []  # Invalid: no providers
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ValidationError):
                manager.load_config()
        finally:
            os.unlink(config_path)


class TestSettingsBackwardCompatibility:
    """Test backward compatibility with Settings class.

    Tests the Settings class which provides backward compatibility with
    the legacy flat settings format, allowing conversion from the new
    hierarchical GatewayConfig structure.

    Key Features Tested:
        - Settings.from_gateway_config() class method
        - Correct mapping of nested config to flat settings
        - Provider weight extraction
    """

    def test_settings_from_gateway_config(self):
        """Test creating Settings from GatewayConfig.

        Verifies that Settings.from_gateway_config() correctly converts
        a hierarchical GatewayConfig to a flat Settings instance.

        Test Configuration:
            - version: "1.5.0"
            - server: host="192.168.1.1", port=9000, debug=True
            - providers: 2 mock providers with weights 0.8 and 0.2

        Expected Mappings:
            - settings.version = gateway_config.version
            - settings.host = gateway_config.server.host
            - settings.port = gateway_config.server.port
            - settings.debug = gateway_config.server.debug
            - settings.provider_weights = gateway_config.get_provider_weights()
        """
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
        assert settings.host == "192.168.1.1"
        assert settings.port == 9000
        assert settings.debug is True
        assert settings.provider_weights == {"provider1": 0.8, "provider2": 0.2}


class TestCircuitBreakerConfig:
    """Test circuit breaker configuration model.

    Tests validation, defaults, and constraints for the CircuitBreakerConfig
    Pydantic model used to configure circuit breaker behavior.

    Attributes Tested:
        - failure_threshold (int): Number of failures before opening circuit (default: 5, must be >= 1)
        - recovery_timeout (float): Time before attempting recovery (default: 60.0, must be > 0)
        - expected_exception (str): Exception type to trigger circuit breaker (default: "Exception")
    """

    def test_valid_circuit_breaker_config(self):
        """Test valid circuit breaker configuration.

        Verifies that CircuitBreakerConfig accepts valid parameters.

        Test Parameters:
            - failure_threshold: 3
            - recovery_timeout: 30.0
            - expected_exception: "HTTPException"
        """
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            expected_exception="HTTPException",
        )

        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.expected_exception == "HTTPException"

    def test_circuit_breaker_config_defaults(self):
        """Test circuit breaker configuration defaults.

        Verifies that CircuitBreakerConfig uses correct default values.

        Expected Defaults:
            - failure_threshold: 5
            - recovery_timeout: 60.0
            - expected_exception: "Exception"
        """
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.expected_exception == "Exception"

    def test_invalid_failure_threshold(self):
        """Test invalid failure threshold validation.

        Verifies that failure thresholds less than 1 are rejected.

        Raises:
            ValidationError: When failure_threshold is 0 or negative
        """
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=0)

        with pytest.raises(ValidationError):
            CircuitBreakerConfig(failure_threshold=-1)

    def test_invalid_recovery_timeout(self):
        """Test invalid recovery timeout validation.

        Verifies that recovery timeouts less than or equal to 0 are rejected.

        Raises:
            ValidationError: When recovery_timeout is 0 or negative
        """
        with pytest.raises(ValidationError):
            CircuitBreakerConfig(recovery_timeout=0)

        with pytest.raises(ValidationError):
            CircuitBreakerConfig(recovery_timeout=-1.0)


class TestRetryConfig:
    """Test retry configuration model.

    Tests validation, defaults, and constraints for the RetryConfig
    Pydantic model used to configure retry behavior with exponential backoff.

    Attributes Tested:
        - max_attempts (int): Maximum retry attempts (default: 3, must be >= 1)
        - min_wait (float): Minimum wait time in seconds (default: 1.0, must be > 0)
        - max_wait (float): Maximum wait time in seconds (default: 10.0, must be > 0)
        - exponential_base (float): Exponential backoff base (default: 2.0, must be > 1)
        - jitter (bool): Add random jitter to wait times (default: True)
    """

    def test_valid_retry_config(self):
        """Test valid retry configuration.

        Verifies that RetryConfig accepts valid parameters.

        Test Parameters:
            - max_attempts: 5
            - min_wait: 0.5
            - max_wait: 30.0
            - exponential_base: 1.5
            - jitter: False
        """
        config = RetryConfig(
            max_attempts=5,
            min_wait=0.5,
            max_wait=30.0,
            exponential_base=1.5,
            jitter=False,
        )

        assert config.max_attempts == 5
        assert config.min_wait == 0.5
        assert config.max_wait == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False

    def test_retry_config_defaults(self):
        """Test retry configuration defaults.

        Verifies that RetryConfig uses correct default values.

        Expected Defaults:
            - max_attempts: 3
            - min_wait: 1.0
            - max_wait: 10.0
            - exponential_base: 2.0
            - jitter: True
        """
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.min_wait == 1.0
        assert config.max_wait == 10.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_invalid_max_attempts(self):
        """Test invalid max attempts validation.

        Verifies that max_attempts less than 1 is rejected.

        Raises:
            ValidationError: When max_attempts is 0 or negative
        """
        with pytest.raises(ValidationError):
            RetryConfig(max_attempts=0)

        with pytest.raises(ValidationError):
            RetryConfig(max_attempts=-1)

    def test_invalid_min_wait(self):
        """Test invalid min wait validation.

        Verifies that min_wait less than or equal to 0 is rejected.

        Raises:
            ValidationError: When min_wait is 0 or negative
        """
        with pytest.raises(ValidationError):
            RetryConfig(min_wait=0)

        with pytest.raises(ValidationError):
            RetryConfig(min_wait=-1.0)

    def test_invalid_max_wait(self):
        """Test invalid max wait validation.

        Verifies that max_wait less than or equal to 0 is rejected.

        Raises:
            ValidationError: When max_wait is 0 or negative
        """
        with pytest.raises(ValidationError):
            RetryConfig(max_wait=0)

        with pytest.raises(ValidationError):
            RetryConfig(max_wait=-1.0)

    def test_invalid_exponential_base(self):
        """Test invalid exponential base validation.

        Verifies that exponential_base less than or equal to 1 is rejected.

        Raises:
            ValidationError: When exponential_base is 1 or less
        """
        with pytest.raises(ValidationError):
            RetryConfig(exponential_base=1.0)

        with pytest.raises(ValidationError):
            RetryConfig(exponential_base=0.5)


class TestResilienceConfig:
    """Test resilience configuration model.

    Tests the ResilienceConfig Pydantic model which contains both
    circuit breaker and retry configurations.

    Attributes Tested:
        - circuit_breaker (CircuitBreakerConfig): Circuit breaker configuration
        - retry (RetryConfig): Retry configuration
    """

    def test_valid_resilience_config(self):
        """Test valid resilience configuration.

        Verifies that ResilienceConfig accepts valid circuit breaker
        and retry configurations.

        Test Configuration:
            - Custom circuit breaker with failure_threshold=3
            - Custom retry with max_attempts=5
        """
        config = ResilienceConfig(
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=3, recovery_timeout=45.0
            ),
            retry=RetryConfig(max_attempts=5, min_wait=0.5, max_wait=20.0),
        )

        assert config.circuit_breaker.failure_threshold == 3
        assert config.circuit_breaker.recovery_timeout == 45.0
        assert config.retry.max_attempts == 5
        assert config.retry.min_wait == 0.5
        assert config.retry.max_wait == 20.0

    def test_resilience_config_defaults(self):
        """Test resilience configuration defaults.

        Verifies that ResilienceConfig creates default CircuitBreakerConfig
        and RetryConfig instances when not explicitly provided.

        Expected Behavior:
            - circuit_breaker uses CircuitBreakerConfig defaults
            - retry uses RetryConfig defaults
        """
        config = ResilienceConfig()

        # Check circuit breaker defaults
        assert config.circuit_breaker.failure_threshold == 5
        assert config.circuit_breaker.recovery_timeout == 60.0
        assert config.circuit_breaker.expected_exception == "Exception"

        # Check retry defaults
        assert config.retry.max_attempts == 3
        assert config.retry.min_wait == 1.0
        assert config.retry.max_wait == 10.0
        assert config.retry.exponential_base == 2.0
        assert config.retry.jitter is True

    def test_resilience_config_partial_override(self):
        """Test partial configuration override.

        Verifies that ResilienceConfig allows overriding only one
        of the nested configurations while using defaults for the other.

        Test Cases:
            - Override only circuit_breaker, use default retry
            - Override only retry, use default circuit_breaker
        """
        # Override only circuit breaker
        config1 = ResilienceConfig(
            circuit_breaker=CircuitBreakerConfig(failure_threshold=7)
        )
        assert config1.circuit_breaker.failure_threshold == 7
        assert config1.retry.max_attempts == 3  # Default

        # Override only retry
        config2 = ResilienceConfig(retry=RetryConfig(max_attempts=10))
        assert config2.circuit_breaker.failure_threshold == 5  # Default
        assert config2.retry.max_attempts == 10


class TestGatewayConfigWithResilience:
    """Test gateway configuration with resilience settings.

    Tests the integration of ResilienceConfig into the main GatewayConfig
    model and validates that resilience settings are properly included
    in the overall configuration.
    """

    def test_gateway_config_with_default_resilience(self):
        """Test gateway configuration with default resilience settings.

        Verifies that GatewayConfig includes default resilience configuration
        when not explicitly provided.
        """
        config = GatewayConfig()

        assert hasattr(config, "resilience")
        assert isinstance(config.resilience, ResilienceConfig)
        assert config.resilience.circuit_breaker.failure_threshold == 5
        assert config.resilience.retry.max_attempts == 3

    def test_gateway_config_with_custom_resilience(self):
        """Test gateway configuration with custom resilience settings.

        Verifies that GatewayConfig accepts custom resilience configuration
        and properly integrates it with other configuration sections.
        """
        custom_resilience = ResilienceConfig(
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout=30.0,
                expected_exception="HTTPException",
            ),
            retry=RetryConfig(
                max_attempts=4,
                min_wait=0.25,
                max_wait=15.0,
                exponential_base=1.8,
                jitter=False,
            ),
        )

        config = GatewayConfig(version="2.0.0", resilience=custom_resilience)

        assert config.version == "2.0.0"
        assert config.resilience.circuit_breaker.failure_threshold == 2
        assert config.resilience.circuit_breaker.recovery_timeout == 30.0
        assert config.resilience.circuit_breaker.expected_exception == "HTTPException"
        assert config.resilience.retry.max_attempts == 4
        assert config.resilience.retry.min_wait == 0.25
        assert config.resilience.retry.max_wait == 15.0
        assert config.resilience.retry.exponential_base == 1.8
        assert config.resilience.retry.jitter is False

    def test_gateway_config_resilience_yaml_integration(self):
        """Test gateway configuration resilience settings from YAML.

        Verifies that resilience configuration can be loaded from YAML
        and properly integrated into the GatewayConfig model.
        """
        config_data = {
            "version": "1.5.0",
            "resilience": {
                "circuit_breaker": {
                    "failure_threshold": 4,
                    "recovery_timeout": 45.0,
                    "expected_exception": "TimeoutError",
                },
                "retry": {
                    "max_attempts": 6,
                    "min_wait": 0.8,
                    "max_wait": 25.0,
                    "exponential_base": 1.6,
                    "jitter": True,
                },
            },
            "providers": [{"name": "test_provider", "type": "mock", "weight": 1.0}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()

            assert config.version == "1.5.0"
            assert config.resilience.circuit_breaker.failure_threshold == 4
            assert config.resilience.circuit_breaker.recovery_timeout == 45.0
            assert (
                config.resilience.circuit_breaker.expected_exception == "TimeoutError"
            )
            assert config.resilience.retry.max_attempts == 6
            assert config.resilience.retry.min_wait == 0.8
            assert config.resilience.retry.max_wait == 25.0
            assert config.resilience.retry.exponential_base == 1.6
            assert config.resilience.retry.jitter is True
        finally:
            os.unlink(config_path)
