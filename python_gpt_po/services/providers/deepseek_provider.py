"""
DeepSeek provider implementation.
"""
import logging
from typing import List

import requests

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class DeepSeekProvider(ModelProviderInterface):
    """DeepSeek model provider implementation."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from DeepSeek."""
        models = []

        if not self.is_client_initialized(provider_clients):
            logging.error("DeepSeek API key not set")
            return models

        try:
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
        except Exception as e:
            logging.error("Error fetching DeepSeek models: %s", str(e))
            models = self.get_fallback_models()

        return models

    def get_default_model(self) -> str:
        """Get the default DeepSeek model."""
        return "deepseek-chat"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred DeepSeek models for a task."""
        return ["deepseek-chat"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if DeepSeek client is initialized."""
        return provider_clients.deepseek_api_key is not None

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for DeepSeek."""
        return ["deepseek-chat", "deepseek-coder"]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from DeepSeek API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError("DeepSeek client not initialized")

        headers = {
            "Authorization": f"Bearer {provider_clients.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 4000
        }
        response = requests.post(
            f"{provider_clients.deepseek_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
