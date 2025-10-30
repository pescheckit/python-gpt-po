# gpt-po-translator: Advanced Usage and Internal Mechanics

This guide provides an in-depth look at what really happens when you run `gpt-po-translator` and details every available parameter. It is intended for users who want to understand the inner workings of the tool as well as all the configuration options.

---

## Overview

`gpt-po-translator` is a multi-provider tool for translating gettext (.po) files using AI models. It supports OpenAI, Azure OpenAI, Anthropic, and DeepSeek. The tool offers two primary translation modes:
- **Bulk Mode:** Processes a list of texts in batches to reduce the number of API calls.
- **Individual Mode:** Translates each text entry one-by-one for more fine-grained control.

It also manages fuzzy translations (by disabling or removing them) and can infer target languages from folder names if desired.

---

## Internal Workflow

### 1. Argument Parsing and Configuration
- **Command-Line Parsing:**  
  The program uses Python's `argparse` module to parse command-line options. Every parameter you pass on the command line (such as `--folder`, `--lang`, `--bulk`, etc.) is processed and stored in a configuration object (`TranslationConfig`).

- **API Key Setup:**  
  The tool collects API keys from multiple sources:
  - Specific arguments (`--openai-key`, `--azure-openai-key`, `--anthropic-key`, `--deepseek-key`)
  - A fallback argument (`--api_key`) for OpenAI if no dedicated key is provided
  - Environment variables (e.g., `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`)
  
  It then initializes a `ProviderClients` instance that creates API client objects for the chosen providers.

- **Provider and Model Selection:**  
  If you don’t explicitly select a provider using `--provider`, the tool auto-selects the first provider for which an API key is available. Likewise, if no model is specified with `--model`, it defaults to a provider-specific model (e.g., `"gpt-4o-mini"` for OpenAI).

---

### 2. Processing .po Files

- **Fuzzy Translation Handling:**  
  If the `--fuzzy` flag is set, the tool calls `disable_fuzzy_translations()`. This method:
  - Reads the entire file content and removes fuzzy markers (lines like `#, fuzzy`).
  - Loads the file using the `polib` library.
  - Removes the `fuzzy` flag from each entry and cleans up metadata.
  
- **Language Detection:**  
  The tool determines the language of a `.po` file by:
  - Reading the `Language` field in the PO file metadata.
  - If that isn’t conclusive and the `--folder-language` flag is enabled, it inspects the file path (directory names) to match against the provided language codes.

- **Preparing for Translation:**  
  After filtering and cleaning the PO file, the tool gathers all source texts (`msgid`) that have no translation (`msgstr` empty).

---

### 3. Translation Process

- **Bulk vs. Individual Translation:**  
  - **Bulk Mode (`--bulk`):**  
    The tool groups source texts into batches of a specified size (using `--bulksize`, default is 50). It then generates a prompt instructing the provider to translate all texts at once and return a JSON array of translations.
  - **Individual Mode:**  
    Each text is sent in a separate API call with a prompt asking for a direct translation.

- **Prompt Generation:**  
  Prompts are dynamically generated depending on the mode:
  - In bulk mode, the prompt instructs the provider to return a JSON array, preserving the order of texts.
  - In individual mode, the prompt emphasizes returning a concise, direct translation without any additional commentary.
  
  If the `--detail-lang` option is provided, the full language name is used in the prompt instead of the ISO code. This improves context for the AI.

- **API Calls and Response Handling:**  
  The tool sends the prompt to the selected provider’s API (using the corresponding client or direct HTTP request). It then:
  - Processes the response (e.g., stripping markdown code block wrappers from DeepSeek responses).
  - Validates the translation by ensuring it isn’t overly long or containing extraneous explanations.
  - If the translation fails validation, it retries the request (up to three times) using a more concise prompt.

- **Translation Post-Processing:**  
  The tool checks whether the translation is excessively verbose compared to the original text. If so, it retries the translation to ensure it remains concise.

- **Updating PO Files:**  
  After translation, each PO file entry is updated with the new translation using `polib`. By default, AI-generated translations are marked with a comment (`#. AI-generated`) for easy identification. The tool logs a summary of how many entries were successfully translated and warns if any remain untranslated.

