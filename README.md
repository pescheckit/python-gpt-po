# GPT-PO Translator

[![Python Package CI](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/pescheckit/python-gpt-po/actions/workflows/ci-cd.yml)
![PyPI](https://img.shields.io/pypi/v/gpt-po-translator?label=gpt-po-translator)
![Downloads](https://pepy.tech/badge/gpt-po-translator)

**Translate gettext (.po) files using AI models.** Supports OpenAI, Azure OpenAI, Anthropic/Claude, and DeepSeek with automatic AI translation tagging.

## 🚀 Quick Start

```bash
# Install
pip install gpt-po-translator

# Set API key
export OPENAI_API_KEY='your_api_key_here'

# Translate to German and French
gpt-po-translator --folder ./locales --lang de,fr --bulk
```

## ✨ Key Features

- **Multiple AI providers** - OpenAI, Azure OpenAI, Anthropic/Claude, DeepSeek
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

### API Keys

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

## 💡 Usage Examples

### Basic Translation
```bash
# Translate to German (default: shows warnings/errors only)
gpt-po-translator --folder ./locales --lang de

# With progress information
gpt-po-translator --folder ./locales --lang de -v

# Multiple languages with verbose output
gpt-po-translator --folder ./locales --lang de,fr,es -v --bulk
```

### Different AI Providers
```bash
# Use Claude (Anthropic)
gpt-po-translator --provider anthropic --folder ./locales --lang de

# Use DeepSeek
gpt-po-translator --provider deepseek --folder ./locales --lang de

# Use Azure OpenAI
gpt-po-translator --provider azure_openai --folder ./locales --lang de
```

### Docker Usage
```bash
# Basic usage
docker run -v $(pwd):/data \
  -e OPENAI_API_KEY="your_key" \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --folder /data --lang de,fr --bulk

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
| `--provider` | AI provider: `openai`, `azure_openai`, `anthropic`, `deepseek` |
| `--bulk` | Enable batch translation (recommended for large files) |
| `--bulksize` | Entries per batch (default: 50) |
| `--model` | Specific model to use |
| `--list-models` | Show available models |
| `--fix-fuzzy` | Translate fuzzy entries |
| `--folder-language` | Auto-detect languages from folders |
| `--no-ai-comment` | Disable AI tagging |
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
