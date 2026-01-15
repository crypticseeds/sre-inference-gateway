"""Provider factory for creating provider instances.

This module provides a factory pattern implementation for creating inference
provider instances from configuration. It supports multiple provider types
(OpenAI, vLLM, Mock) and handles provider-specific initialization logic.

The factory abstracts the complexity of provider instantiation, including:
- API key retrieval from environment variables
- Base URL configuration
- Timeout and retry settings
- Provider-specific parameter handling

Example:
    ```python
    from app.config.models import ProviderConfig
    from app.providers.factory import ProviderFactory

    # Create OpenAI provider from config
    config = ProviderConfig(
        name="openai-gpt4",
        type="openai",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        timeout=30.0,
        max_retries=3
    )

    provider = ProviderFactory.create_provider(config)

    # Use the provider
    response = await provider.chat_completion(request, "req-123")
    ```

Supported Provider Types:
    - openai: OpenAI API adapter (requires API key)
    - vllm: vLLM inference service adapter (OpenAI-compatible)
    - mock: Mock providers for testing (MockOpenAIProvider, MockVLLMProvider)
"""

import logging
import os
from typing import Dict, Any

from app.config.models import ProviderConfig
from app.providers.base import BaseProvider
from app.providers.openai import OpenAIAdapter
from app.providers.vllm import VLLMAdapter

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating provider instances from configuration.

    This factory class provides static methods to instantiate different types
    of inference providers based on configuration. It handles provider-specific
    initialization logic and validates required configuration parameters.

    The factory supports:
        - OpenAI API providers (with API key authentication)
        - vLLM inference service providers (OpenAI-compatible)
        - Mock providers for testing (auto-selected based on name)

    All provider creation is done through the `create_provider` static method,
    which dispatches to provider-specific factory methods based on the
    provider type specified in the configuration.

    Example:
        ```python
        # Create from ProviderConfig
        config = ProviderConfig(
            name="openai-gpt4",
            type="openai",
            api_key_env="OPENAI_API_KEY",
            timeout=30.0
        )
        provider = ProviderFactory.create_provider(config)

        # Create vLLM provider
        vllm_config = ProviderConfig(
            name="vllm-local",
            type="vllm",
            base_url="http://localhost:8000/v1",
            timeout=60.0
        )
        vllm_provider = ProviderFactory.create_provider(vllm_config)

        # Create mock provider for testing
        mock_config = ProviderConfig(
            name="mock-openai-test",
            type="mock"
        )
        mock_provider = ProviderFactory.create_provider(mock_config)
        ```
    """

    @staticmethod
    def create_provider(config: ProviderConfig) -> BaseProvider:
        """Create provider instance from configuration.

        This is the main factory method that creates provider instances based
        on the provider type specified in the configuration. It validates the
        configuration and dispatches to provider-specific factory methods.

        Provider Type Mapping:
            - "openai": Creates OpenAIAdapter instance
            - "vllm": Creates VLLMAdapter instance
            - "mock": Creates MockOpenAIProvider or MockVLLMProvider based on name

        Args:
            config: Provider configuration containing:
                - name (str): Provider identifier
                - type (str): Provider type ("openai", "vllm", "mock")
                - base_url (str, optional): API base URL
                - api_key_env (str, optional): Environment variable for API key
                - timeout (float): Request timeout in seconds
                - max_retries (int): Maximum retry attempts
                - weight (float): Routing weight
                - enabled (bool): Whether provider is enabled

        Returns:
            BaseProvider: Configured provider instance ready for use.
                The specific type depends on the provider type:
                - OpenAIAdapter for "openai" type
                - VLLMAdapter for "vllm" type
                - MockOpenAIProvider or MockVLLMProvider for "mock" type

        Raises:
            ValueError: If provider type is unknown or unsupported
            ValueError: If required configuration is missing (e.g., API key for OpenAI)

        Example:
            ```python
            # Create OpenAI provider
            config = ProviderConfig(
                name="openai-gpt4",
                type="openai",
                api_key_env="OPENAI_API_KEY",
                base_url="https://api.openai.com/v1",
                timeout=30.0,
                max_retries=3
            )

            provider = ProviderFactory.create_provider(config)

            # Use the provider
            request = ChatCompletionRequest(
                model="gpt-4",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            response = await provider.chat_completion(request, "req-123")
            ```
        """
        provider_type = config.type.lower()
        provider_config = config.model_dump()

        if provider_type == "openai":
            return ProviderFactory._create_openai_adapter(config, provider_config)
        if provider_type == "vllm":
            return ProviderFactory._create_vllm_adapter(config, provider_config)
        if provider_type == "mock":
            # Import mock provider dynamically to avoid circular imports
            # pylint: disable=import-outside-toplevel
            from app.providers.mock import MockOpenAIAdapter, MockVLLMAdapter

            # Determine which mock provider to use based on name
            if "openai" in config.name.lower():
                return MockOpenAIAdapter(config.name, provider_config)
            if "vllm" in config.name.lower():
                return MockVLLMAdapter(config.name, provider_config)
            # Default to OpenAI mock
            return MockOpenAIAdapter(config.name, provider_config)

        raise ValueError(f"Unknown provider type: {provider_type}")

    @staticmethod
    def _create_openai_adapter(
        config: ProviderConfig, provider_config: Dict[str, Any]
    ) -> OpenAIAdapter:
        """Create OpenAI provider instance with API key authentication.

        This method handles OpenAI-specific initialization, including:
        - API key retrieval from environment variables
        - Base URL configuration (defaults to official OpenAI API)
        - Timeout and retry settings
        - Logging of provider creation

        Args:
            config: Provider configuration object containing:
                - name (str): Provider identifier for logging
                - api_key_env (str, optional): Environment variable name for API key
                    (defaults to "OPENAI_API_KEY" if not specified)
                - base_url (str, optional): OpenAI API base URL
                    (defaults to "https://api.openai.com/v1")
                - timeout (float): Request timeout in seconds
                - max_retries (int): Maximum retry attempts
            provider_config: Provider configuration as dictionary for passing
                to the provider constructor

        Returns:
            OpenAIAdapter: Configured OpenAI provider instance with:
                - API key authentication configured
                - HTTP client initialized
                - Retry logic enabled
                - Timeout settings applied

        Raises:
            ValueError: If API key environment variable is not set or empty.
                Error message includes the environment variable name that was checked.

        Example:
            ```python
            # Set API key in environment
            import os
            os.environ["OPENAI_API_KEY"] = "sk-..."

            # Create config
            config = ProviderConfig(
                name="openai-gpt4",
                type="openai",
                api_key_env="OPENAI_API_KEY",
                base_url="https://api.openai.com/v1",
                timeout=30.0,
                max_retries=3
            )

            # Create provider (internal method, called by create_provider)
            provider_config = config.model_dump()
            provider = ProviderFactory._create_openai_adapter(
                config,
                provider_config
            )
            ```

        Note:
            This is an internal method. Use `create_provider()` instead for
            standard provider creation.
        """
        # Get API key from environment variable
        api_key_env = config.api_key_env or "OPENAI_API_KEY"
        api_key = os.getenv(api_key_env)

        if not api_key:
            raise ValueError(
                f"OpenAI API key not found in environment variable: {api_key_env}"
            )

        base_url = config.base_url or "https://api.openai.com/v1"

        logger.info(
            "Creating OpenAI adapter: name=%s, base_url=%s, timeout=%s",
            config.name,
            base_url,
            config.timeout,
        )

        return OpenAIAdapter(
            name=config.name,
            config=provider_config,
            api_key=api_key,
            base_url=base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    @staticmethod
    def _create_vllm_adapter(
        config: ProviderConfig, provider_config: Dict[str, Any]
    ) -> VLLMAdapter:
        """Create vLLM provider instance for local or remote inference.

        This method handles vLLM-specific initialization for OpenAI-compatible
        vLLM inference services. vLLM providers do not require API keys but
        need a base URL pointing to the vLLM service endpoint.

        Args:
            config: Provider configuration object containing:
                - name (str): Provider identifier for logging
                - base_url (str, optional): vLLM service base URL
                    (defaults to "http://localhost:8000/v1")
                - timeout (float): Request timeout in seconds
                - max_retries (int): Maximum retry attempts
            provider_config: Provider configuration as dictionary for passing
                to the provider constructor

        Returns:
            VLLMAdapter: Configured vLLM adapter instance with:
                - HTTP client initialized
                - Retry logic enabled
                - Timeout settings applied
                - OpenAI-compatible endpoint configured

        Example:
            ```python
            # Create config for local vLLM service
            config = ProviderConfig(
                name="vllm-local",
                type="vllm",
                base_url="http://localhost:8000/v1",
                timeout=60.0,
                max_retries=3
            )

            # Create provider (internal method, called by create_provider)
            provider_config = config.model_dump()
            provider = ProviderFactory._create_vllm_adapter(
                config,
                provider_config
            )

            # Use with remote vLLM service
            remote_config = ProviderConfig(
                name="vllm-remote",
                type="vllm",
                base_url="https://vllm.example.com/v1",
                timeout=90.0
            )
            remote_provider = ProviderFactory.create_provider(remote_config)
            ```

        Note:
            This is an internal method. Use `create_provider()` instead for
            standard provider creation.

            vLLM services must expose an OpenAI-compatible API endpoint at
            `/v1/chat/completions` for this provider to work correctly.
        """
        base_url = config.base_url or "http://localhost:8000/v1"

        logger.info(
            "Creating vLLM adapter: name=%s, base_url=%s, timeout=%s",
            config.name,
            base_url,
            config.timeout,
        )

        return VLLMAdapter(
            name=config.name,
            config=provider_config,
            base_url=base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )
