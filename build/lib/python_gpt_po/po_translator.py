"""
Module docstring: This module provides functionality for translating .po files
using OpenAI's GPT models. It supports bulk and individual translation modes.
"""

import argparse
import logging
import os
import time

import polib
from dotenv import load_dotenv
from openai import OpenAI
from python_gpt_po.version import __version__

# Initialize environment variables and logging
load_dotenv()
logging.basicConfig(level=logging.INFO)


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

    def __init__(self, config):
        self.config = config
        self.batch_size = 50
        self.total_batches = 0

    def translate_bulk(self, texts, target_language, po_file_path, current_batch):
        """Translates a list of texts in bulk and handles retries."""
        translated_texts = []
        for i, _ in enumerate(range(0, len(texts), self.batch_size), start=current_batch):
            batch_texts = texts[i:i + self.batch_size]
            batch_info = f"File: {po_file_path}, Batch {i}/{self.total_batches}"
            batch_info += f" (texts {i + 1}-{min(i + self.batch_size, len(texts))})"
            translation_request = f"Translate the following texts into {target_language}:\n\n"
            translation_request += "\n\n".join(batch_texts)
            retries = 3

            while retries:
                try:
                    if self.config.bulk_mode:
                        logging.info("Translating %s.", batch_info)
                    self.perform_translation(translation_request, translated_texts)
                    break
                except Exception as e:  # pylint: disable=W0718
                    error_message = f"Error in translating {batch_info}: {e}. Retrying... {retries - 1} attempts left."
                    logging.error(error_message)
                    if retries <= 1:
                        logging.error("Maximum retries reached for %s. Skipping this batch.", batch_info)
                        translated_texts.extend(['Error in translation'] * len(batch_texts))
                    retries -= 1
                    time.sleep(1)

        return translated_texts

    def perform_translation(self, translation_request, translated_texts):
        """Performs the translation and updates the results."""
        message = {"role": "user", "content": translation_request}
        completion = self.config.client.chat.completions.create(model=self.config.model, messages=[message])
        batch_translations = completion.choices[0].message.content.strip().split('\n\n')
        translated_texts.extend(batch_translations)

    def scan_and_process_po_files(self, input_folder, languages):
        """Scans and processes .po files in the given input folder."""
        for root, _, files in os.walk(input_folder):
            for file in filter(lambda f: f.endswith(".po"), files):
                po_file_path = os.path.join(root, file)
                logging.info("Discovered .po file: %s", po_file_path)  # Log each discovered file
                self.process_po_file(po_file_path, languages)

    def process_po_file(self, po_file_path, languages):
        """Processes an individual .po file."""
        try:
            po_file = polib.pofile(po_file_path)
            file_lang = po_file.metadata.get('Language', '')

            # If language is not in the list, try inferring from any part of the directory
            if not file_lang or file_lang not in languages:
                if self.config.folder_language:
                    folder_parts = po_file_path.split(os.sep)
                    inferred_lang = next((part for part in folder_parts if part in languages), None)
                    logging.info("Attempting to infer language for .po file: %s", po_file_path)
                    if inferred_lang:
                        file_lang = inferred_lang
                        logging.info("Inferred language for .po file: %s as %s", po_file_path, file_lang)
                    else:
                        logging.warning("Skipping .po file due to inferred language mismatch: %s", po_file_path)
                        return
                else:
                    logging.warning("Skipping .po file due to language mismatch: %s", po_file_path)
                    return

            # Process the file if language matches
            if file_lang in languages:
                texts_to_translate = [
                    entry.msgid
                    for entry in po_file
                    if not entry.msgstr and entry.msgid and (self.config.fuzzy or 'fuzzy' not in entry.flags)
                ]
                self.process_translations(texts_to_translate, file_lang, po_file, po_file_path)

                po_file.save(po_file_path)
                logging.info("Finished processing .po file: %s", po_file_path)
        except Exception as e:  # pylint: disable=W0718
            logging.error("Error processing file %s: %s", po_file_path, e)

    def process_translations(self, texts, target_language, po_file, po_file_path):
        """Processes translations either in bulk or one by one."""
        if self.config.bulk_mode:
            self.translate_in_bulk(texts, target_language, po_file, po_file_path)
        else:
            self.translate_one_by_one(texts, target_language, po_file, po_file_path)

    def translate_in_bulk(self, texts, target_language, po_file, po_file_path):
        """Translates texts in bulk and applies them to the .po file."""
        self.total_batches = (len(texts) - 1) // 50 + 1
        translated_texts = self.translate_bulk(texts, target_language, po_file_path, 0)
        self.apply_translations_to_po_file(translated_texts, texts, po_file)

    def translate_one_by_one(self, texts, target_language, po_file, po_file_path):
        """Translates texts one by one and updates the .po file."""
        for index, text in enumerate(texts):
            logging.info("Translating text %s/%s in file %s", (index + 1), len(texts), po_file_path)
            translated_text = self.translate_bulk([text], target_language, po_file_path, index)[0]
            self.apply_translations_to_po_file(translated_text, texts, po_file)

    def update_po_entry(self, po_file, original_text, translated_text):
        """Updates a .po file entry with the translated text."""
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text

    def apply_translations_to_po_file(self, translated_texts, original_texts, po_file):
        """Applies the list of translations to the corresponding .po file entries."""
        for original, translated in zip(original_texts, translated_texts):
            if not translated.startswith("Error in translation"):
                self.update_po_entry(po_file, original, translated)


def main():
    """Main function to parse arguments and initiate processing."""
    parser = argparse.ArgumentParser(description="Scan and process .po files")
    parser.add_argument("--version", action="version", version=f'%(prog)s {__version__}')
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    parser.add_argument("--bulk", action="store_true", help="Use bulk translation mode")
    parser.add_argument("--bulksize", type=int, default=50, help="Batch size for bulk translation")
    parser.add_argument("--model", default="gpt-3.5-turbo-1106", help="OpenAI model to use for translations")
    parser.add_argument("--api_key", help="OpenAI API key")
    parser.add_argument("--folder-language", action="store_true", help="Set language from directory structure")

    args = parser.parse_args()

    # Initialize OpenAI client
    api_key = args.api_key if args.api_key else os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Create a configuration object
    config = TranslationConfig(client, args.model, args.bulk, args.fuzzy, args.folder_language)

    # Initialize the translation service with the configuration object
    translation_service = TranslationService(config)

    # Extract languages
    languages = [lang.strip() for lang in args.lang.split(',')]
    translation_service.scan_and_process_po_files(args.folder, languages)


if __name__ == "__main__":
    main()