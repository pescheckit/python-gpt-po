from argparse import Namespace
from unittest.mock import MagicMock, patch

import pytest

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.deepseek_provider import DeepSeekProvider
from python_gpt_po.services.providers.openai_compatible_provider import OpenAICompatibleProvider

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
def mock_provider_clients() -> ProviderClients:
    """Mock provider clients for testing."""
    clients = ProviderClients()
    clients.openai_compatible_api_key = "sk-deepseek-mock-key"
    clients.openai_compatible_base_url = "https://api.deepseek.com/v1"
    return clients


@patch('python_gpt_po.services.providers.openai_compatible_provider.requests.post')
def test_translate(mock_post: MagicMock, mock_provider_clients: ProviderClients) -> None:
    """Test translation with DeepSeek."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = DEEPSEEK_TRANSLATION_RESPONSE
    mock_post.return_value = mock_response

    provider = DeepSeekProvider()
    translations = provider.translate(
        provider_clients=mock_provider_clients,
        model="deepseek-chat",
        content="['Hello', 'World', 'Welcome to our application', 'Goodbye']"
    )

    print(type(translations))
    assert translations == '```json\n["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]\n```'


def test_deepseek_is_alias_to_openai_compatible() -> None:
    """Test that DeepSeekProvider is an alias to OpenAICompatibleProvider."""
    assert DeepSeekProvider is OpenAICompatibleProvider


def test_backward_compatibility_deepseek_args() -> None:
    """Test that old --deepseek-* arguments still work."""
    args = Namespace(
        provider='deepseek',
        deepseek_key='sk-test-key',
        deepseek_base_url=None,
        openai_compatible_key=None,
        openai_compatible_base_url=None,
        folder=None
    )

    clients = ProviderClients()
    clients.initialize_clients(args)

    # Old deepseek args should set openai_compatible fields
    assert clients.openai_compatible_api_key == 'sk-test-key'
    # Should get DeepSeek default base URL when using deepseek provider
    assert clients.openai_compatible_base_url == 'https://api.deepseek.com/v1'


def test_new_openai_compatible_args() -> None:
    """Test that new --openai-compatible-* arguments work."""
    args = Namespace(
        provider='openai_compatible',
        deepseek_key=None,
        deepseek_base_url=None,
        openai_compatible_key='sk-test-key',
        openai_compatible_base_url='http://localhost:1234/v1',
        folder=None
    )

    clients = ProviderClients()
    clients.initialize_clients(args)

    assert clients.openai_compatible_api_key == 'sk-test-key'
    assert clients.openai_compatible_base_url == 'http://localhost:1234/v1'


def test_deepseek_args_priority_over_openai_compatible() -> None:
    """Test that openai_compatible args have priority over deepseek args."""
    args = Namespace(
        provider='openai_compatible',
        deepseek_key='sk-old-key',
        deepseek_base_url='https://old.api.com/v1',
        openai_compatible_key='sk-new-key',
        openai_compatible_base_url='http://new.api.com/v1',
        folder=None
    )

    clients = ProviderClients()
    clients.initialize_clients(args)

    # New args should take priority
    assert clients.openai_compatible_api_key == 'sk-new-key'
    assert clients.openai_compatible_base_url == 'http://new.api.com/v1'
