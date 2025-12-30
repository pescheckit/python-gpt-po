"""
Tests for default context support in translations.
"""
import tempfile
from pathlib import Path
from unittest.mock import patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService


class TestDefaultContext:
    """Test default context functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            flags=TranslationFlags(bulk_mode=True, folder_language=False),
            default_context="web application"
        )
        self.service = TranslationService(self.config)

    def test_default_context_applied_when_no_msgctxt(self):
        """Test that default context is applied to entries without msgctxt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file without msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'fr',
            }

            # Entry without context
            entry = polib.POEntry(
                msgid='Save',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = self.service._prepare_translation_request(
                po_loaded, str(po_file_path), 'fr', {}
            )

            # Verify default context was applied
            assert len(request.contexts) == 1
            assert request.contexts[0] == "web application"

    def test_msgctxt_overrides_default_context(self):
        """Test that msgctxt takes precedence over default context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file with msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'fr',
            }

            # Entry with explicit context
            entry = polib.POEntry(
                msgctxt='button',
                msgid='Save',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = self.service._prepare_translation_request(
                po_loaded, str(po_file_path), 'fr', {}
            )

            # Verify msgctxt was used, not default context
            assert len(request.contexts) == 1
            assert request.contexts[0] == 'button'

    def test_mixed_contexts_with_default(self):
        """Test that entries with and without msgctxt are handled correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file with mixed contexts
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'de',
            }

            # Entry with explicit context
            entry1 = polib.POEntry(
                msgctxt='button',
                msgid='Save',
                msgstr=''
            )
            po.append(entry1)

            # Entry without context (should get default)
            entry2 = polib.POEntry(
                msgid='Hello',
                msgstr=''
            )
            po.append(entry2)

            # Another entry with explicit context
            entry3 = polib.POEntry(
                msgctxt='menu item',
                msgid='Delete',
                msgstr=''
            )
            po.append(entry3)

            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = self.service._prepare_translation_request(
                po_loaded, str(po_file_path), 'de', {}
            )

            # Verify contexts
            assert len(request.contexts) == 3
            assert request.contexts[0] == 'button'
            assert request.contexts[1] == 'web application'  # Default applied here
            assert request.contexts[2] == 'menu item'

    def test_no_default_context_configured(self):
        """Test behavior when no default context is configured."""
        # Create config without default context
        config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            flags=TranslationFlags(bulk_mode=True, folder_language=False),
            default_context=None
        )
        service = TranslationService(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file without msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'es',
            }

            entry = polib.POEntry(
                msgid='Hello',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = service._prepare_translation_request(
                po_loaded, str(po_file_path), 'es', {}
            )

            # Verify context is None (not default applied)
            assert len(request.contexts) == 1
            assert request.contexts[0] is None

    def test_default_context_passed_to_translation(self):
        """Test that default context is passed through to translation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file without msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'fr',
            }

            entry = polib.POEntry(
                msgid='Submit',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Mock the translation
            with patch.object(self.service, 'perform_translation', return_value=['Soumettre']) as mock_translate:
                self.service.process_po_file(str(po_file_path), ['fr'])

                # Verify default context was used in translation call
                assert mock_translate.called
                call_args = mock_translate.call_args
                assert call_args[1].get('context') == 'web application'

            # Verify translation was saved
            po_result = POFileHandler.load_po_file(str(po_file_path))
            assert po_result[0].msgstr == 'Soumettre'

    def test_empty_string_default_context(self):
        """Test that empty string default context is treated as None."""
        config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            flags=TranslationFlags(bulk_mode=True, folder_language=False),
            default_context=""
        )
        service = TranslationService(config)

        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'nl',
            }

            entry = polib.POEntry(
                msgid='Welcome',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = service._prepare_translation_request(
                po_loaded, str(po_file_path), 'nl', {}
            )

            # Empty string should not be applied
            assert len(request.contexts) == 1
            assert request.contexts[0] is None or request.contexts[0] == ""

    def test_default_context_in_bulk_mode(self):
        """Test that default context works correctly in bulk mode."""
        with patch.object(self.service, 'perform_translation', return_value=['Enregistrer', 'Annuler']) as mock_translate:
            translations = self.service.translate_bulk(
                ['Save', 'Cancel'],
                'fr',
                'test.po',
                contexts=[None, None]  # No explicit contexts
            )

            # Should use default context if most entries don't have context
            assert mock_translate.called
            # When all contexts are None, it should not pass context
            # (or pass the most common one which is None)
            assert len(translations) == 2
