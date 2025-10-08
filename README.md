# GPT-PO Translator

[![Python Package CI](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml)
![PyPI](https://img.shields.io/pypi/v/gpt-po-translator?label=gpt-po-translator)
![Downloads](https://pepy.tech/badge/gpt-po-translator)

**Translate gettext (.po) files using AI models.** Supports OpenAI, Azure OpenAI, Anthropic/Claude, DeepSeek, and Ollama (local) with automatic AI translation tagging.

## 🚀 Quick Start

```bash
# Install
pip install gpt-po-translator

# Set API key
export OPENAI_API_KEY='your_api_key_here'

# Auto-detect and translate all languages
gpt-po-translator --folder ./locales --bulk
```

## ✨ Key Features

- **Multiple AI providers** - OpenAI, Azure OpenAI, Anthropic/Claude, DeepSeek, and Ollama (local)
- **Privacy option** - Use Ollama for local, offline translations with no cloud API
- **AI translation tracking** - Auto-tags AI-generated translations with `#. AI-generated` comments
- **Bulk processing** - Efficient batch translation for large files
- **Smart language detection** - Auto-detects target languages from folder structure
- **Fuzzy entry handling** - Translates and fixes fuzzy entries properly
- **Docker ready** - Available as container for easy deployment

## 📦 Installation

### PyPI (Recommended)
```bash
pip install gpt-po-translator
```

### Docker
```bash
docker pull ghcr.io/pescheckit/python-gpt-po:latest
```

### Manual
```bash
git clone https://github.com/pescheckit/python-gpt-po.git
cd python-gpt-po
pip install -e .
```

## 🔧 Setup

### API Keys (Cloud Providers)

Choose your AI provider and set the corresponding API key:

```bash
# OpenAI
export OPENAI_API_KEY='your_key'

# Anthropic/Claude
export ANTHROPIC_API_KEY='your_key'

# DeepSeek
export DEEPSEEK_API_KEY='your_key'

# Azure OpenAI
export AZURE_OPENAI_API_KEY='your_key'
export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'
export AZURE_OPENAI_API_VERSION='2024-02-01'
```

### Or Use Ollama (Local, No API Key Needed)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull qwen2.5    # Best for multilingual (Arabic, Chinese, etc.)
# OR
ollama pull llama3.2   # Fast for European languages

# 3. Translate (no API key required!)
gpt-po-translator --provider ollama --folder ./locales

# For non-Latin scripts, use qwen2.5 WITHOUT --bulk
gpt-po-translator --provider ollama --model qwen2.5 --folder ./locales --lang ar
```

> **💡 Important:** For Ollama with **non-Latin languages** (Arabic, Chinese, Japanese, etc.), **omit the `--bulk` flag**. Single-item translation is more reliable because the model doesn't have to format responses as JSON.

## 💡 Usage Examples

### Basic Translation
```bash
# Auto-detect languages from PO files (recommended)
gpt-po-translator --folder ./locales --bulk -v

# Or specify languages explicitly
gpt-po-translator --folder ./locales --lang de,fr,es --bulk -v

# Single language with progress information
gpt-po-translator --folder ./locales --lang de -v
```

### Different AI Providers
```bash
# Use Claude (Anthropic) - auto-detect languages
gpt-po-translator --provider anthropic --folder ./locales --bulk

# Use DeepSeek with specific languages
gpt-po-translator --provider deepseek --folder ./locales --lang de

# Use Azure OpenAI with auto-detection
gpt-po-translator --provider azure_openai --folder ./locales --bulk

# Use Ollama (local, private, free) - omit --bulk for non-Latin scripts
gpt-po-translator --provider ollama --folder ./locales
```

### Docker Usage
```bash
# Basic usage with OpenAI
docker run -v $(pwd):/data \
  -e OPENAI_API_KEY="your_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /data --bulk

# With Ollama (local, no API key needed)
# Note: Omit --bulk for better quality with non-Latin scripts
docker run --rm \
  -v $(pwd):/data \
  --network host \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --provider ollama \
  --folder /data

# With Azure OpenAI
docker run -v $(pwd):/data \
  -e AZURE_OPENAI_API_KEY="your_key" \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_API_VERSION="2024-02-01" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --provider azure_openai --folder /data --lang de
```

## 🏷️ AI Translation Tracking

**All AI translations are automatically tagged** for transparency and compliance:

```po
#. AI-generated
msgid "Hello"
msgstr "Hallo"
```

This helps you:
- Track which translations are AI vs human-generated
- Comply with AI content disclosure requirements
- Manage incremental translation workflows

**Note:** Django's `makemessages` removes these comments but preserves translations. Re-run the translator after `makemessages` to restore tags.

## 📚 Command Reference

| Option | Description |
|--------|-------------|
| `--folder` | Path to .po files |
| `--lang` | Target languages (e.g., `de,fr,es`, `fr_CA`, `pt_BR`) |
| `--provider` | AI provider: `openai`, `azure_openai`, `anthropic`, `deepseek`, `ollama` |
| `--bulk` | Enable batch translation (recommended for large files) |
| `--bulksize` | Entries per batch (default: 50) |
| `--model` | Specific model to use |
| `--list-models` | Show available models |
| `--fix-fuzzy` | Translate fuzzy entries |
| `--folder-language` | Auto-detect languages from folders |
| `--no-ai-comment` | Disable AI tagging |
| `--ollama-base-url` | Ollama server URL (default: `http://localhost:11434`) |
| `--ollama-timeout` | Ollama timeout in seconds (default: 120) |
| `-v, --verbose` | Show progress information (use `-vv` for debug) |
| `-q, --quiet` | Only show errors |
| `--version` | Show version and exit |

## 🛠️ Development

### Build Docker Locally
```bash
git clone https://github.com/pescheckit/python-gpt-po.git
cd python-gpt-po
docker build -t python-gpt-po .
```

### Run Tests
```bash
# Local
python -m pytest

# Docker
docker run --rm -v $(pwd):/app -w /app --entrypoint python python-gpt-po -m pytest -v
```

## 📋 Requirements

- Python 3.9+
- Dependencies: `polib`, `openai`, `anthropic`, `requests`, `tenacity`

## 📖 Documentation

- **[Advanced Usage Guide](docs/usage.md)** - Comprehensive options and mechanics
- **[Development Guide](docs/development.md)** - Contributing guidelines
- **[GitHub Issues](https://github.com/pescheckit/python-gpt-po/issues)** - Bug reports and feature requests

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
