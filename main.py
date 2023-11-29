import argparse
import os
import polib
import openai
from dotenv import load_dotenv

def translate_text(text, target_language):
    """
    Translate the given text to the target language using OpenAI's gpt-4-1106-preview model.

    :param text: Text to translate.
    :param target_language: Language code to translate the text into.
    :return: Translated text.
    """
    completion = openai.ChatCompletion.create(
        model="gpt-4-1106-preview",
        messages=[
            {
                "role": "user",
                "content": f"Translate this into {target_language}: {text}",
            },
        ],
    )
    return completion.choices[0].message.content.strip()

def scan_and_process_po_files(input_folder, languages, fuzzy):
    """
    Scans all .po files in the specified folder and subfolders.
    Translates and removes 'fuzzy' entries if specified.

    :param input_folder: The root folder to start the scan.
    :param languages: List of language codes to filter the .po files.
    :param fuzzy: Boolean indicating whether to remove fuzzy entries.
    """
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith(".po"):
                po_file_path = os.path.join(root, file)
                po_file = polib.pofile(po_file_path)
                file_lang = po_file.metadata.get('Language', '')
                if file_lang in languages:
                    for entry in po_file:
                        if not entry.msgstr and entry.msgid:
                            entry.msgstr = translate_text(entry.msgid, file_lang)
                    if fuzzy:
                        po_file.remove_fuzzy_entries()
                    po_file.save(po_file_path)
                    print(f"Processed {po_file_path}")

def main():
    load_dotenv()  # Load environment variables from .env file
    openai.api_key = os.getenv("OPENAI_API_KEY")

    parser = argparse.ArgumentParser(description="Scan and process .po files")
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    
    args = parser.parse_args()

    languages = [lang.strip() for lang in args.lang.split(',')]
    scan_and_process_po_files(args.folder, languages, args.fuzzy)

if __name__ == "__main__":
    main()
