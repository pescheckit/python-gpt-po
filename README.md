# Python GPT-4 PO File Translator

This Python script provides a robust and flexible tool for translating `.po` files using OpenAI's GPT-4 model. It accommodates various translation modes, handles fuzzy entries, and integrates batch processing for larger projects, making it suitable for diverse `.po` file structures and sizes.

## Features

- **Bulk and Individual Translation Modes**: Allows efficient bulk translation or precise, entry-by-entry translations for nuanced content.
- **Detailed Language Option (`--detail-lang`)**: Supports using full language names (e.g., "Netherlands, German") alongside shortcodes (e.g., `nl, de`), ensuring clarity in translation prompts.
- **Configurable Batch Size**: Set the number of entries to translate per batch during bulk translation, optimizing API usage.
- **Fuzzy Entry Management**: Automatically removes fuzzy flags and entries, ensuring only valid translations are processed.
- **Language Inference from Folder Structure**: Infers the target language from the folder structure, reducing the need for explicit language specifications.
- **Translation Validation and Retry Logic**: Built-in mechanisms validate translations and automatically retry to avoid incorrect or verbose translations.
- **Logging for Transparency**: Detailed logging for monitoring, debugging, and ensuring progress throughout the translation process.
- **OpenAI API Key Management**: Supports environment variables or command-line arguments for securely providing OpenAI API credentials.
- **Retry Mechanism for Failed Translations**: Retries failed translations up to three times, reducing incomplete or incorrect outputs.
- **Post-Processing for Concise Translations**: Automatically reviews translations to ensure they are concise and free of unnecessary explanations or repetitions.

## Requirements

- Python 3.x
- `polib` library (for `.po` file handling)
- `openai` Python package (for integration with OpenAI GPT models)
- `tenacity` library (for retry mechanisms)
- `python-dotenv` (for managing environment variables)

## Installation

### Via PyPI

Install the `gpt-po-translator` package directly from PyPI:

```bash
pip install gpt-po-translator
```

### Manual Installation

For manual installation or working with the latest code from the repository:

1. Clone the repository:
   ```bash
   git clone [repository URL]
   ```
2. Navigate to the cloned directory and install the package:
   ```bash
   pip install .
   ```

## API Key Configuration

The `gpt-po-translator` supports two methods for providing OpenAI API credentials:

1. **Environment Variable**: Set your OpenAI API key as an environment variable named `OPENAI_API_KEY`. This method is recommended for security and ease of API key management.

   ```bash
   export OPENAI_API_KEY='your_api_key_here'
   ```

2. **Command-Line Argument**: Pass the API key as a command-line argument using the `--api_key` option.

   ```bash
   gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100 --folder-language
   ```

Make sure your API key is securely stored and not exposed in public spaces or repositories.

## Usage

Use `gpt-po-translator` as a command-line tool for translating `.po` files:

```bash
gpt-po-translator --folder [path_to_po_files] --lang [language_codes] [--api_key [your_openai_api_key]] [--fuzzy] [--bulk] [--bulksize [batch_size]] [--folder-language] [--detail-lang [full_language_names]]
```

### Example

```bash
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 40 --folder-language --detail-lang "German,French"
```

This command translates `.po` files in the `./locales` folder to German and French, using the provided OpenAI API key and processing 40 translations per batch in bulk mode. It also infers the language from the folder structure.

### Command-Line Options

- `--folder`: Specifies the input folder containing `.po` files.
- `--lang`: Comma-separated language codes to filter `.po` files (e.g., `de,fr`).
- `--detail-lang`: Optional argument for full language names, matching the order of `--lang` (e.g., "German,French").
- `--fuzzy`: Removes fuzzy entries before processing.
- `--bulk`: Enables bulk translation mode for faster processing.
- `--bulksize`: Sets the batch size for bulk translation (default is 50).
- `--model`: Specifies the OpenAI model to use for translations (default is `gpt-3.5-turbo-0125`).
- `--api_key`: OpenAI API key. Can be provided through the command line or as an environment variable.
- `--folder-language`: Infers the target language from the folder structure.

## Detailed Language Names and Shortcodes

The `--detail-lang` option complements `--lang` by allowing you to specify full language names (e.g., `Netherlands,German`) instead of language shortcodes. The full names are then used in the context of OpenAI prompts, improving clarity for the GPT model.

Example usage:

```bash
gpt-po-translator --folder ./locales --lang nl,de --detail-lang "Netherlands,German"
```

## Logging

The script logs detailed information about the files being processed, the number of translations, and batch details in bulk mode. Logs are essential for monitoring progress, debugging issues, and ensuring transparency throughout the translation process.

## Error Handling and Retries

The script includes robust error handling and retries to ensure reliable translation:

- **Failed Translations**: Automatically retries failed translations up to three times.
- **Empty Translations**: If an empty translation is returned, the script will attempt to translate the text again using an alternative approach.
- **Lengthy or Incorrect Translations**: Translations that are too long or contain explanations instead of direct translations are flagged and retried.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.