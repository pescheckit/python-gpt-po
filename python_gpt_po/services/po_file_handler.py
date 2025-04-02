"""
PO file handling service for the PO translator.
This module provides utilities for working with PO files, including reading, writing,
language detection, and translation status tracking.
"""
import logging
import os

import polib
import pycountry


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
            str or None: The normalized language code or None if not found
        """
        file_lang = po_file.metadata.get('Language', '')
        normalized_lang = POFileHandler.normalize_language_code(file_lang)

        if normalized_lang in languages:
            return normalized_lang

        if folder_language:
            for part in po_file_path.split(os.sep):
                norm_part = POFileHandler.normalize_language_code(part)
                if norm_part in languages:
                    logging.info("Inferred language for .po file: %s as %s", po_file_path, norm_part)
                    return norm_part

        return None

    @staticmethod
    def normalize_language_code(lang):
        """Convert language name or code to ISO 639-1 code.

        Args:
            lang (str): Language name or code to normalize

        Returns:
            str or None: The normalized ISO 639-1 language code or None if not found
        """
        if not lang:
            return None

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
    def update_po_entry(po_file, original_text, translated_text):
        """Updates a .po file entry with the translated text.

        Args:
            po_file (polib.POFile): The PO file object
            original_text (str): The original text to find
            translated_text (str): The translated text to set
        """
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text
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
        return [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]

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
