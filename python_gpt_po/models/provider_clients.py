"""
Client classes for different AI providers.
"""

import os
from argparse import Namespace
from typing import Dict

from anthropic import Anthropic
from openai import AzureOpenAI, OpenAI

from .enums import ModelProvider


class ProviderClients:
    """Class to store API clients for various providers."""

    def __init__(self):
        self.openai_client = None
        self.azure_openai_client = None
        self.anthropic_client = None
        self.deepseek_api_key = None
        self.deepseek_base_url = "https://api.deepseek.com/v1"

    def initialize_clients(self, args: Namespace, api_keys: Dict[str, str]):
        """Initialize API clients for all providers with available keys.

        Args:
            api_keys (Dict[str, str]): Dictionary of provider names to API keys
        """
        if api_keys.get(ModelProvider.OPENAI.value):
            self.openai_client = OpenAI(api_key=api_keys[ModelProvider.OPENAI.value])

        if api_keys.get(ModelProvider.AZURE_OPENAI.value):
            endpoint = args.azure_openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError("Missing Azure OpenAI endpoint.")

            api_version = args.azure_openai_api_version or os.getenv("AZURE_OPENAI_API_VERSION")
            if not api_version:
                raise ValueError("Missing Azure OpenAI API version.")

            self.azure_openai_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_keys[ModelProvider.AZURE_OPENAI.value],
                api_version=api_version
            )

        if api_keys.get(ModelProvider.ANTHROPIC.value):
            self.anthropic_client = Anthropic(api_key=api_keys[ModelProvider.ANTHROPIC.value])

        if api_keys.get(ModelProvider.DEEPSEEK.value):
            self.deepseek_api_key = api_keys[ModelProvider.DEEPSEEK.value]
