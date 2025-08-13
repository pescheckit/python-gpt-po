"""
Test to ensure English text is not used as fallback when translation fails.
"""
import unittest
from unittest.mock import patch

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.translation_service import TranslationService


class TestEnglishFallback(unittest.TestCase):
    """Test that failed translations don't fall back to English text."""

    def setUp(self):
        """Set up test fixtures."""
        from python_gpt_po.models.provider_clients import ProviderClients

        self.config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-3.5-turbo",
            flags=TranslationFlags(bulk_mode=False)
        )
        self.service = TranslationService(self.config)

    def test_retry_long_translation_returns_empty_on_too_long(self):
        """Test that retry_long_translation returns empty string when translation is still too long."""
        with patch.object(self.service, '_get_provider_response') as mock_response:
            # Simulate a response that's too long (like an explanation)
            mock_response.return_value = (
                "I apologize, but I don't have a translation system. "
                "This text means 'Homepage Banner updated' in English and it refers to "
                "a notification message that appears when the homepage banner has been modified."
            )

            result = self.service.retry_long_translation("Homepage Banner updated", "fr")

            # Should return empty string, not the English text
            self.assertEqual(result, "")

    def test_retry_long_translation_returns_empty_on_error(self):
        """Test that retry_long_translation returns empty string when an error occurs."""
        with patch.object(self.service, '_get_provider_response') as mock_response:
            # Simulate an error
            mock_response.side_effect = Exception("API error")

            result = self.service.retry_long_translation("Test text", "fr")

            # Should return empty string, not the English text
            self.assertEqual(result, "")

    def test_retry_long_translation_returns_translation_when_valid(self):
        """Test that retry_long_translation returns the translation when it's valid."""
        with patch.object(self.service, '_get_provider_response') as mock_response:
            # Simulate a valid short translation
            mock_response.return_value = "Bannière d'accueil mise à jour"

            result = self.service.retry_long_translation("Homepage Banner updated", "fr")

            # Should return the French translation
            self.assertEqual(result, "Bannière d'accueil mise à jour")

    def test_validate_translation_with_explanation_triggers_retry(self):
        """Test that translations containing explanations trigger retry."""
        with patch.object(self.service, 'retry_long_translation') as mock_retry:
            mock_retry.return_value = ""  # Simulate retry returning empty

            # Test with an explanation-like response
            result = self.service.validate_translation(
                "Test",
                "I'm sorry, but I cannot translate this text",
                "fr"  # target language
            )

            # Should have called retry_long_translation
            mock_retry.assert_called_once()
            self.assertEqual(result, "")

    def test_translate_single_returns_empty_on_failure(self):
        """Test that translate_single returns empty string on complete failure."""
        with patch.object(self.service, 'perform_translation') as mock_translate:
            with patch.object(self.service, 'perform_translation_without_validation') as mock_fallback:
                # First attempt returns empty
                mock_translate.return_value = ""
                # Fallback also returns empty
                mock_fallback.return_value = ""

                result = self.service.translate_single("Test text", "fr")

                # Should return empty string, not English text
                self.assertEqual(result, "")


if __name__ == '__main__':
    unittest.main()