---

### 4. Error Handling and Logging

- **Retries:**  
  API calls are wrapped with the `tenacity` library’s retry mechanism. In case of network issues or unexpected responses, the call is retried (default is three attempts with a fixed wait).

- **Logging:**  
  Detailed logging is implemented throughout:
  - Successful API calls and connection validations.
  - Warnings when translations are missing or appear too verbose.
  - Error logs when something goes wrong (e.g., API connection issues, language detection failures).

---

## Command-Line Options

Below is a detailed explanation of all command-line arguments:

### Required Options

- **`--folder <path>`**  
  *Description:* Specifies the input folder containing one or more `.po` files to be processed.  
  *Behind the scenes:* The tool recursively scans this folder and processes every file ending with `.po`.

### Optional Options

- **`--lang <language_codes>`** *(Optional)*  
  *Description:* A comma-separated list of ISO 639-1 language codes (e.g., `de,fr`) or locale codes (e.g., `fr_CA,pt_BR`). **If not provided, the tool will auto-detect languages from PO file metadata or folder structure.**  
  *Behind the scenes:* The tool filters PO files by comparing these codes with the file metadata and folder names (if `--folder-language` is enabled). When omitted, it scans all PO files to extract language information automatically.

- **`--detail-lang <language_names>`**  
  *Description:* A comma-separated list of full language names (e.g., `"German,French"`) that correspond to the codes provided with `--lang`.  
  *Behind the scenes:* These names are used in the translation prompts to give the AI clearer context, potentially improving translation quality.  
  *Note:* The number of detailed names must match the number of language codes.

- **`--fuzzy`** *(DEPRECATED)*  
  *Description:* A flag that, when set, instructs the tool to remove fuzzy entries from the PO files before translation. **This option is DEPRECATED due to its risky behavior of removing fuzzy markers without actually translating the content.**  
  *Behind the scenes:* The tool calls a dedicated method to strip fuzzy markers and flags from both the file content and metadata.  
  *Warning:* This can lead to data loss and confusion. Use `--fix-fuzzy` instead.

- **`--fix-fuzzy`**  
  *Description:* Translate and clean fuzzy entries safely (recommended over `--fuzzy`).  
  *Behind the scenes:* The tool filters for entries with the 'fuzzy' flag and attempts to translate them, removing the flag upon successful translation.

- **`--bulk`**  
  *Description:* Enables bulk translation mode, meaning multiple texts will be translated in a single API call.  
  *Behind the scenes:* The tool splits the list of texts into batches and generates a combined prompt for each batch.

- **`--bulksize <number>`**  
  *Description:* Sets the number of PO file entries to translate per API request when in bulk mode (default is 50).  
  *Behind the scenes:* Controls the size of each batch sent to the translation provider, affecting performance and API cost.

- **`--api_key <your_api_key>`**  
  *Description:* Provides a fallback API key for OpenAI if no dedicated key (e.g., via `--openai-key`) is provided.  
  *Behind the scenes:* This key is merged with keys provided through other command-line arguments or environment variables.

- **`--provider <provider>`**  
  *Description:* Specifies the AI provider to use for translations. Acceptable values are `openai`, `azure_openai`, `anthropic`, or `deepseek`.  
  *Behind the scenes:* If not specified, the tool auto-selects the first provider for which an API key is available.

- **`--model <model>`**  
  *Description:* Specifies the model name to use for translations. If omitted, a default model is chosen based on the provider.  
  *Behind the scenes:* The chosen model is passed along to the provider’s API calls. If the model is not available, a warning is logged and the default is used.

- **`--list-models`**  
  *Description:* Lists all available models for the selected provider and exits without processing any files. This is the only command that doesn't require `--folder` and `--lang` parameters.  
  *Behind the scenes:* Makes a test API call to retrieve a list of models and prints them to the console. When this flag is provided, the CLI parser automatically makes the usually required parameters optional.

- **`--openai-key`**  
  *Description:* Provides the OpenAI API key directly as a command-line argument (alternative to using `--api_key` or the environment variable).  
  *Behind the scenes:* Overrides any fallback key for OpenAI if provided.

