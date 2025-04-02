"""
GPT-PO Translator - A tool for translating PO files using GPT language models.
This package provides utilities to translate gettext PO files to multiple languages
with support for multiple AI providers including OpenAI and Anthropic.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "0.1.0"
