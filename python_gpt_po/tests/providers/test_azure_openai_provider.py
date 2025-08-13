from unittest.mock import MagicMock

import pytest

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.azure_openai_provider import AzureOpenAIProvider


@pytest.fixture
def mock_provider_clients() -> ProviderClients:
    """Mock provider clients for testing."""
    clients = ProviderClients()
    clients.azure_openai_client = MagicMock()
    clients.azure_openai_client.api_key = "sk-aoi-mock-key"
    return clients


def test_translate(mock_provider_clients: ProviderClients) -> None:
    """Test bulk translation with Azure OpenAI."""
    # Setup mock response
    mock_chatcompletion = MagicMock()
    mock_chatcompletion.choices = [MagicMock()]
    mock_chatcompletion.choices[0].message.content = (
        '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
    )
    mock_provider_clients.azure_openai_client.chat.completions.create.return_value = mock_chatcompletion

    provider = AzureOpenAIProvider()
    translations = provider.translate(
        provider_clients=mock_provider_clients,
        model="gpt-4",
        content="['Hello', 'World', 'Welcome to our application', 'Goodbye']"
    )

    assert translations == '["Bonjour", "Monde", "Bienvenue dans notre application", "Au revoir"]'
