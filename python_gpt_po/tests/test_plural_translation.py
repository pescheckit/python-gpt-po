"""
Tests for plural form translation functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import polib
import pytest

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.translation_service import TranslationService
from python_gpt_po.utils.plural_form_helpers import get_plural_count, get_plural_form_names, is_plural_entry


def create_test_config(bulk_mode=True):
    """Helper to create a test TranslationConfig."""
    mock_client = MagicMock()
    provider_clients = ProviderClients()
    provider_clients.openai_client = mock_client

    flags = TranslationFlags(
        bulk_mode=bulk_mode,
        fuzzy=False,
        folder_language=False,
        mark_ai_generated=True
    )

    return TranslationConfig(
        provider_clients=provider_clients,
        provider=ModelProvider.OPENAI,
        model="gpt-3.5-turbo",
        flags=flags
    )


class TestPluralFormHelpers:
    """Unit tests for plural form helper functions."""

    def test_get_plural_count_from_header(self):
        """Test parsing nplurals from Plural-Forms header."""
        # Create a mock PO file with Plural-Forms header
        po_file = MagicMock()
        po_file.metadata = {
            'Plural-Forms': (
                'nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : '
                'n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);'
            )
        }

        count = get_plural_count(po_file, 'ru')
        assert count == 3

    def test_get_plural_count_from_header_2_forms(self):
        """Test parsing nplurals=2 from Plural-Forms header."""
        po_file = MagicMock()
        po_file.metadata = {
            'Plural-Forms': 'nplurals=2; plural=(n != 1);'
        }

        count = get_plural_count(po_file, 'en')
        assert count == 2

    def test_get_plural_count_default_fallback(self):
        """Test fallback to defaults when header missing."""
        po_file = MagicMock()
        po_file.metadata = {}

        # Russian should default to 3
        assert get_plural_count(po_file, 'ru') == 3

        # English should default to 2
        assert get_plural_count(po_file, 'en') == 2

        # Arabic should default to 6
        assert get_plural_count(po_file, 'ar') == 6

        # Japanese should default to 1
        assert get_plural_count(po_file, 'ja') == 1

    def test_get_plural_count_ultimate_fallback(self):
        """Test ultimate fallback to 2 for unknown language."""
        po_file = MagicMock()
        po_file.metadata = {}

        count = get_plural_count(po_file, 'xyz')  # Unknown language code
        assert count == 2

    def test_get_plural_form_names(self):
        """Test getting plural form names for different counts."""
        assert get_plural_form_names(1) == ["singular"]
        assert get_plural_form_names(2) == ["singular", "plural"]
        assert get_plural_form_names(3) == ["singular", "few", "many"]
        assert get_plural_form_names(6) == ["zero", "one", "two", "few", "many", "other"]

    def test_get_plural_form_names_fallback(self):
        """Test fallback for unexpected counts."""
        names = get_plural_form_names(7)  # Unusual count
        assert names[0] == "singular"
        assert len(names) == 7

    def test_is_plural_entry_true(self):
        """Test detection of plural entries."""
        entry = MagicMock()
        entry.msgid = "One file"
        entry.msgid_plural = "%d files"

        assert is_plural_entry(entry) is True

    def test_is_plural_entry_false(self):
        """Test detection of non-plural entries."""
        entry = MagicMock()
        entry.msgid = "Hello"
        entry.msgid_plural = None

        assert is_plural_entry(entry) is False

    def test_is_plural_entry_empty_plural(self):
        """Test detection when msgid_plural is empty string."""
        entry = MagicMock()
        entry.msgid = "Hello"
        entry.msgid_plural = ""

        assert is_plural_entry(entry) is False


class TestPluralRequestExpansion:
    """Tests for plural entry expansion in translation requests."""

    def test_expand_plural_request(self):
        """Test that plural entries are expanded correctly."""
        config = create_test_config(bulk_mode=True)
        service = TranslationService(config)

        # Create a temporary PO file with a plural entry
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """
# Test PO file
msgid ""
msgstr ""
"Language: en\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = polib.pofile(po_file_path)

            # Prepare translation request
            request = service._prepare_translation_request(
                po_file, po_file_path, 'en', {}
            )

            # Should expand to 2 translation requests (singular + plural)
            assert len(request.texts) == 2
            assert request.texts[0] == "One file"
            assert request.texts[1] == "%d files"

            # Check plural metadata
            assert request.plural_metadata is not None
            assert len(request.plural_metadata) == 2

            # First form (singular)
            assert request.plural_metadata[0]['is_plural'] is True
            assert request.plural_metadata[0]['form_index'] == 0
            assert request.plural_metadata[0]['form_name'] == 'singular'
            assert request.plural_metadata[0]['total_forms'] == 2

            # Second form (plural)
            assert request.plural_metadata[1]['is_plural'] is True
            assert request.plural_metadata[1]['form_index'] == 1
            assert request.plural_metadata[1]['form_name'] == 'plural'
            assert request.plural_metadata[1]['total_forms'] == 2

        finally:
            Path(po_file_path).unlink()

    def test_mixed_regular_and_plural_entries(self):
        """Test that mixed entries are handled correctly."""
        config = create_test_config(bulk_mode=True)
        service = TranslationService(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """
msgid ""
msgstr ""
"Language: en\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "Hello"
msgstr ""

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] ""

msgid "Goodbye"
msgstr ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = polib.pofile(po_file_path)

            request = service._prepare_translation_request(
                po_file, po_file_path, 'en', {}
            )

            # Should have 4 texts: Hello, One file, %d files, Goodbye
            assert len(request.texts) == 4
            assert request.texts[0] == "Hello"
            assert request.texts[1] == "One file"
            assert request.texts[2] == "%d files"
            assert request.texts[3] == "Goodbye"

            # Check metadata
            assert request.plural_metadata[0]['is_plural'] is False
            assert request.plural_metadata[1]['is_plural'] is True
            assert request.plural_metadata[2]['is_plural'] is True
            assert request.plural_metadata[3]['is_plural'] is False

        finally:
            Path(po_file_path).unlink()


class TestPluralPromptGeneration:
    """Tests for plural form prompt generation."""

    def test_prompt_includes_plural_context(self):
        """Test that plural prompts include proper context."""
        config = create_test_config(bulk_mode=False)
        service = TranslationService(config)

        prompt = service.get_translation_prompt(
            target_language='nl',
            is_bulk=False,
            plural_form='plural',
            plural_sources={
                'singular': 'One file',
                'plural': '%d files'
            }
        )

        assert 'PLURAL FORM: plural' in prompt
        assert 'Singular: "One file"' in prompt
        assert 'Plural: "%d files"' in prompt
        assert 'plural form appropriately' in prompt

    def test_prompt_without_plural_context(self):
        """Test that regular prompts work without plural context."""
        config = create_test_config(bulk_mode=False)
        service = TranslationService(config)

        prompt = service.get_translation_prompt(
            target_language='nl',
            is_bulk=False
        )

        assert 'PLURAL FORM' not in prompt


@pytest.mark.integration
class TestPluralTranslationIntegration:
    """Integration tests for plural translation."""

    @patch('python_gpt_po.services.translation_service.TranslationService._get_provider_response')
    def test_translate_2_form_plural_bulk(self, mock_provider):
        """Test translating 2-form plural in bulk mode."""
        # Mock the AI response
        mock_provider.return_value = '["Een bestand", "%d bestanden"]'

        config = create_test_config(bulk_mode=True)
        service = TranslationService(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """
msgid ""
msgstr ""
"Language: nl\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = polib.pofile(po_file_path)
            request = service._prepare_translation_request(
                po_file, po_file_path, 'nl', {}
            )

            # Process with incremental save
            service._process_with_incremental_save_bulk(request)

            # Check that msgstr_plural was filled
            plural_entry = [e for e in po_file if hasattr(e, 'msgid_plural') and e.msgid_plural][0]
            assert plural_entry.msgstr_plural[0] == "Een bestand"
            assert plural_entry.msgstr_plural[1] == "%d bestanden"

        finally:
            Path(po_file_path).unlink()

    @patch('python_gpt_po.services.translation_service.TranslationService._get_provider_response')
    def test_translate_2_form_plural_single(self, mock_provider):
        """Test translating 2-form plural in single mode."""
        # Mock responses for each form
        mock_provider.side_effect = ["Een bestand", "%d bestanden"]

        config = create_test_config(bulk_mode=False)
        service = TranslationService(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """
msgid ""
msgstr ""
"Language: nl\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = polib.pofile(po_file_path)
            request = service._prepare_translation_request(
                po_file, po_file_path, 'nl', {}
            )

            # Process with single mode
            service._process_with_incremental_save_single(request)

            # Check that msgstr_plural was filled
            plural_entry = [e for e in po_file if hasattr(e, 'msgid_plural') and e.msgid_plural][0]
            assert plural_entry.msgstr_plural[0] == "Een bestand"
            assert plural_entry.msgstr_plural[1] == "%d bestanden"

        finally:
            Path(po_file_path).unlink()

    @patch('python_gpt_po.services.translation_service.TranslationService._get_provider_response')
    def test_translate_3_form_plural(self, mock_provider):
        """Test translating 3-form plural (Russian)."""
        # Mock the AI response for 3 forms
        mock_provider.return_value = '["один файл", "%d файла", "%d файлов"]'

        config = create_test_config(bulk_mode=True)
        service = TranslationService(config)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = """
msgid ""
msgstr ""
"Language: ru\\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
"n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\\n"

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""
"""
            f.write(po_content)
            po_file_path = f.name

        try:
            po_file = polib.pofile(po_file_path)
            request = service._prepare_translation_request(
                po_file, po_file_path, 'ru', {}
            )

            # Should expand to 3 translation requests
            assert len(request.texts) == 3

            # Process translations
            service._process_with_incremental_save_bulk(request)

            # Check that all 3 forms were filled
            plural_entry = [e for e in po_file if hasattr(e, 'msgid_plural') and e.msgid_plural][0]
            assert plural_entry.msgstr_plural[0] == "один файл"
            assert plural_entry.msgstr_plural[1] == "%d файла"
            assert plural_entry.msgstr_plural[2] == "%d файлов"

        finally:
            Path(po_file_path).unlink()