- **`--anthropic-key`**  
  *Description:* Provides the Anthropic API key directly.  
  *Behind the scenes:* This key is used to initialize the Anthropic client.

- **`--azure-openai-key`**  
  *Description:* Provides the Azure OpenAI API key directly.  
  *Behind the scenes:* This key is used to initialize the Azure OpenAI client.

- **`--azure-openai-endpoint`**  
  *Description:* Provides the Azure OpenAI endpoint URL (e.g., `https://your-resource.openai.azure.com/`).  
  *Behind the scenes:* Required for Azure OpenAI connections along with the API version.

- **`--azure-openai-api-version`**  
  *Description:* Specifies the Azure OpenAI API version (e.g., `2024-02-01`).  
  *Behind the scenes:* Different API versions support different features and models.

- **`--deepseek-key`**  
  *Description:* Provides the DeepSeek API key directly.  
  *Behind the scenes:* This key is required to make API calls to DeepSeek’s translation service.

- **`--folder-language`**
  *Description:* Enables inferring the target language from the folder structure.
  *Behind the scenes:* The tool inspects the path components (directory names) of each PO file and matches them against the provided language codes. Supports locale codes (e.g., folder `fr_CA` matches `-l fr_CA` for Canadian French, or falls back to `-l fr` for standard French).

- **`--default-context CONTEXT`**
  *Description:* Sets a default translation context for entries without `msgctxt`.
  *Behind the scenes:* When the tool encounters PO entries without explicit `msgctxt` context, it applies this default context to provide additional information to the AI. Entries with explicit `msgctxt` always take precedence. Can also be set via the `GPT_TRANSLATOR_CONTEXT` environment variable or `default_context` in `pyproject.toml`.
  *Priority:* CLI argument > Environment variable > Config file
  *Example:* `--default-context "web application UI"` helps the AI understand the context for all translations without specific msgctxt.
  *Note:* Use descriptive context (e.g., "e-commerce product page" rather than just "web") for best results.

- **`--no-ai-comment`**
  *Description:* Disables the automatic addition of 'AI-generated' comments to translated entries.
  *Behind the scenes:* **By default (without this flag), every translation made by the AI is marked with a `#. AI-generated` comment in the PO file.** This flag prevents that marking, making AI translations indistinguishable from human translations in the file.
  *Note:* AI tagging is enabled by default for tracking, compliance, and quality assurance purposes.

- **`-v, --verbose`**  
  *Description:* Increases output verbosity. Can be used multiple times for more detail.  
  *Behind the scenes:* Controls the logging level:
    - No flag: Shows only warnings and errors (default)
    - `-v`: Shows info messages including progress tracking  
    - `-vv`: Shows debug messages for troubleshooting
  *Note:* Progress tracking shows translation progress for both single and bulk modes.

- **`-q, --quiet`**  
  *Description:* Reduces output to only show errors.  
  *Behind the scenes:* Sets logging level to ERROR, suppressing all info and warning messages.

- **`--version`**  
  *Description:* Shows the program version and exits.  
  *Behind the scenes:* Displays the current version from package metadata.

---

## Locale and Regional Variant Handling

### Overview

The tool now fully supports locale codes (e.g., `fr_CA`, `pt_BR`, `en_US`) in addition to simple language codes. This allows you to translate content for specific regional variants of a language.

### How Locale Matching Works

The tool uses a smart matching system that:
1. **First tries exact match**: `fr_CA` matches `fr_CA`
2. **Then tries format conversion**: `fr_CA` matches `fr-CA` (underscore ↔ hyphen)
3. **Finally tries base language fallback**: `fr_CA` matches `fr`

### Language Detection Priority

When a PO file is processed, the language is determined in this order:
1. **File metadata**: The `Language` field in the PO file header
2. **Folder structure** (with `--folder-language`): Directory names in the file path

### Examples

**Working with Canadian French:**
```bash
# Translate specifically to Canadian French
gpt-po-translator --folder ./locales --lang fr_CA

# With detailed language name for better AI context
gpt-po-translator --folder ./locales --lang fr_CA --detail-lang "Canadian French"

# Process files in fr_CA folders
gpt-po-translator --folder ./locales --lang fr_CA --folder-language
```

