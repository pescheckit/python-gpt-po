# Python GPT-4 PO File Translator

This Python script provides a comprehensive tool for translating `.po` files using OpenAI's GPT-4 model. It is designed to accommodate both bulk and individual translation modes, making it suitable for a wide range of project sizes and `.po` file structures.

## Features

- **Bulk Translation Mode**: Enhances efficiency by translating multiple text entries simultaneously. Ideal for large `.po` files.
- **Individual Translation Mode**: Offers flexibility to translate entries one at a time, ensuring precise translation. Useful for complex or nuanced content.
- **Configurable Batch Size**: Users can set the number of entries to be translated per batch during bulk translation, allowing for optimized API usage.
- **Fuzzy Entry Management**: Automatically handles 'fuzzy' entries by removing fuzzy flags, ensuring that only verified translations are processed.
- **Language Inference from Folder Structure**: Optionally infers the target language based on the folder structure of the `.po` files, streamlining the translation process.
- **Translation Validation and Retry Logic**: Built-in mechanisms validate translations, retrying where necessary to avoid incorrect or overly verbose translations.
- **Comprehensive Logging**: Detailed logging for progress monitoring, debugging, and ensuring transparency in the translation process.
- **Flexible API Key Configuration**: Supports providing the OpenAI API key via command-line arguments or environment variables for enhanced security and ease of use.
- **Retry Mechanism for Failed Translations**: Automatically retries failed translations up to three times, reducing the chance of incomplete or incorrect outputs.
- **Post-Processing for Translations**: Translations are reviewed to ensure they are concise and free from unnecessary explanations or repeated content.

## Requirements

- Python 3.x
- `polib` library
- `openai` Python package
- `tenacity` library (for retry mechanisms)
- `python-dotenv` (for environment variable management)

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

Ensure your API key is kept secure and not exposed in shared or public spaces.

## Installation

### Via PyPI

Install the `gpt-po-translator` package directly from PyPI:

```bash
pip install gpt-po-translator
```

### Manual Installation

For manual installation or to work with the latest code from the repository:

1. Clone the repository:
   ```bash
   git clone [repository URL]
   ```
2. Navigate to the cloned directory and install the package:
   ```bash
   pip install .
   ```

## Usage

Use `gpt-po-translator` as a command-line tool:

```
gpt-po-translator --folder [path_to_po_files] --lang [language_codes] [--api_key [your_openai_api_key]] [--fuzzy] [--bulk] [--bulksize [batch_size]] [--folder-language]
```

### Example

```
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 40 --folder-language
```

This command translates `.po` files in the `./locales` folder to German and French, using the provided OpenAI API key, and processes 40 translations per batch in bulk mode. It also infers the language from the folder structure.

### Command-Line Options

- `--folder`: Specifies the input folder containing `.po` files.
- `--lang`: Comma-separated language codes to filter `.po` files.
- `--fuzzy`: Remove fuzzy entries before processing.
- `--bulk`: Enables bulk translation mode for faster processing.
- `--bulksize`: Sets the batch size for bulk translation. Default is 50.
- `--model`: Specifies the OpenAI model to use for translations. Default is `gpt-3.5-turbo-0125`.
- `--api_key`: OpenAI API key. Can be provided through the command line or as an environment variable.
- `--folder-language`: Infers the target language from the folder structure.

## Logging

The script logs detailed information about the files being processed, the number of translations, and batch details in bulk mode. The logs are essential for monitoring the progress, debugging issues, and ensuring all translations are handled correctly.

## Error Handling and Retries

The translation process includes robust error handling and retries:

- **Failed Translations**: If a translation fails, the script will automatically retry up to three times.
- **Empty Translations**: If an empty translation is returned, the script will attempt to translate the text again using a different approach.
- **Lengthy or Incorrect Translations**: Translations that are too long or contain explanations instead of direct translations are flagged and retried.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
