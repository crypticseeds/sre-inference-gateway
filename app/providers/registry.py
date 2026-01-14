"""Provider registry for managing available providers."""

import logging
from typing import Dict, List, Optional

from app.config.models import ProviderConfig
from app.providers.base import BaseProvider
from app.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing inference providers."""

    def __init__(self):
        """Initialize provider registry."""
        self._providers: Dict[str, BaseProvider] = {}

    def initialize_from_config(self, provider_configs: List[ProviderConfig]) -> None:
        """Initialize providers from configuration.

        Args:
            provider_configs: List of provider configurations
        """
        # Clear existing providers
        self._providers.clear()

        # Create and register providers from config
        for config in provider_configs:
            if not config.enabled:
                logger.info(f"Skipping disabled provider: {config.name}")
                continue

            try:
                provider = ProviderFactory.create_provider(config)
                self.register_provider(config.name, provider)
            except Exception as e:
                logger.error(f"Failed to create provider {config.name}: {e}")
                # Continue with other providers

        if not self._providers:
            logger.warning(
                "No providers registered - all providers are disabled or failed to initialize"
            )

    def register_provider(self, name: str, provider: BaseProvider) -> None:
        """Register a provider.

        Args:
            name: Provider name
            provider: Provider instance
        """
        self._providers[name] = provider
        logger.info(f"Registered provider: {name} (type: {type(provider).__name__})")

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get provider by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names.

        Returns:
            List of provider names
        """
        return list(self._providers.keys())

    def get_all_providers(self) -> Dict[str, BaseProvider]:
        """Get all registered providers.

        Returns:
            Dictionary of provider name to provider instance
        """
        return self._providers.copy()

    async def close_all(self) -> None:
        """Close all provider connections."""
        import inspect

        for name, provider in self._providers.items():
            try:
                if hasattr(provider, "close") and callable(provider.close):
                    close_result = provider.close()
                    # Check if the result is awaitable (async function)
                    if inspect.iscoroutine(close_result) or inspect.isawaitable(
                        close_result
                    ):
                        await close_result
                    logger.info(f"Closed provider: {name}")
            except Exception as e:
                logger.error(f"Error closing provider {name}: {e}")


# Global provider registry instance
provider_registry = ProviderRegistry()
