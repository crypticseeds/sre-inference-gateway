"""Application settings using Pydantic Settings with YAML support and hot-reload."""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.config.models import GatewayConfig


logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes."""

    def __init__(
        self, config_manager: "ConfigManager", loop: asyncio.AbstractEventLoop
    ):
        """Initialize handler with config manager reference and event loop.

        Args:
            config_manager: Configuration manager instance
            loop: Main event loop for scheduling coroutines
        """
        self.config_manager = config_manager
        self.loop = loop
        super().__init__()

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith((".yaml", ".yml")):
            logger.info(f"Configuration file changed: {event.src_path}")
            # Schedule coroutine from watchdog thread to main event loop
            asyncio.run_coroutine_threadsafe(
                self.config_manager.reload_config(), self.loop
            )


class ConfigManager:
    """Configuration manager with hot-reload capability."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Optional[GatewayConfig] = None
        self.observer: Optional[Observer] = None
        self._lock = threading.Lock()
        self._reload_callbacks = []

    def load_config(self) -> GatewayConfig:
        """Load configuration from YAML file.

        Returns:
            Loaded configuration

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValueError: If configuration validation fails
        """
        with self._lock:
            if not self.config_path.exists():
                logger.warning(
                    f"Config file not found: {self.config_path}, using defaults"
                )
                self.config = GatewayConfig()
                return self.config

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}

                self.config = GatewayConfig(**config_data)
                logger.info(f"Configuration loaded from {self.config_path}")
                return self.config

            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML config: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                raise

    async def reload_config(self) -> None:
        """Reload configuration and notify callbacks."""
        try:
            # Snapshot old config and callbacks under lock
            with self._lock:
                old_config = self.config
                callbacks = list(self._reload_callbacks)

            # Load new config (may take time, don't hold lock)
            new_config = self.load_config()

            # Notify callbacks about config change
            for callback in callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(old_config, new_config)
                    else:
                        callback(old_config, new_config)
                except Exception as e:
                    logger.error(f"Error in config reload callback: {e}")

            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

    def start_watching(self) -> None:
        """Start watching configuration file for changes."""
        if self.observer is not None:
            return

        config_dir = self.config_path.parent
        if not config_dir.exists():
            logger.warning(f"Config directory doesn't exist: {config_dir}")
            return

        # Get the current event loop (may not exist during test collection)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.info("No running event loop, skipping config file watching")
            return

        self.observer = Observer()
        handler = ConfigFileHandler(self, loop)
        self.observer.schedule(handler, str(config_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started watching config directory: {config_dir}")

    def stop_watching(self) -> None:
        """Stop watching configuration file."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching config file")

    def add_reload_callback(self, callback) -> None:
        """Add callback to be called when config is reloaded.

        Args:
            callback: Function to call on config reload
        """
        self._reload_callbacks.append(callback)

    def get_config(self) -> GatewayConfig:
        """Get current configuration with thread-safe double-checked locking.

        Returns:
            Current configuration
        """
        # Fast path: check without lock
        if self.config is not None:
            return self.config

        # Slow path: load config (load_config handles its own locking)
        return self.load_config()


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


class Settings(BaseSettings):
    """Application settings with backward compatibility."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Provider Configuration
    provider_weights: Dict[str, float] = Field(
        default_factory=lambda: {"mock_openai": 0.5, "mock_vllm": 0.5},
        description="Provider routing weights",
    )

    # Request Processing
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum request size in bytes",
    )
    request_timeout: float = Field(
        default=30.0, description="Request timeout in seconds"
    )

    # Health Check
    health_check_interval: float = Field(
        default=30.0, description="Health check interval in seconds"
    )

    # Metrics
    metrics_port: int = Field(
        default=9090, description="Prometheus metrics server port"
    )

    @classmethod
    def from_gateway_config(cls, gateway_config: GatewayConfig) -> "Settings":
        """Create Settings instance from GatewayConfig for backward compatibility.

        Args:
            gateway_config: Gateway configuration

        Returns:
            Settings instance
        """
        return cls(
            version=gateway_config.version,
            debug=gateway_config.server.debug,
            host=gateway_config.server.host,
            port=gateway_config.server.port,
            log_level=gateway_config.logging.level,
            provider_weights=gateway_config.get_provider_weights(),
            max_request_size=gateway_config.max_request_size,
            request_timeout=gateway_config.request_timeout,
            health_check_interval=gateway_config.health.check_interval,
            metrics_port=gateway_config.metrics.port,
        )


def get_settings() -> Settings:
    """Get application settings with YAML config support.

    Note: Not cached to support hot-reload. Settings are derived from
    gateway config on each call.
    """
    config_manager = get_config_manager()
    gateway_config = config_manager.get_config()
    return Settings.from_gateway_config(gateway_config)


def get_gateway_config() -> GatewayConfig:
    """Get gateway configuration from YAML file."""
    config_manager = get_config_manager()
    return config_manager.get_config()


def setup_logging() -> None:
    """Setup application logging."""
    gateway_config = get_gateway_config()

    # Safely get log level with fallback to INFO
    log_level = getattr(logging, gateway_config.logging.level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=gateway_config.logging.format,
        handlers=[logging.StreamHandler()],
        force=True,
    )


def start_config_watching() -> None:
    """Start configuration file watching."""
    config_manager = get_config_manager()
    config_manager.start_watching()


def stop_config_watching() -> None:
    """Stop configuration file watching."""
    config_manager = get_config_manager()
    config_manager.stop_watching()
