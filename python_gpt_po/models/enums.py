"""
Enumerations used throughout the PO translator application.
"""

from enum import Enum


class ModelProvider(Enum):
    """Enum for supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
