"""
Tests for msgctxt (message context) support in translations.
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


class TestMsgctxtSupport:
    """Test msgctxt context passing to AI translations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TranslationConfig(
            provider_clients=ProviderClients(),
            provider=ModelProvider.OPENAI,
            model="gpt-4o-mini",
            flags=TranslationFlags(bulk_mode=True, folder_language=False)
        )
        self.service = TranslationService(self.config)

    def test_msgctxt_extracted_from_po_entries(self):
        """Test that msgctxt is extracted from PO entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file with msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'fr',
            }

            # Entry with context
            entry1 = polib.POEntry(
                msgctxt='button',
                msgid='Save',
                msgstr=''
            )
            po.append(entry1)

            # Entry without context
            entry2 = polib.POEntry(
                msgid='Hello',
                msgstr=''
            )
            po.append(entry2)

            # Entry with different context
            entry3 = polib.POEntry(
                msgctxt='menu item',
                msgid='Save',
                msgstr=''
            )
            po.append(entry3)

            po.save(str(po_file_path))

            # Load and prepare translation request
            po_loaded = POFileHandler.load_po_file(str(po_file_path))
            request = self.service._prepare_translation_request(
                po_loaded, str(po_file_path), 'fr', {}
            )

            # Verify contexts were extracted
            assert len(request.contexts) == 3
            assert request.contexts[0] == 'button'
            assert request.contexts[1] is None
            assert request.contexts[2] == 'menu item'

    def test_msgctxt_passed_to_prompt_single_mode(self):
        """Test that msgctxt is included in translation prompt for single mode."""
        with patch.object(self.service, 'perform_translation', return_value='Enregistrer') as mock_translate:
            translation = self.service.translate_single(
                'Save',
                'fr',
                detail_language='French',
                context='button'
            )

            # Verify perform_translation was called with context
            assert mock_translate.called
            call_args = mock_translate.call_args
            assert call_args[1]['context'] == 'button'
            assert translation == 'Enregistrer'

    def test_msgctxt_passed_to_prompt_bulk_mode(self):
        """Test that msgctxt is included in translation prompt for bulk mode."""
        with patch.object(self.service, 'perform_translation', return_value=['Enregistrer', 'Annuler']) as mock_translate:
            translations = self.service.translate_bulk(
                ['Save', 'Cancel'],
                'fr',
                'test.po',
                detail_language='French',
                contexts=['button', 'button']
            )

            # Verify perform_translation was called with context
            assert mock_translate.called
            call_args = mock_translate.call_args
            assert call_args[1]['context'] == 'button'
            assert translations == ['Enregistrer', 'Annuler']

    def test_prompt_includes_context_information(self):
        """Test that the generated prompt includes context information."""
        # Without context
        prompt_no_context = TranslationService.get_translation_prompt(
            'fr', is_bulk=False, detail_language='French', context=None
        )
        assert 'IMPORTANT CONTEXT' not in prompt_no_context

        # With context
        prompt_with_context = TranslationService.get_translation_prompt(
            'fr', is_bulk=False, detail_language='French', context='button'
        )
        assert 'CONTEXT: button' in prompt_with_context
        assert 'Choose the translation that matches this specific context' in prompt_with_context

    def test_bulk_mode_with_mixed_contexts(self):
        """Test bulk mode handles entries with different contexts."""
        with patch.object(self.service, 'perform_translation', return_value=['Enregistrer', 'Sauvegarder', 'OK']) as mock_translate:
            translations = self.service.translate_bulk(
                ['Save', 'Save', 'OK'],
                'fr',
                'test.po',
                contexts=['button', 'menu item', None]
            )

            # Should use most common context ('button' appears once, 'menu item' once, None once)
            # In this case it would pick 'button' or 'menu item' depending on Counter
            assert mock_translate.called
            assert len(translations) == 3

    def test_end_to_end_msgctxt_translation(self):
        """Test full translation flow with msgctxt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

            # Create PO file with msgctxt
            po = polib.POFile()
            po.metadata = {
                'Content-Type': 'text/plain; charset=UTF-8',
                'Language': 'de',
            }

            entry = polib.POEntry(
                msgctxt='button',
                msgid='Delete',
                msgstr=''
            )
            po.append(entry)
            po.save(str(po_file_path))

            # Mock the translation (return list for bulk mode)
            with patch.object(self.service, 'perform_translation', return_value=['Löschen']) as mock_translate:
                self.service.process_po_file(str(po_file_path), ['de'])

                # Verify context was used
                assert mock_translate.called
                call_args = mock_translate.call_args
                assert call_args[1].get('context') == 'button'

            # Verify translation was saved
            po_result = POFileHandler.load_po_file(str(po_file_path))
            assert po_result[0].msgstr == 'Löschen'
            assert po_result[0].msgctxt == 'button'  # Context preserved

    def test_msgctxt_with_no_context_entries(self):
        """Test that entries without msgctxt still work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            po_file_path = Path(tmpdir) / "test.po"

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

            # Mock translation (return list for bulk mode)
            with patch.object(self.service, 'perform_translation', return_value=['Hola']) as mock_translate:
                self.service.process_po_file(str(po_file_path), ['es'])

                # Verify context was None
                assert mock_translate.called
                call_args = mock_translate.call_args
                assert call_args[1].get('context') is None

            # Verify translation worked
            po_result = POFileHandler.load_po_file(str(po_file_path))
            assert po_result[0].msgstr == 'Hola'
