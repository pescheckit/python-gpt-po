"""
GPT Translator
"""


import argparse
import json
import logging
import os

import polib
from dotenv import load_dotenv
from openai import OpenAI
from pkg_resources import DistributionNotFound, get_distribution
from tenacity import retry, stop_after_attempt, wait_fixed

# Initialize environment variables and logging
load_dotenv()
logging.basicConfig(level=logging.INFO)


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
        """Determines the language for a .po file."""
        # Attempt to get language from the file metadata first
        file_lang = po_file.metadata.get('Language', '')

        # If the file's language is not valid, infer it from the folder structure
        if not file_lang or file_lang not in languages:
            if folder_language:
                inferred_lang = next((part for part in po_file_path.split(os.sep) if part in languages), None)
                if inferred_lang:
                    logging.info("Inferred language for .po file: %s as %s", po_file_path, inferred_lang)
                    return inferred_lang
            return None
        return file_lang

    @staticmethod
    def log_translation_status(po_file_path, original_texts, translations):
        """Logs the status of translations for a .po file."""
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
        """Updates a .po file entry with the translated text."""
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text
            logging.debug("Updated translation for '%s' to '%s'", original_text, translated_text)
        else:
            logging.warning("Original text '%s' not found in the .po file.", original_text)


class TranslationConfig:
    """ Class to hold configuration parameters for the translation service. """
    def __init__(self, client, model, bulk_mode=False, fuzzy=False, folder_language=False):  # pylint: disable=R0913
        self.client = client
        self.model = model
        self.bulk_mode = bulk_mode
        self.fuzzy = fuzzy
        self.folder_language = folder_language


