from unittest.mock import MagicMock

import pytest

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.openai_provider import OpenAIProvider


@pytest.fixture
def mock_provider_clients() -> ProviderClients:
    """Mock provider clients for testing."""
    clients = ProviderClients()
    clients.openai_client = MagicMock()
    return clients


def test_translate(mock_provider_clients: ProviderClients) -> None:
    """Test bulk translation with OpenAI."""
    # Setup mock response
    mock_chatcompletion = MagicMock()
    mock_chatcompletion.choices = [MagicMock()]
    mock_chatcompletion.choices[0].message.content = (
        '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
    )
    mock_provider_clients.openai_client.chat.completions.create.return_value = mock_chatcompletion

    provider = OpenAIProvider()
    translations = provider.translate(
        provider_clients=mock_provider_clients,
        model="gpt-4",
        content="['Hello', 'World', 'Welcome to our application', 'Goodbye']"
    )

    assert translations == '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
