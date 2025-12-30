from unittest.mock import MagicMock, patch

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService
from python_gpt_po.tests.test_multi_provider import SAMPLE_PO_CONTENT


def test_fix_fuzzy_entries_on_sample_po_content(tmp_path):
    # Write SAMPLE_PO_CONTENT to a real temp file
    po_file_path = tmp_path / "sample.po"
    po_file_path.write_text(SAMPLE_PO_CONTENT, encoding="utf-8")

    # Parse the file with polib
    po_file = POFileHandler.load_po_file(str(po_file_path))

    # Sanity check - confirm fuzzy is present
    fuzzy_entries = [entry for entry in po_file if 'fuzzy' in entry.flags]
    assert len(fuzzy_entries) == 1
    assert fuzzy_entries[0].msgid == "This is a fuzzy translation"

    # Setup dummy config
    clients = ProviderClients()
    flags = TranslationFlags(bulk_mode=True, fuzzy=False, folder_language=False, fix_fuzzy=True)
    config = TranslationConfig(
        provider_clients=clients,
        provider=ModelProvider.OPENAI,
        model="gpt-4o",
        flags=flags
    )
    service = TranslationService(config=config)

    # Mock get_translations to return a valid translation
    service.get_translations = MagicMock(return_value=["Ceci est une traduction correcte"])

    # Patch save to avoid actual file I/O
    with patch.object(po_file, 'save') as mock_save:
        service.fix_fuzzy_entries(po_file, str(po_file_path), "fr")

        # Validate that the entry was updated and fuzzy flag removed
        assert fuzzy_entries[0].msgstr == "Ceci est une traduction correcte"
        assert 'fuzzy' not in fuzzy_entries[0].flags

        # Validate save was called
        mock_save.assert_called_once_with(str(po_file_path))
