"""
Custom provider implementation (OpenAI-compatible).
"""
import logging
from typing import List

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class CustomProvider(ModelProviderInterface):
    """Custom model provider implementation (OpenAI-compatible)."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from the custom provider."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("Custom client not initialized")
            return models

        try:
            response = provider_clients.custom_client.models.list()
            models = [model.id for model in response.data]
        except Exception as e:
            logging.error("Error fetching custom models: %s", str(e))
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get a generic default model name for custom providers."""
        return "gpt-4o-mini"  # Often used as a safe default for proxies

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get possible models for the custom provider."""
        return ["gpt-4", "gpt-4o", "gpt-4o-mini", "llama3", "mistral"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if custom client is initialized."""
        return provider_clients.custom_client is not None

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for custom provider."""
        return [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4",
            "gpt-3.5-turbo"
        ]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from custom OpenAI-compatible API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("Custom client not initialized")

        message = {"role": "user", "content": content}
        completion = provider_clients.custom_client.chat.completions.create(
            model=model,
            messages=[message]
        )
        return completion.choices[0].message.content.strip()
