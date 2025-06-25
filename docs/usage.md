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

- **`--lang <language_codes>`**  
  *Description:* A comma-separated list of ISO 639-1 language codes (e.g., `de,fr`).  
  *Behind the scenes:* The tool filters PO files by comparing these codes with the file metadata and folder names (if `--folder-language` is enabled).

### Optional Options

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
  *Behind the scenes:* The tool filters for entries with the 'fuzzy' flag and attempts to translate them, removing the flag upon successful translation. AI-generated translations are marked as usual unless `--no-ai-comment` is used.

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
  *Behind the scenes:* The tool inspects the path components (directory names) of each PO file and matches them against the provided language codes.

- **`--no-ai-comment`**  
  *Description:* Disables the automatic addition of 'AI-generated' comments to translated entries.  
  *Behind the scenes:* **By default (without this flag), every translation made by the AI is marked with a `#. AI-generated` comment in the PO file.** This flag prevents that marking, making AI translations indistinguishable from human translations in the file.  
  *Note:* AI tagging is enabled by default for tracking, compliance, and quality assurance purposes.

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

### Programmatic Access

The tool provides helper methods for working with AI-generated translations programmatically:

```python
from python_gpt_po.services.po_file_handler import POFileHandler
import polib

# Load a PO file
po_file = polib.pofile('messages.po')

# Get all AI-generated entries
ai_entries = POFileHandler.get_ai_generated_entries(po_file)

# Remove AI-generated comments if needed
POFileHandler.remove_ai_generated_comments(po_file)
po_file.save()
```

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
