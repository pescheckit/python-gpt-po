"""
PO file handling service for the PO translator.
This module provides utilities for working with PO files, including reading, writing,
language detection, and translation status tracking.
"""
import logging
import os

import polib
import pycountry

from ..utils.po_entry_helpers import is_entry_untranslated


class POFileHandler:
    """Handles operations related to .po files."""

    @staticmethod
    def disable_fuzzy_translations(po_file_path):
        """Disables fuzzy translations in a .po file."""
        try:
            # Read the file content
            with open(po_file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Remove fuzzy markers from the content
            content = content.replace('#, fuzzy\n', '')

            # Write the updated content back to the file
            with open(po_file_path, 'w', encoding='utf-8') as file:
                file.write(content)

            # Load the .po file and remove fuzzy flags from entries
            po_file = polib.pofile(po_file_path)
            fuzzy_entries = [entry for entry in po_file if 'fuzzy' in entry.flags]
            for entry in fuzzy_entries:
                entry.flags.remove('fuzzy')

            # Remove 'Fuzzy' from the metadata if present
            if po_file.metadata:
                po_file.metadata.pop('Fuzzy', None)

            # Save the updated .po file
            po_file.save(po_file_path)
            logging.info("Fuzzy translations disabled in file: %s", po_file_path)

        except Exception as e:
            logging.error("Error while disabling fuzzy translations in file %s: %s", po_file_path, e)

    @staticmethod
    def get_file_language(po_file_path, po_file, languages, folder_language):
        """Determines the language for a .po file.

        Args:
            po_file_path (str): Path to the .po file
            po_file (polib.POFile): Loaded PO file object
            languages (List[str]): List of valid language codes
            folder_language (bool): Whether to infer language from folder structure

        Returns:
            str or None: The matched language code or None if not found
        """
        file_lang = po_file.metadata.get('Language', '')

        # Debug logging for language matching issues
        if file_lang in ['zh_Hans', 'no']:
            logging.debug("Checking Django special code %s against languages: %s", file_lang, languages)

        # Try exact match first (e.g., fr_CA matches fr_CA, zh_Hans matches zh_Hans)
        if file_lang in languages:
            logging.info("Matched language for .po file: %s as %s", po_file_path, file_lang)
            return file_lang

        # Try converting underscore to hyphen (fr_CA -> fr-CA, zh_Hans -> zh-Hans)
        if '_' in file_lang:
            hyphen_lang = file_lang.replace('_', '-')
            if hyphen_lang in languages:
                return hyphen_lang

        # Try converting hyphen to underscore (fr-CA -> fr_CA, zh-Hans -> zh_Hans)
        if '-' in file_lang:
            underscore_lang = file_lang.replace('-', '_')
            if underscore_lang in languages:
                return underscore_lang

        # Try base language fallback (fr_CA -> fr)
        # Special handling for Django codes that shouldn't fallback
        if file_lang in ['zh_Hans', 'zh_Hant', 'sr_Latn', 'sr@latin', 'be@tarask']:
            # These special codes should not fallback to base language
            pass
        else:
            # Standard locale codes should fallback to base language
            normalized_lang = POFileHandler.normalize_language_code(file_lang)
            if normalized_lang and normalized_lang in languages:
                return normalized_lang

        if folder_language:
            for part in po_file_path.split(os.sep):
                # Try exact match first
                if part in languages:
                    logging.info("Inferred language for .po file: %s as %s", po_file_path, part)
                    return part

                # Try converting underscore to hyphen (fr_CA -> fr-CA)
                if '_' in part:
                    hyphen_part = part.replace('_', '-')
                    if hyphen_part in languages:
                        logging.info("Inferred language for .po file: %s as %s (converted from %s)",
                                     po_file_path, hyphen_part, part)
                        return hyphen_part

                # Try converting hyphen to underscore (fr-CA -> fr_CA)
                if '-' in part:
                    underscore_part = part.replace('-', '_')
                    if underscore_part in languages:
                        logging.info("Inferred language for .po file: %s as %s (converted from %s)",
                                     po_file_path, underscore_part, part)
                        return underscore_part

                # Try base language fallback (fr_CA -> fr, fr-CA -> fr)
                # But skip certain Django special codes that shouldn't fallback
                if part not in ['zh_Hans', 'zh_Hant', 'sr_Latn', 'sr@latin', 'be@tarask']:
                    norm_part = POFileHandler.normalize_language_code(part)
                    if norm_part and norm_part in languages:
                        logging.info("Inferred language for .po file: %s as %s (base of %s)",
                                     po_file_path, norm_part, part)
                        return norm_part

        return None

    @staticmethod
    def _is_django_special_code(lang):
        """Check if a language code is a Django special code that shouldn't be normalized.

        Args:
            lang (str): Language code to check

        Returns:
            bool: True if it's a Django special code
        """
        # Comprehensive list of Django special codes that don't follow standard patterns
        django_special_codes = {
            # Chinese variants (script-based)
            'zh_Hans', 'zh_Hant',
            'zh-hans', 'zh-hant',  # Hyphenated variants
            'zh_CN', 'zh_TW', 'zh_HK', 'zh_MO', 'zh_MY', 'zh_SG',  # Regional Chinese

            # Serbian variants (script-based)
            'sr_Latn', 'sr-latn', 'sr@latin',

            # Norwegian variants
            'no', 'nb', 'nn',  # Norwegian (no), Bokmål (nb), Nynorsk (nn)

            # Belarusian variant
            'be@tarask',

            # Other special regional codes
            'en_AU', 'en_GB',  # English variants
            'es_AR', 'es_CO', 'es_MX', 'es_NI', 'es_VE',  # Spanish variants
            'pt_BR',  # Portuguese variant
            'ar_DZ',  # Arabic variant
            'fy_NL',  # Frisian
        }

        # Check exact match
        if lang in django_special_codes:
            return True

        # Check with case variations
        if lang.lower() in {code.lower() for code in django_special_codes}:
            return True

        # Check if it's a variant with @ or has script/region codes
        if '@' in lang or '_' in lang and len(lang) > 3:
            parts = lang.replace('-', '_').split('_')
            if len(parts) == 2 and (len(parts[1]) > 2 or parts[1].isupper()):
                return True

        return False

    @staticmethod
    def normalize_language_code(lang):
        """Convert language name or code to ISO 639-1 base code.

        This function extracts the base language from locale codes.
        For example: fr_CA -> fr, en_US -> en, pt_BR -> pt

        Special handling for Django language codes like zh_Hans, zh_Hant, etc.

        Args:
            lang (str): Language name, code, or locale to normalize

        Returns:
            str or None: The base ISO 639-1 language code or None if not found
        """
        if not lang:
            return None

        # Special handling for Django language codes that should be kept as-is
        # These are valid Django language codes that don't follow the typical pattern
        django_special_mapping = {
            # Chinese script variants
            'zh_Hans': 'zh', 'zh-hans': 'zh',  # Simplified Chinese
            'zh_Hant': 'zh', 'zh-hant': 'zh',  # Traditional Chinese
            'zh_CN': 'zh', 'zh_TW': 'zh', 'zh_HK': 'zh',  # Regional Chinese
            'zh_MO': 'zh', 'zh_MY': 'zh', 'zh_SG': 'zh',

            # Serbian script variants
            'sr_Latn': 'sr', 'sr-latn': 'sr', 'sr@latin': 'sr',  # Serbian Latin

            # Norwegian variants
            'no': 'no',  # Norwegian (kept as-is)
            'nb': 'nb',  # Norwegian Bokmål
            'nn': 'nn',  # Norwegian Nynorsk

            # Belarusian variant
            'be@tarask': 'be',  # Belarusian Taraskievica
        }

        if lang in django_special_mapping:
            return django_special_mapping[lang]

        # Handle locale codes (e.g., fr_CA, en_US, pt_BR)
        # Extract the language part before underscore or dash
        if '_' in lang or '-' in lang:
            base_lang = lang.split('_')[0] if '_' in lang else lang.split('-')[0]
            # Recursively normalize the base language part
            return POFileHandler.normalize_language_code(base_lang)

        # Try direct lookup for 2-letter codes
        if len(lang) == 2:
            try:
                return pycountry.languages.get(alpha_2=lang.lower()).alpha_2
            except AttributeError:
                pass

        # Try by name
        try:
            return pycountry.languages.get(name=lang.title()).alpha_2
        except AttributeError:
            pass

        # Try by native name
        for language in pycountry.languages:
            if hasattr(language, 'inverted_name') and language.inverted_name.lower() == lang.lower():
                return language.alpha_2

        return None

    @staticmethod
    def log_translation_status(po_file_path, original_texts, translations):
        """Logs the status of translations for a .po file.

        Args:
            po_file_path (str): Path to the .po file
            original_texts (List[str]): List of original texts to translate
            translations (List[str]): List of translated texts
        """
        total = len(original_texts)
        translated = sum(1 for t in translations if t)

        # Log a warning if there are untranslated texts
        if translated < total:
            logging.warning(
                "File: %s - %s/%s texts translated. Some translations are missing.",
                po_file_path, translated, total
            )
            for original, translation in zip(original_texts, translations):
                if not translation:
                    logging.warning("Missing translation for: '%s'", original)
        else:
            logging.info("File: %s - All %s texts successfully translated.", po_file_path, total)

    @staticmethod
    def update_po_entry(po_file, original_text, translated_text, mark_ai_generated=True):
        """Updates a .po file entry with the translated text.

        Args:
            po_file (polib.POFile): The PO file object
            original_text (str): The original text to find
            translated_text (str): The translated text to set
            mark_ai_generated (bool): Whether to mark this translation as AI-generated
        """
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text

            # Add AI-generated comment if enabled
            if mark_ai_generated:
                ai_comment = "AI-generated"
                if not entry.comment or ai_comment not in entry.comment:
                    if entry.comment:
                        entry.comment = f"{entry.comment}\n{ai_comment}"
                    else:
                        entry.comment = ai_comment

            logging.debug("Updated translation for '%s' to '%s'", original_text, translated_text)
        else:
            logging.warning("Original text '%s' not found in the .po file.", original_text)

    @staticmethod
    def read_po_file(po_file_path):
        """Reads a .po file and returns the PO file object.

        Args:
            po_file_path (str): Path to the .po file

        Returns:
            polib.POFile: The loaded PO file object
        """
        try:
            return polib.pofile(po_file_path)
        except Exception as e:
            logging.error("Error reading .po file %s: %s", po_file_path, e)
            return None

    @staticmethod
    def save_po_file(po_file, po_file_path):
        """Saves changes to a .po file.

        Args:
            po_file (polib.POFile): The PO file object to save
            po_file_path (str): Path where the file should be saved

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            po_file.save(po_file_path)
            logging.info("Successfully saved translations to %s", po_file_path)
            return True
        except Exception as e:
            logging.error("Error saving .po file %s: %s", po_file_path, e)
            return False

    @staticmethod
    def get_untranslated_entries(po_file):
        """Gets all untranslated entries from a PO file.

        Args:
            po_file (polib.POFile): The PO file object

        Returns:
            List[polib.POEntry]: List of untranslated entries
        """
        return [entry for entry in po_file if is_entry_untranslated(entry)]

    @staticmethod
    def extract_metadata(po_file):
        """Extracts and returns metadata from a PO file.

        Args:
            po_file (polib.POFile): The PO file object

        Returns:
            dict: Dictionary containing metadata
        """
        metadata = {}
        if po_file.metadata:
            metadata = {
                'language': po_file.metadata.get('Language', ''),
                'project': po_file.metadata.get('Project-Id-Version', ''),
                'last_translator': po_file.metadata.get('Last-Translator', ''),
                'language_team': po_file.metadata.get('Language-Team', '')
            }
        return metadata

    @staticmethod
    def get_ai_generated_entries(po_file):
        """Gets all AI-generated entries from a PO file.

        Args:
            po_file (polib.POFile): The PO file object

        Returns:
            List[polib.POEntry]: List of AI-generated entries
        """
        ai_generated = []
        for entry in po_file:
            if entry.comment and "AI-generated" in entry.comment:
                ai_generated.append(entry)
        return ai_generated

    @staticmethod
    def remove_ai_generated_comments(po_file):
        """Removes AI-generated comments from all entries in a PO file.

        Args:
            po_file (polib.POFile): The PO file object
        """
        for entry in po_file:
            if entry.comment and "AI-generated" in entry.comment:
                # Remove the AI-generated line from the comment
                comment_lines = entry.comment.split('\n')
                comment_lines = [line for line in comment_lines if "AI-generated" not in line]
                entry.comment = '\n'.join(comment_lines).strip()
                if not entry.comment:
                    entry.comment = None
