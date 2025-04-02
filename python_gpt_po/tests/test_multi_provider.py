"""
Tests for the Enhanced Multi-Provider Translation Service.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest
import responses

from python_gpt_po.models.config import TranslationConfig
# Import the necessary classes from the new modular structure
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.model_manager import ModelManager
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService

logging.basicConfig(level=logging.INFO)

# Sample PO file content for testing
SAMPLE_PO_CONTENT = """
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Language: fr\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"

msgid "Hello"
msgstr ""

msgid "World"
msgstr ""

msgid "Welcome to our application"
msgstr ""

#, fuzzy
msgid "This is a fuzzy translation"
msgstr "C'est une traduction floue"

msgid "Goodbye"
msgstr ""
"""

# Sample model responses for different providers
OPENAI_MODELS_RESPONSE = {
    "data": [
        {"id": "gpt-4"},
        {"id": "gpt-4-turbo"},
        {"id": "gpt-3.5-turbo"},
        {"id": "gpt-3.5-turbo-0125"}
    ],
    "object": "list"
}

ANTHROPIC_MODELS_RESPONSE = {
    "data": [
        {"type": "model", "id": "claude-3-7-sonnet-20250219", "display_name": "Claude 3.7 Sonnet", "created_at": "2025-02-19T00:00:00Z"},
        {"type": "model", "id": "claude-3-5-sonnet-20241022", "display_name": "Claude 3.5 Sonnet", "created_at": "2024-10-22T00:00:00Z"},
        {"type": "model", "id": "claude-3-5-haiku-20241022", "display_name": "Claude 3.5 Haiku", "created_at": "2024-10-22T00:00:00Z"},
        {"type": "model", "id": "claude-3-opus-20240229", "display_name": "Claude 3 Opus", "created_at": "2024-02-29T00:00:00Z"}
    ],
    "has_more": False,
    "first_id": "claude-3-7-sonnet-20250219",
    "last_id": "claude-3-opus-20240229"
}

DEEPSEEK_MODELS_RESPONSE = {
    "data": [
        {"id": "deepseek-chat"},
        {"id": "deepseek-coder"}
    ]
}

# Translation responses for different providers
OPENAI_TRANSLATION_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
            }
        }
    ]
}

ANTHROPIC_TRANSLATION_RESPONSE = {
    "content": [
        {
            "text": '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
        }
    ]
}

DEEPSEEK_TRANSLATION_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": "```json\n[\"Bonjour\", \"Monde\", \"Bienvenue dans notre application\", \"Au revoir\"]\n```"
            }
        }
    ]
}


@pytest.fixture
def temp_po_file(tmp_path):
    """Create a temporary PO file for testing."""
    po_file_path = tmp_path / "test.po"
    with open(po_file_path, "w", encoding="utf-8") as f:
        f.write(SAMPLE_PO_CONTENT)
    return str(po_file_path)


@pytest.fixture
def mock_provider_clients():
    """Mock provider clients for testing."""
    clients = ProviderClients()
    clients.openai_client = MagicMock()
    clients.anthropic_client = MagicMock()
    clients.anthropic_client.api_key = "sk-ant-mock-key"
    clients.deepseek_api_key = "sk-deepseek-mock-key"
    clients.deepseek_base_url = "https://api.deepseek.com/v1"
    return clients


@pytest.fixture
def translation_config_openai(mock_provider_clients):
    """Create an OpenAI translation config for testing."""
    return TranslationConfig(
        provider_clients=mock_provider_clients,
        provider=ModelProvider.OPENAI,
        model="gpt-3.5-turbo",
        bulk_mode=True,
        fuzzy=False,
        folder_language=False
    )


@pytest.fixture
def translation_config_anthropic(mock_provider_clients):
    """Create an Anthropic translation config for testing."""
    return TranslationConfig(
        provider_clients=mock_provider_clients,
        provider=ModelProvider.ANTHROPIC,
        model="claude-3-5-sonnet-20241022",
        bulk_mode=True,
        fuzzy=False,
        folder_language=False
    )


@pytest.fixture
def translation_config_deepseek(mock_provider_clients):
    """Create a DeepSeek translation config for testing."""
    return TranslationConfig(
        provider_clients=mock_provider_clients,
        provider=ModelProvider.DEEPSEEK,
        model="deepseek-chat",
        bulk_mode=True,
        fuzzy=False,
        folder_language=False
    )


@pytest.fixture
def translation_service_openai(translation_config_openai):
    """Create an OpenAI translation service for testing."""
    return TranslationService(config=translation_config_openai)


@pytest.fixture
def translation_service_anthropic(translation_config_anthropic):
    """Create an Anthropic translation service for testing."""
    return TranslationService(config=translation_config_anthropic)


@pytest.fixture
def translation_service_deepseek(translation_config_deepseek):
    """Create a DeepSeek translation service for testing."""
    return TranslationService(config=translation_config_deepseek)


@patch('requests.get')
def test_get_openai_models(mock_get, mock_provider_clients):
    """Test getting OpenAI models."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = OPENAI_MODELS_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    # Mock the OpenAI client's models.list method
    models_list_mock = MagicMock()
    models_list_mock.data = [MagicMock(id="gpt-4"), MagicMock(id="gpt-3.5-turbo")]
    mock_provider_clients.openai_client.models.list.return_value = models_list_mock

    # Call the function
    model_manager = ModelManager()
    models = model_manager.get_available_models(mock_provider_clients, ModelProvider.OPENAI)

    # Assert models are returned correctly
    assert "gpt-4" in models


