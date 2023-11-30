import argparse
import logging
import os
import time

import polib
from dotenv import load_dotenv
from openai import OpenAI

# Initialize environment variables and logging
load_dotenv()
logging.basicConfig(level=logging.INFO)

def translate_text_bulk(texts, target_language, po_file_path, current_batch, total_batches, is_bulk, model, client):
    """Translates a list of texts in bulk and handles retries."""
    translated_texts = []
    batch_size = 50

    for i, _ in enumerate(range(0, len(texts), batch_size), start=current_batch):
        batch_texts = texts[i:i + batch_size]
        batch_info = f"File: {po_file_path}, Batch {i}/{total_batches} (texts {i + 1}-{min(i + batch_size, len(texts))})"
        translation_request = f"Translate the following texts into {target_language}:\n\n" + "\n\n".join(batch_texts)
        retries = 3

        while retries:
            try:
                if is_bulk:
                    logging.info(f"Translating {batch_info}.")
                perform_translation(batch_texts, translation_request, model, translated_texts, retries, batch_info, client)
                break
            except Exception as e:
                handle_translation_error(e, retries, batch_info, translated_texts, batch_texts)

    return translated_texts

def perform_translation(batch_texts, translation_request, model, translated_texts, retries, batch_info, client):
    """Performs the translation and updates the results."""
    # For the cheapest models or more acurate models check https://openai.com/pricing
    completion = client.chat.completions.create(model=model, messages=[{"role": "user", "content": translation_request}])
    batch_translations = completion.choices[0].message.content.strip().split('\n\n')
    translated_texts.extend(batch_translations)

def handle_translation_error(e, retries, batch_info, translated_texts, batch_texts):
    """Handles errors during translation attempts."""
    retries -= 1
    logging.error(f"Error in translating {batch_info}: {e}. Retrying... {retries} attempts left.")
    if not retries:
        logging.error(f"Maximum retries reached for {batch_info}. Skipping this batch.")
        translated_texts.extend(['Error in translation'] * len(batch_texts))
    time.sleep(1)

def scan_and_process_po_files(input_folder, languages, fuzzy, bulk_mode, model, client):
    """Scans and processes .po files in the given input folder."""
    for root, dirs, files in os.walk(input_folder):
        for file in filter(lambda f: f.endswith(".po"), files):
            po_file_path = os.path.join(root, file)
            process_po_file(po_file_path, languages, fuzzy, bulk_mode, model, client)

def process_po_file(po_file_path, languages, fuzzy, bulk_mode, model, client):
    """Processes an individual .po file."""
    try:
        po_file = polib.pofile(po_file_path)
        file_lang = po_file.metadata.get('Language', '')
        if file_lang in languages:
            texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr and entry.msgid and not (fuzzy and 'fuzzy' in entry.flags)]
            process_translations(texts_to_translate, file_lang, po_file, po_file_path, bulk_mode, model, client)

            po_file.save(po_file_path)
            logging.info(f"Finished processing .po file: {po_file_path}")
    except Exception as e:
        logging.error(f"Error processing file {po_file_path}: {e}")

def process_translations(texts, target_language, po_file, po_file_path, bulk_mode, model, client):
    """Processes translations either in bulk or one by one."""
    if bulk_mode:
        translate_in_bulk(texts, target_language, po_file, po_file_path, model, client)
    else:
        translate_one_by_one(texts, target_language, po_file, po_file_path, model, client)

def translate_in_bulk(texts, target_language, po_file, po_file_path, model, client):
    """Translates texts in bulk and applies them to the .po file."""
    total_batches = (len(texts) - 1) // 50 + 1
    translated_texts = translate_text_bulk(texts, target_language, po_file_path, 0, total_batches, True, model, client)
    apply_translations_to_po_file(translated_texts, texts, po_file)

def translate_one_by_one(texts, target_language, po_file, po_file_path, model, client):
    """Translates texts one by one and updates the .po file."""
    for index, text in enumerate(texts):
        logging.info(f"Translating text {index + 1}/{len(texts)} in file {po_file_path}")
        translated_text = translate_text_bulk([text], target_language, po_file_path, index, len(texts), False, model, client)[0]
        update_po_entry(po_file, text, translated_text)

def update_po_entry(po_file, original_text, translated_text):
    """Updates a .po file entry with the translated text."""
    entry = po_file.find(original_text)
    if entry:
        entry.msgstr = translated_text

def apply_translations_to_po_file(translated_texts, original_texts, po_file):
    """Applies the list of translations to the corresponding .po file entries."""
    for original, translated in zip(original_texts, translated_texts):
        if not translated.startswith("Error in translation"):
            update_po_entry(po_file, original, translated)

def main():
    """Main function to parse arguments and initiate processing."""
    parser = argparse.ArgumentParser(description="Scan and process .po files")
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    parser.add_argument("--bulk", action="store_true", help="Use bulk translation mode")
    parser.add_argument("--bulksize", type=int, default=50, help="Batch size for bulk translation")
    # Default model is fast and cheap, but you can also use gpt-4 or others see https://openai.com/pricing
    parser.add_argument("--model", default="gpt-3.5-turbo-1106", help="OpenAI model to use for translations")
    parser.add_argument("--api_key", help="OpenAI API key")

    args = parser.parse_args()

    # Initialize OpenAI client with either provided API key or from .env file
    api_key = args.api_key if args.api_key else os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    # Pass the client to the function that requires it
    languages = [lang.strip() for lang in args.lang.split(',')]
    scan_and_process_po_files(args.folder, languages, args.fuzzy, args.bulk, args.model, client)

if __name__ == "__main__":
    main()
