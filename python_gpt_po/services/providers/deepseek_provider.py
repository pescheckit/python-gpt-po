"""
DeepSeek provider implementation (legacy alias).
This module is maintained for backward compatibility.
New code should use openai_compatible_provider instead.
"""
# Import the new provider and create an alias
from .openai_compatible_provider import OpenAICompatibleProvider

# DeepSeekProvider is now an alias to OpenAICompatibleProvider
DeepSeekProvider = OpenAICompatibleProvider