**Working with Brazilian Portuguese:**
```bash
# Translate to Brazilian Portuguese (different vocabulary from European Portuguese)
gpt-po-translator --folder ./locales --lang pt_BR --detail-lang "Brazilian Portuguese"

# Fall back to European Portuguese
gpt-po-translator --folder ./locales --lang pt
```

### What the AI Sees

The language code or detail name is passed directly to the AI in the translation prompt:

| Command | AI Sees in Prompt |
|---------|-------------------|
| `-l fr` | "Translate to fr" |
| `-l fr_CA` | "Translate to fr_CA" |
| `-l fr_CA --detail-lang "Canadian French"` | "Translate to Canadian French" |
| `-l pt_BR --detail-lang "Brazilian Portuguese"` | "Translate to Brazilian Portuguese" |

### Folder Language Behavior

With `--folder-language`, the tool matches folder names against your `-l` parameter:

| Folder | `-l` Parameter | Result |
|--------|----------------|--------|
| `locales/fr_CA/` | `fr_CA` | Translates to Canadian French |
| `locales/fr_CA/` | `fr` | Translates to standard French (fallback) |
| `locales/pt_BR/` | `pt_BR` | Translates to Brazilian Portuguese |
| `locales/pt_BR/` | `pt` | Translates to European Portuguese (fallback) |

### Best Practices

1. **For regional variants**, always use the full locale code:
   ```bash
   gpt-po-translator --folder ./locales --lang fr_CA,pt_BR,en_US
   ```

2. **Add detail names** for better AI understanding:
   ```bash
   gpt-po-translator --folder ./locales --lang fr_CA,pt_BR \
                     --detail-lang "Canadian French,Brazilian Portuguese"
   ```

3. **Use folder detection** for projects with locale-based directory structure:
   ```bash
   # Processes files in locales/fr_CA/, locales/pt_BR/, etc.
   gpt-po-translator --folder ./locales --lang fr_CA,pt_BR --folder-language
   ```

---

## Performance and Progress Tracking

### Overview

The tool provides intelligent performance warnings and progress tracking to help you manage large translation tasks efficiently.

### Performance Modes

1. **Single Mode (Default)**: Makes one API call per translation
   - Better for small files (< 30 entries)
   - More accurate for context-sensitive translations
   - Shows progress for each entry with `-v` flag

2. **Bulk Mode (`--bulk`)**: Batches multiple translations per API call
   - Recommended for large files (> 30 entries)
   - Significantly faster (up to 10x for large files)
   - Shows progress per batch with `-v` flag

### Automatic Performance Warnings

When processing files with more than 30 entries in single mode, the tool will:
1. Display a performance warning with time estimates
2. Recommend switching to bulk mode
3. For very large files (>100 entries), provide a 10-second countdown to cancel

Example warning:
```
2024-01-15 10:30:45 - WARNING - PERFORMANCE WARNING
2024-01-15 10:30:45 - WARNING -   Current mode: SINGLE (1 API call per translation)
2024-01-15 10:30:45 - WARNING -   This will make 548 separate API calls
2024-01-15 10:30:45 - WARNING -   Estimated time: ~14 minutes
2024-01-15 10:30:45 - WARNING -   
2024-01-15 10:30:45 - WARNING -   Recommendation: Use BULK mode for faster processing
2024-01-15 10:30:45 - WARNING -     Command: add --bulk --bulksize 50
2024-01-15 10:30:45 - WARNING -     Estimated time with bulk: ~2 minutes
2024-01-15 10:30:45 - WARNING -     Speed improvement: 7x faster
```

### Progress Tracking

Enable progress tracking with the `-v` flag:

```bash
# See progress for each file and translation
gpt-po-translator --folder ./locales --lang fr -v

# Output includes:
# - File processing status
# - Translation progress (X/Y entries)
# - Percentage completion
# - Batch progress (in bulk mode)
```

Example progress output:
```
2024-01-15 10:31:00 - INFO - Processing: ./locales/fr/messages.po (45 entries)
2024-01-15 10:31:01 - INFO - [SINGLE 1/45] Translating entry...
2024-01-15 10:31:02 - INFO - [SINGLE 2/45] Translating entry...
2024-01-15 10:31:10 - INFO - Progress: 10/45 entries completed (22.2%)
```

