from unittest.mock import MagicMock, patch

import pytest

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.deepseek_provider import DeepSeekProvider

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
    clients.deepseek_api_key = "sk-deepseek-mock-key"
    clients.deepseek_base_url = "https://api.deepseek.com/v1"
    return clients


@patch('python_gpt_po.services.providers.deepseek_provider.requests.post')
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
