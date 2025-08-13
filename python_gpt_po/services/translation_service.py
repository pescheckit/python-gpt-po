"""
Translation service for the PO translator.
This module handles the core translation functionality, including communicating with
various AI providers, processing translations in bulk or individually, and updating
PO files with the translated content.
"""
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import polib
from tenacity import retry, stop_after_attempt, wait_fixed

from ..models.config import TranslationConfig
from ..utils.gitignore import create_gitignore_parser
from ..utils.po_entry_helpers import add_ai_generated_comment, is_entry_untranslated
from .po_file_handler import POFileHandler
from .providers.registry import ProviderRegistry


@dataclass
class FileCounters:
    """File-related counters."""
    processed: int = 0
    skipped: int = 0


@dataclass
class EntryCounters:
    """Entry-related counters."""
    translated: int = 0
    failed: int = 0
    attempted: int = 0
    total_in_files: int = 0
    translated_before: int = 0


@dataclass
class TranslationStats:
    """Statistics for translation processing."""
    files: FileCounters = None
    entries: EntryCounters = None
    elapsed_time: float = 0.0

    def __post_init__(self):
        if self.files is None:
            self.files = FileCounters()
        if self.entries is None:
            self.entries = EntryCounters()


@dataclass
class TranslationRequest:
    """Parameters for translation processing."""
    po_file: object  # polib.POFile
    entries: list
    texts: List[str]
    target_language: str
    po_file_path: str
    detail_language: Optional[str] = None


@dataclass
class ScanResults:
    """Results from scanning PO files."""
    files_to_process: list = None
    total_entries: int = 0
    total_entries_in_all_files: int = 0
    total_translated_in_all_files: int = 0
    skipped_files: list = None
    files_scanned: int = 0
    language_mismatch_files: int = 0

    def __post_init__(self):
        if self.files_to_process is None:
            self.files_to_process = []
        if self.skipped_files is None:
            self.skipped_files = []


