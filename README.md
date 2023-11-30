# Python GPT-4 PO File Translator

This Python script provides a convenient tool for translating `.po` files using OpenAI's GPT-4 model. It is designed to handle both bulk and individual translation modes, making it suitable for a wide range of project sizes and `.po` file structures.

## Features

- **Bulk Translation Mode**: Facilitates the translation of multiple text entries simultaneously, enhancing efficiency.
- **Individual Translation Mode**: Offers the flexibility to translate entries one at a time for greater precision.
- **Configurable Batch Size**: Users can set the number of entries to be translated in each batch during bulk translation.
- **Comprehensive Logging**: The script logs detailed information for progress monitoring and debugging purposes.
- **Fuzzy Entry Exclusion**: Provides the option to omit 'fuzzy' entries from translation in `.po` files.
- **Flexible API Key Configuration**: Supports providing the OpenAI API key either through command-line arguments or a `.env` file.

## Requirements

- Python 3.x
- `polib` library
- `openai` Python package

## API Key Configuration

The `gpt-po-translator` supports two methods for providing OpenAI API credentials:

1. **Environment Variable**: You can set your OpenAI API key as an environment variable. The script will automatically look for an environment variable named `OPENAI_API_KEY`. This method is recommended for maintaining security and ease of API key management, especially in shared or collaborative development environments.

   To set the environment variable, you can add the following line to your `.env` file or your shell's configuration file (like `.bashrc` or `.bash_profile`):

   ```bash
   export OPENAI_API_KEY='your_api_key_here'
   ```

2. **Command-Line Argument**: Alternatively, you can directly pass the API key as a command-line argument using the `--api_key` option. This method is straightforward and can be suitable for quick tests or when the environment variable is not set.

   Usage example with the `--api_key` argument:

   ```bash
   gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100 --folder-language
   ```

Please ensure that your API key is kept secure and not exposed in shared or public spaces.

## Installation

### Via PyPI

You can install the `gpt-po-translator` package directly from PyPI:

```bash
pip install gpt-po-translator
```

This command will install the package along with its dependencies.

### Manual Installation

If you prefer to install manually or want to work with the latest code from the repository:

1. Clone the repository:
   ```bash
   git clone [repository URL]
   ```
2. Navigate to the cloned directory and install the package:
   ```bash
   pip install .
   ```

## Usage

After installation, you can use `gpt-po-translator` as a command-line tool:

```
gpt-po-translator --folder [path_to_po_files] --lang [language_codes] [--api_key [your_openai_api_key]] [--fuzzy] [--bulk] [--bulksize [batch_size]] [--folder-language]
```

- `--folder`: Path to the folder containing `.po` files.
- `--lang`: Comma-separated list of language codes for filtering `.po` files.
- `--api_key`: (Optional) Your OpenAI API key. If omitted, the script will look for it in the `.env` file.
- `--fuzzy`: (Optional) Flag to skip 'fuzzy' entries in translation.
- `--bulk`: (Optional) Enable bulk translation mode.
- `--bulksize`: (Optional) Set the batch size for translations in bulk mode (default is 50).
- `--folder-language`: (Optional) Enable the script to infer the language from the directory structure of the `.po` files.

### Example

```
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100 --folder-language
```

This command translates `.po` files in the `./locales` folder to German and French, using the provided OpenAI API key, and processes 100 translations per batch in bulk mode. It also infers the language from the directory structure if necessary.

## Logging

The script provides detailed logging that includes information about the files being processed, the number of translations, and batch details in bulk mode.

## License

[MIT](LICENSE)