"""
This module contains unit tests for the PO Translator.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from python_gpt_po.po_translator import (ModelProvider, POFileHandler, ProviderClients, TranslationConfig,
                                         TranslationService)

logging.basicConfig(level=logging.INFO)


@pytest.fixture(name='mock_openai_client')
def fixture_mock_openai_client():
    """
    Fixture to mock the OpenAI client.
    """
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = '["Inquilino", "Salud", "Transporte"]'
    return client


@pytest.fixture(name='translation_config')
def fixture_translation_config(mock_openai_client):
    """
    Fixture to create a TranslationConfig instance.
    """
    provider_clients = ProviderClients()
    provider_clients.openai_client = mock_openai_client
    
    model = "gpt-3.5-turbo"
    return TranslationConfig(
        provider_clients=provider_clients,
        provider=ModelProvider.OPENAI,
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


@pytest.fixture(name='mock_po_file_handler')
def fixture_mock_po_file_handler():
    """
    Fixture to mock the POFileHandler.
    """
    return MagicMock(spec=POFileHandler)


def test_validate_openai_connection(translation_service):
    """Test to validate the connection."""
    # The new method is validate_provider_connection instead of validate_openai_connection
    assert translation_service.validate_provider_connection() is True


@patch('python_gpt_po.po_translator.POFileHandler')
def test_process_po_file(mock_po_file_handler_class, translation_service, tmp_path):
    """
    Test the process_po_file method.
    """
    # Create a temporary .po file
    po_file_path = tmp_path / "django.po"
    po_file_content = '''msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Language: es\\n"
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
'''
    po_file_path.write_text(po_file_content)

    # Mock POFileHandler methods
    mock_po_file_handler = mock_po_file_handler_class.return_value
    mock_po_file_handler.get_file_language.return_value = 'es'

    # Explicitly setting fuzzy=True to trigger the function
    translation_service.config.fuzzy = True

    # Process the .po file
    translation_service.process_po_file(str(po_file_path), ['es'])


def test_translate_bulk(translation_service, tmp_path):
    """Test the bulk translation functionality."""
    texts_to_translate = ["HR", "TENANT", "HEALTHCARE", "TRANSPORT", "SERVICES"]
    po_file_path = str(tmp_path / "django.po")

    # Mock the response based on provider
    if translation_service.config.provider == ModelProvider.OPENAI:
        translation_service.config.provider_clients.openai_client.chat.completions.create.return_value.choices[0].message.content = (
            '["HR", "Inquilino", "Salud", "Transporte", "Servicios"]'
        )

    translated_texts = translation_service.translate_bulk(texts_to_translate, 'es', po_file_path)
    assert translated_texts == ["HR", "Inquilino", "Salud", "Transporte", "Servicios"]


def test_translate_single(translation_service):
    """Test the single translation functionality."""
    text_to_translate = "HEALTHCARE"

    # Mock based on provider
    if translation_service.config.provider == ModelProvider.OPENAI:
        translation_service.config.provider_clients.openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='Salud'))]
        )
    elif translation_service.config.provider == ModelProvider.ANTHROPIC:
        translation_service.config.provider_clients.anthropic_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='Salud')]
        )
    elif translation_service.config.provider == ModelProvider.DEEPSEEK:
        # For DeepSeek, we need to mock the requests module
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Salud"}}]
            }
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            translated_text = translation_service.translate_single(text_to_translate, 'es')
            assert translated_text == "Salud"
            return

    # For OpenAI and Anthropic
    translated_text = translation_service.translate_single(text_to_translate, 'es')
    assert translated_text == "Salud"
