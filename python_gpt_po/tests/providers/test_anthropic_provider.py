from unittest.mock import MagicMock

import pytest

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.anthropic_provider import AnthropicProvider


@pytest.fixture
def mock_provider_clients() -> ProviderClients:
    """Mock provider clients for testing."""
    clients = ProviderClients()
    clients.anthropic_client = MagicMock()
    clients.anthropic_client.api_key = "sk-ant-mock-key"
    return clients


def test_translate(mock_provider_clients: ProviderClients) -> None:
    """Test bulk translation with Anthropic."""
    # Setup mock response
    mock_chatcompletion = MagicMock()
    mock_chatcompletion.content = [MagicMock()]
    mock_chatcompletion.content[0].text = '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
    mock_provider_clients.anthropic_client.messages.create.return_value = mock_chatcompletion

    provider = AnthropicProvider()
    translations = provider.translate(
        provider_clients=mock_provider_clients,
        model="gpt-4",
        content="['Hello', 'World', 'Welcome to our application', 'Goodbye']"
    )

    assert translations == '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
