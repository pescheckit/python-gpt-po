"""
Anthropic provider implementation.
"""
import logging
from typing import List

import requests

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class AnthropicProvider(ModelProviderInterface):
    """Anthropic model provider implementation."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from Anthropic."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("Anthropic client not initialized")
            return models

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
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get the default Anthropic model."""
        return "claude-3-5-haiku-latest"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred Anthropic models for a task."""
        if task == "translation":
            return ["claude-3-opus", "claude-3-5-sonnet", "claude-3-5-haiku"]
        return ["claude-3-5-haiku-latest"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if Anthropic client is initialized."""
        return provider_clients.anthropic_client is not None

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for Anthropic."""
        return [
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-5-sonnet-latest",
            "claude-3-opus-20240229",
        ]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from Anthropic API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("Anthropic client not initialized")

        message = {"role": "user", "content": content}
        completion = provider_clients.anthropic_client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[message]
        )
        return completion.content[0].text.strip()
