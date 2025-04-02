"""
Model management service for the PO translator.
This module handles model discovery, validation, and selection across different AI providers.
"""
import logging
from typing import List

import requests

from ..models.enums import ModelProvider
from ..models.provider_clients import ProviderClients


class ModelManager:
    """Class to manage models from different providers."""

    @staticmethod
    def get_available_models(provider_clients: ProviderClients, provider: ModelProvider) -> List[str]:
        """Retrieve available models from a specific provider."""
        models = []

        try:
            if provider == ModelProvider.OPENAI:
                if provider_clients.openai_client:
                    response = provider_clients.openai_client.models.list()
                    models = [model.id for model in response.data]
                else:
                    logging.error("OpenAI client not initialized")

            elif provider == ModelProvider.ANTHROPIC:
                if provider_clients.anthropic_client:
                    # Use Anthropic's models endpoint
                    try:
                        headers = {
                            "x-api-key": provider_clients.anthropic_client.api_key,
                            "anthropic-version": "2023-06-01"
                        }
                        response = requests.get(
                            "https://api.anthropic.com/v1/models",
                            headers=headers,
                            timeout=15
                        )
                        response.raise_for_status()
                        model_data = response.json().get("data", [])
                        models = [model["id"] for model in model_data]
                    except Exception as e:
                        logging.error("Error fetching Anthropic models: %s", str(e))
                        # Fallback to commonly used models if API call fails
                        models = [
                            "claude-3-7-sonnet-latest",
                            "claude-3-5-haiku-latest",
                            "claude-3-5-sonnet-latest",
                            "claude-3-opus-20240229",
                        ]
                else:
                    logging.error("Anthropic client not initialized")

            elif provider == ModelProvider.DEEPSEEK:
                if provider_clients.deepseek_api_key:
                    headers = {
                        "Authorization": f"Bearer {provider_clients.deepseek_api_key}",
                        "Content-Type": "application/json"
                    }
                    response = requests.get(
                        f"{provider_clients.deepseek_base_url}/models",
                        headers=headers,
                        timeout=15
                    )
                    response.raise_for_status()
                    models = [model["id"] for model in response.json().get("data", [])]
                else:
                    logging.error("DeepSeek API key not set")

        except Exception as e:
            logging.error("Error fetching models from %s: %s", provider.value, str(e))

        return models

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
        default_models = {
            ModelProvider.OPENAI: "gpt-4o-mini",
            ModelProvider.ANTHROPIC: "claude-3-5-haiku-latest",
            ModelProvider.DEEPSEEK: "deepseek-chat"
        }
        return default_models.get(provider)

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

    @staticmethod
    def suggest_model(provider_clients: ProviderClients, provider: ModelProvider,
                      task: str = "translation") -> str:
        """
        Suggests the best model for a given task and provider.

        Args:
            provider_clients (ProviderClients): The initialized provider clients
            provider (ModelProvider): The provider to use
            task (str): The task the model will be used for

        Returns:
            str: The suggested model ID
        """
        # For translation tasks, prefer more capable models when available
        if task == "translation":
            preferred_models = {
                ModelProvider.OPENAI: ["gpt-4", "gpt-4o", "gpt-3.5-turbo"],
                ModelProvider.ANTHROPIC: ["claude-3-opus", "claude-3-5-sonnet", "claude-3-5-haiku"],
                ModelProvider.DEEPSEEK: ["deepseek-chat"]
            }

            available_models = ModelManager.get_available_models(provider_clients, provider)

            # Try to find a match from the preferred models list
            for preferred in preferred_models.get(provider, []):
                for available in available_models:
                    if preferred in available.lower():
                        return available

            # Fall back to the first available model or the default
            if available_models:
                return available_models[0]

        # Default to the standard default model
        return ModelManager.get_default_model(provider)
