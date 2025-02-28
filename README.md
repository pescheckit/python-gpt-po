# Python GPT-4 PO File Translator

A robust tool for translating gettext (.po) files using AI models from multiple providers (OpenAI, Anthropic / Claude, and DeepSeek). It supports both bulk and individual translations, handles fuzzy entries, and can infer target languages based on folder structures.

## Features

- **Multi-Provider Support:** Integrates with OpenAI, Anthropic / Claude, and DeepSeek.
- **Bulk & Individual Modes:** Translate entire files in batches or process entries one by one.
- **Fuzzy Entry Management:** Automatically removes fuzzy entries to ensure clean translations.
- **Folder-Based Language Inference:** Detects the target language from directory structure.
- **Customizable Batch Size:** Configure the number of entries per translation request.
- **Retry & Validation:** Automatic retries and validation to ensure concise, correct translations.
- **Detailed Logging:** Transparent logging for progress monitoring and debugging.
- **Flexible API Key Configuration:** Supply API keys via environment variables or command-line arguments.
- **Detailed Language Option:** Use full language names (e.g., "German") for clearer prompts alongside language codes (e.g., de).

## Requirements

- Python 3.x
- [polib](https://pypi.org/project/polib/)
- [openai](https://pypi.org/project/openai/)
- [tenacity](https://pypi.org/project/tenacity/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Installation

### Via PyPI

```bash
pip install gpt-po-translator
```

### Manual Installation

Clone the repository and install the package:

```bash
git clone https://github.com/yourusername/python-gpt-po.git
cd python-gpt-po
pip install .
```

## API Key Configuration

You can provide your API key in two ways:

### Environment Variable

Set your OpenAI API key:

```bash
export OPENAI_API_KEY='your_api_key_here'
```

### Command-Line Argument

Pass your API key directly when invoking the tool:

```bash
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100 --folder-language
```

## Usage

Run the tool from the command line to translate your .po files:

```bash
gpt-po-translator --folder <path_to_po_files> --lang <language_codes> [options]
```

### Example

Translate .po files in the `./locales` folder to German and French:

```bash
gpt-po-translator --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 40 --folder-language --detail-lang "German,French"
```

## Documentation

For a detailed explanation of all available parameters and a deep dive into the internal workings of the tool, please see our [Advanced Usage Guide](docs/usage.md).

## Command-Line Options

- `--folder`: Path to the directory containing .po files.
- `--lang`: Comma-separated target language codes (e.g., de,fr).
- `--detail-lang`: Comma-separated full language names corresponding to the codes (e.g., "German,French").
- `--fuzzy`: Remove fuzzy entries before processing.
- `--bulk`: Enable bulk translation mode.
- `--bulksize`: Set the number of entries per bulk translation (default is 50).
- `--model`: Specify the translation model (defaults are provider-specific).
- `--api_key`: API key for translation; can also be provided via environment variable.
- `--folder-language`: Infer the target language from the folder structure.

## Logging & Error Handling

- **Logging:** Detailed logs track the translation process and help with debugging.
- **Error Handling:** The tool automatically retries failed translations (up to three times) and validates output to prevent overly verbose responses.

## Testing

To run all tests:

```bash
python -m pytest
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## About

Powered by state-of-the-art AI models (including OpenAI’s GPT-4 and GPT-3.5), this tool is designed to streamline the localization process for .po files. Whether you need to process large batches or handle specific entries, the Python GPT-4 PO File Translator adapts to your translation needs.

For more details, contributions, or bug reports, please visit our [GitHub repository](https://github.com/yourusername/python-gpt-po).