### Verbosity Levels

Control output detail with verbosity flags:

| Flag | Level | Shows |
|------|-------|-------|
| (default) | WARNING | Performance warnings, errors |
| `-v` | INFO | Progress tracking, status updates |
| `-vv` | DEBUG | Detailed API calls, responses |
| `-q` | ERROR | Only critical errors |

### Best Practices for Large Files

1. **Always use bulk mode for files > 100 entries**:
   ```bash
   gpt-po-translator --folder ./locales --lang fr --bulk --bulksize 50 -v
   ```

2. **Adjust batch size based on content**:
   - Short entries (1-5 words): `--bulksize 100`
   - Medium entries (sentences): `--bulksize 50` (default)
   - Long entries (paragraphs): `--bulksize 20`

3. **Monitor progress for long-running tasks**:
   ```bash
   # Run with progress tracking
   gpt-po-translator --folder ./large-project --lang de,fr,es --bulk -v
   ```

---

## AI Translation Tracking

### Overview

**AI translation tracking is enabled by default.** The tool automatically tracks which translations were generated by AI versus human translators. This is particularly useful for:
- Quality assurance and review processes
- Compliance with requirements to identify AI-generated content
- Incremental translation workflows where you need to track changes

### How It Works

When a translation is generated by the AI, the tool adds a translator comment to the PO entry:

```po
#. AI-generated
msgid "Hello, world!"
msgstr "Hola, mundo!"
```

These comments are:
- **Persistent**: They're saved in the PO file and preserved across edits
- **Standard-compliant**: Using the official gettext translator comment syntax (`#.`)
- **Tool-friendly**: Visible in PO editors like Poedit, Lokalize, etc.
- **Searchable**: Easy to find with grep or other search tools

### Managing AI Comments

**Finding AI translations:**
```bash
# Count AI-generated translations
grep -c "^#\. AI-generated" locales/es/LC_MESSAGES/messages.po

# List files with AI translations
grep -l "^#\. AI-generated" locales/**/*.po
```

**Important: Django Workflow Consideration**
Django's `makemessages` command removes translator comments (including AI-generated tags) when updating PO files. This means:

- **After running our translator**: AI comments are preserved in PO files
- **After running Django makemessages**: AI comments are removed, but translations remain
- **Best practice**: Re-run the AI translator after Django makemessages to restore AI tagging on any remaining untranslated entries

**Disabling AI comments:**
If you don't want AI translations to be marked, use the `--no-ai-comment` flag:
```bash
gpt-po-translator --folder ./locales --lang de --no-ai-comment
```

---

## Using Ollama (Local AI Provider)

### Overview

Ollama allows you to run AI models locally on your machine, providing:
- **Privacy**: All translations happen locally, no data sent to cloud services
- **Cost**: No API fees - completely free
- **Offline**: Works without internet connection
- **Control**: Full control over model and infrastructure

### Prerequisites

1. **Install Ollama**
   ```bash
   # macOS/Linux
   curl -fsSL https://ollama.com/install.sh | sh

   # Or download from https://ollama.com
   ```

2. **Pull a model**
   ```bash
   # For multilingual (Arabic, Chinese, etc.)
   ollama pull qwen2.5

   # For European languages only
   ollama pull llama3.2

   # Other options
   ollama pull llama3.1   # Better quality, slower
   ollama pull mistral    # Good for European languages
   ```

3. **Start Ollama** (if not already running)
   ```bash
   ollama serve
   ```

### Basic Usage

```bash
# Latin scripts (English, French, Spanish, etc.) - can use bulk mode
gpt-po-translator --provider ollama --folder ./locales --bulk

# Non-Latin scripts (Arabic, Chinese, Japanese, etc.) - omit --bulk for better quality
gpt-po-translator --provider ollama --model qwen2.5 --folder ./locales --lang ar

# Specify a model
gpt-po-translator --provider ollama --model llama3.1 --folder ./locales

# List available models
gpt-po-translator --provider ollama --list-models
```

> **⚠️ Important:** For **non-Latin languages**, **omit the `--bulk` flag**. Local models struggle with JSON formatting for Arabic/Chinese/etc., resulting in poor translation quality or errors. Single-item mode is more reliable.

