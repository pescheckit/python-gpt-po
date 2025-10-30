"""
Command-line interface utilities for the PO translator.
This module provides the argument parsing and command-line handling functionality,
including argument definitions, help text generation, and command processing.
"""
import logging
import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from typing import Dict, List, Optional

from ..models.enums import ModelProvider, ModelProviderList
from .helpers import get_version


class CustomArgumentParser(ArgumentParser):
    """
    Custom ArgumentParser that handles errors in a more user-friendly way.
    """
    def error(self, message: str):
        """
        Display a cleaner error message with usage information.

        Args:
            message (str): Error message
        """
        self.print_help()
        sys.stderr.write(f'\nError: {message}\n')
        sys.exit(2)


def parse_args() -> Namespace:
    """
    Parse command-line arguments with a more user-friendly interface.

    Returns:
        Namespace: Parsed arguments
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
  # Auto-detect languages from PO files (recommended)
  gpt-po-translator --folder ./locales --bulk

  # Specify languages explicitly
  gpt-po-translator --folder ./locales --lang fr,es,de

  # Use Anthropic with detailed language names
  gpt-po-translator --folder ./i18n --lang nl,de --detail-lang "Dutch,German" --provider anthropic

  # List available models for a provider (no need for --folder or --lang)
  gpt-po-translator --provider deepseek --list-models
""",
        formatter_class=lambda prog: RawDescriptionHelpFormatter(prog, max_help_position=35, width=100)
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

    # Language options
    language_group.add_argument(
        "-l", "--lang",
        metavar="LANG",
        help=("Comma-separated language codes to translate (e.g., fr,es,de or locale codes like fr_CA,pt_BR,en-US). "
              "If not provided, will auto-detect from PO files")
    )
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
        choices=ModelProviderList,
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
        "--azure-openai-key",
        metavar="KEY",
        help="Azure OpenAI API key (can also use AZURE_OPENAI_API_KEY env var)"
    )
    api_group.add_argument(
        "--api_key",
        metavar="KEY",
        help="Fallback API key for OpenAI (deprecated, use --openai-key instead)"
    )

    # Azure OpenAI options
    advanced_group.add_argument(
        "--azure-openai-endpoint",
        metavar="ENDPOINT",
        help="Azure OpenAI endpoint URL (can also use AZURE_OPENAI_ENDPOINT env var)"
    )
    advanced_group.add_argument(
        "--azure-openai-api-version",
        metavar="VERSION",
        help="Azure OpenAI API version (can also use AZURE_OPENAI_API_VERSION env var)"
    )

    # Ollama options
    advanced_group.add_argument(
        "--ollama-base-url",
        metavar="URL",
        help="Ollama API base URL (default: http://localhost:11434 or OLLAMA_BASE_URL env var)"
    )
    advanced_group.add_argument(
        "--ollama-timeout",
        type=int,
        metavar="SECONDS",
        help="Ollama request timeout in seconds (default: 120)"
    )

    # Advanced options
    advanced_group.add_argument(
        "--default-context",
        metavar="CONTEXT",
        help="Default translation context to use when entries lack msgctxt "
             "(can also use GPT_TRANSLATOR_CONTEXT env var)"
    )
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
        help="DEPRECATED: Remove fuzzy markers without translating (risky! use --fix-fuzzy instead)"
    )
    fuzzy_group.add_argument(
        "--fix-fuzzy",
        action="store_true",
        help="Translate and clean fuzzy entries safely (recommended)"
    )
    advanced_group.add_argument(
        "--no-ai-comment",
        action="store_true",
        help="Disable 'AI-generated' comment tagging (enabled by default for tracking)"
    )
    advanced_group.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity (-v for INFO, -vv for DEBUG)"
    )
    advanced_group.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode - only show warnings and errors"
    )
    advanced_group.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Disable .gitignore file processing (scan all directories)"
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


def get_provider_from_args(args: Namespace) -> Optional[ModelProvider]:
    """
    Get the provider from command line arguments.

    Args:
        args (Namespace): Parsed command line arguments

    Returns:
        Optional[ModelProvider]: The selected provider or None if not specified
    """
    if args.provider:
        return ModelProvider(args.provider)
    return None


def auto_select_provider(api_keys: Dict[str, str]) -> Optional[ModelProvider]:
    """
    Auto-select a provider based on available API keys.

    Args:
        api_keys (Dict[str, str]): Dictionary of provider names to API keys

    Returns:
        Optional[ModelProvider]: The auto-selected provider or None if no keys available
    """
    for provider_name in ModelProviderList:
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
