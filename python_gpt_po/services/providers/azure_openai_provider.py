"""
Azure OpenAI provider implementation.
"""
import logging
from typing import List

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class AzureOpenAIProvider(ModelProviderInterface):
    """Azure OpenAI model provider implementation."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from Azure OpenAI."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("Azure OpenAI client not initialized")
            return models

        try:
            response = provider_clients.azure_openai_client.models.list()
            models = [model.id for model in response.data]
        except Exception as e:
            logging.error("Error fetching Azure OpenAI models: %s", str(e))
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get the default Azure OpenAI model."""
        return "gpt-35-turbo"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred Azure OpenAI models for a task."""
        if task == "translation":
            return ["gpt-4", "gpt-35-turbo"]
        return ["gpt-35-turbo"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if Azure OpenAI client is initialized."""
        return provider_clients.azure_openai_client is not None

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for Azure OpenAI."""
        return ["gpt-35-turbo", "gpt-4"]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from OpenAI API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("OpenAI client not initialized")

        message = {"role": "user", "content": content}
        completion = provider_clients.azure_openai_client.chat.completions.create(
            model=model,
            max_tokens=4000,
            messages=[message]
        )
        return completion.choices[0].message.content.strip()
