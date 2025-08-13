"""
Model management service for the PO translator.
This module handles model discovery, validation, and selection across different AI providers.
"""
import logging
from typing import List

from ..models.enums import ModelProvider
from ..models.provider_clients import ProviderClients
from .providers.registry import ProviderRegistry


class ModelManager:
    """Class to manage models from different providers."""
    @staticmethod
    def get_available_models(provider_clients: ProviderClients, provider: ModelProvider) -> List[str]:
        """Retrieve available models from a specific provider."""
        provider_impl = ProviderRegistry.get_provider(provider)
        if not provider_impl:
            logging.error("Provider %s not registered", provider.value)
            return []
        try:
            return provider_impl.get_models(provider_clients)
        except Exception as e:
            logging.error("Error fetching models from %s: %s", provider.value, str(e))
            return []

    @staticmethod
    def validate_model(provider_clients: ProviderClients, provider: ModelProvider, model: str) -> bool:
        """
        Validates whether the specified model is available for the given provider.
        Uses prefix matching so that a shorthand (e.g. "claude") will match a full model name.
        Args:
            provider_clients (ProviderClients): The initialized provider clients
            provider (ModelProvider): The provider to check against
            model (str): The model name/ID to validate
        Returns:
            bool: True if the model is valid, False otherwise
        """
        available_models = ModelManager.get_available_models(provider_clients, provider)
        if not available_models:
            return False
        return any(avail.lower().startswith(model.lower()) for avail in available_models)

    @staticmethod
    def get_default_model(provider: ModelProvider) -> str:
        """
        Returns the default model for a given provider.
        Args:
            provider (ModelProvider): The provider to get the default model for
        Returns:
            str: The default model ID
        """
        provider_impl = ProviderRegistry.get_provider(provider)
        if not provider_impl:
            logging.warning("Provider %s not registered, returning empty default", provider.value)
            return ""
        return provider_impl.get_default_model()

    @staticmethod
    def verify_model_capabilities(
        provider_clients: ProviderClients,
        provider: ModelProvider,
        model: str,
        required_capability: str = "translation"
    ) -> bool:
        """
        Verifies if a model has the required capabilities.
        Args:
            provider_clients (ProviderClients): The initialized provider clients
            provider (ModelProvider): The provider to check against
            model (str): The model to verify
            required_capability (str): The capability to check for
        Returns:
            bool: True if the model has the required capability, False otherwise
        """
        # This is a simplified implementation - in a real-world scenario,
        # you might want to check model specifications/documentation
        # For now, assume all models support translation
        # In the future, this could check model specs for specific capabilities
        if required_capability == "translation":
            return ModelManager.validate_model(provider_clients, provider, model)
        return False
