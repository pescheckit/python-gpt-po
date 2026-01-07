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
from typing import Any, Dict, List, Optional, Tuple

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


def get_offline_provider_info(args: Namespace) -> Tuple[Any, Any, str]:
    """
    Get provider and model information without making network calls.
    """
    from .models.provider_clients import ProviderClients
    from .services.model_manager import ModelManager
    from .utils.cli import auto_select_provider, get_provider_from_args, validate_provider_key

    # Initialize provider clients (reads environment variables and args)
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

    # Determine model - use CLI arg or default
    model = args.model
    if not model:
        model = ModelManager.get_default_model(provider)

    return provider_clients, provider, model


def initialize_provider(args: Namespace, provider_clients: Any, provider: Any, model: str) -> Tuple[Any, Any, str]:
    """
    Finalize provider initialization with network validation if needed.
    """
    from .services.model_manager import ModelManager

    # Create model manager for model operations
    model_manager = ModelManager()

    # List models if requested and exit (this makes network calls)
    if args.list_models:
        models = model_manager.get_available_models(provider_clients, provider)
        print(f"Available models for {provider.value}:")
        for m in models:
            print(f"  - {m}")
        sys.exit(0)

    # Validate model (this makes network calls)
    final_model = get_appropriate_model(provider, provider_clients, model_manager, model)

    return provider_clients, provider, final_model


def get_appropriate_model(
    provider: Any,
    provider_clients: Any,
    model_manager: Any,
    requested_model: Optional[str]
) -> str:
    """
    Get the appropriate model for the provider.
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
    config: Any
    folder: str
    languages: List[str]
    detail_languages: Dict[str, str]
    batch_size: int
    respect_gitignore: bool = True


def process_translations(task: TranslationTask):
    """
    Process translations for the given task parameters.
    """
    from .services.translation_service import TranslationService

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
    from .utils.cli import parse_args, show_help_and_exit

    # Show help if no arguments
    if len(sys.argv) == 1:
        show_help_and_exit()

    # Parse command line arguments
    args = parse_args()

    # Initialize logging with verbosity settings
    setup_logging(verbose=args.verbose, quiet=args.quiet)

    try:
        from .services.language_detector import LanguageDetector
        from .utils.cost_estimator import CostEstimator

        # 1. Get languages (Pure logic)
        try:
            respect_gitignore = not args.no_gitignore
            languages = LanguageDetector.validate_or_detect_languages(
                folder=args.folder,
                lang_arg=args.lang,
                use_folder_structure=args.folder_language,
                respect_gitignore=respect_gitignore
            )
        except ValueError as e:
            logging.error(str(e))
            sys.exit(1)

        # 2. Extract model name for offline estimation (Purely offline)
        # Defaults to gpt-4o-mini if not specified. Avoids ModelManager to prevent early side-effects.
        estimated_model = args.model or "gpt-4o-mini"

        # 3. Estimate cost if requested (Strictly Offline Terminal Flow)
        if args.estimate_cost:
            estimation = CostEstimator.estimate_cost(
                args.folder,
                languages,
                estimated_model,
                fix_fuzzy=args.fix_fuzzy,
                respect_gitignore=respect_gitignore
            )

            print(f"\n{'='*40}")
            print("   OFFLINE TOKEN ESTIMATION REPORT")
            print(f"{'='*40}")
            print(f"Model:          {estimation['model']}")
            print(f"Rate:           {estimation['rate_info']}")
            print(f"Unique msgids:  {estimation['unique_texts']:,}")
            print(f"Total Tokens:   {estimation['total_tokens']:,} (estimated expansion included)")

            if estimation['estimated_cost'] is not None:
                print(f"Estimated Cost: ${estimation['estimated_cost']:.4f}")
            
            print("\nPer-language Breakdown:")
            for lang, data in estimation['breakdown'].items():
                cost_str = f"${data['cost']:.4f}" if data['cost'] is not None else "unavailable"
                print(f"  - {lang:5}: {data['tokens']:8,} tokens | {cost_str}")

            print(f"{'='*40}\n")
            
            if estimation['total_tokens'] == 0:
                logging.info("No entries require translation.")
                return

            if not args.yes:
                confirm = input("Run actual translation with these settings? (y/n): ").lower()
                if confirm != 'y':
                    logging.info("Cancelled by user.")
                    return

            # Issue #57: Hard exit after estimation to ensure zero side effects.
            # Estimation is a terminal dry-run. This prevents "Registered provider" logs
            # or connection attempts from leaking into the audit output.
            print(
                "\n[Audit Successful] To proceed with actual translation, "
                "run the command again WITHOUT --estimate-cost."
            )
            return

        # 4. Initialize providers (Online Execution Path Starts Here)
        # Localize imports to ensure strictly offline estimation phase
        from .models.config import TranslationConfig, TranslationFlags
        from .utils.cli import create_language_mapping

        provider_clients, provider, final_model_id = get_offline_provider_info(args)
        provider_clients, provider, model = initialize_provider(args, provider_clients, provider, final_model_id)

        # 5. Create mapping between language codes and detailed names
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
