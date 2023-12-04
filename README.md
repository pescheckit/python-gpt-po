# Python GPT-4 PO File Translator

This Python script provides a convenient tool for translating `.po` files using OpenAI's GPT-4 model. It is designed to handle both bulk and individual translation modes, making it suitable for a wide range of project sizes and `.po` file structures.

## Features

- **Bulk Translation Mode**: Enhances efficiency by facilitating the translation of multiple text entries simultaneously.
- **Individual Translation Mode**: Offers the flexibility to translate entries one at a time for greater precision.
- **Configurable Batch Size**: Allows users to set the number of entries to be translated in each batch during bulk translation.
- **Comprehensive Logging**: Logs detailed information for progress monitoring and debugging purposes.
- **Fuzzy Entry Exclusion**: Enables the option to omit 'fuzzy' entries from translation in `.po` files.
- **Flexible API Key Configuration**: Supports providing the OpenAI API key either through command-line arguments or a `.env` file.

## Requirements

- Python 3.x
- `polib` library
- `openai` Python package

![gpt-po](https://github.com/pescheckit/python-gpt-po/assets/78353155/d76ebc10-b24d-47b3-acef-7c02805faee3)

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
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100 --folder-language
```

This command translates `.po` files in the `./locales` folder to German and French, using the provided OpenAI API key, and processes 100 translations per batch in bulk mode.

## Logging

The script logs detailed information about the files being processed, the number of translations, and batch details in bulk mode.

## License

[MIT](LICENSE)
