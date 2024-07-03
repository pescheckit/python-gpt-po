"""
This module contains unit tests for the PO Translator.
"""

from unittest.mock import MagicMock

import polib
import pytest

from python_gpt_po.po_translator import TranslationConfig, TranslationService


@pytest.fixture(name='mock_openai_client')
def fixture_mock_openai_client():
    """
    Fixture to mock the OpenAI client.
    """
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = (
        "0: HR\n"
        "1: Tenant\n"
        "2: Healthcare\n"
        "3: Transport\n"
        "4: Accounting & Consulting\n"
        "5: Agriculture\n"
        "6: Construction\n"
        "7: Entertainment\n"
        "8: Mining\n"
        "9: Energy\n"
        "10: Financial Services\n"
        "11: Hospitality\n"
        "12: IT\n"
        "13: Manufacturing\n"
        "14: Education\n"
        "15: Real estate\n"
        "16: Other\n"
    )
    return client


@pytest.fixture(name='translation_config')
def fixture_translation_config(mock_openai_client):
    """
    Fixture to create a TranslationConfig instance.
    """
    model = "gpt-3.5-turbo-1106"
    return TranslationConfig(
        client=mock_openai_client,
        model=model,
        bulk_mode=True,
        fuzzy=False,
        folder_language=False
    )


@pytest.fixture(name='translation_service')
def fixture_translation_service(translation_config):
    """
    Fixture to create a TranslationService instance.
    """
    return TranslationService(config=translation_config)


def test_validate_openai_connection(translation_service):
    """
    Test to validate the OpenAI connection.
    """
    assert translation_service.validate_openai_connection() is True


def test_translate_bulk(translation_service, tmp_path):
    """
    Test the bulk translation functionality.
    """
    # Create a temporary .po file
    po_file_path = tmp_path / "django.po"
    po_file_content = '''msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2024-06-20 09:17+0000\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "HR"
msgstr ""
msgid "TENANT"
msgstr ""
msgid "HEALTHCARE"
msgstr ""
msgid "TRANSPORT"
msgstr ""
msgid "SERVICES"
msgstr ""
msgid "AGRO"
msgstr ""
msgid "CONSTRUCTION"
msgstr ""
msgid "ENTERTAINMENT"
msgstr ""
msgid "MINING"
msgstr ""
msgid "ENERGY"
msgstr ""
msgid "FINANCE"
msgstr ""
msgid "HOSPITALITY"
msgstr ""
msgid "IT"
msgstr ""
msgid "MANUFACTURING"
msgstr ""
msgid "EDUCATION"
msgstr ""
msgid "REALESTATE"
msgstr ""
msgid "OTHER"
msgstr ""
'''
    po_file_path.write_text(po_file_content)

    po_file = polib.pofile(po_file_path)
    texts_to_translate = [entry.msgid for entry in po_file if not entry.msgstr]

    # Perform translation
    translated_texts = translation_service.translate_bulk(texts_to_translate, 'es', str(po_file_path), 0)

    # Apply translations
    translation_service.apply_translations_to_po_file(translated_texts, texts_to_translate, po_file)

    # Save .po file
    po_file.save(po_file_path)

    # Reload .po file to check translations
    translated_po_file = polib.pofile(po_file_path)

    for entry in translated_po_file:
        assert entry.msgstr != ""

    # Check a few translations to ensure correctness
    assert translated_po_file.find("HR").msgstr == "HR"
    assert translated_po_file.find("TENANT").msgstr == "Tenant"
    assert translated_po_file.find("HEALTHCARE").msgstr == "Healthcare"