### Configuration

#### Option 1: Environment Variable

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
gpt-po-translator --provider ollama --folder ./locales --bulk
```

#### Option 2: CLI Arguments

```bash
# Custom port
gpt-po-translator --provider ollama \
  --ollama-base-url http://localhost:8080 \
  --folder ./locales --bulk

# Increase timeout for slow models
gpt-po-translator --provider ollama \
  --ollama-timeout 300 \
  --folder ./locales --bulk
```

#### Option 3: Config File

Add to your `pyproject.toml`:

```toml
[tool.gpt-po-translator.provider.ollama]
base_url = "http://localhost:11434"
model = "llama3.2"
timeout = 120

[tool.gpt-po-translator]
bulk_mode = true
bulk_size = 50
```

Then simply run:
```bash
gpt-po-translator --provider ollama --folder ./locales
```

### Advanced Scenarios

#### Remote Ollama Server

Run Ollama on a different machine:

```bash
# On the Ollama server (192.168.1.100)
ollama serve --host 0.0.0.0

# On your machine
gpt-po-translator --provider ollama \
  --ollama-base-url http://192.168.1.100:11434 \
  --folder ./locales --bulk
```

Or set in `pyproject.toml`:
```toml
[tool.gpt-po-translator.provider.ollama]
base_url = "http://192.168.1.100:11434"
```

#### Docker with Ollama

Run Ollama on your host machine, then use Docker with `--network host`:

```bash
# 1. Start Ollama on host
ollama serve

# 2. Pull a model on host
ollama pull qwen2.5

# 3. Run translator in Docker (Linux/macOS)
docker run --rm \
  -v $(pwd):/data \
  --network host \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --provider ollama \
  --folder /data

# macOS/Windows Docker Desktop: use host.docker.internal
docker run --rm \
  -v $(pwd):/data \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --provider ollama \
  --ollama-base-url http://host.docker.internal:11434 \
  --folder /data
```

**With config file:**
```bash
# Add Ollama config to pyproject.toml in your project
docker run --rm \
  -v $(pwd):/data \
  -v $(pwd)/pyproject.toml:/data/pyproject.toml \
  --network host \
  ghcr.io/pescheckit/python-gpt-po:latest \
  --provider ollama \
  --folder /data
```

### Performance Considerations

**Pros:**
- No API costs
- Privacy and data control
- No rate limits
- Offline capability

**Cons:**
- Quality varies by model (may not match GPT-4)
- Requires local resources (RAM, GPU recommended)
- Initial setup needed (install Ollama, pull models)

**Performance Tips:**
1. **Use GPU**: Install Ollama with GPU support for 10-100x speedup
2. **Choose appropriate models**:
   - Small projects: `llama3.2` (fast, good quality)
   - Better quality: `llama3.1` (slower, better accuracy)
   - Multilingual: `qwen2.5` (excellent for non-Latin scripts like Arabic, Chinese, etc.)
   - Specialized: `mistral`, `gemma2`
3. **Increase timeout** for large models: `--ollama-timeout 300`
4. **Bulk mode vs Single mode**:
   - **Bulk mode (`--bulk`)**: Faster but requires model to return valid JSON - recommended for cloud providers
   - **Single mode (no `--bulk`)**: Slower but more reliable for local models, especially with non-Latin scripts
   - For Ollama with languages like Arabic/Chinese/Japanese, **omit `--bulk`** for better quality

### Recommended Models for Translation

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `llama3.2` | 3B | ⚡⚡⚡ Fast | ⭐⭐⭐ Good | General use, Latin scripts only |
| `llama3.1` | 8B | ⚡⚡ Medium | ⭐⭐⭐⭐ Better | Better quality, medium projects |
| `qwen2.5` | 7B | ⚡⚡ Medium | ⭐⭐⭐⭐ Excellent | **Multilingual** (Arabic, Chinese, etc.) |
| `mistral` | 7B | ⚡⚡ Medium | ⭐⭐⭐ Good | European languages |
| `gemma2` | 9B | ⚡ Slower | ⭐⭐⭐⭐ Better | High quality translations |

**Note:** For non-Latin scripts (Arabic, Chinese, Japanese, etc.), use `qwen2.5` or larger models **without `--bulk` flag** for best results.

### Troubleshooting

**"Cannot connect to Ollama"**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve

# Check if running on different port
ollama serve --help
```

