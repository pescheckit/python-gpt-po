"""
Base interface for model providers.
"""
from abc import ABC, abstractmethod
from typing import List

from ...models.provider_clients import ProviderClients


class ModelProviderInterface(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from the provider.

        Args:
            provider_clients: Initialized provider clients

        Returns:
            List of available model IDs
        """

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider.

        Returns:
            Default model ID
        """

    @abstractmethod
    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred models for a specific task.

        Args:
            task: The task type (default: "translation")

        Returns:
            List of preferred model IDs in order of preference
        """

    @abstractmethod
    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if the provider client is initialized.

        Args:
            provider_clients: Provider clients instance

        Returns:
            True if client is initialized, False otherwise
        """

    def get_fallback_models(self) -> List[str]:
        """Get fallback models when API calls fail.

        Returns:
            List of fallback model IDs
        """
        return []

    @abstractmethod
    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Translate content using the specified model.

        Args:
            provider_clients: Provider clients instance
            model: Model to use for translation
            content: Content to translate

        Returns:
            Translated content
        """
