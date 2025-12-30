"""
Language detection service for PO files.
"""

import logging
import os
from typing import List, Optional, Set

import pycountry

from ..utils.gitignore import create_gitignore_parser
from .po_file_handler import POFileHandler


class LanguageDetector:
    """Detects languages from PO files in a directory."""

    # Cache for valid language codes
    _valid_codes_cache: Optional[Set[str]] = None

    @classmethod
    def _get_valid_language_codes(cls) -> Set[str]:
        """Get a set of all valid language codes using pycountry and known Django codes."""
        if cls._valid_codes_cache is not None:
            return cls._valid_codes_cache

        valid_codes = set()

        # Add ISO 639-1 codes (2-letter codes like 'en', 'fr')
        for lang in pycountry.languages:
            if hasattr(lang, 'alpha_2'):
                valid_codes.add(lang.alpha_2)
            if hasattr(lang, 'alpha_3'):
                # Also add 3-letter codes
                valid_codes.add(lang.alpha_3)

        # Add locale codes with country (like 'en_US', 'pt_BR')
        for country in pycountry.countries:
            if hasattr(country, 'alpha_2'):
                country_code = country.alpha_2
                # Common combinations
                common_langs = [
                    'en', 'es', 'fr', 'de', 'pt', 'zh', 'ar', 'ru', 'ja', 'ko',
                    'it', 'nl', 'pl', 'tr', 'sv', 'da', 'no', 'fi', 'uk', 'cs',
                    'hu', 'ro', 'bg', 'hr', 'sr', 'sl', 'sk', 'lt', 'lv', 'et',
                    'hi', 'ur', 'bn', 'ta', 'te', 'mr', 'gu', 'kn', 'ml', 'pa', 'ne'
                ]
                for lang_code in common_langs:
                    valid_codes.add(f"{lang_code}_{country_code}")
                    valid_codes.add(f"{lang_code}-{country_code}")

        # Add Django special codes
        django_special = {
            'zh_Hans', 'zh_Hant', 'zh-hans', 'zh-hant',  # Chinese variants
            'sr_Latn', 'sr-latn', 'sr@latin',  # Serbian variants
            'be@tarask',  # Belarusian variant
            'en-us', 'en-gb', 'en-au', 'en-ca',  # English variants
            'es-es', 'es-mx', 'es-ar',  # Spanish variants
            'pt-pt', 'pt-br',  # Portuguese variants
            'no', 'nb', 'nn',  # Norwegian variants
        }
        valid_codes.update(django_special)

        cls._valid_codes_cache = valid_codes
        return valid_codes

    @staticmethod
    def detect_languages_from_folder(folder: str, use_folder_structure: bool = False,
                                     respect_gitignore: bool = True) -> List[str]:
        """
        Scan all PO files in a folder and detect their languages.

        Args:
            folder: Path to folder containing PO files
            use_folder_structure: If True, detect languages from folder names instead of metadata
            respect_gitignore: If True, respect .gitignore patterns when scanning

        Returns:
            List of unique language codes found in PO files

        Raises:
            ValueError: If no languages could be detected
        """
        if use_folder_structure:
            return LanguageDetector._detect_from_folder_structure(folder, respect_gitignore)

        return LanguageDetector._detect_from_metadata(folder, respect_gitignore)

    @staticmethod
    def _detect_from_folder_structure(folder: str, respect_gitignore: bool = True) -> List[str]:
        """Detect languages from folder structure based on common framework patterns."""
        languages = set()
        po_files_found = 0
        valid_codes = LanguageDetector._get_valid_language_codes()
        gitignore_parser = create_gitignore_parser(folder, respect_gitignore)

        for root, dirs, files in os.walk(folder):
            dirs[:], files = gitignore_parser.filter_walk_results(root, dirs, files)
            po_files_in_dir = [f for f in files if f.endswith('.po')]

            if not po_files_in_dir:
                continue

            for file in po_files_in_dir:
                po_files_found += 1
                relative_path = os.path.relpath(os.path.join(root, file), folder)
                path_parts = relative_path.split(os.sep)

                detected_lang = LanguageDetector._detect_language_from_path(
                    path_parts, file, valid_codes
                )

                if detected_lang:
                    languages.add(detected_lang)
                    logging.debug("Found language '%s' from path %s", detected_lang,
                                  os.path.join(root, file))

        LanguageDetector._validate_detection_results(po_files_found, languages)
        detected = sorted(list(languages))
        logging.info("Auto-detected languages from folder structure in %d PO files: %s",
                     po_files_found, ', '.join(detected))
        return detected

    @staticmethod
    def _detect_language_from_path(path_parts: List[str], filename: str,
                                   valid_codes: set) -> Optional[str]:
        """Detect language from a single file path using various patterns."""
        # Pattern 1: LC_MESSAGES structure
        detected_lang = LanguageDetector._detect_from_lc_messages(path_parts, valid_codes)
        if detected_lang:
            return detected_lang

        # Pattern 2: WordPress filename pattern
        detected_lang = LanguageDetector._detect_from_filename(filename, valid_codes)
        if detected_lang:
            return detected_lang

        # Pattern 3: Directory structure
        detected_lang = LanguageDetector._detect_from_directories(path_parts, valid_codes)
        if detected_lang:
            return detected_lang

        # Pattern 4: Flat structure
        return LanguageDetector._detect_from_flat_structure(filename, valid_codes)

    @staticmethod
    def _detect_from_lc_messages(path_parts: List[str], valid_codes: set) -> Optional[str]:
        """Detect language from LC_MESSAGES pattern."""
        if 'LC_MESSAGES' in path_parts:
            lc_idx = path_parts.index('LC_MESSAGES')
            if lc_idx > 0:
                potential_lang = path_parts[lc_idx - 1]
                if potential_lang in valid_codes or potential_lang.lower() in valid_codes:
                    return potential_lang
        return None

    @staticmethod
    def _detect_from_filename(filename: str, valid_codes: set) -> Optional[str]:
        """Detect language from WordPress-style filename pattern."""
        if '-' in filename:
            parts = filename.replace('.po', '').split('-')
            if len(parts) >= 2:
                potential_lang = parts[-1]
                if potential_lang in valid_codes or potential_lang.lower() in valid_codes:
                    return potential_lang
        return None

    @staticmethod
    def _detect_from_directories(path_parts: List[str], valid_codes: set) -> Optional[str]:
        """Detect language from directory structure."""
        locale_dirs = ['locale', 'locales', 'i18n', 'translations', 'lang', 'languages', 'po']

        for i, part in enumerate(path_parts[:-1]):  # Exclude filename
            if part in locale_dirs:
                continue

            if part in valid_codes or part.lower() in valid_codes:
                prev_is_locale = i > 0 and path_parts[i - 1] in locale_dirs
                is_po_parent = i == len(path_parts) - 2

                if prev_is_locale or is_po_parent:
                    return part
        return None

    @staticmethod
    def _detect_from_flat_structure(filename: str, valid_codes: set) -> Optional[str]:
        """Detect language from flat structure where filename is the language code."""
        if filename.endswith('.po'):
            lang_candidate = filename.replace('.po', '')
            if lang_candidate in valid_codes or lang_candidate.lower() in valid_codes:
                return lang_candidate
        return None

    @staticmethod
    def _validate_detection_results(po_files_found: int, languages: set):
        """Validate detection results and raise appropriate errors."""
        if not po_files_found:
            raise ValueError("No .po files found in folder")

        if not languages:
            raise ValueError(
                f"Could not detect any languages from folder structure in {po_files_found} .po files. "
                f"Please ensure your PO files are in language-named folders (e.g., locale/fr/), "
                f"or use -l to specify languages."
            )

    @staticmethod
    def _detect_from_metadata(folder: str, respect_gitignore: bool = True) -> List[str]:
        """Detect languages from PO file metadata."""
        languages = set()
        po_files_found = 0
        files_with_language = 0

        # Create gitignore parser for filtering
        gitignore_parser = create_gitignore_parser(folder, respect_gitignore)

        # Scan all PO files
        for root, dirs, files in os.walk(folder):
            # Filter directories and files using gitignore parser
            dirs[:], files = gitignore_parser.filter_walk_results(root, dirs, files)
            for file in files:
                if not file.endswith('.po'):
                    continue

                po_files_found += 1
                po_path = os.path.join(root, file)

                try:
                    # Load PO file and check metadata
                    po_file = POFileHandler.load_po_file(po_path)

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
        """Check if a string is a valid language code."""
        if not code or len(code) < 2:
            return False

        # Get valid codes
        valid_codes = LanguageDetector._get_valid_language_codes()

        # Check if code is valid (case-insensitive)
        if code in valid_codes or code.lower() in valid_codes:
            return True

        # Check with normalization
        normalized = code.replace('-', '_')
        if normalized in valid_codes or normalized.lower() in valid_codes:
            return True

        return False

    @staticmethod
    def validate_or_detect_languages(folder: str, lang_arg: str = None,
                                     use_folder_structure: bool = False,
                                     respect_gitignore: bool = True) -> List[str]:
        """
        Get languages from command line or auto-detect from PO files.

        Args:
            folder: Path to folder containing PO files
            lang_arg: Language argument from command line (optional)
            use_folder_structure: If True, detect languages from folder names instead of metadata
            respect_gitignore: If True, respect .gitignore patterns when scanning

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
            return LanguageDetector.detect_languages_from_folder(folder, use_folder_structure, respect_gitignore)
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
