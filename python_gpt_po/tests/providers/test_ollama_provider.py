"""
Tests for Ollama provider.
"""
import unittest
from unittest.mock import MagicMock, patch

import requests

from python_gpt_po.models.provider_clients import ProviderClients
from python_gpt_po.services.providers.ollama_provider import OllamaProvider


class TestOllamaProvider(unittest.TestCase):
    """Test cases for Ollama provider."""

    def setUp(self):
        """Set up test fixtures."""
        self.provider = OllamaProvider()
        self.provider_clients = ProviderClients()
        self.provider_clients.ollama_base_url = "http://localhost:11434"
        self.provider_clients.ollama_timeout = 120

    @patch('requests.get')
    def test_is_client_initialized_success(self, mock_get):
        """Test successful Ollama connection check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.provider.is_client_initialized(self.provider_clients)

        self.assertTrue(result)
        mock_get.assert_called_once_with(
            "http://localhost:11434/api/tags",
            timeout=5
        )

    @patch('requests.get')
    def test_is_client_initialized_connection_error(self, mock_get):
        """Test Ollama connection failure."""
        mock_get.side_effect = requests.ConnectionError()

        result = self.provider.is_client_initialized(self.provider_clients)

        self.assertFalse(result)

    @patch('requests.get')
    def test_is_client_initialized_timeout(self, mock_get):
        """Test Ollama timeout."""
        mock_get.side_effect = requests.Timeout()

        result = self.provider.is_client_initialized(self.provider_clients)

        self.assertFalse(result)

    @patch('requests.get')
    def test_get_models_success(self, mock_get):
        """Test retrieving models from Ollama."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3.2"},
                {"name": "llama3.1"},
                {"name": "mistral"}
            ]
        }
        mock_get.return_value = mock_response

        models = self.provider.get_models(self.provider_clients)

        self.assertEqual(models, ["llama3.2", "llama3.1", "mistral"])

    @patch('requests.get')
    def test_get_models_failure_returns_fallback(self, mock_get):
        """Test fallback models when API fails."""
        mock_get.side_effect = requests.ConnectionError()

        models = self.provider.get_models(self.provider_clients)

        # Should return fallback models
        self.assertIn("llama3.2", models)
        self.assertIn("mistral", models)

    @patch('requests.post')
    @patch('requests.get')
    def test_translate_success(self, mock_get, mock_post):
        """Test successful translation with Ollama."""
        # Mock connection check
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        # Mock translation response
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"response": "Bonjour"}
        mock_post.return_value = mock_post_response

        result = self.provider.translate(
            self.provider_clients,
            "llama3.2",
            "Translate to French: Hello"
        )

        self.assertEqual(result, "Bonjour")
        mock_post.assert_called_once()

    @patch('requests.post')
    @patch('requests.get')
    def test_translate_timeout(self, mock_get, mock_post):
        """Test translation timeout handling."""
        # Mock connection check
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        # Mock timeout
        mock_post.side_effect = requests.Timeout()

        with self.assertRaises(TimeoutError) as context:
            self.provider.translate(
                self.provider_clients,
                "llama3.2",
                "Translate to French: Hello"
            )

        self.assertIn("timed out", str(context.exception))

    @patch('requests.get')
    def test_translate_not_initialized(self, mock_get):
        """Test translation when Ollama is not accessible."""
        mock_get.side_effect = requests.ConnectionError()

        with self.assertRaises(ValueError) as context:
            self.provider.translate(
                self.provider_clients,
                "llama3.2",
                "Translate to French: Hello"
            )

        self.assertIn("not accessible", str(context.exception))

    def test_get_default_model(self):
        """Test default model."""
        self.assertEqual(self.provider.get_default_model(), "llama3.2")

    def test_get_preferred_models(self):
        """Test preferred models for translation."""
        models = self.provider.get_preferred_models("translation")
        self.assertIn("llama3.2", models)
        self.assertIn("llama3.1", models)

    def test_get_fallback_models(self):
        """Test fallback models."""
        models = self.provider.get_fallback_models()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        self.assertIn("llama3.2", models)

    @patch('requests.get')
    def test_custom_base_url(self, mock_get):
        """Test using custom Ollama base URL."""
        self.provider_clients.ollama_base_url = "http://192.168.1.100:8080"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = self.provider.is_client_initialized(self.provider_clients)

        self.assertTrue(result)
        mock_get.assert_called_once_with(
            "http://192.168.1.100:8080/api/tags",
            timeout=5
        )


if __name__ == '__main__':
    unittest.main()