class TranslationService:
    """ Class to encapsulate translation functionalities. """

    def __init__(self, config, batch_size=40):
        self.config = config
        self.batch_size = batch_size  # Use the bulk size provided by the user
        self.total_batches = 0
        self.po_file_handler = POFileHandler()

    def validate_openai_connection(self):
        """Validates the OpenAI connection by making a test API call."""
        try:
            test_message = {"role": "system", "content": "Test message to validate connection."}
            self.config.client.chat.completions.create(model=self.config.model, messages=[test_message])
            logging.info("OpenAI connection validated successfully.")
            return True
        except Exception as e:
            logging.error("Failed to validate OpenAI connection: %s", str(e))
            return False

    def translate_bulk(self, texts, target_language, po_file_path):
        """Translates a list of texts in bulk, processing in smaller chunks."""
        translated_texts = []
        chunk_size = self.batch_size

        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            logging.info("Translating chunk %d of %d", i // chunk_size + 1, (len(texts) - 1) // chunk_size + 1)

            try:
                translations = self.perform_translation(chunk, target_language, is_bulk=True)
                translated_texts.extend(translations)
            except Exception as e:
                logging.error("Bulk translation failed for chunk %d: %s", i // chunk_size + 1, str(e))
                for text in chunk:
                    try:
                        translation = self.perform_translation(text, target_language, is_bulk=False)
                        translated_texts.append(translation)
                    except Exception as inner_e:
                        logging.error("Individual translation failed for text '%s': %s", text, str(inner_e))
                        translated_texts.append("")  # Placeholder for failed translation

            logging.info("Processed %d out of %d translations", len(translated_texts), len(texts))

        if len(translated_texts) != len(texts):
            logging.error(
                "Translation count mismatch in %s. Expected %d, got %d",
                po_file_path, len(texts), len(translated_texts)
            )

        return translated_texts

    def translate_single(self, text, target_language):
        """Translates a single text."""
        try:
            translation = self.perform_translation(text, target_language, is_bulk=False)
            if not translation.strip():
                logging.warning("Empty translation returned for '%s'. Attempting without validation.", text)
                translation = self.perform_translation_without_validation(text, target_language)
            return translation
        except Exception as e:
            logging.error("Error translating '%s': %s", text, str(e))
            return ""

    def perform_translation_without_validation(self, text, target_language):
        """Performs translation without validation for single words or short phrases."""
        prompt = (
            f"Translate this single word or short phrase from English to {target_language}. "
            "Return only the direct translation without any explanation, additional text, or repetition. "
            "If the word should not be translated (like technical terms or names), return it unchanged:\n"
        )
        message = {
            "role": "user",
            "content": prompt + text
        }
        try:
            completion = self.config.client.chat.completions.create(
                model=self.config.model,
                messages=[message]
            )
            return self.post_process_translation(text, completion.choices[0].message.content.strip())
        except Exception as e:
            logging.error("Error in perform_translation_without_validation: %s", str(e))
            return ""

    @staticmethod
    def post_process_translation(original, translated):
        """Post-processes the translation to handle repetitions and long translations."""
        if ' - ' in translated:
            parts = translated.split(' - ')
            if len(parts) == 2 and parts[0] == parts[1]:
                return parts[0]

        if len(translated.split()) > 2 * len(original.split()) + 1:
            logging.warning("Translation seems too long, might be an explanation: '%s'", translated)
            return original

        return translated

    @staticmethod
    def get_translation_prompt(target_language, is_bulk):
        """Returns the appropriate translation prompt based on the translation mode."""
        if is_bulk:
            return (
                f"Translate the following list of texts from English to {target_language}. "
                "Provide only the translations in a JSON array format, maintaining the original order. "
                "Each translation should be concise and direct, without explanations or additional context. "
                "Keep special characters, placeholders, and formatting intact. "
                "If a term should not be translated (like 'URL' or technical terms), keep it as is. "
                "Example format: [\"Translation 1\", \"Translation 2\", ...]\n\n"
                "Texts to translate:\n"
            )
        return (
            f"Translate the following text from English to {target_language}. "
            "Return only the direct, word-for-word translation without any explanation or additional context. "
            "Keep special characters, placeholders, and formatting intact. "
            "If a term should not be translated (like 'URL' or technical terms), keep it as is. "
            "Here is the text to translate:\n"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def perform_translation(self, texts, target_language, is_bulk=False):
        """Performs the actual translation using the OpenAI API."""
        logging.debug("Performing translation to: %s", target_language)  # Log the target language
        prompt = self.get_translation_prompt(target_language, is_bulk)
        message = {
            "role": "user",
            "content": prompt + (json.dumps(texts) if is_bulk else texts)
        }

        try:
            completion = self.config.client.chat.completions.create(
                model=self.config.model,
                messages=[message]
            )
            response = completion.choices[0].message.content.strip()

            if is_bulk:
                try:
                    translated_texts = json.loads(response)
                    if not isinstance(translated_texts, list) or len(translated_texts) != len(texts):
                        raise ValueError("Invalid response format")
                    return [
                        self.validate_translation(original, translated)
                        for original, translated in zip(texts, translated_texts)
                    ]
                except json.JSONDecodeError as e:
                    logging.error("Invalid JSON response: %s", response)
                    raise ValueError("Invalid JSON response") from e
            else:
                return self.validate_translation(texts, response)
        except Exception as e:
            logging.error("Translation error: %s", str(e))
            raise

    def validate_translation(self, original, translated):
        """Validates the translation and retries if necessary."""
        translated = translated.strip()

        if len(translated.split()) > 2 * len(original.split()) + 1:
            logging.warning("Translation too long, retrying: %s -> %s", original[:50], translated[:50])
            return self.retry_long_translation(original, self.config.model.split('-')[-1])

        explanation_indicators = ["I'm sorry", "I cannot", "This refers to", "This means", "In this context"]
        if any(indicator.lower() in translated.lower() for indicator in explanation_indicators):
            logging.warning("Translation contains explanation: %s", translated[:50])
            return self.retry_long_translation(original, self.config.model.split('-')[-1])

        return translated

    def retry_long_translation(self, text, target_language):
        """Retries translation for long or explanatory responses."""
        prompt = (
            f"Translate this text concisely from English to {target_language}. "
            "Provide only the direct translation without any explanation or additional context. "
            "Keep special characters, placeholders, and formatting intact. "
            "If a term should not be translated (like 'URL' or technical terms), keep it as is.\n"
            "Text to translate:\n"
        )
        message = {
            "role": "user",
            "content": prompt + text
        }
        try:
            completion = self.config.client.chat.completions.create(
                model=self.config.model,
                messages=[message]
            )
            retried_translation = completion.choices[0].message.content.strip()

            if len(retried_translation.split()) > 2 * len(text.split()) + 1:
                logging.warning("Retried translation still too long: %s -> %s", text[:50], retried_translation[:50])
                return text

            logging.info("Successfully retried translation: %s -> %s", text[:50], retried_translation[:50])
            return retried_translation
        except Exception as e:
            logging.error("Error in retry_long_translation: %s", str(e))
            return text

    def scan_and_process_po_files(self, input_folder, languages):
        """Scans and processes .po files in the given input folder."""
        for root, _, files in os.walk(input_folder):
            for file in filter(lambda f: f.endswith(".po"), files):
                logging.debug("File: %s", file)
                po_file_path = os.path.join(root, file)
                logging.info("Discovered .po file: %s", po_file_path)  # Log each discovered file
                self.process_po_file(po_file_path, languages)

    def process_po_file(self, po_file_path, languages):
        """Processes .po files"""
        try:
            po_file = self._prepare_po_file(po_file_path, languages)
            if not po_file:
                return

            # Use file_lang obtained from get_file_language method
            file_lang = self.po_file_handler.get_file_language(
                po_file_path,
                po_file,
                languages,
                self.config.folder_language
            )

            texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip() and entry.msgid]
            translations = self.get_translations(texts_to_translate, file_lang, po_file_path)

            self._update_po_entries(po_file, translations, file_lang)
            self._handle_untranslated_entries(po_file, file_lang)

            po_file.save(po_file_path)
            self.po_file_handler.log_translation_status(
                po_file_path,
                texts_to_translate,
                [entry.msgstr for entry in po_file if entry.msgid in texts_to_translate]
            )
        except Exception as e:
            logging.error("Error processing file %s: %s", po_file_path, e)

    def _prepare_po_file(self, po_file_path, languages):
        """Prepares the .po file for translation."""
        if self.config.fuzzy:
            self.po_file_handler.disable_fuzzy_translations(po_file_path)
        po_file = polib.pofile(po_file_path)
        file_lang = self.po_file_handler.get_file_language(
            po_file_path,
            po_file,
            languages,
            self.config.folder_language
        )
        if not file_lang:
            logging.warning("Skipping .po file due to language mismatch: %s", po_file_path)
            return None
        return po_file

    def get_translations(self, texts, target_language, po_file_path):
        """
        Retrieves translations for the given texts using either bulk or individual translation.
        """
        if self.config.bulk_mode:
            return self.translate_bulk(texts, target_language, po_file_path)
        return [self.translate_single(text, target_language) for text in texts]

    def _update_po_entries(self, po_file, translations, target_language):
        """Updates the .po file entries with the provided translations."""
        for entry, translation in zip((e for e in po_file if not e.msgstr.strip()), translations):
            if translation.strip():
                self.po_file_handler.update_po_entry(po_file, entry.msgid, translation)
                logging.info("Translated '%s' to '%s'", entry.msgid, translation)
            else:
                self._handle_empty_translation(entry, target_language)

    def _handle_empty_translation(self, entry, target_language):
        """Handles cases where the initial translation is empty."""
        logging.warning("Empty translation for '%s'. Attempting individual translation.", entry.msgid)
        individual_translation = self.translate_single(entry.msgid, target_language)
        if individual_translation.strip():
            self.po_file_handler.update_po_entry(entry.po_file, entry.msgid, individual_translation)
            logging.info(
                "Individual translation successful: '%s' to '%s'",
                entry.msgid,
                individual_translation
            )
        else:
            logging.error("Failed to translate '%s' after individual attempt.", entry.msgid)

    def _handle_untranslated_entries(self, po_file, target_language):
        """Handles any remaining untranslated entries in the .po file."""
        for entry in po_file:
            if not entry.msgstr.strip() and entry.msgid:
                logging.warning("Untranslated entry found: '%s'. Attempting final translation.", entry.msgid)
                final_translation = self.translate_single(entry.msgid, target_language)
                if final_translation.strip():
                    self.po_file_handler.update_po_entry(po_file, entry.msgid, final_translation)
                    logging.info(
                        "Final translation successful: '%s' to '%s'",
                        entry.msgid,
                        final_translation
                    )
                else:
                    logging.error("Failed to translate '%s' after final attempt.", entry.msgid)

    def translate_in_bulk(self, texts, target_language, po_file, po_file_path):
        """Translates texts in bulk and applies them to the .po file."""
        self.total_batches = (len(texts) - 1) // 50 + 1
        translated_texts = self.translate_bulk(texts, target_language, po_file_path)
        self.apply_translations_to_po_file(translated_texts, texts, po_file)

    def process_translations(self, texts, target_language, po_file, po_file_path):
        """Processes translations either in bulk or one by one."""
        if self.config.bulk_mode:
            self.translate_in_bulk(texts, target_language, po_file, po_file_path)
        else:
            self.translate_one_by_one(texts, target_language, po_file, po_file_path)

    def translate_one_by_one(self, texts, target_language, po_file, po_file_path):
        """Translates texts one by one and updates the .po file."""
        for index, text in enumerate(texts):
            logging.info(
                "Translating text %s/%s in file %s",
                (index + 1),
                len(texts),
                po_file_path
            )
            translation_request = f"Please translate the following text from English into {target_language}: {text}"
            translated_texts = []
            self.perform_translation(translation_request, translated_texts, is_bulk=False)
            if translated_texts:
                translated_text = translated_texts[0]["translation"]
                self.update_po_entry(po_file, text, translated_text)
            else:
                logging.error("No translation returned for text: %s", text)

    @staticmethod
    def update_po_entry(po_file, original_text, translated_text):
        """Updates a .po file entry with the translated text."""
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text

    @staticmethod
    def apply_translations_to_po_file(translated_texts, original_texts, po_file):
        """
        Applies the translated texts to the .po file.
        """
        # Create a mapping from original texts to translations
        translation_map = {
            original_text: translation["translation"]
            for original_text, translation in zip(original_texts, translated_texts)
        }

        for entry in po_file:
            if entry.msgid in translation_map:
                entry.msgstr = translation_map[entry.msgid]
                logging.info("Applied translation for '%s'", entry.msgid)
            elif not entry.msgstr:
                logging.warning("No translation applied for '%s'", entry.msgid)

        po_file.save()
        logging.info("Po file saved.")


def main():
    """Main function to parse arguments and initiate processing."""

    try:
        package_version = get_distribution("gpt-po-translator").version
    except DistributionNotFound:
        package_version = "0.0.0"  # Default version if the package is not found (e.g., during development)

    parser = argparse.ArgumentParser(description="Scan and process .po files")
    parser.add_argument("--version", action="version", version=f'%(prog)s {package_version}')
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    parser.add_argument("--bulk", action="store_true", help="Use bulk translation mode")
    parser.add_argument("--bulksize", type=int, default=50, help="Batch size for bulk translation")
    parser.add_argument("--model", default="gpt-3.5-turbo-0125", help="OpenAI model to use for translations")
    parser.add_argument("--api_key", help="OpenAI API key")
    parser.add_argument("--folder-language", action="store_true", help="Set language from directory structure")

    args = parser.parse_args()

    # Initialize OpenAI client
    api_key = args.api_key if args.api_key else os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Create a configuration object
    config = TranslationConfig(client, args.model, args.bulk, args.fuzzy, args.folder_language)

    # Initialize the translation service with the configuration object
    translation_service = TranslationService(config, args.bulksize)

    # Validate the OpenAI connection
    if not translation_service.validate_openai_connection():
        logging.error("OpenAI connection failed. Please check your API key and network connection.")
        return

    # Extract languages
    languages = [lang.strip() for lang in args.lang.split(',')]
    translation_service.scan_and_process_po_files(args.folder, languages)


if __name__ == "__main__":
    main()
