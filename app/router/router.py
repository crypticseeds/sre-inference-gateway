"""Request router with weighted and deterministic routing."""

import logging
import random
from typing import Dict, List, Optional

from app.providers.base import BaseProvider
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class RequestRouter:
    """Router for selecting providers based on weights and headers."""
    
    def __init__(self, provider_weights: Dict[str, float]):
        """Initialize router with provider weights.
        
        Args:
            provider_weights: Dictionary mapping provider names to weights
        """
        self.provider_weights = provider_weights.copy()
        self._validate_weights()
    
    def _validate_weights(self) -> None:
        """Validate provider weights."""
        if not self.provider_weights:
            raise ValueError("Provider weights cannot be empty")
        
        # Check for negative weights
        negative_providers = [name for name, weight in self.provider_weights.items() if weight < 0]
        if negative_providers:
            raise ValueError(f"Provider weights cannot be negative: {negative_providers}")
        
        total_weight = sum(self.provider_weights.values())
        if total_weight <= 0:
            raise ValueError("Total provider weights must be positive")
        
        # Normalize weights to sum to 1.0
        for provider_name in self.provider_weights:
            self.provider_weights[provider_name] /= total_weight
        
        logger.info(f"Normalized provider weights: {self.provider_weights}")
    
    def select_provider(
        self, 
        provider_priority: Optional[str] = None
    ) -> Optional[BaseProvider]:
        """Select a provider based on weights or deterministic pinning.
        
        Args:
            provider_priority: Optional provider name for deterministic routing
            
        Returns:
            Selected provider instance or None if not available
        """
        # Deterministic routing via header
        if provider_priority:
            provider = provider_registry.get_provider(provider_priority)
            if provider:
                logger.info(f"Selected provider via priority: {provider_priority}")
                return provider
            else:
                logger.warning(f"Priority provider not found: {provider_priority}")
        
        # Weighted random selection
        available_providers = []
        weights = []
        
        for provider_name, weight in self.provider_weights.items():
            provider = provider_registry.get_provider(provider_name)
            if provider:
                available_providers.append(provider)
                weights.append(weight)
        
        if not available_providers:
            logger.error("No available providers for routing")
            return None
        
        # Handle case where all weights sum to zero
        total_weight = sum(weights)
        if total_weight == 0:
            logger.warning("All provider weights are zero, using uniform selection")
            selected_provider = random.choice(available_providers)
        else:
            # Use random.choices for weighted selection
            selected_provider = random.choices(available_providers, weights=weights)[0]
        
        logger.info(f"Selected provider via weighted routing: {selected_provider.name}")
        
        return selected_provider
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names.
        
        Returns:
            List of available provider names
        """
        return [
            name for name in self.provider_weights.keys()
            if provider_registry.get_provider(name) is not None
        ]
    
    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update provider weights.
        
        Args:
            new_weights: New provider weights
        """
        self.provider_weights = new_weights.copy()
        self._validate_weights()
        logger.info(f"Updated provider weights: {self.provider_weights}")