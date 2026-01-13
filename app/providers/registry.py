"""Provider registry for managing available providers."""

import logging
from typing import Dict, List, Optional

from app.providers.base import BaseProvider
from app.providers.mock import MockOpenAIProvider, MockVLLMProvider

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for managing inference providers."""
    
    def __init__(self):
        """Initialize provider registry."""
        self._providers: Dict[str, BaseProvider] = {}
        self._setup_default_providers()
    
    def _setup_default_providers(self) -> None:
        """Setup default mock providers."""
        # Mock OpenAI provider
        mock_openai = MockOpenAIProvider(
            name="mock_openai",
            config={"type": "mock", "provider": "openai"}
        )
        self.register_provider("mock_openai", mock_openai)
        
        # Mock vLLM provider
        mock_vllm = MockVLLMProvider(
            name="mock_vllm", 
            config={"type": "mock", "provider": "vllm"}
        )
        self.register_provider("mock_vllm", mock_vllm)
        
        logger.info("Registered default mock providers")
    
    def register_provider(self, name: str, provider: BaseProvider) -> None:
        """Register a provider.
        
        Args:
            name: Provider name
            provider: Provider instance
        """
        self._providers[name] = provider
        logger.info(f"Registered provider: {name}")
    
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


# Global provider registry instance
provider_registry = ProviderRegistry()