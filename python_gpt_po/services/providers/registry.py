"""
Registry for model providers.
"""
import logging
from typing import Dict, Optional, Type

from ...models.enums import ModelProvider
from .base import ModelProviderInterface


class ProviderRegistry:
    """Registry to manage model provider implementations."""

    _providers: Dict[ModelProvider, Type[ModelProviderInterface]] = {}
    _instances: Dict[ModelProvider, ModelProviderInterface] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, provider: ModelProvider, provider_class: Type[ModelProviderInterface]) -> None:
        """Register a provider implementation.

        Args:
            provider: The provider enum value
            provider_class: The provider implementation class
        """
        cls._providers[provider] = provider_class
        logging.debug("Registered provider: %s", provider.value)

    @classmethod
    def _ensure_initialized(cls):
        """Ensure providers are initialized."""
        if not cls._initialized:
            # Import here to avoid circular imports
            from .provider_init import initialize_providers
            initialize_providers()
            cls._initialized = True

    @classmethod
    def get_provider(cls, provider: ModelProvider) -> Optional[ModelProviderInterface]:
        """Get a provider instance.

        Args:
            provider: The provider enum value

        Returns:
            Provider instance or None if not registered
        """
        cls._ensure_initialized()
        if provider not in cls._instances:
            provider_class = cls._providers.get(provider)
            if provider_class:
                cls._instances[provider] = provider_class()
            else:
                logging.warning("Provider %s not registered", provider.value)
                return None

        return cls._instances[provider]

    @classmethod
    def is_registered(cls, provider: ModelProvider) -> bool:
        """Check if a provider is registered.

        Args:
            provider: The provider enum value

        Returns:
            True if registered, False otherwise
        """
        return provider in cls._providers

    @classmethod
    def get_all_providers(cls) -> Dict[ModelProvider, Type[ModelProviderInterface]]:
        """Get all registered providers.

        Returns:
            Dictionary of all registered providers
        """
        return cls._providers.copy()
