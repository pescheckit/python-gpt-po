"""
Configuration classes for the PO translator application.
"""

from dataclasses import dataclass

from .enums import ModelProvider
from .provider_clients import ProviderClients


@dataclass
class TranslationConfig:
    """Class to hold configuration parameters for the translation service."""
    provider_clients: ProviderClients
    provider: ModelProvider
    model: str
    bulk_mode: bool = False
    fuzzy: bool = False
    fix_fuzzy: bool = False
    folder_language: bool = False
