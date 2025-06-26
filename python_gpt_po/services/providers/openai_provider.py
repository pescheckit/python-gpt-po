"""
OpenAI provider implementation.
"""
import logging
from typing import List

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class OpenAIProvider(ModelProviderInterface):
    """OpenAI model provider implementation."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from OpenAI."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("OpenAI client not initialized")
            return models

        try:
            response = provider_clients.openai_client.models.list()
            models = [model.id for model in response.data]
        except Exception as e:
            logging.error("Error fetching OpenAI models: %s", str(e))
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get the default OpenAI model."""
        return "gpt-4o-mini"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred OpenAI models for a task."""
        if task == "translation":
            return ["gpt-4", "gpt-4o", "gpt-3.5-turbo"]
        return ["gpt-4o-mini"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if OpenAI client is initialized."""
        return provider_clients.openai_client is not None

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for OpenAI."""
        return [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from OpenAI API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("OpenAI client not initialized")

        message = {"role": "user", "content": content}
        completion = provider_clients.openai_client.chat.completions.create(
            model=model,
            messages=[message]
        )
        return completion.choices[0].message.content.strip()
