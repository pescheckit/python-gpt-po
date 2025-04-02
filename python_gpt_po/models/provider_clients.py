"""
Client classes for different AI providers.
"""

from typing import Dict

from anthropic import Anthropic
from openai import OpenAI


class ProviderClients:
    """Class to store API clients for various providers."""

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.deepseek_api_key = None
        self.deepseek_base_url = "https://api.deepseek.com/v1"

    def initialize_clients(self, api_keys: Dict[str, str]):
        """Initialize API clients for all providers with available keys.

        Args:
            api_keys (Dict[str, str]): Dictionary of provider names to API keys
        """
        if api_keys.get("openai"):
            self.openai_client = OpenAI(api_key=api_keys["openai"])

        if api_keys.get("anthropic"):
            self.anthropic_client = Anthropic(api_key=api_keys["anthropic"])

        if api_keys.get("deepseek"):
            self.deepseek_api_key = api_keys["deepseek"]
