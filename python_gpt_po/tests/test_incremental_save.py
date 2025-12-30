"""
Tests for incremental save functionality and Ctrl+C handling.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService


class TestIncrementalSave(unittest.TestCase):
    """Test incremental save functionality and interruption handling."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock config
        self.mock_flags = TranslationFlags(
            bulk_mode=False,
            fuzzy=False,
            fix_fuzzy=False,
            folder_language=False,
            mark_ai_generated=True
        )

        self.mock_config = TranslationConfig(
            provider_clients=MagicMock(),
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            flags=self.mock_flags
        )

        # Create translation service
        self.service = TranslationService(self.mock_config, batch_size=10)

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_po_file(self, num_entries=20):
        """Create a test PO file with specified number of untranslated entries."""
        po_file = polib.POFile()
        po_file.metadata = {
            'Language': 'fr',
            'Content-Type': 'text/plain; charset=utf-8',
        }

        for i in range(num_entries):
            entry = polib.POEntry(
                msgid=f"Test string {i+1}",
                msgstr=""  # Empty translation
            )
            po_file.append(entry)

        po_path = os.path.join(self.temp_dir, "test.po")
        po_file.save(po_path)
        return po_path, po_file

    @patch('python_gpt_po.services.translation_service.TranslationService.translate_single')
    def test_single_mode_incremental_save(self, mock_translate):
        """Test that single mode saves periodically."""
        # Create test file with 25 entries
        po_path, po_file = self.create_test_po_file(25)

        # Mock translations
        mock_translate.side_effect = [f"Translation {i+1}" for i in range(25)]

        # Reload the file to simulate fresh read
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Track save calls
        original_save = po_file.save
        save_calls = []

        def track_save(path):
            save_calls.append(len([e for e in po_file if e.msgstr.strip()]))
            original_save(path)

        po_file.save = track_save

        # Process with single mode
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        self.service._process_with_incremental_save_single(request)

        # Should save every 10 entries and at the end (10, 20, 25)
        self.assertEqual(len(save_calls), 3)
        self.assertEqual(save_calls, [10, 20, 25])

        # Verify final file has all translations
        final_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in final_po if e.msgstr.strip()])
        self.assertEqual(translated_count, 25)

    @patch('python_gpt_po.services.translation_service.TranslationService.perform_translation')
    def test_bulk_mode_incremental_save(self, mock_translate):
        """Test that bulk mode saves after each batch."""
        # Set bulk mode
        self.mock_config.flags.bulk_mode = True
        self.service.batch_size = 10

        # Create test file with 35 entries
        po_path, po_file = self.create_test_po_file(35)

        # Mock bulk translations (4 batches: 10, 10, 10, 5)
        mock_translate.side_effect = [
            [f"Translation {i+1}" for i in range(0, 10)],   # Batch 1
            [f"Translation {i+1}" for i in range(10, 20)],  # Batch 2
            [f"Translation {i+1}" for i in range(20, 30)],  # Batch 3
            [f"Translation {i+1}" for i in range(30, 35)],  # Batch 4
        ]

        # Reload the file
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Track save calls
        save_counts = []
        original_save = po_file.save

        def track_save(path):
            save_counts.append(len([e for e in po_file if e.msgstr.strip()]))
            original_save(path)

        po_file.save = track_save

        # Process with bulk mode
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        self.service._process_with_incremental_save_bulk(request)

        # Should save after each batch (10, 20, 30, 35)
        self.assertEqual(len(save_counts), 4)
        self.assertEqual(save_counts, [10, 20, 30, 35])

    @patch('python_gpt_po.services.translation_service.TranslationService.translate_single')
    def test_single_mode_keyboard_interrupt(self, mock_translate):
        """Test that Ctrl+C in single mode saves partial progress."""
        po_path, po_file = self.create_test_po_file(20)

        # Mock translations, but raise KeyboardInterrupt after 7 translations
        translations_done = []

        def translate_with_interrupt(text, lang, detail_language=None, context=None):
            if len(translations_done) >= 7:
                raise KeyboardInterrupt("User pressed Ctrl+C")
            result = f"Translation {len(translations_done) + 1}"
            translations_done.append(result)
            return result

        mock_translate.side_effect = translate_with_interrupt

        # Reload file
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Process and expect KeyboardInterrupt
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        with self.assertRaises(KeyboardInterrupt):
            self.service._process_with_incremental_save_single(request)

        # Check that file was saved with partial translations
        # (Should have saved at least the first batch before interrupt)
        saved_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in saved_po if e.msgstr.strip()])

        # Should have at least some translations saved
        self.assertGreater(translated_count, 0)
        self.assertLess(translated_count, 20)

    @patch('python_gpt_po.services.translation_service.TranslationService.perform_translation')
    def test_bulk_mode_keyboard_interrupt(self, mock_translate):
        """Test that Ctrl+C in bulk mode saves completed batches."""
        self.mock_config.flags.bulk_mode = True
        self.service.batch_size = 10

        po_path, po_file = self.create_test_po_file(30)

        # Mock translations - interrupt during batch 2 (after batch 1 completes)
        def translate_with_interrupt(texts, lang, is_bulk=False, detail_language=None, context=None):
            if mock_translate.call_count == 1:
                # First batch completes successfully
                return [f"Translation {i+1}" for i in range(1, 11)]
            elif mock_translate.call_count == 2:
                # Second batch is interrupted
                raise KeyboardInterrupt("User pressed Ctrl+C")
            return [f"Translation {i+1}" for i in range(len(texts))]

        mock_translate.side_effect = translate_with_interrupt

        # Reload file
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Process and expect KeyboardInterrupt
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        with self.assertRaises(KeyboardInterrupt):
            self.service._process_with_incremental_save_bulk(request)

        # Check that completed batches were saved
        saved_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in saved_po if e.msgstr.strip()])

        # Should have saved 1 complete batch (10 translations)
        self.assertEqual(translated_count, 10)

    @patch('python_gpt_po.services.translation_service.TranslationService._get_provider_response')
    def test_process_po_file_with_interrupt(self, mock_response):
        """Test the main process_po_file method handles interrupts correctly."""
        po_path, _ = self.create_test_po_file(15)

        # Mock provider to interrupt after a few calls
        call_count = [0]

        def response_with_interrupt(content):
            call_count[0] += 1
            if call_count[0] > 5:
                raise KeyboardInterrupt("User pressed Ctrl+C")
            return "Translated text"

        mock_response.side_effect = response_with_interrupt

        # Process file and expect graceful handling
        with self.assertRaises(KeyboardInterrupt):
            self.service.process_po_file(po_path, ["fr"], None)

        # Verify file was saved with partial translations
        saved_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in saved_po if e.msgstr.strip()])

        # Should have some translations but not all
        self.assertGreater(translated_count, 0)
        self.assertLess(translated_count, 15)

    @patch('python_gpt_po.services.translation_service.TranslationService.translate_single')
    def test_continue_on_error_single_mode(self, mock_translate):
        """Test that single mode continues translating even if one fails."""
        po_path, po_file = self.create_test_po_file(10)

        # Mock translations with one failure
        def translate_with_error(text, lang, detail_language=None, context=None):
            if "string 5" in text:
                raise Exception("API error for string 5")
            return f"Translation for {text}"

        mock_translate.side_effect = translate_with_error

        # Reload file
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Process - should continue despite error
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        self.service._process_with_incremental_save_single(request)

        # Should have 9 translations (all except the failed one)
        saved_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in saved_po if e.msgstr.strip()])
        self.assertEqual(translated_count, 9)

        # The failed entry should remain untranslated
        failed_entry = [e for e in saved_po if "string 5" in e.msgid][0]
        self.assertEqual(failed_entry.msgstr, "")

    @patch('python_gpt_po.services.translation_service.TranslationService.perform_translation')
    def test_continue_on_error_bulk_mode(self, mock_translate):
        """Test that bulk mode continues with next batch even if one fails."""
        self.mock_config.flags.bulk_mode = True
        self.service.batch_size = 5

        po_path, po_file = self.create_test_po_file(15)

        # Mock translations with batch 2 failing
        def translate_with_error(texts, lang, is_bulk=False, detail_language=None, context=None):
            if mock_translate.call_count == 2:
                raise Exception("API error for batch 2")
            return [f"Translation {i+1}" for i in range(len(texts))]

        mock_translate.side_effect = translate_with_error

        # Reload file
        po_file = POFileHandler.load_po_file(po_path)
        texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr.strip()]

        # Process - should continue despite batch 2 error
        entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
        from python_gpt_po.services.translation_service import TranslationRequest
        request = TranslationRequest(
            po_file=po_file,
            entries=entries_to_translate,
            texts=texts_to_translate,
            target_language="fr",
            po_file_path=po_path,
            detail_language=None
        )
        self.service._process_with_incremental_save_bulk(request)

        # Should have 10 translations (batch 1 and 3, but not batch 2)
        saved_po = POFileHandler.load_po_file(po_path)
        translated_count = len([e for e in saved_po if e.msgstr.strip()])
        self.assertEqual(translated_count, 10)


if __name__ == '__main__':
    unittest.main()
