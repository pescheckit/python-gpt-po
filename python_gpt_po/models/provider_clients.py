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

    def initialize_clients(self, args: Namespace) -> Dict[str, str]:
        """Initialize API clients for all providers with available keys.

        Args:
            args (Namespace): Parsed command line arguments
        Returns:
            Dict[str, str]: Dictionary of API keys for each provider
        """
        openai_key = args.openai_key or args.api_key or os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)

        azure_openai_key = args.azure_openai_key or os.getenv("AZURE_OPENAI_API_KEY", "")
        if azure_openai_key:
            endpoint = args.azure_openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
            if not endpoint:
                raise ValueError("Missing Azure OpenAI endpoint.")

            api_version = args.azure_openai_api_version or os.getenv("AZURE_OPENAI_API_VERSION")
            if not api_version:
                raise ValueError("Missing Azure OpenAI API version.")

            self.azure_openai_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=azure_openai_key,
                api_version=api_version
            )

        antropic_key = args.anthropic_key or os.getenv("ANTHROPIC_API_KEY", "")
        if antropic_key:
            self.anthropic_client = Anthropic(api_key=antropic_key)

        deepseek_key = args.deepseek_key or os.getenv("DEEPSEEK_API_KEY", "")
        if deepseek_key:
            self.deepseek_api_key = deepseek_key

        return {
            ModelProvider.OPENAI.value: openai_key,
            ModelProvider.ANTHROPIC.value: antropic_key,
            ModelProvider.DEEPSEEK.value: deepseek_key,
            ModelProvider.AZURE_OPENAI.value: azure_openai_key,
        }