**Slow translations**
- Use GPU-enabled Ollama installation
- Choose a smaller model (`llama3.2` instead of `llama3.1`)
- Increase `--bulksize` to batch more entries together
- Close other applications to free up RAM

**Model not found**
```bash
# List installed models
ollama list

# Pull the model
ollama pull llama3.2
```

**Timeout errors**
```bash
# Increase timeout
gpt-po-translator --provider ollama --ollama-timeout 300 --folder ./locales
```

### Configuration Priority

Ollama settings are loaded in this order (highest to lowest):

1. **CLI arguments**: `--ollama-base-url`, `--ollama-timeout`
2. **Environment variables**: `OLLAMA_BASE_URL`
3. **Config file**: `pyproject.toml` under `[tool.gpt-po-translator.provider.ollama]`
4. **Defaults**: `http://localhost:11434`, timeout `120s`

---

## Whitespace Handling in Translations

### Overview

The tool automatically preserves leading and trailing whitespace from `msgid` entries in translations. While **best practice** is to handle whitespace in your UI framework rather than in translation strings, the tool ensures that any existing whitespace patterns are maintained exactly.

### How Whitespace Preservation Works

The tool uses a three-step process to reliably preserve whitespace:

1. **Detection and Warning**
   When processing PO files, the tool scans for entries with leading or trailing whitespace and logs a warning:
   ```
   WARNING: Found 3 entries with leading/trailing whitespace in messages.po
   Whitespace will be preserved in translations, but ideally should be handled in your UI framework.
   ```

2. **Before Sending to AI** (Bulk Mode)
   To prevent the AI from being confused by or accidentally modifying whitespace, the tool:
   - Strips all leading/trailing whitespace from texts
   - Stores the original whitespace pattern
   - Sends only the clean text content to the AI

   For example, if `msgid` is `" Incorrect"` (with leading space), the AI receives only `"Incorrect"`.

3. **After Receiving Translation**
   Once the AI returns the translation, the tool:
   - Extracts the original whitespace pattern from the source `msgid`
   - Applies that exact pattern to the translated `msgstr`
   - Ensures the output matches the input whitespace structure

   So `" Incorrect"` → AI translates `"Incorrect"` → Result: `" Incorreto"` (leading space preserved)

### Examples

| Original msgid | AI Receives | AI Returns | Final msgstr |
|----------------|-------------|------------|--------------|
| `" Hello"` | `"Hello"` | `"Bonjour"` | `" Bonjour"` |
| `"World "` | `"World"` | `"Monde"` | `"Monde "` |
| `"  Hi  "` | `"Hi"` | `"Salut"` | `"  Salut  "` |
| `"\tTab"` | `"Tab"` | `"Onglet"` | `"\tOnglet"` |

### Why This Approach Is Reliable

This implementation is **bulletproof** because:
- **The AI never sees the problematic whitespace**, so it can't strip or modify it
- **Whitespace is managed entirely in code**, not reliant on AI behavior
- **Works consistently across all providers** (OpenAI, Anthropic, Azure, DeepSeek)
- **Handles edge cases**: empty strings, whitespace-only strings, mixed whitespace types (spaces, tabs, newlines)

### Single vs. Bulk Mode

- **Single Mode**: Each text is stripped before sending to AI, then whitespace is restored after receiving the translation
- **Bulk Mode**: Entire batches are stripped before sending to AI (JSON array of clean texts), then whitespace is restored to each translation individually

Both modes use the same preservation logic, ensuring consistent behavior.

### Best Practices

1. **Avoid whitespace in msgid when possible**
   Whitespace in translation strings can cause formatting issues. Instead, handle spacing in your UI layer:
   ```python
   # Bad - whitespace in msgid
   msgid " Settings"

   # Good - whitespace in code
   print(f"  {_('Settings')}")
   ```

2. **If whitespace is unavoidable**
   The tool will preserve it automatically. Use verbose mode to see which entries contain whitespace:
   ```bash
   gpt-po-translator --folder ./locales --lang fr -vv
   ```

