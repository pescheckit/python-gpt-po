"""
Language detection service for PO files.
"""

import logging
import os
import re
from typing import List

import polib


class LanguageDetector:
    """Detects languages from PO files in a directory."""

    @staticmethod
    def detect_languages_from_folder(folder: str, use_folder_structure: bool = False) -> List[str]:
        """
        Scan all PO files in a folder and detect their languages.

        Args:
            folder: Path to folder containing PO files
            use_folder_structure: If True, detect languages from folder names instead of metadata

        Returns:
            List of unique language codes found in PO files

        Raises:
            ValueError: If no languages could be detected
        """
        if use_folder_structure:
            return LanguageDetector._detect_from_folder_structure(folder)

        return LanguageDetector._detect_from_metadata(folder)

    @staticmethod
    def _detect_from_folder_structure(folder: str) -> List[str]:
        """Detect languages from folder structure (e.g., locale/it/LC_MESSAGES/)."""
        languages = set()
        po_files_found = 0

        # Scan all PO files
        for root, _, files in os.walk(folder):
            for file in files:
                if not file.endswith('.po'):
                    continue

                po_files_found += 1
                po_path = os.path.join(root, file)

                # Extract language code from path
                # Common patterns: locale/it/LC_MESSAGES/, it/, locale/it/, etc.
                relative_path = os.path.relpath(po_path, folder)
                path_parts = relative_path.split(os.sep)

                # Look for language codes in path components
                for part in path_parts:
                    # Skip common directory names
                    if part in ['locale', 'locales', 'LC_MESSAGES', 'po', 'i18n', 'translations']:
                        continue
                    if part.endswith('.po'):
                        continue

                    # Check if this looks like a language code
                    if LanguageDetector._is_language_code(part):
                        languages.add(part)
                        logging.debug("Found language '%s' from path %s", part, po_path)
                        break

        if not po_files_found:
            raise ValueError(f"No .po files found in folder: {folder}")

        if not languages:
            raise ValueError(
                f"Could not detect any languages from folder structure in {po_files_found} .po files. "
                f"Please ensure your PO files are in language-named folders (e.g., locale/fr/), "
                f"or use -l to specify languages."
            )

        # Convert to sorted list for consistent ordering
        detected = sorted(list(languages))

        logging.info("Auto-detected languages from folder structure in %d PO files: %s",
                     po_files_found, ', '.join(detected))

        return detected

    @staticmethod
    def _detect_from_metadata(folder: str) -> List[str]:
        """Detect languages from PO file metadata."""
        languages = set()
        po_files_found = 0
        files_with_language = 0

        # Scan all PO files
        for root, _, files in os.walk(folder):
            for file in files:
                if not file.endswith('.po'):
                    continue

                po_files_found += 1
                po_path = os.path.join(root, file)

                try:
                    # Load PO file and check metadata
                    po_file = polib.pofile(po_path)

                    # Try to get language from metadata
                    language = po_file.metadata.get('Language', '').strip()

                    if language:
                        languages.add(language)
                        files_with_language += 1
                        logging.debug("Found language '%s' in %s", language, po_path)
                    else:
                        logging.debug("No language metadata in %s", po_path)

                except Exception as e:
                    logging.warning("Error reading PO file %s: %s", po_path, str(e))

        if not po_files_found:
            raise ValueError(f"No .po files found in folder: {folder}")

        if not languages:
            raise ValueError(
                f"Could not detect any languages from {po_files_found} .po files. "
                f"Please ensure your PO files have 'Language' metadata set, or use -l to specify languages."
            )

        # Convert to sorted list for consistent ordering
        detected = sorted(list(languages))

        logging.info("Auto-detected languages from %d/%d PO files: %s",
                     files_with_language, po_files_found, ', '.join(detected))

        return detected

    @staticmethod
    def _is_language_code(code: str) -> bool:
        """Check if a string looks like a language code."""
        # Basic validation
        if not code or len(code) < 2 or len(code) > 10 or not code[0].isalpha():
            return False

        # Common language code patterns:
        # - 2-letter codes: en, fr, de, etc.
        # - 2+2 codes: en_US, fr_FR, etc.
        # - Special codes: zh_Hans, sr_Latn, be@tarask, etc.

        # Special cases used in Django
        special_codes = {
            'zh-hans', 'zh-hant', 'sr-latn', 'sr-cyrl', 'az-latn', 'az-cyrl',
            'uz-latn', 'uz-cyrl', 'kk-latn', 'kk-cyrl', 'ky-latn', 'ky-cyrl'
        }

        # Check all valid patterns
        pattern_match = re.match(r'^[a-z]{2,3}(_[A-Z][a-z]+|_[A-Z]{2}|@[a-z]+)?$', code) is not None
        in_special = code.lower() in special_codes
        basic_match = re.match(r'^[a-z]{2,3}$', code) is not None
        return pattern_match or in_special or basic_match

    @staticmethod
    def validate_or_detect_languages(folder: str, lang_arg: str = None,
                                     use_folder_structure: bool = False) -> List[str]:
        """
        Get languages from command line or auto-detect from PO files.

        Args:
            folder: Path to folder containing PO files
            lang_arg: Language argument from command line (optional)
            use_folder_structure: If True, detect languages from folder names instead of metadata

        Returns:
            List of language codes to process

        Raises:
            ValueError: If no languages provided and none could be detected
        """
        if lang_arg:
            # User provided languages explicitly (-l flag takes precedence)
            languages = [lang.strip() for lang in lang_arg.split(',')]
            logging.info("Using specified languages: %s", ', '.join(languages))
            return languages

        # No languages provided, try to auto-detect
        detection_method = "folder structure" if use_folder_structure else "PO file metadata"
        logging.info("No languages specified with -l, auto-detecting from %s...", detection_method)

        try:
            return LanguageDetector.detect_languages_from_folder(folder, use_folder_structure)
        except ValueError as e:
            # Re-raise with more helpful message
            if use_folder_structure:
                raise ValueError(
                    f"{str(e)}\n\n"
                    f"To fix this, either:\n"
                    f"1. Ensure your PO files are in language-named directories (e.g., locale/fr/)\n"
                    f"2. Specify target languages explicitly: -l fr,de,es\n"
                ) from e

            raise ValueError(
                f"{str(e)}\n\n"
                f"To fix this, either:\n"
                f"1. Add Language metadata to your PO files (e.g., 'Language: fr')\n"
                f"2. Specify target languages explicitly: -l fr,de,es\n"
                f"3. Use --folder-language to detect from directory structure\n"
            ) from e
