"""
GPT Translator - Enhanced Multi-Provider Version
Main entry point for the translator application.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from argparse import Namespace
from dataclasses import dataclass
from typing import Dict, List, Optional

from .models.config import TranslationConfig, TranslationFlags
from .models.enums import ModelProvider
from .models.provider_clients import ProviderClients
from .services.language_detector import LanguageDetector
from .services.model_manager import ModelManager
from .services.translation_service import TranslationService
from .utils.cli import (auto_select_provider, create_language_mapping, get_provider_from_args, parse_args,
                        show_help_and_exit, validate_provider_key)
from .utils.config_loader import ConfigLoader


def setup_logging(verbose: int = 0, quiet: bool = False):
    """
    Initialize logging configuration based on verbosity level.

    Args:
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
        quiet: If True, only show errors
    """
    # Determine logging level based on flags
    if quiet:
        level = logging.ERROR
    elif verbose >= 2:
        level = logging.DEBUG
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.WARNING  # Default: only warnings and errors

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True  # Force reconfiguration even if logging is already configured
    )

    # Explicitly set root logger level
    logging.getLogger().setLevel(level)


def initialize_provider(args: Namespace) -> tuple[ProviderClients, ModelProvider, str]:
    """
    Initialize the provider client and determine the appropriate model.

    Args:
        args: Command line arguments from argparse

    Returns:
        tuple: (provider_clients, provider, model)

    Raises:
        SystemExit: If no valid provider can be found or initialized
    """
    # Initialize provider clients
    provider_clients = ProviderClients()
    api_keys = provider_clients.initialize_clients(args)

    # Get provider from arguments or auto-select
    provider = get_provider_from_args(args)
    if not provider:
        provider = auto_select_provider(api_keys)
        if not provider:
            logging.error("No API keys provided for any provider. Please provide at least one API key.")
            sys.exit(1)

    # Validate provider has an API key
    if not validate_provider_key(provider, api_keys):
        sys.exit(1)

    # Create model manager for model operations
    model_manager = ModelManager()

    # List models if requested and exit
    if args.list_models:
        models = model_manager.get_available_models(provider_clients, provider)
        print(f"Available models for {provider.value}:")
        for model in models:
            print(f"  - {model}")
        sys.exit(0)

    # Determine appropriate model
    model = get_appropriate_model(provider, provider_clients, model_manager, args.model)

    return provider_clients, provider, model


def get_appropriate_model(
    provider: ModelProvider,
    provider_clients: ProviderClients,
    model_manager: ModelManager,
    requested_model: Optional[str]
) -> str:
    """
    Get the appropriate model for the provider.

    Args:
        provider (ModelProvider): The selected provider
        provider_clients (ProviderClients): The initialized provider clients
        model_manager (ModelManager): The model manager instance
        requested_model (Optional[str]): Model requested by the user

    Returns:
        str: The appropriate model ID
    """
    # If a specific model was requested, validate it
    if requested_model:
        if model_manager.validate_model(provider_clients, provider, requested_model):
            return requested_model
        # If requested model is not valid, log a warning
        logging.warning(
            "Model '%s' not available. Using default model for %s provider.",
            requested_model, provider.value
        )

    # Try to get list of available models
    available_models = model_manager.get_available_models(provider_clients, provider)
    if available_models:
        chosen_model = available_models[0]
        logging.info("Using model: %s", chosen_model)
        return chosen_model

    # Fall back to default model if no models could be retrieved
    default_model = model_manager.get_default_model(provider)
    logging.info("Using default model: %s", default_model)
    return default_model


@dataclass
class TranslationTask:
    """Parameters for translation processing."""
    config: TranslationConfig
    folder: str
    languages: List[str]
    detail_languages: Dict[str, str]
    batch_size: int
    respect_gitignore: bool = True


def process_translations(task: TranslationTask):
    """
    Process translations for the given task parameters.

    Args:
        task: TranslationTask containing all processing parameters
    """
    # Initialize translation service
    translation_service = TranslationService(task.config, task.batch_size)

    # Validate provider connection
    if not translation_service.validate_provider_connection():
        logging.error(
            "%s connection failed. Please check your API key and network connection.", task.config.provider.value
        )
        sys.exit(1)

    # Start processing files
    logging.info("Starting translation with %s using model %s in folder %s",
                 task.config.provider.value, task.config.model, task.folder)
    translation_service.scan_and_process_po_files(
        task.folder, task.languages, task.detail_languages, task.respect_gitignore
    )
    logging.info("Translation completed successfully")


def main():
    """
    Main function to parse arguments and initiate processing.
    """
    # Show help if no arguments
    if len(sys.argv) == 1:
        show_help_and_exit()

    # Parse command line arguments
    args = parse_args()

    # Initialize logging with verbosity settings
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        # Initialize provider
        provider_clients, provider, model = initialize_provider(args)

        # Get languages - either from args or auto-detect from PO files
        try:
            respect_gitignore = not args.no_gitignore  # Invert the flag
            languages = LanguageDetector.validate_or_detect_languages(
                folder=args.folder,
                lang_arg=args.lang,
                use_folder_structure=args.folder_language,
                respect_gitignore=respect_gitignore
            )
        except ValueError as e:
            logging.error(str(e))
            sys.exit(1)

        # Create mapping between language codes and detailed names
        try:
            detail_languages = create_language_mapping(languages, args.detail_lang)
        except ValueError as e:
            logging.error(str(e))
            sys.exit(1)

        # Check for deprecated --fuzzy option
        if args.fuzzy:
            logging.warning(
                "Note: --fuzzy flag is deprecated. Use --fix-fuzzy for safer fuzzy entry handling."
            )

        # Get default context: Priority is CLI arg > Env var > Config file
        default_context = None
        if hasattr(args, 'default_context') and args.default_context:
            default_context = args.default_context
        elif os.getenv('GPT_TRANSLATOR_CONTEXT'):
            default_context = os.getenv('GPT_TRANSLATOR_CONTEXT')
        else:
            # Try to get from config file
            default_context = ConfigLoader.get_default_context(args.folder)

        if default_context:
            logging.info("Using default translation context: %s", default_context)

        # Create translation configuration
        flags = TranslationFlags(
            bulk_mode=args.bulk,
            fuzzy=args.fuzzy,
            fix_fuzzy=args.fix_fuzzy,
            folder_language=args.folder_language,
            mark_ai_generated=not args.no_ai_comment
        )
        config = TranslationConfig(
            provider_clients=provider_clients,
            provider=provider,
            model=model,
            flags=flags,
            default_context=default_context
        )

        # Process translations
        respect_gitignore = not args.no_gitignore  # Invert the flag
        task = TranslationTask(
            config=config,
            folder=args.folder,
            languages=languages,
            detail_languages=detail_languages,
            batch_size=args.bulksize,
            respect_gitignore=respect_gitignore
        )
        process_translations(task)

    except KeyboardInterrupt:
        logging.info("\nTranslation cancelled.")
        logging.info("All completed translations have been saved.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except Exception as e:
        logging.error("An unexpected error occurred: %s", str(e))
        logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
