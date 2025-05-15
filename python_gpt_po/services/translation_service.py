"""
Translation service for the PO translator.
This module handles the core translation functionality, including communicating with
various AI providers, processing translations in bulk or individually, and updating
PO files with the translated content.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import polib
import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models.config import TranslationConfig
from ..models.enums import ModelProvider
from .model_manager import ModelManager
from .po_file_handler import POFileHandler


class TranslationService:
    """Class to encapsulate translation functionalities."""

    def __init__(self, config: TranslationConfig, batch_size: int = 40):
        """Initialize the translation service.

        Args:
            config (TranslationConfig): Configuration for the translation service
            batch_size (int): Size of batches for bulk translation
        """
        self.config = config
        self.batch_size = batch_size
        self.total_batches = 0
        self.po_file_handler = POFileHandler()
        self.model_manager = ModelManager()

    def _get_openai_response(self, content: str) -> str:
        """Get response from OpenAI API."""
        if not self.config.provider_clients.openai_client:
            raise ValueError("OpenAI client not initialized")

        message = {"role": "user", "content": content}
        completion = self.config.provider_clients.openai_client.chat.completions.create(
            model=self.config.model,
            messages=[message]
        )
        return completion.choices[0].message.content.strip()

    def _get_anthropic_response(self, content: str) -> str:
        """Get response from Anthropic API."""
        if not self.config.provider_clients.anthropic_client:
            raise ValueError("Anthropic client not initialized")

        message = {"role": "user", "content": content}
        completion = self.config.provider_clients.anthropic_client.messages.create(
            model=self.config.model,
            max_tokens=4000,
            messages=[message]
        )
        return completion.content[0].text.strip()

    def _get_deepseek_response(self, content: str) -> str:
        """Get response from DeepSeek API."""
        if not self.config.provider_clients.deepseek_api_key:
            raise ValueError("DeepSeek API key not set")

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
        return response.json()["choices"][0]["message"]["content"].strip()

    def validate_provider_connection(self) -> bool:
        """Validates the connection to the selected provider by making a test API call."""
        provider = self.config.provider
        try:
            # Use the generic translation method to validate connection
            self.perform_translation("Test connection", "en", is_bulk=False)
            logging.info("%s connection validated successfully.", provider.value)
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

        return self.validate_translation(text, self.perform_translation(
            prompt + text, target_language, is_bulk=False, detail_language=detail_language
        ))

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
            # Get the response text from the provider
            response_text = self._get_provider_response(content)

            # Process the response according to bulk mode
            if is_bulk:
                return self._process_bulk_response(response_text, texts)
            return self.validate_translation(texts, response_text)

        except Exception as e:
            logging.error("Translation error: %s", str(e))
            raise

    def _get_provider_response(self, content: str) -> str:
        """Get translation response from the selected provider."""
        provider = self.config.provider

        if provider == ModelProvider.OPENAI:
            return self._get_openai_response(content)
        if provider == ModelProvider.ANTHROPIC:
            return self._get_anthropic_response(content)
        if provider == ModelProvider.DEEPSEEK:
            return self._get_deepseek_response(content)
        return ""

    def _process_bulk_response(self, response_text: str, original_texts: List[str]) -> List[str]:
        """Process a bulk translation response."""
        try:
            # Clean the response text for formatting issues
            clean_response = self._clean_json_response(response_text)
            logging.debug("Cleaned JSON response: %s...", clean_response[:100])

            # Parse the JSON response
            translated_texts = json.loads(clean_response)

            # Validate the format
            if not isinstance(translated_texts, list) or len(translated_texts) != len(original_texts):
                raise ValueError("Invalid response format")

            # Validate each translation
            return [
                self.validate_translation(original, translated)
                for original, translated in zip(original_texts, translated_texts)
            ]
        except json.JSONDecodeError as e:
            logging.error("Invalid JSON response: %s", response_text)
            raise ValueError("Invalid JSON response") from e

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
            content = prompt + text
            retried_translation = self._get_provider_response(content)

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
                po_file_result = self._prepare_po_file(po_file_path, languages)
                if po_file_result is None:
                    logging.info("Skipping file %s due to language mismatch or other issues", po_file_path)
                    continue

                # Process the file, passing the prepared po_file and file_lang
                self.process_po_file(po_file_path, languages, detail_languages, po_file_result)

    def process_po_file(
        self,
        po_file_path: str,
        languages: List[str],
        detail_languages: Optional[Dict[str, str]] = None,
        po_file_result=None,
    ):
        """Processes a single .po file with translations."""
        try:
            # Only prepare the po_file if not provided (for backward compatibility)
            if po_file_result is None:
                po_file_result = self._prepare_po_file(po_file_path, languages)
                if po_file_result is None:
                    return

            po_file, file_lang = po_file_result

            # Get the detailed language name if available
            detail_lang = detail_languages.get(file_lang) if detail_languages else None

            if self.config.fix_fuzzy:
                self.fix_fuzzy_entries(po_file, po_file_path, file_lang, detail_lang)
                return

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
            logging.warning(
                "Consider running with '--fix-fuzzy' to clean and update the fuzzy translations properly.",
            )
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
        return po_file, file_lang

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

    def _update_fuzzy_po_entries(
        self,
        po_file,
        translations: List[str],
        entries_to_update: list
    ):
        """Update only fuzzy entries, remove 'fuzzy' flag, and log cleanly."""
        for entry, translation in zip(entries_to_update, translations):
            if translation.strip():
                self.po_file_handler.update_po_entry(po_file, entry.msgid, translation)
                if 'fuzzy' in entry.flags:
                    entry.flags.remove('fuzzy')
                logging.info("Fixed fuzzy entry '%s' -> '%s'", entry.msgid, translation)
            else:
                logging.warning("Translation for fuzzy '%s' is still empty, leaving fuzzy.", entry.msgid)

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

    def fix_fuzzy_entries(
        self,
        po_file,
        po_file_path: str,
        target_language: str,
        detail_language: Optional[str] = None,
    ):
        """Find and fix fuzzy entries in a PO file using AI translation."""
        fuzzy_entries = [entry for entry in po_file if 'fuzzy' in entry.flags]

        if not fuzzy_entries:
            logging.info("No fuzzy entries found in %s", po_file_path)
            return

        logging.info("Found %d fuzzy entries to fix in %s", len(fuzzy_entries), po_file_path)

        texts_to_translate = [entry.msgid for entry in fuzzy_entries]
        translations = self.get_translations(texts_to_translate, target_language, po_file_path, detail_language)

        self._update_fuzzy_po_entries(po_file, translations, entries_to_update=fuzzy_entries)

        po_file.save(po_file_path)

        self.po_file_handler.log_translation_status(
            po_file_path,
            texts_to_translate,
            [entry.msgstr for entry in fuzzy_entries]
        )

        logging.info("Fuzzy fix completed for %s", po_file_path)
