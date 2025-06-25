"""
Initialize and register all providers.
"""
from ...models.enums import ModelProvider
from .registry import ProviderRegistry
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .deepseek_provider import DeepSeekProvider
from .azure_openai_provider import AzureOpenAIProvider


def initialize_providers():
    """Register all available providers."""
    ProviderRegistry.register(ModelProvider.OPENAI, OpenAIProvider)
    ProviderRegistry.register(ModelProvider.ANTHROPIC, AnthropicProvider)
    ProviderRegistry.register(ModelProvider.DEEPSEEK, DeepSeekProvider)
    ProviderRegistry.register(ModelProvider.AZURE_OPENAI, AzureOpenAIProvider)


# Initialize providers when module is imported
initialize_providers()
