"""
Tests for whitespace preservation in translations.
"""
import unittest
from unittest.mock import patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.translation_service import TranslationService


class TestWhitespacePreservation(unittest.TestCase):
    """Test whitespace preservation during translation."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        flags = TranslationFlags(
            bulk_mode=False,
            fuzzy=False,
            folder_language=False,
            fix_fuzzy=False,
            mark_ai_generated=False
        )
        self.config = TranslationConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            flags=flags,
            provider_clients=None
        )
        self.service = TranslationService(self.config)

    def test_validate_translation_preserves_leading_whitespace(self):
        """Test that leading whitespace is preserved."""
        original = "   Hello"
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "   Bonjour")

    def test_validate_translation_preserves_trailing_whitespace(self):
        """Test that trailing whitespace is preserved."""
        original = "Hello   "
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "Bonjour   ")

    def test_validate_translation_preserves_both_whitespace(self):
        """Test that both leading and trailing whitespace are preserved."""
        original = "  Hello  "
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "  Bonjour  ")

    def test_validate_translation_preserves_single_space(self):
        """Test that single space whitespace is preserved."""
        original = " Incorrect"
        translated = "Incorreto"
        result = self.service.validate_translation(original, translated, "pt")
        self.assertEqual(result, " Incorreto")

    def test_validate_translation_no_whitespace(self):
        """Test normal case without whitespace."""
        original = "Hello"
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "Bonjour")

    def test_validate_translation_newlines_preserved(self):
        """Test that newlines are preserved."""
        original = "\nHello\n"
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "\nBonjour\n")

    def test_validate_translation_tabs_preserved(self):
        """Test that tabs are preserved."""
        original = "\tHello\t"
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "\tBonjour\t")

    def test_validate_translation_mixed_whitespace(self):
        """Test that mixed whitespace types are preserved."""
        original = " \t\nHello \n\t "
        translated = "Bonjour"
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, " \t\nBonjour \n\t ")

    @patch.object(TranslationService, '_get_provider_response')
    def test_retry_long_translation_preserves_whitespace(self, mock_provider):
        """Test that retry_long_translation preserves whitespace."""
        mock_provider.return_value = "Bonjour"

        original = "  Hello  "
        result = self.service.retry_long_translation(original, "fr")

        self.assertEqual(result, "  Bonjour  ")
        # Verify that the text sent to the provider is stripped
        call_args = mock_provider.call_args[0][0]
        self.assertIn("Hello", call_args)
        self.assertNotIn("  Hello  ", call_args)

    @patch.object(TranslationService, 'perform_translation')
    def test_perform_translation_without_validation_preserves_whitespace(self, mock_translate):
        """Test that perform_translation_without_validation preserves whitespace."""
        mock_translate.return_value = "Bonjour"

        original = " Hello "
        result = self.service.perform_translation_without_validation(original, "fr")

        self.assertEqual(result, " Bonjour ")

    @patch.object(TranslationService, '_get_provider_response')
    def test_end_to_end_whitespace_preservation(self, mock_provider):
        """Test end-to-end whitespace preservation in translation."""
        # Mock the provider response
        mock_provider.return_value = "Bonjour"

        # Create a test PO file
        po_file = polib.POFile()
        po_file.metadata = {'Language': 'fr'}

        # Add entries with various whitespace patterns
        entries = [
            polib.POEntry(msgid=" Leading", msgstr=""),
            polib.POEntry(msgid="Trailing ", msgstr=""),
            polib.POEntry(msgid="  Both  ", msgstr=""),
            polib.POEntry(msgid="NoSpace", msgstr=""),
        ]
        for entry in entries:
            po_file.append(entry)

        # Translate single entry
        result = self.service.translate_single(" Leading", "fr")
        self.assertEqual(result, " Bonjour")

    def test_whitespace_only_string(self):
        """Test handling of whitespace-only strings."""
        original = "   "
        translated = ""
        result = self.service.validate_translation(original, translated, "fr")
        # Whitespace-only strings should be preserved as-is
        self.assertEqual(result, "   ")

    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        original = ""
        translated = ""
        result = self.service.validate_translation(original, translated, "fr")
        self.assertEqual(result, "")

    @patch.object(TranslationService, '_get_provider_response')
    def test_bulk_mode_strips_before_ai_call(self, mock_provider):
        """Test that bulk mode strips whitespace before sending to AI."""
        import json
        mock_provider.return_value = json.dumps(["Bonjour", "Monde"])

        # Set service to bulk mode
        self.service.config.flags.bulk_mode = True

        texts_with_whitespace = [" Hello", "World "]
        result = self.service.perform_translation(
            texts_with_whitespace, "fr", is_bulk=True
        )

        # Verify that the AI received stripped texts
        call_args = mock_provider.call_args[0][0]
        self.assertIn('"Hello"', call_args)  # AI should see "Hello" not " Hello"
        self.assertNotIn('" Hello"', call_args)

        # But the result should have original whitespace
        self.assertEqual(result[0], " Bonjour")
        self.assertEqual(result[1], "Monde ")


if __name__ == '__main__':
    unittest.main()