3. **Review whitespace warnings**
   When the tool warns about whitespace entries, consider refactoring your code to move the whitespace out of the translation strings.

---

## Context-Aware Translations with msgctxt

### Overview

The tool automatically uses `msgctxt` (message context) from PO entries to provide context to the AI, improving translation accuracy for ambiguous terms.

### How It Works

When a PO entry includes `msgctxt`, it's automatically passed to the AI:

```po
msgctxt "button"
msgid "Save"
msgstr ""
```

The AI receives:
```
CONTEXT: button
IMPORTANT: Choose the translation that matches this specific context and usage.

Translate to German: Save
```

Result: **"Speichern"** (button action) instead of **"Sparen"** (to save money)

### Default Context

For entries without explicit `msgctxt`, you can provide a default context that applies to all translations:

#### Configuration Methods

**1. Command-Line Argument (highest priority):**
```bash
gpt-po-translator --folder ./locales --default-context "web application" --bulk
```

**2. Environment Variable:**
```bash
export GPT_TRANSLATOR_CONTEXT="mobile app for iOS"
gpt-po-translator --folder ./locales --bulk
```

**3. Configuration File (pyproject.toml):**
```toml
[tool.gpt-po-translator]
default_context = "e-commerce checkout flow"
```

#### Priority Order
CLI argument > Environment variable > Config file

#### Behavior
- Entries **with** `msgctxt` → Uses the explicit `msgctxt` (always takes precedence)
- Entries **without** `msgctxt` → Uses the default context
- No default context configured → No context provided (original behavior)

#### Example
```bash
gpt-po-translator --folder ./locales --default-context "medical device interface" --lang de
```

With this setup:
```po
# Entry WITH msgctxt - uses "button"
msgctxt "button"
msgid "Start"
msgstr ""  → "Starten" (button action)

# Entry WITHOUT msgctxt - uses default "medical device interface"
msgid "Start"
msgstr ""  → "Start" (medical procedure start, preserving technical term)
```

### Best Practices

**✓ Good - Detailed, Explicit Context:**
```po
msgctxt "status: not Halten (verb), but Angehalten/Wartend (state)"
msgid "Hold"
msgstr ""  → "Angehalten" ✓
```

**⚠️ Limited - Simple Context:**
```po
msgctxt "status"
msgid "Hold"
msgstr ""  → "Halten" (may still be wrong)
```

**Key Points:**
- **Be explicit** - Describe what you want AND what you don't want
- **Provide examples** - Include similar terms or expected word forms
- **Use default context for project-wide context** - Helps all translations understand domain (e.g., "legal contract", "gaming UI", "medical records")
- **Use msgctxt for specific terms** - Override default with specific context when needed
- **Human review still needed** - Context improves results but doesn't guarantee perfection

---

## Behind the Scenes: API Calls and Post-Processing

- **Provider-Specific API Calls:**  
  The tool constructs different API requests based on the selected provider. For example:
  - **OpenAI:** Uses the OpenAI Python client to create a chat completion.
  - **Azure OpenAI:** Uses the OpenAI Python client configured for Azure endpoints.
  - **Anthropic:** Sends a request to Anthropic’s API using custom headers.
  - **DeepSeek:** Uses the `requests` library to post JSON data, and then cleans up responses that may be wrapped in markdown code blocks.

- **Response Cleanup:**  
  For providers like DeepSeek, responses may include extra markdown formatting. The method `_clean_json_response` strips away these wrappers so that the JSON can be parsed correctly.

- **Validation and Retry:**  
  If a translation is too long or includes extra explanations, the tool automatically retries the translation with a more concise prompt. This is handled by `validate_translation` and `retry_long_translation` methods, ensuring the final output meets the expected format.

---

## Conclusion

This document has provided an in-depth explanation of the internal workflow of `gpt-po-translator` and detailed every command-line argument along with its behind-the-scenes effect. By understanding these mechanics, you can better configure and extend the tool to fit your localization needs.

For a quick start, please refer to the [Usage Guide](./usage.md). For any questions or further contributions, visit our [GitHub repository](https://github.com/pescheckit/python-gpt-po).
