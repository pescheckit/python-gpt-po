"""
Unit tests for the custom provider.
"""
import unittest
from unittest.mock import MagicMock, patch
from argparse import Namespace

from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.custom_provider import CustomProvider

class TestCustomProvider(unittest.TestCase):
    def setUp(self):
        self.provider = CustomProvider()
        self.args = Namespace(
            custom_key="test-key",
            custom_base_url="https://api.custom-ai.com/v1",
            folder="."
        )

    @patch('python_gpt_po.models.provider_clients.OpenAI')
    def test_provider_initialization(self, mock_openai):
        """Verify that ProviderClients initializes the custom client correctly."""
        clients = ProviderClients()
        clients.initialize_clients(self.args)
        
        mock_openai.assert_called_once_with(
            api_key="test-key",
            base_url="https://api.custom-ai.com/v1"
        )
        self.assertIsNotNone(clients.custom_client)

    def test_is_client_initialized(self):
        """Verify initialization check."""
        clients = ProviderClients()
        self.assertFalse(self.provider.is_client_initialized(clients))
        
        clients.custom_client = MagicMock()
        self.assertTrue(self.provider.is_client_initialized(clients))

    @patch('python_gpt_po.models.provider_clients.OpenAI')
    def test_translate_call(self, mock_openai):
        """Verify that translate calls the underlying openai client correctly."""
        clients = ProviderClients()
        clients.custom_client = MagicMock()
        
        # Mock the chat.completions.create response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Translated Text"
        clients.custom_client.chat.completions.create.return_value = mock_response
        
        result = self.provider.translate(clients, "model-x", "Hello")
        
        clients.custom_client.chat.completions.create.assert_called_once_with(
            model="model-x",
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertEqual(result, "Translated Text")

if __name__ == '__main__':
    unittest.main()
