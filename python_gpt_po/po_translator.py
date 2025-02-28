"""
GPT Translator - Enhanced Multi-Provider Version
"""

import argparse
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import polib
import pycountry
import requests  # For DeepSeek API
from anthropic import Anthropic  # Added Anthropic client
from dotenv import load_dotenv
from openai import OpenAI
from pkg_resources import DistributionNotFound, get_distribution
from tenacity import retry, stop_after_attempt, wait_fixed

# Initialize environment variables and logging
load_dotenv()
logging.basicConfig(level=logging.INFO)


class ModelProvider(Enum):
    """Enum for supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class ProviderClients:
    """Class to store API clients for various providers."""

    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.deepseek_api_key = None
        self.deepseek_base_url = "https://api.deepseek.com/v1"

    def initialize_clients(self, api_keys: Dict[str, str]):
        """Initialize API clients for all providers with available keys."""
        if api_keys.get("openai"):
            self.openai_client = OpenAI(api_key=api_keys["openai"])

        if api_keys.get("anthropic"):
            self.anthropic_client = Anthropic(api_key=api_keys["anthropic"])

        if api_keys.get("deepseek"):
            self.deepseek_api_key = api_keys["deepseek"]


class POFileHandler:
    """Handles operations related to .po files."""

    @staticmethod
    def disable_fuzzy_translations(po_file_path):
        """Disables fuzzy translations in a .po file."""
        try:
            # Read the file content
            with open(po_file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Remove fuzzy markers from the content
            content = content.replace('#, fuzzy\n', '')

            # Write the updated content back to the file
            with open(po_file_path, 'w', encoding='utf-8') as file:
                file.write(content)

            # Load the .po file and remove fuzzy flags from entries
            po_file = polib.pofile(po_file_path)
            fuzzy_entries = [entry for entry in po_file if 'fuzzy' in entry.flags]
            for entry in fuzzy_entries:
                entry.flags.remove('fuzzy')

            # Remove 'Fuzzy' from the metadata if present
            if po_file.metadata:
                po_file.metadata.pop('Fuzzy', None)

            # Save the updated .po file
            po_file.save(po_file_path)
            logging.info("Fuzzy translations disabled in file: %s", po_file_path)

        except Exception as e:
            logging.error("Error while disabling fuzzy translations in file %s: %s", po_file_path, e)

    @staticmethod
    def get_file_language(po_file_path, po_file, languages, folder_language):
        """Determines the language for a .po file."""
        file_lang = po_file.metadata.get('Language', '')
        normalized_lang = POFileHandler.normalize_language_code(file_lang)

        if normalized_lang in languages:
            return normalized_lang

        if folder_language:
            for part in po_file_path.split(os.sep):
                norm_part = POFileHandler.normalize_language_code(part)
                if norm_part in languages:
                    logging.info("Inferred language for .po file: %s as %s", po_file_path, norm_part)
                    return norm_part

        return None

    @staticmethod
    def normalize_language_code(lang):
        """Convert language name or code to ISO 639-1 code."""
        if not lang:
            return None

        # Try direct lookup
        if len(lang) == 2:
            try:
                return pycountry.languages.get(alpha_2=lang.lower()).alpha_2
            except AttributeError:
                pass

        # Try by name
        try:
            return pycountry.languages.get(name=lang.title()).alpha_2
        except AttributeError:
            pass

        # Try by native name
        for language in pycountry.languages:
            if hasattr(language, 'inverted_name') and language.inverted_name.lower() == lang.lower():
                return language.alpha_2

        return None

    @staticmethod
    def log_translation_status(po_file_path, original_texts, translations):
        """Logs the status of translations for a .po file."""
        total = len(original_texts)
        translated = sum(1 for t in translations if t)

        # Log a warning if there are untranslated texts
        if translated < total:
            logging.warning(
                "File: %s - %s/%s texts translated. Some translations are missing.",
                po_file_path, translated, total
            )
            for original, translation in zip(original_texts, translations):
                if not translation:
                    logging.warning("Missing translation for: '%s'", original)
        else:
            logging.info("File: %s - All %s texts successfully translated.", po_file_path, total)

    @staticmethod
    def update_po_entry(po_file, original_text, translated_text):
        """Updates a .po file entry with the translated text."""
        entry = po_file.find(original_text)
        if entry:
            entry.msgstr = translated_text
            logging.debug("Updated translation for '%s' to '%s'", original_text, translated_text)
        else:
            logging.warning("Original text '%s' not found in the .po file.", original_text)


@dataclass
class TranslationConfig:
    """Class to hold configuration parameters for the translation service."""
    provider_clients: ProviderClients
    provider: ModelProvider
    model: str
    bulk_mode: bool = False
    fuzzy: bool = False
    folder_language: bool = False


class ModelManager:
    """Class to manage models from different providers."""

    @staticmethod
    # pylint: disable=too-many-return-statements
    def get_available_models(provider_clients: ProviderClients, provider: ModelProvider) -> List[str]:
        """Retrieve available models from a specific provider."""
        try:
            if provider == ModelProvider.OPENAI:
                if not provider_clients.openai_client:
                    logging.error("OpenAI client not initialized")
                    return []
                response = provider_clients.openai_client.models.list()
                return [model.id for model in response.data]

            if provider == ModelProvider.ANTHROPIC:
                if not provider_clients.anthropic_client:
                    logging.error("Anthropic client not initialized")
                    return []

                # Use Anthropic's models endpoint
                headers = {
                    "x-api-key": provider_clients.anthropic_client.api_key,
                    "anthropic-version": "2023-06-01"
                }

                try:
                    response = requests.get(
                        "https://api.anthropic.com/v1/models",
                        headers=headers,
                        timeout=15
                    )
                    response.raise_for_status()
                    model_data = response.json().get("data", [])
                    return [model["id"] for model in model_data]
                except Exception as e:
                    logging.error("Error fetching Anthropic models: %s", str(e))
                    # Fallback to commonly used models if API call fails
                    return [
                        "claude-3-7-sonnet-latest",
                        "claude-3-5-haiku-latest",
                        "claude-3-5-sonnet-latest",
                        "claude-3-opus-20240229",
                    ]

            if provider == ModelProvider.DEEPSEEK:
                if not provider_clients.deepseek_api_key:
                    logging.error("DeepSeek API key not set")
                    return []

                headers = {
                    "Authorization": f"Bearer {provider_clients.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.get(
                    f"{provider_clients.deepseek_base_url}/models",
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                return [model["id"] for model in response.json().get("data", [])]

            return []
        except Exception as e:
            logging.error("Error fetching models from %s: %s", provider.value, str(e))
            return []


class TranslationService:
    """Class to encapsulate translation functionalities."""

    def __init__(self, config: TranslationConfig, batch_size: int = 40):
        self.config = config
        self.batch_size = batch_size
        self.total_batches = 0
        self.po_file_handler = POFileHandler()
        self.model_manager = ModelManager()

    def validate_provider_connection(self) -> bool:
        """Validates the connection to the selected provider by making a test API call."""
        provider = self.config.provider
        try:
            if provider == ModelProvider.OPENAI:
                if not self.config.provider_clients.openai_client:
                    logging.error("OpenAI client not initialized")
                    return False

                test_message = {"role": "system", "content": "Test message to validate connection."}
                self.config.provider_clients.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[test_message]
                )
                logging.info("OpenAI connection validated successfully.")

            elif provider == ModelProvider.ANTHROPIC:
                if not self.config.provider_clients.anthropic_client:
                    logging.error("Anthropic client not initialized")
                    return False

                self.config.provider_clients.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Test message to validate connection."}]
                )
                logging.info("Anthropic connection validated successfully.")

            elif provider == ModelProvider.DEEPSEEK:
                if not self.config.provider_clients.deepseek_api_key:
                    logging.error("DeepSeek API key not set")
                    return False

                headers = {
                    "Authorization": f"Bearer {self.config.provider_clients.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": "Test message to validate connection."}],
                    "max_tokens": 10
                }
                response = requests.post(
                    f"{self.config.provider_clients.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                logging.info("DeepSeek connection validated successfully.")

            return True

        except Exception as e:
            logging.error("Failed to validate %s connection: %s", provider.value, str(e))
            return False

    def translate_bulk(
            self,
            texts: List[str],
            target_language: str,
            po_file_path: str,
            detail_language: Optional[str] = None) -> List[str]:
        """Translates a list of texts in bulk, processing in smaller chunks."""
        translated_texts = []
        chunk_size = self.batch_size

        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            logging.info("Translating chunk %d of %d", i // chunk_size + 1, (len(texts) - 1) // chunk_size + 1)

            try:
                translations = self.perform_translation(
                    chunk, target_language, is_bulk=True, detail_language=detail_language
                )
                translated_texts.extend(translations)
            except Exception as e:
                logging.error("Bulk translation failed for chunk %d: %s", i // chunk_size + 1, str(e))
                for text in chunk:
                    try:
                        translation = self.perform_translation(
                            text, target_language, is_bulk=False, detail_language=detail_language
                        )
                        translated_texts.append(translation)
                    except Exception as inner_e:
                        logging.error("Individual translation failed for text '%s': %s", text, str(inner_e))
                        translated_texts.append("")  # Placeholder for failed translation

            logging.info("Processed %d out of %d translations", len(translated_texts), len(texts))

        if len(translated_texts) != len(texts):
            logging.error(
                "Translation count mismatch in %s. Expected %d, got %d",
                po_file_path, len(texts), len(translated_texts)
            )

        return translated_texts

    def translate_single(self, text: str, target_language: str, detail_language: Optional[str] = None) -> str:
        """Translates a single text."""
        try:
            translation = self.perform_translation(
                text, target_language, is_bulk=False, detail_language=detail_language
            )
            if not translation.strip():
                logging.warning("Empty translation returned for '%s'. Attempting without validation.", text)
                translation = self.perform_translation_without_validation(
                    text, target_language, detail_language=detail_language
                )
            return translation
        except Exception as e:
            logging.error("Error translating '%s': %s", text, str(e))
            return ""

    def perform_translation_without_validation(
            self,
            text: str,
            target_language: str,
            detail_language: Optional[str] = None) -> str:
        """Performs translation without validation for single words or short phrases."""
        # Use the detailed language name if provided, otherwise use the short code
        target_lang_text = detail_language if detail_language else target_language

        prompt = (
            f"Translate this single word or short phrase from English to {target_lang_text}. "
            "Return only the direct translation without any explanation, additional text, or repetition. "
            "If the word should not be translated (like technical terms or names), return it unchanged:\n"
        )

        try:
            provider = self.config.provider

            if provider == ModelProvider.OPENAI:
                message = {"role": "user", "content": prompt + text}
                completion = self.config.provider_clients.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[message]
                )
                return self.post_process_translation(text, completion.choices[0].message.content.strip())

            if provider == ModelProvider.ANTHROPIC:
                message = {"role": "user", "content": prompt + text}
                completion = self.config.provider_clients.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=100,
                    messages=[message]
                )
                return self.post_process_translation(text, completion.content[0].text)

            if provider == ModelProvider.DEEPSEEK:
                headers = {
                    "Authorization": f"Bearer {self.config.provider_clients.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt + text}],
                    "max_tokens": 100
                }
                response = requests.post(
                    f"{self.config.provider_clients.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                return self.post_process_translation(text, response.json()["choices"][0]["message"]["content"].strip())

            return ""

        except Exception as e:
            logging.error("Error in perform_translation_without_validation: %s", str(e))
            return ""

    @staticmethod
    def post_process_translation(original: str, translated: str) -> str:
        """Post-processes the translation to handle repetitions and long translations."""
        if not translated:
            return ""

        if ' - ' in translated:
            parts = translated.split(' - ')
            if len(parts) == 2 and parts[0] == parts[1]:
                return parts[0]

        if len(translated.split()) > 2 * len(original.split()) + 1:
            logging.warning("Translation seems too long, might be an explanation: '%s'", translated)
            return original

        return translated

    @staticmethod
    def get_translation_prompt(target_language: str, is_bulk: bool, detail_language: Optional[str] = None) -> str:
        """Returns the appropriate translation prompt based on the translation mode."""
        # Use detailed language if provided, otherwise use the short target language code
        target_lang_text = detail_language if detail_language else target_language

        if is_bulk:
            return (
                f"Translate the following list of texts from English to {target_lang_text}. "
                "Provide only the translations in a JSON array format, maintaining the original order. "
                "Each translation should be concise and direct, without explanations or additional context. "
                "Keep special characters, placeholders, and formatting intact. "
                "If a term should not be translated (like 'URL' or technical terms), keep it as is. "
                "Example format: [\"Translation 1\", \"Translation 2\", ...]\n\n"
                "Texts to translate:\n"
            )
        return (
            f"Translate the following text from English to {target_lang_text}. "
            "Return only the direct, word-for-word translation without any explanation or additional context. "
            "Keep special characters, placeholders, and formatting intact. "
            "If a term should not be translated (like 'URL' or technical terms), keep it as is. "
            "Here is the text to translate:\n"
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    # pylint: disable=too-many-locals
    def perform_translation(
            self,
            texts: Any,
            target_language: str,
            is_bulk: bool = False,
            detail_language: Optional[str] = None) -> Any:
        """Performs the actual translation using the selected provider's API."""
        logging.debug("Performing translation to: %s using %s", target_language, self.config.provider.value)
        prompt = self.get_translation_prompt(target_language, is_bulk, detail_language)
        content = prompt + (json.dumps(texts) if is_bulk else texts)

        try:
            provider = self.config.provider
            response_text = ""

            if provider == ModelProvider.OPENAI:
                message = {"role": "user", "content": content}
                completion = self.config.provider_clients.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[message]
                )
                response_text = completion.choices[0].message.content.strip()

            elif provider == ModelProvider.ANTHROPIC:
                message = {"role": "user", "content": content}
                completion = self.config.provider_clients.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=4000,
                    messages=[message]
                )
                response_text = completion.content[0].text.strip()

            elif provider == ModelProvider.DEEPSEEK:
                headers = {
                    "Authorization": f"Bearer {self.config.provider_clients.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 4000
                }
                response = requests.post(
                    f"{self.config.provider_clients.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                response_text = response.json()["choices"][0]["message"]["content"].strip()

            if is_bulk:
                try:
                    # Clean the response text for DeepSeek
                    clean_response = self._clean_json_response(response_text)
                    logging.debug("Cleaned JSON response: %s...", clean_response[:100])

                    translated_texts = json.loads(clean_response)
                    if not isinstance(translated_texts, list) or len(translated_texts) != len(texts):
                        raise ValueError("Invalid response format")
                    return [
                        self.validate_translation(original, translated)
                        for original, translated in zip(texts, translated_texts)
                    ]
                except json.JSONDecodeError as e:
                    logging.error("Invalid JSON response: %s", response_text)
                    raise ValueError("Invalid JSON response") from e
            else:
                return self.validate_translation(texts, response_text)

        except Exception as e:
            logging.error("Translation error: %s", str(e))
            raise

    def _clean_json_response(self, response_text: str) -> str:
        """Clean JSON response, especially for models that return markdown code blocks."""
        # Check if the response is wrapped in markdown code blocks
        if response_text.startswith("```") and "```" in response_text[3:]:
            # Extract content between code blocks
            start_idx = response_text.find("\n", 3) + 1  # Skip the first line with ```json
            end_idx = response_text.rfind("```")
            return response_text[start_idx:end_idx].strip()

        # Check for any leading/trailing characters that might break JSON parsing
        # Remove any text before the first "[" or "{" for arrays or objects
        if "[" in response_text:
            array_start = response_text.find("[")
            response_text = response_text[array_start:]
        elif "{" in response_text:
            obj_start = response_text.find("{")
            response_text = response_text[obj_start:]

        # Remove any text after the last "]" or "}" for arrays or objects
        if "]" in response_text:
            array_end = response_text.rfind("]") + 1
            response_text = response_text[:array_end]
        elif "}" in response_text:
            obj_end = response_text.rfind("}") + 1
            response_text = response_text[:obj_end]

        return response_text

    def validate_translation(self, original: str, translated: str) -> str:
        """Validates the translation and retries if necessary."""
        translated = translated.strip()

        if len(translated.split()) > 2 * len(original.split()) + 1:
            logging.warning("Translation too long, retrying: %s -> %s", original[:50], translated[:50])
            return self.retry_long_translation(original, self.config.model.split('-')[-1])

        explanation_indicators = ["I'm sorry", "I cannot", "This refers to", "This means", "In this context"]
        if any(indicator.lower() in translated.lower() for indicator in explanation_indicators):
            logging.warning("Translation contains explanation: %s", translated[:50])
            return self.retry_long_translation(original, self.config.model.split('-')[-1])

        return translated

    def retry_long_translation(self, text: str, target_language: str) -> str:
        """Retries translation for long or explanatory responses."""
        prompt = (
            f"Translate this text concisely from English to {target_language}. "
            "Provide only the direct translation without any explanation or additional context. "
            "Keep special characters, placeholders, and formatting intact. "
            "If a term should not be translated (like 'URL' or technical terms), keep it as is.\n"
            "Text to translate:\n"
        )

        try:
            provider = self.config.provider
            retried_translation = ""

            if provider == ModelProvider.OPENAI:
                message = {"role": "user", "content": prompt + text}
                completion = self.config.provider_clients.openai_client.chat.completions.create(
                    model=self.config.model,
                    messages=[message]
                )
                retried_translation = completion.choices[0].message.content.strip()

            elif provider == ModelProvider.ANTHROPIC:
                message = {"role": "user", "content": prompt + text}
                completion = self.config.provider_clients.anthropic_client.messages.create(
                    model=self.config.model,
                    max_tokens=4000,
                    messages=[message]
                )
                retried_translation = completion.content[0].text.strip()

            elif provider == ModelProvider.DEEPSEEK:
                headers = {
                    "Authorization": f"Bearer {self.config.provider_clients.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.config.model,
                    "messages": [{"role": "user", "content": prompt + text}],
                    "max_tokens": 4000
                }
                response = requests.post(
                    f"{self.config.provider_clients.deepseek_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                retried_translation = response.json()["choices"][0]["message"]["content"].strip()

            if len(retried_translation.split()) > 2 * len(text.split()) + 1:
                logging.warning("Retried translation still too long: %s -> %s", text[:50], retried_translation[:50])
                return text

            logging.info("Successfully retried translation: %s -> %s", text[:50], retried_translation[:50])
            return retried_translation

        except Exception as e:
            logging.error("Error in retry_long_translation: %s", str(e))
            return text

    def scan_and_process_po_files(
            self,
            input_folder: str,
            languages: List[str],
            detail_languages: Optional[Dict[str, str]] = None):
        """Scans and processes .po files in the given input folder."""
        for root, _, files in os.walk(input_folder):
            for file in filter(lambda f: f.endswith(".po"), files):
                po_file_path = os.path.join(root, file)
                logging.info("Discovered .po file: %s", po_file_path)

                # Prepare the PO file, if it returns None then skip this file
                po_file = self._prepare_po_file(po_file_path, languages)
                if po_file is None:
                    logging.info("Skipping file %s due to language mismatch or other issues", po_file_path)
                    continue

                # Process the file
                self.process_po_file(po_file_path, languages, detail_languages)

    def process_po_file(
            self, po_file_path: str, languages: List[str],
            detail_languages: Optional[Dict[str, str]] = None):
        """Processes .po files"""
        try:
            po_file = self._prepare_po_file(po_file_path, languages)
            if not po_file:
                return

            file_lang = self.po_file_handler.get_file_language(
                po_file_path,
                po_file,
                languages,
                self.config.folder_language
            )

            # Get the detailed language name if available
            detail_lang = detail_languages.get(file_lang) if detail_languages else None

            texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip() and entry.msgid]
            translations = self.get_translations(texts_to_translate, file_lang, po_file_path, detail_lang)

            self._update_po_entries(po_file, translations, file_lang, detail_lang)
            self._handle_untranslated_entries(po_file, file_lang, detail_lang)

            po_file.save(po_file_path)
            self.po_file_handler.log_translation_status(
                po_file_path,
                texts_to_translate,
                [entry.msgstr for entry in po_file if entry.msgid in texts_to_translate]
            )
        except Exception as e:
            logging.error("Error processing file %s: %s", po_file_path, e)

    def _prepare_po_file(self, po_file_path: str, languages: List[str]):
        """Prepares the .po file for translation."""
        if self.config.fuzzy:
            self.po_file_handler.disable_fuzzy_translations(po_file_path)
        po_file = polib.pofile(po_file_path)
        file_lang = self.po_file_handler.get_file_language(
            po_file_path,
            po_file,
            languages,
            self.config.folder_language
        )
        if not file_lang:
            logging.warning("Skipping .po file due to language mismatch: %s", po_file_path)
            return None
        return po_file

    def get_translations(
            self,
            texts: List[str],
            target_language: str,
            po_file_path: str,
            detail_language: Optional[str] = None) -> List[str]:
        """
        Retrieves translations for the given texts using either bulk or individual translation.
        """
        if self.config.bulk_mode:
            return self.translate_bulk(texts, target_language, po_file_path, detail_language)
        return [self.translate_single(text, target_language, detail_language) for text in texts]

    def _update_po_entries(
            self,
            po_file,
            translations: List[str],
            target_language: str,
            detail_language: Optional[str] = None):
        """Updates the .po file entries with the provided translations."""
        for entry, translation in zip((e for e in po_file if not e.msgstr.strip()), translations):
            if translation.strip():
                self.po_file_handler.update_po_entry(po_file, entry.msgid, translation)
                logging.info("Translated '%s' to '%s'", entry.msgid, translation)
            else:
                self._handle_empty_translation(entry, target_language, detail_language)

    def _handle_empty_translation(self, entry, target_language: str, detail_language: Optional[str] = None):
        """Handles cases where the initial translation is empty."""
        logging.warning("Empty translation for '%s'. Attempting individual translation.", entry.msgid)
        individual_translation = self.translate_single(entry.msgid, target_language, detail_language)
        if individual_translation.strip():
            self.po_file_handler.update_po_entry(entry.po_file, entry.msgid, individual_translation)
            logging.info(
                "Individual translation successful: '%s' to '%s'",
                entry.msgid,
                individual_translation
            )
        else:
            logging.error("Failed to translate '%s' after individual attempt.", entry.msgid)

    def _handle_untranslated_entries(self, po_file, target_language: str, detail_language: Optional[str] = None):
        """Handles any remaining untranslated entries in the .po file."""
        for entry in po_file:
            if not entry.msgstr.strip() and entry.msgid:
                logging.warning("Untranslated entry found: '%s'. Attempting final translation.", entry.msgid)
                final_translation = self.translate_single(entry.msgid, target_language, detail_language)
                if final_translation.strip():
                    self.po_file_handler.update_po_entry(po_file, entry.msgid, final_translation)
                    logging.info(
                        "Final translation successful: '%s' to '%s'",
                        entry.msgid,
                        final_translation
                    )
                else:
                    logging.error("Failed to translate '%s' after final attempt.", entry.msgid)


def get_version():
    """Get package version."""
    try:
        return get_distribution("gpt-po-translator").version
    except DistributionNotFound:
        return "0.0.0"  # Default version if the package is not found (e.g., during development)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Scan and process .po files with multiple AI providers")
    parser.add_argument("--version", action="version", version=f'%(prog)s {get_version()}')
    parser.add_argument("--folder", required=True, help="Input folder containing .po files")
    parser.add_argument("--lang", required=True, help="Comma-separated language codes to filter .po files")
    parser.add_argument('--detail-lang', type=str, help="Comma-separated detailed language names, e.g. 'Dutch,German'")
    parser.add_argument("--fuzzy", action="store_true", help="Remove fuzzy entries")
    parser.add_argument("--bulk", action="store_true", help="Use bulk translation mode")
    parser.add_argument("--bulksize", type=int, default=50, help="Batch size for bulk translation")
    parser.add_argument("--api_key", help="Fallback API key for ChatGPT (OpenAI) if --openai-key is not provided")

    # Provider selection
    parser.add_argument(
        "--provider",
        choices=[
            "openai",
            "anthropic",
            "deepseek"],
        help="AI provider to use for translations (default: will use first provider with an available API key)")

    # Model selection
    parser.add_argument(
        "--model",
        help="Model name to use for translations. If not specified, will use default for the provider")
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for the selected provider and exit")

    # API keys
    parser.add_argument("--openai-key", help="OpenAI API key (can also use OPENAI_API_KEY env var)")
    parser.add_argument("--anthropic-key", help="Anthropic API key (can also use ANTHROPIC_API_KEY env var)")
    parser.add_argument("--deepseek-key", help="DeepSeek API key (can also use DEEPSEEK_API_KEY env var)")

    # Folder language options
    parser.add_argument("--folder-language", action="store_true", help="Set language from directory structure")

    return parser.parse_args()


def main():
    """Main function to parse arguments and initiate processing."""
    args = parse_args()

    # Setup API keys (prioritize command line arguments over environment variables)
    api_keys = {
        "openai": args.openai_key or args.api_key or os.getenv("OPENAI_API_KEY"),
        "anthropic": args.anthropic_key or os.getenv("ANTHROPIC_API_KEY"),
        "deepseek": args.deepseek_key or os.getenv("DEEPSEEK_API_KEY")
    }

    # Initialize provider clients
    provider_clients = ProviderClients()
    provider_clients.initialize_clients(api_keys)

    # Auto-select provider if not explicitly specified
    if not args.provider:
        # Use the first provider that has an API key
        for provider_name in ["openai", "anthropic", "deepseek"]:
            if api_keys.get(provider_name):
                provider = ModelProvider(provider_name)
                logging.info("Auto-selected provider: %s (based on available API key)", provider_name)
                break
        else:
            logging.error("No API keys provided for any provider. Please provide at least one API key.")
            return
    else:
        provider = ModelProvider(args.provider)
        if not api_keys.get(provider.value):
            logging.error("No API key provided for %s. Please provide an API key.", provider.value)
            return

    # Create model manager for listing models
    model_manager = ModelManager()

    # List models if requested
    if args.list_models:
        models = model_manager.get_available_models(provider_clients, provider)
        print(f"Available models for {provider.value}:")
        for model in models:
            print(f"  - {model}")
        return

    # Default models for each provider if none specified
    default_models = {
        ModelProvider.OPENAI: "gpt-4o-mini",
        ModelProvider.ANTHROPIC: "claude-3-5-haiku-latest",
        ModelProvider.DEEPSEEK: "deepseek-chat"
    }

    # Use specified model or default for the provider
    model = args.model or default_models.get(provider)

    # Validate the selected model is available
    if not model_manager.validate_model(provider_clients, provider, model):
        logging.warning(
            "Model '%s' not found for provider %s. "
            "Using default model %s.",
            model, provider.value, default_models.get(provider)
        )
        model = default_models.get(provider)

    # Parse language codes and detailed language names
    lang_codes = [lang.strip() for lang in args.lang.split(',')]

    # Create a mapping of language codes to detailed names if provided
    detail_langs_dict = {}
    if args.detail_lang:
        detail_langs = [lang.strip() for lang in args.detail_lang.split(',')]

        if len(lang_codes) != len(detail_langs):
            logging.error("The number of languages in --lang and --detail-lang must match.")
            return

        detail_langs_dict = dict(zip(lang_codes, detail_langs))

    # Initialize translation configuration
    config = TranslationConfig(
        provider_clients=provider_clients,
        provider=provider,
        model=model,
        bulk_mode=args.bulk,
        fuzzy=args.fuzzy,
        folder_language=args.folder_language
    )

    # Initialize translation service
    translation_service = TranslationService(config, args.bulksize)

    # Validate the provider connection
    if not translation_service.validate_provider_connection():
        logging.error("%s connection failed. Please check your API key and network connection.", provider.value)
        return

    # Start processing files
    logging.info("Starting translation with %s using model %s", provider.value, model)
    translation_service.scan_and_process_po_files(args.folder, lang_codes, detail_langs_dict)
    logging.info("Translation completed successfully")


if __name__ == "__main__":
    main()
