"""
Command-line interface utilities for the PO translator.
This module provides the argument parsing and command-line handling functionality,
including argument definitions, help text generation, and command processing.
"""
import argparse
import logging
import os
import sys
from typing import Dict, List, Optional

from ..models.enums import ModelProvider
from .helpers import get_version


class CustomArgumentParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser that handles errors in a more user-friendly way.
    """
    def error(self, message):
        """
        Display a cleaner error message with usage information.

        Args:
            message (str): Error message
        """
        self.print_help()
        sys.stderr.write(f'\nError: {message}\n')
        sys.exit(2)


def parse_args():
    """
    Parse command-line arguments with a more user-friendly interface.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    # First pass - check if list-models is in args
    # This allows us to make folder and lang not required when listing models
    list_models_present = False
    for arg in sys.argv:
        if arg in ("--list-models", "--version"):
            list_models_present = True
            break
    parser = CustomArgumentParser(
        description="Translate .po files using AI language models",
        epilog="""
Examples:
  # Basic usage with OpenAI
  gpt-po-translator --folder ./locales --lang fr,es,de

  # Use Anthropic with detailed language names
  gpt-po-translator --folder ./i18n --lang nl,de --detail-lang "Dutch,German" --provider anthropic

  # List available models for a provider (no need for --folder or --lang)
  gpt-po-translator --provider deepseek --list-models

  # Process multiple translations in bulk with a specific model
  gpt-po-translator --folder ./locales --lang ja,ko --bulk --model gpt-4
""",
        formatter_class=lambda prog: argparse.RawDescriptionHelpFormatter(prog, max_help_position=35, width=100)
    )

    # Create argument groups for better organization
    required_group = parser.add_argument_group('Required Arguments')
    language_group = parser.add_argument_group('Language Options')
    provider_group = parser.add_argument_group('Provider Settings')
    api_group = parser.add_argument_group('API Keys')
    advanced_group = parser.add_argument_group('Advanced Options')
    fuzzy_group = advanced_group.add_mutually_exclusive_group()

    # Required arguments (not required if listing models)
    required_group.add_argument(
        "-f", "--folder",
        required=(not list_models_present),
        metavar="FOLDER",
        help="Input folder containing .po files"
    )
    required_group.add_argument(
        "-l", "--lang",
        required=(not list_models_present),
        metavar="LANG",
        help="Comma-separated language codes to translate (e.g., fr,es,de)"
    )

    # Language options
    language_group.add_argument(
        "--detail-lang",
        metavar="NAMES",
        help="Comma-separated detailed language names (e.g., 'French,Spanish,German')"
    )
    language_group.add_argument(
        "--folder-language",
        action="store_true",
        help="Detect language from directory structure"
    )

    # Provider settings
    provider_group.add_argument(
        "--provider",
        choices=["openai", "anthropic", "deepseek"],
        help="AI provider to use (default: first provider with available API key)"
    )
    provider_group.add_argument(
        "--model",
        metavar="MODEL",
        help="Specific model to use (default: provider's recommended model)"
    )
    provider_group.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider and exit"
    )

    # API Keys
    api_group.add_argument(
        "--openai-key",
        metavar="KEY",
        help="OpenAI API key (can also use OPENAI_API_KEY env var)"
    )
    api_group.add_argument(
        "--anthropic-key",
        metavar="KEY",
        help="Anthropic API key (can also use ANTHROPIC_API_KEY env var)"
    )
    api_group.add_argument(
        "--deepseek-key",
        metavar="KEY",
        help="DeepSeek API key (can also use DEEPSEEK_API_KEY env var)"
    )
    api_group.add_argument(
        "--api_key",
        metavar="KEY",
        help="Fallback API key for OpenAI (deprecated, use --openai-key instead)"
    )

    # Advanced options
    advanced_group.add_argument(
        "--bulk",
        action="store_true",
        help="Use bulk translation mode (faster, but may be less accurate)"
    )
    advanced_group.add_argument(
        "--bulksize",
        type=int,
        default=50,
        metavar="SIZE",
        help="Number of strings to translate in each batch (default: 50)"
    )
    fuzzy_group.add_argument(
        "--fuzzy",
        action="store_true",
        help="Remove fuzzy markers without translating (legacy behavior, risky)"
    )
    fuzzy_group.add_argument(
        "--fix-fuzzy",
        action="store_true",
        help="Translate and clean fuzzy entries safely (recommended)"
    )

    # Version information
    parser.add_argument(
        "--version",
        action="version",
        version=f'%(prog)s {get_version()}'
    )

    # Display help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def show_help_and_exit():
    """
    Display help and exit.
    """
    args = [sys.argv[0], "--help"]
    sys.argv = args
    parse_args()
    sys.exit(0)


def parse_languages(lang_arg: str) -> List[str]:
    """
    Parse comma-separated language string into a list of language codes.

    Args:
        lang_arg (str): Comma-separated language codes

    Returns:
        List[str]: List of language codes
    """
    return [lang.strip() for lang in lang_arg.split(',')]


def create_language_mapping(lang_codes: List[str], detail_langs_arg: Optional[str]) -> Dict[str, str]:
    """
    Create a mapping between language codes and their detailed names.

    Args:
        lang_codes (List[str]): List of language codes
        detail_langs_arg (Optional[str]): Comma-separated detailed language names

    Returns:
        Dict[str, str]: Mapping of language codes to detailed names

    Raises:
        ValueError: If the number of language codes doesn't match the number of detailed names
    """
    if not detail_langs_arg:
        return {}

    detail_langs = [lang.strip() for lang in detail_langs_arg.split(',')]

    if len(lang_codes) != len(detail_langs):
        raise ValueError("The number of languages in --lang and --detail-lang must match")

    return dict(zip(lang_codes, detail_langs))


def get_provider_from_args(args) -> Optional[ModelProvider]:
    """
    Get the provider from command line arguments.

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        Optional[ModelProvider]: The selected provider or None if not specified
    """
    if args.provider:
        return ModelProvider(args.provider)
    return None


def get_api_keys_from_args(args) -> Dict[str, str]:
    """
    Extract API keys from command line arguments and environment variables.

    Args:
        args (argparse.Namespace): Parsed command line arguments

    Returns:
        Dict[str, str]: Dictionary of provider names to API keys
    """
    return {
        "openai": args.openai_key or args.api_key or os.getenv("OPENAI_API_KEY", ""),
        "anthropic": args.anthropic_key or os.getenv("ANTHROPIC_API_KEY", ""),
        "deepseek": args.deepseek_key or os.getenv("DEEPSEEK_API_KEY", "")
    }


def auto_select_provider(api_keys: Dict[str, str]) -> Optional[ModelProvider]:
    """
    Auto-select a provider based on available API keys.

    Args:
        api_keys (Dict[str, str]): Dictionary of provider names to API keys

    Returns:
        Optional[ModelProvider]: The auto-selected provider or None if no keys available
    """
    for provider_name in ["openai", "anthropic", "deepseek"]:
        if api_keys.get(provider_name):
            provider = ModelProvider(provider_name)
            logging.info("Auto-selected provider: %s (based on available API key)", provider_name)
            return provider
    return None


def validate_provider_key(provider: ModelProvider, api_keys: Dict[str, str]) -> bool:
    """
    Validate that the selected provider has an API key.

    Args:
        provider (ModelProvider): The selected provider
        api_keys (Dict[str, str]): Dictionary of provider names to API keys

    Returns:
        bool: True if provider has a key, False otherwise
    """
    if not api_keys.get(provider.value):
        logging.error("No API key provided for %s. Please provide an API key.", provider.value)
        return False
    return True
