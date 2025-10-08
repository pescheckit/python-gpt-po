"""
Initialize and register all providers.
"""
from ...models.enums import ModelProvider
from .registry import ProviderRegistry


def initialize_providers():
    """Register all available providers."""
    # Import providers here to avoid circular imports
    from .anthropic_provider import AnthropicProvider
    from .azure_openai_provider import AzureOpenAIProvider
    from .deepseek_provider import DeepSeekProvider
    from .ollama_provider import OllamaProvider
    from .openai_provider import OpenAIProvider
    ProviderRegistry.register(ModelProvider.OPENAI, OpenAIProvider)
    ProviderRegistry.register(ModelProvider.ANTHROPIC, AnthropicProvider)
    ProviderRegistry.register(ModelProvider.DEEPSEEK, DeepSeekProvider)
    ProviderRegistry.register(ModelProvider.AZURE_OPENAI, AzureOpenAIProvider)
    ProviderRegistry.register(ModelProvider.OLLAMA, OllamaProvider)


# Providers will be initialized lazily when first accessed
