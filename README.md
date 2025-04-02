# Python GPT-4 PO File Translator

[![Python Package CI](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml)
![PyPI](https://img.shields.io/pypi/v/gpt-po-translator?label=gpt-po-translator)
![Downloads](https://pepy.tech/badge/gpt-po-translator)

A robust tool for translating gettext (.po) files using AI models from multiple providers (OpenAI, Anthropic / Claude, and DeepSeek). It supports both bulk and individual translations, handles fuzzy entries, and can infer target languages based on folder structures. Available as a Python package and Docker container with support for Python 3.9-3.12.

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

- Python 3.9+ (Python 3.9, 3.10, 3.11, and 3.12 are officially supported)
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
git clone https://github.com/pescheckit/python-gpt-po.git
cd python-gpt-po
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m python_gpt_po.main --provider="deepseek" --list-models
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
- `--provider`: Specify the AI provider (openai, anthropic, or deepseek).
- `--list-models`: List available models for the selected provider. This is the only command that can be used without `--folder` and `--lang`.
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

## Using Docker

You can use this tool without installing Python on your local machine by running it in a Docker container.

### Using Pre-built Container

Pull the latest container from GitHub Container Registry (defaults to Python 3.11):

```bash
docker pull ghcr.io/pescheckit/python-gpt-po:latest  # Uses Python 3.11 by default
```

You can also use a specific version tag for consistency, or specify a Python version:

```bash 
docker pull ghcr.io/pescheckit/python-gpt-po:0.3.0  # Latest version
docker pull ghcr.io/pescheckit/python-gpt-po:0.3.0-py3.11  # Python 3.11 specific
docker pull ghcr.io/pescheckit/python-gpt-po:latest-py3.12  # Latest with Python 3.12
```

Run the container with any local directory mounted to any path inside the container:

```bash
# Mount current directory to /data in container
docker run -v $(pwd):/data \
  -e OPENAI_API_KEY="your_openai_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /data --lang fr,de --bulk

# Mount a specific absolute path to /translations in container
docker run -v /home/user/my-translations:/translations \
  -e OPENAI_API_KEY="your_openai_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /translations --lang fr,de --bulk
  
# Mount from a different drive or location on Windows
docker run -v D:/projects/website/locales:/locales \
  -e OPENAI_API_KEY="your_openai_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /locales --lang fr,de --bulk
  
# On Mac/Linux, mount from any location
docker run -v /Users/username/Documents/translations:/input \
  -e OPENAI_API_KEY="your_openai_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /input --lang fr,de --bulk
  
# Multiple volumes can be mounted if needed
docker run \
  -v /path/to/source:/input \
  -v /path/to/output:/output \
  -e OPENAI_API_KEY="your_openai_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /input --lang fr,de --bulk
```

Running without arguments will display usage help:

```bash
docker run ghcr.io/pescheckit/python-gpt-po:latest
```

Quick reference - copy & paste commands:

```bash
# Help text
docker run ghcr.io/pescheckit/python-gpt-po:latest

# Translate current directory files to French
docker run -v $(pwd):/data -e OPENAI_API_KEY="your_key" ghcr.io/pescheckit/python-gpt-po:latest --folder /data --lang fr

# Use a specific Python version (3.12)
docker run -v $(pwd):/data -e OPENAI_API_KEY="your_key" ghcr.io/pescheckit/python-gpt-po:latest-py3.12 --folder /data --lang fr

# List available models (no need for --folder or --lang)
docker run -e OPENAI_API_KEY="your_key" ghcr.io/pescheckit/python-gpt-po:latest --provider openai --list-models
```

### Volume Mount Explanation

The `-v` flag uses the format: `-v /host/path:/container/path`

- `/host/path` can be any directory on your system
- `/container/path` is where the directory appears inside the container
- Use the `/container/path` with the `--folder` parameter

For example, if you mount with `-v ~/translations:/data`, then use `--folder /data` in your command.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## About

Powered by state-of-the-art AI models (including OpenAI’s GPT-4 and GPT-3.5), this tool is designed to streamline the localization process for .po files. Whether you need to process large batches or handle specific entries, the Python GPT-4 PO File Translator adapts to your translation needs.

For more details, contributions, or bug reports, please visit our [GitHub repository](https://github.com/pescheckit/python-gpt-po).