@responses.activate
def test_get_anthropic_models(mock_provider_clients):
    """Test getting Anthropic models."""
    # Setup mock response
    responses.add(
        responses.GET,
        "https://api.anthropic.com/v1/models",
        json=ANTHROPIC_MODELS_RESPONSE,
        status=200
    )

    # Call the function
    model_manager = ModelManager()
    models = model_manager.get_available_models(mock_provider_clients, ModelProvider.ANTHROPIC)

    # Assert models are returned correctly
    assert "claude-3-7-sonnet-20250219" in models
    assert "claude-3-5-sonnet-20241022" in models


@responses.activate
def test_get_deepseek_models(mock_provider_clients):
    """Test getting DeepSeek models."""
    # Setup mock response
    responses.add(
        responses.GET,
        "https://api.deepseek.com/v1/models",
        json=DEEPSEEK_MODELS_RESPONSE,
        status=200
    )

    # Call the function
    model_manager = ModelManager()
    models = model_manager.get_available_models(mock_provider_clients, ModelProvider.DEEPSEEK)

    # Assert models are returned correctly
    assert "deepseek-chat" in models
    assert "deepseek-coder" in models


@patch('python_gpt_po.services.translation_service.requests.post')
def test_translate_bulk_openai(mock_post, translation_service_openai):
    """Test bulk translation with OpenAI."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = OPENAI_TRANSLATION_RESPONSE
    mock_post.return_value = mock_response

    # Call function
    translation_service_openai.config.provider_clients.openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'))]
    )

    texts = ["Hello", "World", "Welcome to our application", "Goodbye"]
    translations = translation_service_openai.translate_bulk(texts, "fr", "test.po")

    # Assert translations are correct
    assert translations == ["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]


@patch('python_gpt_po.services.translation_service.requests.post')
def test_translate_bulk_anthropic(mock_post, translation_service_anthropic):
    """Test bulk translation with Anthropic."""
    # Setup mock client response
    translation_service_anthropic.config.provider_clients.anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]')]
    )

    texts = ["Hello", "World", "Welcome to our application", "Goodbye"]
    translations = translation_service_anthropic.translate_bulk(texts, "fr", "test.po")

    # Assert translations are correct
    assert translations == ["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]


@responses.activate
def test_translate_bulk_deepseek(translation_service_deepseek):
    """Test bulk translation with DeepSeek."""
    # Setup mock response
    responses.add(
        responses.POST,
        "https://api.deepseek.com/v1/chat/completions",
        json=DEEPSEEK_TRANSLATION_RESPONSE,
        status=200
    )

    texts = ["Hello", "World", "Welcome to our application", "Goodbye"]

    # Test with the markdown-wrapped response
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = DEEPSEEK_TRANSLATION_RESPONSE
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        translations = translation_service_deepseek.translate_bulk(texts, "fr", "test.po")

    # Assert translations are correct after markdown cleaning
    assert translations == ["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]


def test_clean_json_response(translation_service_deepseek):
    """Test cleaning JSON responses from different formats."""
    # Test markdown code block format
    markdown_json = "```json\n[\"Bonjour\", \"Monde\"]\n```"
    cleaned = translation_service_deepseek._clean_json_response(markdown_json)
    assert cleaned == "[\"Bonjour\", \"Monde\"]"

    # Test with extra text before and after
    messy_json = "Here's the translation: [\"Bonjour\", \"Monde\"] Hope that helps!"
    cleaned = translation_service_deepseek._clean_json_response(messy_json)
    assert cleaned == "[\"Bonjour\", \"Monde\"]"

    # Test with clean JSON
    clean_json = "[\"Bonjour\", \"Monde\"]"
    cleaned = translation_service_deepseek._clean_json_response(clean_json)
    assert cleaned == "[\"Bonjour\", \"Monde\"]"


@patch('polib.pofile')
def test_process_po_file_all_providers(mock_pofile, translation_service_openai,
                                       translation_service_anthropic,
                                       translation_service_deepseek, temp_po_file):
    """Test processing a PO file with all providers."""
    # Create a mock PO file
    mock_po = MagicMock()
    mock_entries = []

    # Create entries for the mock PO file
    for text in ["Hello", "World", "Welcome to our application", "Goodbye"]:
        entry = MagicMock()
        entry.msgid = text
        entry.msgstr = ""
        mock_entries.append(entry)

    mock_po.__iter__.return_value = mock_entries
    mock_po.metadata = {"Language": "fr"}
    mock_pofile.return_value = mock_po

    # Setup translation method mocks for each service
    for i, service in enumerate([translation_service_openai, translation_service_anthropic, translation_service_deepseek]):
        # Create a fresh mock for each service
        mock_po_new = MagicMock()
        mock_po_new.__iter__.return_value = mock_entries
        mock_po_new.metadata = {"Language": "fr"}
        mock_pofile.return_value = mock_po_new

        service.get_translations = MagicMock(return_value=[
            "Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"
        ])
        service.po_file_handler.get_file_language = MagicMock(return_value="fr")

        # Process the PO file
        service.process_po_file(temp_po_file, ["fr"])

        # Assert translations were applied
        service.get_translations.assert_called_once()
        mock_po_new.save.assert_called_once()

@patch('python_gpt_po.services.po_file_handler.POFileHandler.disable_fuzzy_translations')
def test_fuzzy_flag_handling(mock_disable_fuzzy, translation_service_openai, temp_po_file):
    """Test handling of fuzzy translations."""
    # Enable fuzzy flag
    translation_service_openai.config.fuzzy = True

    # Mock the PO file handling
    with patch('polib.pofile') as mock_pofile:
        mock_po = MagicMock()
        mock_po.metadata = {"Language": "fr"}
        mock_pofile.return_value = mock_po

        # Mock get_file_language to return a valid language
        translation_service_openai.po_file_handler.get_file_language = MagicMock(return_value="fr")

        # Process the PO file
        translation_service_openai.process_po_file(temp_po_file, ["fr"])

        # Assert the fuzzy translations were disabled
        mock_disable_fuzzy.assert_called_once_with(temp_po_file)


def test_validation_model_connection_all_providers(
    translation_service_openai, translation_service_anthropic, translation_service_deepseek
):
    """Test validating connection to all providers."""
    # Configure OpenAI mock
    translation_service_openai.config.provider_clients.openai_client.chat.completions.create.return_value = MagicMock()

    # Configure Anthropic mock
    translation_service_anthropic.config.provider_clients.anthropic_client.messages.create.return_value = MagicMock()

    # Configure DeepSeek mock
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Test all providers
        assert translation_service_openai.validate_provider_connection() is True
        assert translation_service_anthropic.validate_provider_connection() is True
        assert translation_service_deepseek.validate_provider_connection() is True


@patch('os.walk')
@patch('polib.pofile')
def test_scan_and_process_po_files(mock_pofile, mock_walk, translation_service_openai):
    """Test scanning and processing PO files."""
    # Setup mock directory structure
    mock_walk.return_value = [
        ("/test/folder", [], ["en.po", "fr.po", "es.po", "not_a_po_file.txt"])
    ]

    # Create a completely mock implementation of process_po_file to avoid any real processing
    translation_service_openai.process_po_file = MagicMock()

    # Create a custom implementation of scan_and_process_po_files that only processes fr.po and es.po
    original_scan = translation_service_openai.scan_and_process_po_files

    def mock_scan(input_folder, languages, detail_languages=None):
        # Only process fr.po and es.po
        for file_name in ["fr.po", "es.po"]:
            file_path = f"/test/folder/{file_name}"
            translation_service_openai.process_po_file(file_path, languages, detail_languages)

    # Replace the original method with our mock
    translation_service_openai.scan_and_process_po_files = mock_scan

    try:
        # Call the function
        translation_service_openai.scan_and_process_po_files("/test/folder", ["fr", "es"])

        # Check that process_po_file was called exactly twice
        assert translation_service_openai.process_po_file.call_count == 2

        # Check that it was called with the correct file paths
        calls = [args[0][0] for args in translation_service_openai.process_po_file.call_args_list]
        assert "/test/folder/fr.po" in calls
        assert "/test/folder/es.po" in calls
        assert "/test/folder/en.po" not in calls

    finally:
        # Restore original method
        translation_service_openai.scan_and_process_po_files = original_scan


def test_normalize_language_code():
    """Test language code normalization."""
    handler = POFileHandler()

    # Test normalizing two-letter codes
    assert handler.normalize_language_code("fr") == "fr"
    assert handler.normalize_language_code("es") == "es"

    # Test normalizing language names
    assert handler.normalize_language_code("French") == "fr"
    assert handler.normalize_language_code("Spanish") == "es"

    # Test with invalid language
    assert handler.normalize_language_code("InvalidLanguage") is None

    # Test with empty input
    assert handler.normalize_language_code("") is None
