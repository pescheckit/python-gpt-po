"""
Test for handling duplicate msgid entries with different contexts.
This ensures that entries with the same msgid but different contexts
(different line numbers, different source files) are handled correctly.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from python_gpt_po.models.config import TranslationConfig
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService


class TestDuplicateMsgidHandling(unittest.TestCase):
    """Test that duplicate msgid entries with different contexts are handled correctly."""

    def setUp(self):
        """Set up test environment."""
        self.config = TranslationConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-3.5-turbo",
            provider_clients={"openai": MagicMock()},
            flags=MagicMock(bulk_mode=False, mark_ai_generated=True, fuzzy=False,
                            fix_fuzzy=False, folder_language=False)
        )
        self.service = TranslationService(self.config)

    def test_duplicate_msgid_different_contexts_single_mode(self):
        """Test that entries with same msgid but different contexts are tracked correctly in single mode."""
        # Create a PO file with duplicate msgid entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """msgid ""
msgstr ""
"Language: fr\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

#: front-page.php:92
msgid "Latest News"
msgstr ""

#: sidebar.php:45
msgid "Latest News"
msgstr ""

#: footer.php:12
msgid "Contact Us"
msgstr ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            # Load the PO file
            po_file = POFileHandler.load_po_file(po_file_path)

            # Verify we have duplicate msgid entries
            latest_news_entries = [e for e in po_file if e.msgid == "Latest News"]
            self.assertEqual(len(latest_news_entries), 2, "Should have 2 'Latest News' entries")

            # Mock the translation responses
            with patch.object(self.service, '_get_provider_response') as mock_translate:
                mock_translate.side_effect = ["Dernières nouvelles", "Dernières nouvelles", "Contactez-nous"]

                # Process the file
                self.service.process_po_file(po_file_path, ["fr"], {"fr": "French"})

            # Reload and verify both "Latest News" entries were translated
            po_file = POFileHandler.load_po_file(po_file_path)
            latest_news_entries = [e for e in po_file if e.msgid == "Latest News"]

            # Both entries should be translated
            for entry in latest_news_entries:
                self.assertEqual(entry.msgstr, "Dernières nouvelles",
                                 f"Entry from {entry.occurrences} should be translated")

            # Verify the Contact Us entry was also translated
            contact_entry = po_file.find("Contact Us")
            self.assertEqual(contact_entry.msgstr, "Contactez-nous")

        finally:
            os.unlink(po_file_path)

    def test_duplicate_msgid_different_contexts_bulk_mode(self):
        """Test that entries with same msgid but different contexts are tracked correctly in bulk mode."""
        # Switch to bulk mode
        self.config.flags.bulk_mode = True

        # Create a PO file with duplicate msgid entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """msgid ""
msgstr ""
"Language: fr\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

#: header.php:10
msgid "Home"
msgstr ""

#: menu.php:20
msgid "Home"
msgstr ""

#: nav.php:30
msgid "Home"
msgstr ""

#: footer.php:40
msgid "About"
msgstr ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            # Load the PO file
            po_file = POFileHandler.load_po_file(po_file_path)

            # Verify we have duplicate msgid entries
            home_entries = [e for e in po_file if e.msgid == "Home"]
            self.assertEqual(len(home_entries), 3, "Should have 3 'Home' entries")

            # Mock the translation responses for bulk mode
            with patch.object(self.service, '_get_provider_response') as mock_translate:
                # Bulk mode will send all texts at once
                mock_translate.return_value = '["Accueil", "Accueil", "Accueil", "À propos"]'

                # Process the file
                self.service.process_po_file(po_file_path, ["fr"], {"fr": "French"})

            # Reload and verify all "Home" entries were translated
            po_file = POFileHandler.load_po_file(po_file_path)
            home_entries = [e for e in po_file if e.msgid == "Home"]

            # All three entries should be translated
            for entry in home_entries:
                self.assertEqual(entry.msgstr, "Accueil",
                                 f"Entry from {entry.occurrences} should be translated")

            # Verify the About entry was also translated
            about_entry = po_file.find("About")
            self.assertEqual(about_entry.msgstr, "À propos")

        finally:
            os.unlink(po_file_path)

    def test_partial_interrupt_with_duplicate_msgid(self):
        """Test that interrupt handling correctly counts completed translations with duplicate msgids."""
        # Create a PO file with duplicate msgid entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """msgid ""
msgstr ""
"Language: fr\\n"
"Content-Type: text/plain; charset=UTF-8\\n"

#: page1.php:10
msgid "Save"
msgstr ""

#: page2.php:20
msgid "Save"
msgstr ""

#: page3.php:30
msgid "Cancel"
msgstr ""

#: page4.php:40
msgid "Delete"
msgstr ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            # Load the PO file
            po_file = POFileHandler.load_po_file(po_file_path)

            # Mock translations - simulate interrupt after first "Save" translation
            translation_count = 0

            def side_effect_interrupt(*args):
                nonlocal translation_count
                translation_count += 1
                if translation_count == 1:
                    return "Enregistrer"  # First "Save"
                elif translation_count == 2:
                    # Simulate interrupt before second "Save"
                    raise KeyboardInterrupt()

            with patch.object(self.service, '_get_provider_response') as mock_translate:
                mock_translate.side_effect = side_effect_interrupt

                # Process the file - should be interrupted
                with self.assertRaises(KeyboardInterrupt):
                    self.service.process_po_file(po_file_path, ["fr"], {"fr": "French"})

            # Reload and verify only the first entry was translated
            po_file = POFileHandler.load_po_file(po_file_path)
            save_entries = [e for e in po_file if e.msgid == "Save"]

            # Only the first Save should be translated
            translated_saves = [e for e in save_entries if e.msgstr.strip()]
            self.assertEqual(len(translated_saves), 1, "Only one 'Save' entry should be translated")
            self.assertEqual(translated_saves[0].msgstr, "Enregistrer")

            # Other entries should remain untranslated
            cancel_entry = po_file.find("Cancel")
            self.assertEqual(cancel_entry.msgstr, "", "Cancel should not be translated")

            delete_entry = po_file.find("Delete")
            self.assertEqual(delete_entry.msgstr, "", "Delete should not be translated")

        finally:
            os.unlink(po_file_path)

    def test_entries_to_translate_tracking(self):
        """Test that entries_to_translate list properly tracks specific entry objects."""
        # Create a PO file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """msgid ""
msgstr ""
"Language: fr\\n"

#: test.php:1
msgid "Test"
msgstr ""

#: test.php:2
msgid "Test"
msgstr ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = POFileHandler.load_po_file(po_file_path)

            # Get entries to translate
            entries_to_translate = [entry for entry in po_file if not entry.msgstr.strip() and entry.msgid]
            texts_to_translate = [entry.msgid for entry in entries_to_translate]

            # Verify we're tracking specific entry objects
            self.assertEqual(len(entries_to_translate), 2)
            self.assertEqual(len(texts_to_translate), 2)

            # Both should have same msgid
            self.assertEqual(texts_to_translate[0], "Test")
            self.assertEqual(texts_to_translate[1], "Test")

            # But they should be different entry objects
            self.assertIsNot(entries_to_translate[0], entries_to_translate[1])

            # Simulate translation of first entry only
            entries_to_translate[0].msgstr = "Translated"

            # Count completed - should be 1, not 2
            completed = len([e for e in entries_to_translate if e.msgstr.strip()])
            self.assertEqual(completed, 1, "Should count only the specific entry that was translated")

        finally:
            os.unlink(po_file_path)


if __name__ == "__main__":
    unittest.main()
