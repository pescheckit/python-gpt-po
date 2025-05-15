"""
GPT Translator - Enhanced Multi-Provider Version
Main entry point for the translator application.
"""

from __future__ import annotations

import logging
import sys
import traceback
from typing import Dict, List, Optional

from .models.config import TranslationConfig
from .models.enums import ModelProvider
from .models.provider_clients import ProviderClients
from .services.model_manager import ModelManager
from .services.translation_service import TranslationService
from .utils.cli import (auto_select_provider, create_language_mapping, get_api_keys_from_args, get_provider_from_args,
                        parse_args, parse_languages, show_help_and_exit, validate_provider_key)


def setup_logging():
    """
    Initialize logging configuration.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def initialize_provider(args) -> tuple[ProviderClients, ModelProvider, str]:
    """
    Initialize the provider client and determine the appropriate model.

    Args:
        args: Command line arguments from argparse

    Returns:
        tuple: (provider_clients, provider, model)

    Raises:
        SystemExit: If no valid provider can be found or initialized
    """
    # Get API keys from arguments and environment variables
    api_keys = get_api_keys_from_args(args)

    # Initialize provider clients
    provider_clients = ProviderClients()
    provider_clients.initialize_clients(api_keys)

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
            "Model '%s' not found for provider %s. Will use a default model instead.",
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
    logging.warning("No available models found from API; defaulting to %s", default_model)
    return default_model


def process_translations(config: TranslationConfig, folder: str,
                         languages: List[str], detail_languages: Dict[str, str],
                         batch_size: int):
    """
    Process translations for the given languages and directory.

    Args:
        config (TranslationConfig): The translation configuration
        folder (str): Directory containing .po files
        languages (List[str]): List of language codes to process
        detail_languages (Dict[str, str]): Mapping of language codes to detailed names
        batch_size (int): Size of batches for bulk translation
    """
    # Initialize translation service
    translation_service = TranslationService(config, batch_size)

    # Validate provider connection
    if not translation_service.validate_provider_connection():
        logging.error(
            "%s connection failed. Please check your API key and network connection.", config.provider.value
        )
        sys.exit(1)

    # Start processing files
    logging.info("Starting translation with %s using model %s", config.provider.value, config.model)
    translation_service.scan_and_process_po_files(folder, languages, detail_languages)
    logging.info("Translation completed successfully")


def main():
    """
    Main function to parse arguments and initiate processing.
    """
    # Initialize logging
    setup_logging()

    # Show help if no arguments
    if len(sys.argv) == 1:
        show_help_and_exit()

    # Parse command line arguments
    args = parse_args()

    try:
        # Initialize provider
        provider_clients, provider, model = initialize_provider(args)

        # Parse languages
        languages = parse_languages(args.lang)

        # Create mapping between language codes and detailed names
        try:
            detail_languages = create_language_mapping(languages, args.detail_lang)
        except ValueError as e:
            logging.error(str(e))
            sys.exit(1)

        # Create translation configuration
        config = TranslationConfig(
            provider_clients=provider_clients,
            provider=provider,
            model=model,
            bulk_mode=args.bulk,
            fuzzy=args.fuzzy,
            fix_fuzzy=args.fix_fuzzy,
            folder_language=args.folder_language
        )

        # Process translations
        process_translations(config, args.folder, languages, detail_languages, args.bulksize)

    except Exception as e:
        logging.error("An unexpected error occurred: %s", str(e))
        logging.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
