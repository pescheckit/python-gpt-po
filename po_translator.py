import argparse
import os
import time
import polib
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setting up logging
logging.basicConfig(level=logging.INFO)

BATCH_SIZE = 50

def translate_text_bulk(texts, target_language, po_file_path, current_batch, total_batches, is_bulk):
    translated_texts = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_info = f"File: {po_file_path}, Batch {current_batch + i // BATCH_SIZE}/{total_batches} (texts {i + 1}-{min(i + BATCH_SIZE, len(texts))})"
        translation_request = f"Translate the following texts into {target_language}:\n\n" + "\n\n".join(batch_texts)
        retries = 3

        while retries > 0:
            try:
                if is_bulk:  # Only log detailed batch info for bulk translations
                    logging.info(f"Translating {batch_info}.")
                    logging.debug(f"Text to translate {batch_texts}")
                    logging.debug(f"Retries {retries}")
                completion = client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[{"role": "user", "content": translation_request}])
                batch_translations = completion.choices[0].message.content.strip().split('\n\n')
                translated_texts.extend(batch_translations)
                break  # Break the loop if successful
            except Exception as e:
                retries -= 1
                logging.error(f"Error in translating {batch_info}: {e}. Retrying... {retries} attempts left.")
                if retries <= 0:
                    logging.error(f"Maximum retries reached for {batch_info}. Skipping this batch.")
                    translated_texts.extend(['Error in translation'] * len(batch_texts))
                time.sleep(1)  # Briefly pause before retrying

    return translated_texts

def scan_and_process_po_files(input_folder, languages, fuzzy, bulk_mode):
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".po"):
                try:
                    po_file_path = os.path.join(root, file)
                    po_file = polib.pofile(po_file_path)
                    file_lang = po_file.metadata.get('Language', '')
                    if file_lang in languages:
                        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr and entry.msgid and not (fuzzy and 'fuzzy' in entry.flags)]
                        total_items = len(texts_to_translate)
                        logging.info(f"Found {total_items} items to translate.")

                        if bulk_mode:
                            translate_in_bulk(texts_to_translate, file_lang, po_file, po_file_path)
                        else:
                            translate_one_by_one(texts_to_translate, file_lang, po_file, po_file_path)

                        po_file.save(po_file_path)
                        logging.info(f"Finished processing .po file: {po_file_path}")
                except Exception as e:
                    logging.error(f"Error processing file {po_file_path}: {e}")

def translate_in_bulk(texts, target_language, po_file, po_file_path):
    total_batches = (len(texts) - 1) // BATCH_SIZE + 1
    translated_texts = translate_text_bulk(texts, target_language, po_file_path, 0, total_batches, True)
    apply_translations_to_po_file(translated_texts, texts, po_file)

def translate_one_by_one(texts, target_language, po_file, po_file_path):
    for index, text in enumerate(texts):
        logging.info(f"Translating text {index + 1}/{len(texts)} in file {po_file_path}")
        translated_text = translate_text_bulk([text], target_language, po_file_path, index, len(texts), False)[0]
        entry = po_file.find(text)  # Corrected this line
        if entry:
            entry.msgstr = translated_text

def apply_translations_to_po_file(translated_texts, original_texts, po_file):
    for original, translated in zip(original_texts, translated_texts):
        if not translated.startswith("Error in translation"):
            entry = po_file.find(original)  # Corrected this line
            if entry:
                entry.msgstr = translated

def main():
    parser = argparse.ArgumentParser(description="Scan and process .po files")
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    parser.add_argument("--bulk", action="store_true", help="Use bulk translation mode")
    parser.add_argument("--bulksize", type=int, default=50, help="Batch size for bulk translation")

    args = parser.parse_args()
    languages = [lang.strip() for lang in args.lang.split(',')]

    # Set the global BATCH_SIZE based on the user input
    global BATCH_SIZE
    BATCH_SIZE = args.bulksize

    scan_and_process_po_files(args.folder, languages, args.fuzzy, args.bulk)

if __name__ == "__main__":
    main()
