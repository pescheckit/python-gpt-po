"""
Test that fully translated files are skipped properly.
"""
import os
import tempfile
import unittest
from unittest.mock import patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.translation_service import TranslationService


class TestSkipTranslatedFiles(unittest.TestCase):
    """Test that fully translated files are properly skipped."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-3.5-turbo",
            flags=TranslationFlags(bulk_mode=True, folder_language=False)
        )
        self.service = TranslationService(self.config, batch_size=10)

    def test_skip_fully_translated_file(self):
        """Test that files with all entries translated are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fully translated PO file
            po_file_path = os.path.join(tmpdir, "fully_translated.po")
            po_file = polib.POFile()
            po_file.metadata = {'Language': 'fr'}

            # Add some fully translated entries
            entry1 = polib.POEntry(
                msgid="Hello",
                msgstr="Bonjour"
            )
            entry2 = polib.POEntry(
                msgid="World",
                msgstr="Monde"
            )
            po_file.append(entry1)
            po_file.append(entry2)
            po_file.save(po_file_path)

            # Mock the provider response (shouldn't be called)
            with patch.object(self.service, '_get_provider_response') as mock_response:
                with patch('logging.info') as mock_log_info:
                    with patch('logging.debug') as mock_log_debug:
                        # Process the folder
                        self.service.scan_and_process_po_files(tmpdir, ['fr'])

                        # Should not have called the API
                        mock_response.assert_not_called()

                        # Check that appropriate log messages were generated
                        info_messages = [str(call[0][0]) for call in mock_log_info.call_args_list]
                        debug_messages = [str(call[0][0]) for call in mock_log_debug.call_args_list]

                        # Should log that file is being skipped (at debug level)
                        self.assertTrue(any("Skipping fully translated file:" in msg for msg in debug_messages))
                        # Should indicate all files are translated (at info level)
                        self.assertTrue(any("All" in msg and "fully translated" in msg for msg in info_messages))

    def test_process_partially_translated_file(self):
        """Test that files with some untranslated entries are processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a partially translated PO file
            po_file_path = os.path.join(tmpdir, "partial.po")
            po_file = polib.POFile()
            po_file.metadata = {'Language': 'fr'}

            # Add translated and untranslated entries
            entry1 = polib.POEntry(
                msgid="Hello",
                msgstr="Bonjour"
            )
            entry2 = polib.POEntry(
                msgid="World",
                msgstr=""  # Empty translation
            )
            entry3 = polib.POEntry(
                msgid="Test",
                msgstr=""  # Empty translation
            )
            po_file.append(entry1)
            po_file.append(entry2)
            po_file.append(entry3)
            po_file.save(po_file_path)

            with patch.object(self.service, '_get_provider_response') as mock_response:
                mock_response.return_value = '["Monde", "Test"]'

                with patch('logging.info') as mock_log_info:
                    # Process the folder
                    self.service.scan_and_process_po_files(tmpdir, ['fr'])

                    # Should have called the API for untranslated entries
                    mock_response.assert_called()

                    # Check log messages
                    log_messages = [str(call[0][0]) for call in mock_log_info.call_args_list]

                    # Should show processing the file (checking for format string)
                    self.assertTrue(any("Processing:" in msg for msg in log_messages))

    def test_mixed_translated_and_untranslated_files(self):
        """Test scanning folder with both fully translated and untranslated files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fully translated file
            po_file1_path = os.path.join(tmpdir, "full.po")
            po_file1 = polib.POFile()
            po_file1.metadata = {'Language': 'fr'}
            po_file1.append(polib.POEntry(msgid="Hello", msgstr="Bonjour"))
            po_file1.save(po_file1_path)

            # Create a file needing translation
            po_file2_path = os.path.join(tmpdir, "partial.po")
            po_file2 = polib.POFile()
            po_file2.metadata = {'Language': 'fr'}
            po_file2.append(polib.POEntry(msgid="World", msgstr=""))
            po_file2.save(po_file2_path)

            with patch.object(self.service, '_get_provider_response') as mock_response:
                mock_response.return_value = '["Monde"]'

                with patch('logging.info') as mock_log_info:
                    with patch('logging.debug') as mock_log_debug:
                        # Process the folder
                        self.service.scan_and_process_po_files(tmpdir, ['fr'])

                        # Check log messages
                        info_messages = [str(call[0][0]) for call in mock_log_info.call_args_list]
                        debug_messages = [str(call[0][0]) for call in mock_log_debug.call_args_list]

                        # Should show summary with both counts (checking format strings)
                        self.assertTrue(any("Files needing translation:" in msg for msg in info_messages))
                        self.assertTrue(any("Files already fully translated:" in msg for msg in info_messages))

                        # Should skip the fully translated file (at debug level)
                        self.assertTrue(any("Skipping fully translated file:" in msg for msg in debug_messages))

                        # Should process the partial file
                        self.assertTrue(any("Processing:" in msg for msg in info_messages))


if __name__ == '__main__':
    unittest.main()