@dataclass
class FileStats:
    """Statistics for a single PO file."""
    total_in_file: int = 0
    untranslated: int = 0
    translated_in_file: int = 0


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
        self.po_file_handler = POFileHandler()

    def validate_provider_connection(self) -> bool:
        """Validates the connection to the selected provider by making a minimal test API call."""
        provider = self.config.provider
        try:
            # Make a minimal API call to validate connection
            # Use a very simple prompt that should work with any model
            test_prompt = "Reply with 'ok'"
            response = self._get_provider_response(test_prompt)

            if response:
                logging.info("%s connection validated successfully", provider.value)
                return True

            logging.error("%s connection failed: Empty response", provider.value)
            return False

        except Exception as e:
            logging.error("Failed to validate %s connection: %s", provider.value, str(e))
            return False

    def _translate_chunk(self, chunk_data):
        """Translate a single chunk of texts."""
        chunk, target_language, detail_language, chunk_num, total_chunks = chunk_data
        logging.info("Batch %d/%d: Translating %d entries...", chunk_num, total_chunks, len(chunk))
        try:
            translations = self.perform_translation(
                chunk, target_language, is_bulk=True, detail_language=detail_language
            )
            logging.info("Batch %d/%d: Successfully translated %d entries",
                         chunk_num, total_chunks, len(translations))
            return translations
        except Exception as e:
            logging.error("Batch %d translation failed: %s", chunk_num, str(e))
            logging.info("Retrying entries individually...")
            results = []
            for j, text in enumerate(chunk, 1):
                try:
                    logging.info("  Translating entry %d/%d...", j, len(chunk))
                    translation = self.perform_translation(
                        text, target_language, is_bulk=False, detail_language=detail_language
                    )
                    results.append(translation)
                except Exception as inner_e:
                    logging.error("  Entry translation failed: %s", str(inner_e)[:100])
                    results.append("")  # Placeholder for failed translation
            return results

    def translate_bulk(
            self,
            texts: List[str],
            target_language: str,
            po_file_path: str,
            detail_language: Optional[str] = None) -> List[str]:
        """Translates a list of texts in bulk, processing in smaller chunks."""
        translated_texts = []
        total_chunks = (len(texts) - 1) // self.batch_size + 1

        for i in range(0, len(texts), self.batch_size):
            chunk_num = i // self.batch_size + 1
            chunk_data = (
                texts[i:i + self.batch_size], target_language, detail_language, chunk_num, total_chunks
            )
            translations = self._translate_chunk(chunk_data)
            translated_texts.extend(translations)

            logging.info("Progress: %d/%d entries (%.1f%% complete)",
                         len(translated_texts), len(texts),
                         100.0 * len(translated_texts) / len(texts))

        if len(translated_texts) != len(texts):
            logging.error(
                "Translation count mismatch in %s: Expected %d, got %d",
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
                display_text = text[:50] if len(text) > 50 else text
                logging.warning("Received empty translation for '%s', retrying...", display_text)
                translation = self.perform_translation_without_validation(
                    text, target_language, detail_language=detail_language
                )
            return translation
        except Exception as e:
            logging.error("Translation failed: %s", str(e)[:100])
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
        ), target_language)

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
        logging.debug("Translating to '%s' via %s API", target_language, self.config.provider.value)
        prompt = self.get_translation_prompt(target_language, is_bulk, detail_language)
        content = prompt + (json.dumps(texts) if is_bulk else texts)

        try:
            # Get the response text from the provider
            response_text = self._get_provider_response(content)

            # Process the response according to bulk mode
            if is_bulk:
                return self._process_bulk_response(response_text, texts, target_language)
            return self.validate_translation(texts, response_text, target_language)

        except Exception as e:
            logging.error("Translation error: %s", str(e)[:200])
            raise

    def _get_provider_response(self, content: str) -> str:
        """Get translation response from the selected provider."""
        provider = self.config.provider

        if not provider:
            return ""

        provider_instance = ProviderRegistry.get_provider(provider)
        if not provider_instance:
            return ""
        return provider_instance.translate(self.config.provider_clients, self.config.model, content)

    def _process_bulk_response(self, response_text: str, original_texts: List[str], target_language: str) -> List[str]:
        """Process a bulk translation response."""
        try:
            # Clean the response text for formatting issues
            clean_response = self._clean_json_response(response_text)
            logging.debug("Cleaned JSON response: %s...", clean_response[:100])

            # First attempt: try parsing as-is
            try:
                translated_texts = json.loads(clean_response)
            except json.JSONDecodeError:
                # Second attempt: fix various quote types that break JSON
                # First, normalize all quote types to standard quotes
                # Handle different languages' quotation marks
                quote_fixes = [
                    ('"', '"'),   # Left double quotation mark
                    ('"', '"'),   # Right double quotation mark
                    ('„', '"'),   # Double low-9 quotation mark (Lithuanian, German)
                    ('"', '"'),   # Left double quotation mark (alternative)
                    (''', "'"),   # Left single quotation mark
                    (''', "'"),   # Right single quotation mark
                    ('‚', "'"),   # Single low-9 quotation mark
                    ('«', '"'),   # Left-pointing double angle quotation mark
                    ('»', '"'),   # Right-pointing double angle quotation mark
                    ('‹', "'"),   # Left-pointing single angle quotation mark
                    ('›', "'"),   # Right-pointing single angle quotation mark
                ]

                fixed_response = clean_response
                for old_quote, new_quote in quote_fixes:
                    fixed_response = fixed_response.replace(old_quote, new_quote)

                # Apply fix to all JSON strings (but not the JSON structure quotes)
                try:
                    # More sophisticated regex to handle quotes inside strings
                    fixed_response = re.sub(
                        r'"([^"\\]*(\\.[^"\\]*)*)"',
                        lambda m: f'"{m.group(1).replace(chr(92) + chr(34), chr(34))}"',
                        fixed_response)
                    translated_texts = json.loads(fixed_response)
                except json.JSONDecodeError as e:
                    # Final attempt: try to extract array elements manually
                    # This is a fallback for severely malformed JSON
                    logging.warning("API returned malformed JSON, attempting to extract translations manually")

                    # Try to find array-like structure and extract elements
                    if '[' in fixed_response and ']' in fixed_response:
                        # Extract content between first [ and last ]
                        start_idx = fixed_response.find('[')
                        end_idx = fixed_response.rfind(']') + 1
                        array_content = fixed_response[start_idx:end_idx]

                        # Try to extract quoted strings
                        matches = re.findall(r'"([^"]*(?:\\.[^"]*)*)"', array_content)
                        if matches and len(matches) == len(original_texts):
                            # Unescape the extracted strings
                            translated_texts = [match.replace('\\"', '"').replace("\\'", "'") for match in matches]
                        else:
                            raise ValueError("Could not extract expected number of translations") from e
                    else:
                        raise

            # Validate the format
            if not isinstance(translated_texts, list) or len(translated_texts) != len(original_texts):
                raise ValueError("Invalid response format")

            # Validate each translation
            return [
                self.validate_translation(original, translated, target_language)
                for original, translated in zip(original_texts, translated_texts)
            ]
        except json.JSONDecodeError as e:
            logging.error("Invalid JSON in API response")
            logging.debug("Raw response: %s", response_text[:500])
            raise ValueError("Invalid JSON response") from e

    def _clean_json_response(self, response_text: str) -> str:
        """Clean JSON response, especially for models that return markdown code blocks."""
        # Check if the response is wrapped in markdown code blocks
        if response_text.startswith("```") and "```" in response_text[3:]:
            # Extract content between code blocks
            start_idx = response_text.find("\n", 3) + 1  # Skip the first line with ```json
            end_idx = response_text.rfind("```")
            response_text = response_text[start_idx:end_idx].strip()

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

    def validate_translation(self, original: str, translated: str, target_language: str) -> str:
        """Validates the translation and retries if necessary."""
        translated = translated.strip()

        if len(translated.split()) > 2 * len(original.split()) + 1:
            logging.debug("Translation too verbose (%d words), retrying", len(translated.split()))
            return self.retry_long_translation(original, target_language)

        explanation_indicators = ["I'm sorry", "I cannot", "This refers to", "This means", "In this context"]
        if any(indicator.lower() in translated.lower() for indicator in explanation_indicators):
            logging.debug("Translation contains explanation, retrying")
            return self.retry_long_translation(original, target_language)

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
                logging.debug("Retry still too verbose, skipping")
                return ""  # Return empty string instead of English text

            logging.debug("Retry successful")
            return retried_translation

        except Exception as e:
            logging.debug("Retry failed: %s", str(e)[:100])
            return ""  # Return empty string instead of English text

    def _show_results_summary(self, stats: TranslationStats):
        """Show final results summary after processing."""
        logging.info("")
        logging.info("=" * 70)
        logging.info("TRANSLATION RESULTS")
        logging.info("=" * 70)

        logging.info("PROCESSING SUMMARY:")
        logging.info("  Files processed: %d", stats.files.processed)
        logging.info("  Files skipped (already complete): %d", stats.files.skipped)
        logging.info("  Total files handled: %d", stats.files.processed + stats.files.skipped)

        logging.info("")
        logging.info("TRANSLATION RESULTS:")
        logging.info("  Entries successfully translated: %d", stats.entries.translated)
        if stats.entries.failed > 0:
            logging.info("  Entries failed/skipped: %d", stats.entries.failed)

        success_rate = (
            (stats.entries.translated / stats.entries.attempted * 100)
            if stats.entries.attempted > 0 else 0
        )
        logging.info("  Success rate: %.1f%%", success_rate)

        logging.info("")
        logging.info("OVERALL PROGRESS:")
        total_translated_after = stats.entries.translated_before + stats.entries.translated
        logging.info("  Total entries: %d", stats.entries.total_in_files)
        logging.info("  Translated before: %d", stats.entries.translated_before)
        logging.info("  Translated now: %d", total_translated_after)

        if stats.entries.total_in_files > 0:
            before_percent = (stats.entries.translated_before / stats.entries.total_in_files) * 100
            after_percent = (total_translated_after / stats.entries.total_in_files) * 100
            logging.info("  Completion: %.1f%% → %.1f%% (+%.1f%%)",
                         before_percent, after_percent, after_percent - before_percent)

        if stats.elapsed_time > 0:
            logging.info("")
            logging.info("PERFORMANCE:")
            minutes = stats.elapsed_time / 60
            logging.info("  Time elapsed: %.1f minutes", minutes)
            if stats.entries.translated > 0:
                rate = stats.entries.translated / minutes
                logging.info("  Translation rate: %.1f entries/minute", rate)
                if self.config.flags.bulk_mode:
                    logging.info("  Mode: BULK (batch size: %d)", self.batch_size)
                else:
                    logging.info("  Mode: SINGLE")

        logging.info("=" * 70)

    def _show_performance_warning(self, total_entries: int):
        """Show performance warning for large single-mode translations."""
        estimated_time = total_entries * 1.5 / 60
        bulk_time = (total_entries // 50 + 1) * 4 / 60
        logging.warning("")
        logging.warning("⚠ Performance Alert: Using SINGLE mode for %d translations", total_entries)
        logging.warning("  This will take approximately %.0f minutes", estimated_time)
        logging.warning("  Tip: Use --bulk mode to reduce time to ~%.0f minutes (%.0fx faster)",
                        bulk_time, estimated_time / bulk_time)
        logging.warning("  Example: gpt-po-translator [your-args] --bulk --bulksize 50")
        logging.warning("")

        if total_entries > 100:
            logging.warning("Starting in 10 seconds. Press Ctrl+C to cancel and use --bulk mode instead.")

            # Give user 10 seconds to press Ctrl+C
            try:
                for i in range(10, 0, -1):
                    sys.stdout.write(f"\rStarting in {i} seconds... ")
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write("\n")
                logging.info("Starting translation...")
            except KeyboardInterrupt:
                logging.info("\nCancelled by user. Restart with --bulk mode for better performance.")
                sys.exit(0)

    def _show_mode_info(self, total_entries: int):
        """Show translation mode information."""
        mode_info = "BULK" if self.config.flags.bulk_mode else "SINGLE"
        if self.config.flags.bulk_mode:
            batches = (total_entries + self.batch_size - 1) // self.batch_size
            logging.info("  Mode: %s (batch size: %d)", mode_info, self.batch_size)
            logging.info("  Batches to process: %d", batches)
        else:
            logging.info("  Mode: %s", mode_info)

    def _show_translation_summary(self, scan_results, languages):
        """Show summary of files to translate."""
        logging.info("=" * 70)
        logging.info("TRANSLATION OVERVIEW")
        logging.info("=" * 70)
        logging.info("SCAN RESULTS:")
        logging.info("  Total PO files found: %d", scan_results['files_scanned'])
        files_matched = len(scan_results['files_to_process']) + len(scan_results['skipped_files'])
        logging.info("  Files matching languages: %d", files_matched)
        logging.info("  Files with language mismatch: %d", scan_results['language_mismatch_files'])
        logging.info("")
        logging.info("TRANSLATION STATUS:")
        logging.info("  Files needing translation: %d", len(scan_results['files_to_process']))
        logging.info("  Files already fully translated: %d", len(scan_results['skipped_files']))
        logging.info("")
        logging.info("ENTRY STATISTICS:")
        logging.info("  Total entries in all files: %d", scan_results['total_entries_in_all_files'])
        logging.info("  Already translated entries: %d", scan_results['total_translated_in_all_files'])
        logging.info("  Entries to translate: %d", scan_results['total_entries'])

        if scan_results['total_entries_in_all_files'] > 0:
            completion_percent = (
                (scan_results['total_translated_in_all_files'] / scan_results['total_entries_in_all_files']) * 100
            )
            logging.info("  Overall completion: %.1f%%", completion_percent)

        logging.info("")
        logging.info("TARGET:")
        logging.info("  Language(s): %s", ', '.join(languages))

    def _analyze_po_file(self, po_file):
        """Analyze a single PO file and return statistics."""
        stats = FileStats()
        stats.total_in_file = len([e for e in po_file if e.msgid])
        stats.untranslated = len([e for e in po_file if is_entry_untranslated(e)])
        stats.translated_in_file = stats.total_in_file - stats.untranslated
        return stats

    def _scan_po_files(self, input_folder: str, languages: List[str], gitignore_parser):
        """Scan PO files and collect statistics."""
        results = ScanResults()

        for root, dirs, files in os.walk(input_folder):
            # Filter directories and files using gitignore parser
            dirs[:], files = gitignore_parser.filter_walk_results(root, dirs, files)
            for file in filter(lambda f: f.endswith(".po"), files):
                results.files_scanned += 1
                po_file_path = os.path.join(root, file)
                po_file_result = self._prepare_po_file(po_file_path, languages)

                if po_file_result is not None:
                    po_file, _ = po_file_result
                    stats = self._analyze_po_file(po_file)

                    results.total_entries_in_all_files += stats.total_in_file
                    results.total_translated_in_all_files += stats.translated_in_file

                    if stats.untranslated > 0:
                        results.files_to_process.append((po_file_path, po_file_result, stats.untranslated))
                        results.total_entries += stats.untranslated
                        logging.debug("File %s: %d/%d entries need translation",
                                      po_file_path, stats.untranslated, stats.total_in_file)
                    else:
                        results.skipped_files.append(po_file_path)
                        logging.debug("Skipping fully translated file: %s", po_file_path)
                else:
                    results.language_mismatch_files += 1

        return vars(results)  # Convert to dict for compatibility

    def _track_file_progress(self, po_file_path, initial_count):
        """Track translation progress for a single file."""
        try:
            po_file = polib.pofile(po_file_path)
            remaining = len([e for e in po_file if is_entry_untranslated(e)])
            return initial_count - remaining, remaining
        except Exception:
            return initial_count, 0

    def _process_files(self, files_to_process, languages, detail_languages, scan_results):
        """Process all files that need translation."""
        stats = TranslationStats()
        start_time = None

        for po_file_path, po_file_result, untranslated_count in files_to_process:
            if start_time is None:
                start_time = time.time()

            logging.info("Processing: %s (%d entries)", po_file_path, untranslated_count)
            self.process_po_file(po_file_path, languages, detail_languages, po_file_result)

            # Track progress
            translated, failed = self._track_file_progress(po_file_path, untranslated_count)
            stats.entries.translated += translated
            stats.entries.failed += failed
            stats.files.processed += 1

        # Show final results summary
        if stats.files.processed > 0:
            stats.elapsed_time = time.time() - start_time if start_time else 0
            stats.files.skipped = len(scan_results['skipped_files'])
            stats.entries.attempted = scan_results['total_entries']
            stats.entries.total_in_files = scan_results['total_entries_in_all_files']
            stats.entries.translated_before = scan_results['total_translated_in_all_files']
            self._show_results_summary(stats)

    def scan_and_process_po_files(
            self,
            input_folder: str,
            languages: List[str],
            detail_languages: Optional[Dict[str, str]] = None,
            respect_gitignore: bool = True):
        """Scans and processes .po files in the given input folder."""
        # Create gitignore parser for filtering
        gitignore_parser = create_gitignore_parser(input_folder, respect_gitignore)
        if respect_gitignore:
            logging.debug("Created gitignore parser for %s (gitignore enabled)", input_folder)
        else:
            logging.debug("Created gitignore parser for %s (gitignore disabled)", input_folder)

        # Scan all PO files
        scan_results = self._scan_po_files(input_folder, languages, gitignore_parser)

        files_to_process = scan_results['files_to_process']
        total_entries = scan_results['total_entries']
        skipped_files = scan_results['skipped_files']

        # Check if all files are already translated
        if not files_to_process:
            if skipped_files:
                logging.info("=" * 70)
                logging.info("All %d PO files are already fully translated. Nothing to do!", len(skipped_files))
                logging.info("=" * 70)
            return

        # Show summary and warning if needed
        self._show_translation_summary(scan_results, languages)

        if not self.config.flags.bulk_mode and total_entries > 30:
            self._show_performance_warning(total_entries)
        else:
            self._show_mode_info(total_entries)

        logging.info("=" * 70)

        # Process all files
        self._process_files(files_to_process, languages, detail_languages, scan_results)

    def _warn_large_file(self, file_path: str, entry_count: int):
        """Warn user about large files in single mode."""
        if not self.config.flags.bulk_mode and entry_count > 30:
            estimated_time = entry_count * 1.5 / 60
            logging.warning(
                "Large file alert: %s has %d translations to process",
                os.path.basename(file_path), entry_count
            )
            logging.warning(
                "  Using single mode (~%.1f minutes). Consider --bulk mode for faster processing.",
                estimated_time
            )
            if entry_count > 100:
                logging.warning("  Starting in 5 seconds. Press Ctrl+C to cancel.")
                time.sleep(5)

    def _prepare_translation_request(self, po_file, po_file_path, file_lang, detail_languages):
        """Prepare a translation request from PO file data."""
        entries = [entry for entry in po_file if is_entry_untranslated(entry)]
        texts = [entry.msgid for entry in entries]
        detail_lang = detail_languages.get(file_lang) if detail_languages else None

        return TranslationRequest(
            po_file=po_file,
            entries=entries,
            texts=texts,
            target_language=file_lang,
            po_file_path=po_file_path,
            detail_language=detail_lang
        )

    def process_po_file(
        self,
        po_file_path: str,
        languages: List[str],
        detail_languages: Optional[Dict[str, str]] = None,
        po_file_result=None,
    ):
        """Processes a single .po file with translations."""
        request = None
        po_file = None

        try:
            # Prepare PO file if not provided
            if po_file_result is None:
                po_file_result = self._prepare_po_file(po_file_path, languages)
                if po_file_result is None:
                    return

            po_file, file_lang = po_file_result

            # Handle fuzzy entries if requested
            if self.config.flags.fix_fuzzy:
                detail_lang = detail_languages.get(file_lang) if detail_languages else None
                self.fix_fuzzy_entries(po_file, po_file_path, file_lang, detail_lang)
                return

            # Prepare translation request
            request = self._prepare_translation_request(po_file, po_file_path, file_lang, detail_languages)

            # Warn about large files
            self._warn_large_file(po_file_path, len(request.texts))

            # Process translations
            if self.config.flags.bulk_mode:
                self._process_with_incremental_save_bulk(request)
            else:
                self._process_with_incremental_save_single(request)

            # Final save and logging
            po_file.save(po_file_path)
            self.po_file_handler.log_translation_status(
                po_file_path, request.texts,
                [entry.msgstr for entry in request.entries]
            )
        except KeyboardInterrupt:
            logging.info("\nTranslation interrupted. Saving progress...")
            if po_file is not None:
                po_file.save(po_file_path)
                if request is not None:
                    completed = len([e for e in request.entries if e.msgstr.strip()])
                    logging.info("Progress saved: %d of %d translations completed",
                                 completed, len(request.texts))
            raise
        except Exception as e:
            logging.error("Error processing file %s: %s", po_file_path, e)

    def _process_batch(self, batch_info, po_file, po_file_path, detail_language=None):
        """Process a single batch of translations."""
        batch_texts, batch_entries, current_batch, total_batches, target_language = batch_info
        translated_count = 0

        logging.info("[BULK %d/%d] Translating %d entries...", current_batch, total_batches, len(batch_texts))

        # Get translations for this batch
        translations = self.perform_translation(
            batch_texts, target_language, is_bulk=True, detail_language=detail_language
        )

        # Update entries with translations
        for entry, translation in zip(batch_entries, translations):
            if translation.strip():
                entry.msgstr = translation
                if self.config.flags.mark_ai_generated:
                    add_ai_generated_comment(entry)
                translated_count += 1

        # Save after batch
        po_file.save(po_file_path)
        return translated_count

    def _process_with_incremental_save_bulk(self, request: TranslationRequest):
        """Process translations in bulk mode with incremental saves after each batch."""
        total_entries = len(request.texts)
        translated_count = 0
        total_batches = (total_entries - 1) // self.batch_size + 1

        # Process in batches
        for i in range(0, total_entries, self.batch_size):
            batch_num = i // self.batch_size + 1
            batch_info = (
                request.texts[i:i + self.batch_size],
                request.entries[i:i + self.batch_size],
                batch_num,
                total_batches,
                request.target_language
            )

            try:
                translated_count += self._process_batch(
                    batch_info, request.po_file, request.po_file_path, request.detail_language
                )
                logging.info("Batch %d/%d completed. Saved %d translations (%.1f%% total)",
                             batch_num, total_batches, translated_count,
                             100.0 * translated_count / total_entries)
            except KeyboardInterrupt:
                logging.info("\nInterrupted at batch %d of %d. Saving...", batch_num, total_batches)
                request.po_file.save(request.po_file_path)
                logging.info("Saved: %d of %d translations completed", translated_count, total_entries)
                raise
            except Exception as e:
                logging.error("Error in batch %d: %s", batch_num, str(e))
                # Continue with next batch even if one fails

    def _process_with_incremental_save_single(self, request: TranslationRequest):
        """Process translations in single mode with periodic saves."""
        total_entries = len(request.texts)
        save_interval = max(10, total_entries // 10) if total_entries > 100 else 10

        for i, (text, entry) in enumerate(zip(request.texts, request.entries), 1):
            try:
                logging.info("[SINGLE %d/%d] Translating entry...", i, total_entries)

                translation = self.translate_single(text, request.target_language, request.detail_language)

                if translation.strip():
                    entry.msgstr = translation
                    if self.config.flags.mark_ai_generated:
                        add_ai_generated_comment(entry)

                # Save periodically
                if i % save_interval == 0 or i == total_entries:
                    request.po_file.save(request.po_file_path)
                    logging.info("Progress: %d/%d entries completed (%.1f%%). File saved.",
                                 i, total_entries, 100.0 * i / total_entries)

            except KeyboardInterrupt:
                logging.info("\nInterrupted at entry %d of %d. Saving...", i, total_entries)
                request.po_file.save(request.po_file_path)
                logging.info("Saved: %d of %d translations", i - 1, total_entries)
                raise
            except Exception as e:
                logging.error("Error translating entry %d: %s", i, str(e))
                # Continue with next entry even if one fails

    def _prepare_po_file(self, po_file_path: str, languages: List[str]):
        """Prepares the .po file for translation."""
        if self.config.flags.fuzzy:
            logging.warning(
                "Consider running with '--fix-fuzzy' to clean and update the fuzzy translations properly.",
            )
            self.po_file_handler.disable_fuzzy_translations(po_file_path)
        po_file = polib.pofile(po_file_path)
        file_lang = self.po_file_handler.get_file_language(
            po_file_path,
            po_file,
            languages,
            self.config.flags.folder_language
        )
        if not file_lang:
            logging.debug("Skipping file (language mismatch): %s", po_file_path)
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
        if self.config.flags.bulk_mode:
            return self.translate_bulk(texts, target_language, po_file_path, detail_language)

        # Single mode with progress tracking
        translations = []
        total = len(texts)
        for i, text in enumerate(texts, 1):
            logging.info("[SINGLE %d/%d] Translating entry...", i, total)
            translation = self.translate_single(text, target_language, detail_language)
            translations.append(translation)
            if i % 10 == 0 or i == total:  # Progress update every 10 items or at the end
                logging.info("Progress: %d/%d entries completed (%.1f%%)", i, total, 100.0 * i / total)
        return translations

    def _update_fuzzy_po_entries(
        self,
        po_file,
        translations: List[str],
        entries_to_update: list
    ):
        """Update only fuzzy entries, remove 'fuzzy' flag, and log cleanly."""
        for entry, translation in zip(entries_to_update, translations):
            if translation.strip():
                self.po_file_handler.update_po_entry(
                    po_file, entry.msgid, translation, self.config.flags.mark_ai_generated
                )
                if 'fuzzy' in entry.flags:
                    entry.flags.remove('fuzzy')
                logging.info("Fixed fuzzy entry '%s' -> '%s'", entry.msgid, translation)
            else:
                logging.warning("Could not translate fuzzy entry: %s", entry.msgid[:50])

    def _handle_empty_translation(self, entry, target_language: str, detail_language: Optional[str] = None):
        """Handles cases where the initial translation is empty."""
        logging.warning("Empty translation received, retrying: %s", entry.msgid[:50])
        individual_translation = self.translate_single(entry.msgid, target_language, detail_language)
        if individual_translation.strip():
            self.po_file_handler.update_po_entry(
                entry.po_file, entry.msgid, individual_translation, self.config.flags.mark_ai_generated
            )
            logging.info(
                "Individual translation successful: '%s' to '%s'",
                entry.msgid,
                individual_translation
            )
        else:
            logging.error("Failed to translate '%s' after individual attempt.", entry.msgid)

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
