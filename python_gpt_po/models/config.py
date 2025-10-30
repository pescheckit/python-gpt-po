"""
Configuration classes for the PO translator application.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from .enums import ModelProvider

if TYPE_CHECKING:
    from .provider_clients import ProviderClients


@dataclass
class TranslationFlags:
    """Boolean flags for translation behavior."""
    bulk_mode: bool = False
    fuzzy: bool = False
    fix_fuzzy: bool = False
    folder_language: bool = False
    mark_ai_generated: bool = True


@dataclass
class TranslationConfig:
    """Class to hold configuration parameters for the translation service."""
    provider_clients: ProviderClients
    provider: ModelProvider
    model: str
    flags: TranslationFlags
    default_context: Optional[str] = None
