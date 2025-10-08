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
        self.deepseek_base_url = None
        self.ollama_base_url = None
        self.ollama_timeout = None

    def _get_setting(self, args: Namespace, arg_name: str, env_var: str = None,
                     config_provider: str = None, config_key: str = None, default: any = None) -> any:
        """Generic helper to get a setting from CLI args, env var, config, or default.

        Args:
            args: Command line arguments
            arg_name: Attribute name in args (e.g., 'ollama_base_url')
            env_var: Environment variable name (optional)
            config_provider: Provider name for config lookup (optional)
            config_key: Config key name (optional)
            default: Default value

        Returns:
            Setting value from first available source
        """
        # Priority 1: CLI argument
        if hasattr(args, arg_name) and getattr(args, arg_name):
            return getattr(args, arg_name)

        # Priority 2: Environment variable
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value

        # Priority 3: Config file
        if config_provider and config_key:
            from ..utils.config_loader import ConfigLoader
            folder_path = args.folder if hasattr(args, 'folder') else None
            config_value = ConfigLoader.get_provider_setting(config_provider, config_key, None, folder_path)
            if config_value is not None:
                return config_value

        # Priority 4: Default
        return default

    def initialize_clients(self, args: Namespace) -> Dict[str, str]:
        """Initialize API clients for all providers with available keys.

        Args:
            args (Namespace): Parsed command line arguments
        Returns:
            Dict[str, str]: Dictionary of API keys for each provider
        """
        # OpenAI
        openai_key = self._get_setting(args, 'openai_key', 'OPENAI_API_KEY', 'openai', 'api_key', '')
        if not openai_key and hasattr(args, 'api_key'):
            openai_key = args.api_key
        if openai_key:
            self.openai_client = OpenAI(api_key=openai_key)

        # Azure OpenAI
        azure_openai_key = self._get_setting(
            args, 'azure_openai_key', 'AZURE_OPENAI_API_KEY', 'azure_openai', 'api_key', ''
        )
        if azure_openai_key:
            endpoint = self._get_setting(
                args, 'azure_openai_endpoint', 'AZURE_OPENAI_ENDPOINT',
                'azure_openai', 'endpoint', None
            )
            if not endpoint:
                raise ValueError("Missing Azure OpenAI endpoint.")

            api_version = self._get_setting(
                args, 'azure_openai_api_version', 'AZURE_OPENAI_API_VERSION',
                'azure_openai', 'api_version', None
            )
            if not api_version:
                raise ValueError("Missing Azure OpenAI API version.")

            self.azure_openai_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=azure_openai_key,
                api_version=api_version
            )

        # Anthropic
        antropic_key = self._get_setting(
            args, 'anthropic_key', 'ANTHROPIC_API_KEY', 'anthropic', 'api_key', ''
        )
        if antropic_key:
            self.anthropic_client = Anthropic(api_key=antropic_key)

        # DeepSeek
        deepseek_key = self._get_setting(
            args, 'deepseek_key', 'DEEPSEEK_API_KEY', 'deepseek', 'api_key', ''
        )
        if deepseek_key:
            self.deepseek_api_key = deepseek_key

        self.deepseek_base_url = self._get_setting(
            args, 'deepseek_base_url', 'DEEPSEEK_BASE_URL',
            'deepseek', 'base_url', 'https://api.deepseek.com/v1'
        )

        # Ollama
        self.ollama_base_url = self._get_setting(
            args, 'ollama_base_url', 'OLLAMA_BASE_URL',
            'ollama', 'base_url', 'http://localhost:11434'
        )
        self.ollama_timeout = self._get_setting(
            args, 'ollama_timeout', None,
            'ollama', 'timeout', 120
        )

        return {
            ModelProvider.OPENAI.value: openai_key,
            ModelProvider.ANTHROPIC.value: antropic_key,
            ModelProvider.DEEPSEEK.value: deepseek_key,
            ModelProvider.AZURE_OPENAI.value: azure_openai_key,
            ModelProvider.OLLAMA.value: "local",  # Ollama doesn't need API key
        }
