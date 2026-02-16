"""
OpenAI-compatible API provider implementation.
Supports any service that implements the OpenAI API format, including:
- DeepSeek
- LM Studio
- z.ai
- Groq
- Together.ai
- Fireworks
- And many others
"""
import logging
from typing import List

import requests

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class OpenAICompatibleProvider(ModelProviderInterface):
    """OpenAI-compatible API provider implementation."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from the API."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("OpenAI-compatible API key not set")
            return models

        try:
            headers = {
                "Authorization": f"Bearer {provider_clients.openai_compatible_api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(
                f"{provider_clients.openai_compatible_base_url}/models",
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            models = [model["id"] for model in response.json().get("data", [])]
        except Exception as e:
            logging.error("Error fetching models: %s", str(e))
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get the default model."""
        return "gpt-3.5-turbo"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred models for a task."""
        return ["gpt-4", "gpt-3.5-turbo"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if client is initialized."""
        has_key = provider_clients.openai_compatible_api_key is not None
        has_url = provider_clients.openai_compatible_base_url is not None
        return has_key and has_url

    def get_fallback_models(self) -> List[str]:
        """Get fallback models."""
        return ["gpt-3.5-turbo", "gpt-4"]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from OpenAI-compatible API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("OpenAI-compatible client not initialized")

        headers = {
            "Authorization": f"Bearer {provider_clients.openai_compatible_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4000
        }
        response = requests.post(
            f"{provider_clients.openai_compatible_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
