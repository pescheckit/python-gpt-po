# GPT-PO Translator

[![Python Package CI](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml)
![PyPI](https://img.shields.io/pypi/v/gpt-po-translator?label=gpt-po-translator)
![Downloads](https://pepy.tech/badge/gpt-po-translator)

A robust tool for translating gettext (.po) files using AI models from multiple providers (OpenAI, Anthropic / Claude, and DeepSeek). It supports both bulk and individual translations, handles fuzzy entries, and can infer target languages based on folder structures. Available as a Python package and Docker container with support for Python 3.8-3.12.

## What is GPT-PO Translator?

This tool helps you translate gettext (.po) files using AI models. It's perfect for developers who need to localize their applications quickly and accurately.

### Key Features

- **Multiple AI providers** - OpenAI, Anthropic/Claude, and DeepSeek
- **Flexible translation modes** - Bulk or entry-by-entry processing
- **Smart language handling** - Auto-detects target languages from folder structure
- **Production-ready** - Includes retry logic, validation, and detailed logging
- **Easy deployment** - Available as a Python package or Docker container
- **Cross-version support** - Works with Python 3.8-3.12

## Getting Started

### Quick Install

```bash
pip install gpt-po-translator
```

### Basic Usage

```bash
# Set up your API key
export OPENAI_API_KEY='your_api_key_here'

# Translate files to German and French
gpt-po-translator --folder ./locales --lang de,fr --bulk
```

## Installation Options

### PyPI (Recommended)

```bash
pip install gpt-po-translator
```

### Manual Installation

```bash
git clone https://github.com/pescheckit/python-gpt-po.git
cd python-gpt-po
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Docker

```bash
# Pull the latest image
docker pull ghcr.io/pescheckit/python-gpt-po:latest

# Run with your local directory mounted
docker run -v $(pwd):/data \
  -e OPENAI_API_KEY="your_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /data --lang fr,de --bulk
```

## Setting Up API Keys

### Option 1: Environment Variables

```bash
export OPENAI_API_KEY='your_api_key_here'
# Or for other providers:
export ANTHROPIC_API_KEY='your_api_key_here'
export DEEPSEEK_API_KEY='your_api_key_here'
```

### Option 2: Command Line

```bash
gpt-po-translator --api_key 'your_api_key_here' [other options]
```

## Usage Examples

### Basic Translation

```bash
# Translate to German
gpt-po-translator --folder ./locales --lang de
```

### Bulk Translation with Language Detection

```bash
# Translate based on folder structure with custom batch size
gpt-po-translator --folder ./locales --lang de,fr --bulk --bulksize 40 --folder-language
```

### Using Different AI Providers

```bash
# Use Claude models from Anthropic
gpt-po-translator --provider anthropic --folder ./locales --lang de

# Use DeepSeek models
gpt-po-translator --provider deepseek --folder ./locales --lang de

# List available models
gpt-po-translator --provider openai --list-models
```

## Command Reference

| Option | Description |
|--------|-------------|
| `--folder` | Path to your .po files |
| `--lang` | Target language codes (comma-separated, e.g., `de,fr`) |
| `--detail-lang` | Full language names (e.g., `"German,French"`) |
| `--fuzzy` | Remove fuzzy entries before translating |
| `--bulk` | Enable batch translation (recommended for large files) |
| `--bulksize` | Entries per batch (default: 50) |
| `--model` | Specific AI model to use |
| `--provider` | AI provider: `openai`, `anthropic`, or `deepseek` |
| `--list-models` | Show available models for selected provider |
| `--api_key` | Your API key |
| `--folder-language` | Auto-detect languages from folder structure |

## Advanced Docker Usage

### Specific Python Versions

```bash
# Python 3.11 (default)
docker pull ghcr.io/pescheckit/python-gpt-po:latest

# Python 3.12
docker pull ghcr.io/pescheckit/python-gpt-po:latest-py3.12

# Specific version
docker pull ghcr.io/pescheckit/python-gpt-po:0.3.0
```

### Volume Mounting

Mount any local directory to use in the container:

```bash
# Windows example
docker run -v D:/projects/website/locales:/locales \
  -e OPENAI_API_KEY="your_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /locales --lang fr,de --bulk

# Mac/Linux example
docker run -v /Users/username/translations:/input \
  -e OPENAI_API_KEY="your_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /input --lang fr,de --bulk
```

## Requirements

- Python 3.9+ (3.9, 3.10, 3.11, or 3.12)
- Core dependencies:
  - polib
  - openai
  - tenacity
  - python-dotenv

## Development

### Running Tests

```bash
python -m pytest
```
```bash
docker run --rm -v $(pwd):/app -w /app --entrypoint python python-gpt-po -m pytest -v
```

## Documentation

For advanced usage and detailed documentation, please see:
- [Advanced Usage Guide](docs/usage.md)
- [GitHub Repository](https://github.com/pescheckit/python-gpt-po)

## License

MIT License - See the [LICENSE](LICENSE) file for details.
