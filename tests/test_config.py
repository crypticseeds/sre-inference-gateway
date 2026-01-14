"""Tests for configuration system."""

import os
import tempfile
import yaml
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config.models import (
    GatewayConfig, 
    ProviderConfig, 
    ServerConfig, 
    HealthConfig,
    LoggingConfig
)
from app.config.settings import ConfigManager, Settings


class TestProviderConfig:
    """Test provider configuration model."""
    
    def test_valid_provider_config(self):
        """Test valid provider configuration."""
        config = ProviderConfig(
            name="test_provider",
            weight=0.5,
            enabled=True,
            health_check_url="http://localhost:8080/health",
            timeout=30.0
        )
        
        assert config.name == "test_provider"
        assert config.weight == 0.5
        assert config.enabled is True
        assert config.health_check_url == "http://localhost:8080/health"
        assert config.timeout == 30.0
    
    def test_provider_config_defaults(self):
        """Test provider configuration defaults."""
        config = ProviderConfig(name="test_provider")
        
        assert config.name == "test_provider"
        assert config.weight == 1.0
        assert config.enabled is True
        assert config.health_check_url is None
        assert config.timeout == 30.0
    
    def test_invalid_weight(self):
        """Test invalid weight validation."""
        with pytest.raises(ValidationError):
            ProviderConfig(name="test", weight=-1.0)


class TestServerConfig:
    """Test server configuration model."""
    
    def test_valid_server_config(self):
        """Test valid server configuration."""
        config = ServerConfig(
            host="127.0.0.1",
            port=9000,
            debug=True
        )
        
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True
    
    def test_invalid_port(self):
        """Test invalid port validation."""
        with pytest.raises(ValidationError):
            ServerConfig(port=0)
        
        with pytest.raises(ValidationError):
            ServerConfig(port=70000)


class TestHealthConfig:
    """Test health configuration model."""
    
    def test_valid_health_config(self):
        """Test valid health configuration."""
        config = HealthConfig(
            check_interval=60.0,
            timeout=10.0,
            retries=5
        )
        
        assert config.check_interval == 60.0
        assert config.timeout == 10.0
        assert config.retries == 5
    
    def test_invalid_values(self):
        """Test invalid health config values."""
        with pytest.raises(ValidationError):
            HealthConfig(check_interval=0)
        
        with pytest.raises(ValidationError):
            HealthConfig(timeout=-1)
        
        with pytest.raises(ValidationError):
            HealthConfig(retries=-1)


class TestLoggingConfig:
    """Test logging configuration model."""
    
    def test_valid_log_levels(self):
        """Test valid log levels."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            config = LoggingConfig(level=level)
            assert config.level == level
    
    def test_case_insensitive_log_level(self):
        """Test case insensitive log level."""
        config = LoggingConfig(level="info")
        assert config.level == "INFO"
    
    def test_invalid_log_level(self):
        """Test invalid log level."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestGatewayConfig:
    """Test gateway configuration model."""
    
    def test_valid_gateway_config(self):
        """Test valid gateway configuration."""
        config = GatewayConfig(
            version="1.0.0",
            providers=[
                ProviderConfig(name="provider1", weight=0.7),
                ProviderConfig(name="provider2", weight=0.3)
            ]
        )
        
        assert config.version == "1.0.0"
        assert len(config.providers) == 2
        assert config.get_provider_weights() == {"provider1": 0.7, "provider2": 0.3}
    
    def test_default_providers(self):
        """Test default provider configuration."""
        config = GatewayConfig()
        
        assert len(config.providers) == 2
        provider_names = [p.name for p in config.providers]
        assert "mock_openai" in provider_names
        assert "mock_vllm" in provider_names
    
    def test_duplicate_provider_names(self):
        """Test validation of duplicate provider names."""
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="duplicate", weight=0.5),
                    ProviderConfig(name="duplicate", weight=0.5)
                ]
            )
    
    def test_no_providers(self):
        """Test validation when no providers configured."""
        with pytest.raises(ValidationError):
            GatewayConfig(providers=[])
    
    def test_all_providers_disabled(self):
        """Test validation when all providers disabled."""
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="provider1", enabled=False),
                    ProviderConfig(name="provider2", enabled=False)
                ]
            )
    
    def test_all_weights_zero(self):
        """Test validation when all weights are zero."""
        with pytest.raises(ValidationError):
            GatewayConfig(
                providers=[
                    ProviderConfig(name="provider1", weight=0.0),
                    ProviderConfig(name="provider2", weight=0.0)
                ]
            )
    
    def test_get_enabled_providers(self):
        """Test getting enabled providers."""
        config = GatewayConfig(
            providers=[
                ProviderConfig(name="enabled1", enabled=True),
                ProviderConfig(name="disabled", enabled=False),
                ProviderConfig(name="enabled2", enabled=True)
            ]
        )
        
        enabled = config.get_enabled_providers()
        assert len(enabled) == 2
        enabled_names = [p.name for p in enabled]
        assert "enabled1" in enabled_names
        assert "enabled2" in enabled_names
        assert "disabled" not in enabled_names


class TestConfigManager:
    """Test configuration manager."""
    
    def test_load_default_config(self):
        """Test loading default configuration when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.yaml"
            manager = ConfigManager(str(config_path))
            
            config = manager.load_config()
            assert isinstance(config, GatewayConfig)
            assert config.version == "0.1.0"
    
    def test_load_yaml_config(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "version": "2.0.0",
            "server": {
                "host": "127.0.0.1",
                "port": 9000,
                "debug": True
            },
            "providers": [
                {
                    "name": "test_provider",
                    "weight": 1.0,
                    "enabled": True
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            config = manager.load_config()
            
            assert config.version == "2.0.0"
            assert config.server.host == "127.0.0.1"
            assert config.server.port == 9000
            assert config.server.debug is True
            assert len(config.providers) == 1
            assert config.providers[0].name == "test_provider"
        finally:
            os.unlink(config_path)
    
    def test_invalid_yaml(self):
        """Test handling of invalid YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            with pytest.raises(yaml.YAMLError):
                manager.load_config()
        finally:
            os.unlink(config_path)
    
    def test_invalid_config_data(self):
        """Test handling of invalid configuration data."""
        config_data = {
            "providers": []  # Invalid: no providers
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            manager = ConfigManager(config_path)
            with pytest.raises(ValidationError):
                manager.load_config()
        finally:
            os.unlink(config_path)


class TestSettingsBackwardCompatibility:
    """Test backward compatibility with Settings class."""
    
    def test_settings_from_gateway_config(self):
        """Test creating Settings from GatewayConfig."""
        gateway_config = GatewayConfig(
            version="1.5.0",
            server=ServerConfig(host="192.168.1.1", port=9000, debug=True),
            providers=[
                ProviderConfig(name="provider1", weight=0.8),
                ProviderConfig(name="provider2", weight=0.2)
            ]
        )
        
        settings = Settings.from_gateway_config(gateway_config)
        
        assert settings.version == "1.5.0"
        assert settings.host == "192.168.1.1"
        assert settings.port == 9000
        assert settings.debug is True
        assert settings.provider_weights == {"provider1": 0.8, "provider2": 0.2}