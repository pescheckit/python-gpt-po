"""
Ollama provider implementation.
"""
import logging
from typing import List

import requests

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class OllamaProvider(ModelProviderInterface):
    """Ollama model provider implementation for local AI models."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from Ollama."""
        try:
            response = requests.get(
                f"{provider_clients.ollama_base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            model_data = response.json().get("models", [])
            models = [model["name"] for model in model_data]
            return models
        except Exception as e:
            logging.error("Error fetching Ollama models: %s", str(e))
            return self.get_fallback_models()

    def get_default_model(self) -> str:
        """Get the default Ollama model."""
        return "llama3.2"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred Ollama models for a task."""
        if task == "translation":
            return ["llama3.2", "llama3.1", "mistral"]
        return ["llama3.2"]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(
                f"{provider_clients.ollama_base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            logging.error(
                "Cannot connect to Ollama at %s",
                provider_clients.ollama_base_url
            )
            logging.error("Possible solutions:")
            logging.error("  1. Start Ollama: 'ollama serve'")
            logging.error("  2. Check if Ollama is running on a different port")
            logging.error("  3. Use --ollama-base-url to specify the correct URL")
            logging.error("     Example: --ollama-base-url http://localhost:8080")
            logging.error("  4. Set OLLAMA_BASE_URL environment variable")
            return False
        except Exception as e:
            logging.error("Unexpected error connecting to Ollama: %s", str(e))
            return False

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for Ollama."""
        return [
            "llama3.2",
            "llama3.1",
            "llama3",
            "mistral",
            "gemma2",
            "qwen2.5"
        ]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from Ollama API."""
        if not self.is_client_initialized(provider_clients):
            raise ValueError(
                f"Ollama not accessible at {provider_clients.ollama_base_url}. "
                "Make sure Ollama is running."
            )

        try:
            response = requests.post(
                f"{provider_clients.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": content,
                    "stream": False
                },
                timeout=provider_clients.ollama_timeout
            )
            response.raise_for_status()
            return response.json()["response"].strip()
        except requests.Timeout as e:
            raise TimeoutError(
                f"Ollama request timed out after {provider_clients.ollama_timeout} seconds. "
                "Consider using --ollama-timeout to increase the timeout or use a smaller model."
            ) from e
        except Exception as e:
            logging.error("Ollama API error: %s", str(e))
            raise
