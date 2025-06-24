"""
Enumerations used throughout the PO translator application.
"""

from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    AZURE_OPENAI = "azure_openai"


ModelProviderList = [
    ModelProvider.OPENAI.value,
    ModelProvider.ANTHROPIC.value,
    ModelProvider.DEEPSEEK.value,
    ModelProvider.AZURE_OPENAI.value
]
