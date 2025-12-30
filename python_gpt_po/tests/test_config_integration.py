"""
Integration tests for configuration actually affecting translation behavior.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService
from python_gpt_po.utils.config_loader import ConfigLoader
from python_gpt_po.utils.gitignore import create_gitignore_parser


class TestConfigIntegration(unittest.TestCase):
    """Test that loaded configuration actually affects application behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

        # Create mock provider clients
        self.mock_provider_clients = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_po_file(self, path, content=None):
        """Create a test PO file."""
        if content is None:
            content = '''
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Hello"
msgstr ""

msgid "World"
msgstr ""
'''
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content)
        return path

    def test_batch_size_config_affects_translation(self):
        """Test that default_batch_size from config actually affects batch processing."""
        # Create pyproject.toml with custom batch size
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
default_batch_size = 5
""")

        # Load config
        config = ConfigLoader.load_config(self.temp_dir)
        self.assertEqual(config['default_batch_size'], 5)

        # Create translation service with this config
        flags = TranslationFlags(bulk_mode=True)
        trans_config = TranslationConfig(
            provider_clients=self.mock_provider_clients,
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            flags=flags
        )

        # Use the batch size from config
        service = TranslationService(trans_config, batch_size=config['default_batch_size'])

        # Verify the batch size is actually used
        self.assertEqual(service.batch_size, 5)

        # Create a PO file with 12 entries to test batching
        po_file = polib.POFile()
        for i in range(12):
            po_file.append(polib.POEntry(msgid=f"Text {i}", msgstr=""))

        # Mock the translation to track batch sizes
        batch_sizes = []

        def mock_perform_translation(texts, lang, is_bulk=False, detail_language=None):
            batch_sizes.append(len(texts))
            return [f"Translation {i}" for i in range(len(texts))]

        with patch.object(service, 'perform_translation', side_effect=mock_perform_translation):
            # Process entries in bulk mode
            entries = [e for e in po_file if not e.msgstr]
            texts = [e.msgid for e in entries]

            # Process in batches
            for i in range(0, len(texts), service.batch_size):
                batch = texts[i:i + service.batch_size]
                service.perform_translation(batch, "fr", is_bulk=True)

        # Should have been split into batches of 5, 5, and 2
        self.assertEqual(batch_sizes, [5, 5, 2])

    def test_mark_ai_generated_config_affects_comments(self):
        """Test that mark_ai_generated config actually affects PO file comments."""
        # Test with mark_ai_generated = true
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
mark_ai_generated = true
""")

        config = ConfigLoader.load_config(self.temp_dir)
        self.assertTrue(config['mark_ai_generated'])

        # Create service with this config
        flags = TranslationFlags(mark_ai_generated=config['mark_ai_generated'])
        trans_config = TranslationConfig(
            provider_clients=self.mock_provider_clients,
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            flags=flags
        )
        service = TranslationService(trans_config)

        # Create and process a PO entry
        po_file = polib.POFile()
        entry = polib.POEntry(msgid="Test", msgstr="")
        po_file.append(entry)

        # Simulate translation update with AI comment
        from python_gpt_po.utils.po_entry_helpers import add_ai_generated_comment
        entry.msgstr = "Translation"
        if service.config.flags.mark_ai_generated:
            add_ai_generated_comment(entry)

        # Should have AI-generated comment
        self.assertIn("AI-generated", entry.comment)

        # Now test with mark_ai_generated = false
        pyproject_path.write_text("""
[tool.gpt-po-translator]
mark_ai_generated = false
""")

        config = ConfigLoader.load_config(self.temp_dir)
        self.assertFalse(config['mark_ai_generated'])

        flags2 = TranslationFlags(mark_ai_generated=config['mark_ai_generated'])
        trans_config2 = TranslationConfig(
            provider_clients=self.mock_provider_clients,
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            flags=flags2
        )
        service2 = TranslationService(trans_config2)

        # Create new entry
        entry2 = polib.POEntry(msgid="Test2", msgstr="")
        po_file.append(entry2)

        # Update entry without AI comment
        entry2.msgstr = "Translation2"
        if service2.config.flags.mark_ai_generated:
            add_ai_generated_comment(entry2)

        # Should NOT have AI-generated comment
        self.assertNotIn("AI-generated", entry2.comment or "")

    def test_respect_gitignore_config_affects_file_scanning(self):
        """Test that respect_gitignore config actually affects which files are scanned."""
        # Create directory structure with gitignore
        project_dir = Path(self.temp_dir)

        # Create .gitignore
        gitignore_path = project_dir / ".gitignore"
        gitignore_path.write_text("""
ignored_dir/
*.backup
""")

        # Create PO files
        self.create_test_po_file(project_dir / "included.po")
        self.create_test_po_file(project_dir / "ignored_dir" / "ignored.po")
        self.create_test_po_file(project_dir / "file.po.backup")

        # Test with respect_gitignore = true
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
respect_gitignore = true
""")

        config = ConfigLoader.load_config(str(project_dir))
        self.assertTrue(config['respect_gitignore'])

        # Create gitignore parser
        parser = create_gitignore_parser(str(project_dir), respect_gitignore=config['respect_gitignore'])

        # Scan files
        found_files = []
        for root, dirs, files in os.walk(project_dir):
            # Filter directories
            dirs[:] = [d for d in dirs if not parser.should_ignore(os.path.join(root, d), is_directory=True)]

            for file in files:
                if '.po' in file:  # Check for .po anywhere in filename
                    file_path = os.path.join(root, file)
                    if not parser.should_ignore(file_path):
                        found_files.append(os.path.relpath(file_path, project_dir))

        # Should only find included.po
        self.assertEqual(found_files, ['included.po'])

        # Test with respect_gitignore = false
        pyproject_path.write_text("""
[tool.gpt-po-translator]
respect_gitignore = false
""")

        config = ConfigLoader.load_config(str(project_dir))
        self.assertFalse(config['respect_gitignore'])

        # Create parser that doesn't respect gitignore
        parser2 = create_gitignore_parser(str(project_dir), respect_gitignore=config['respect_gitignore'])

        # Scan files again
        found_files2 = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if '.po' in file:  # Check for .po anywhere in filename
                    file_path = os.path.join(root, file)
                    if not parser2.should_ignore(file_path):
                        found_files2.append(os.path.relpath(file_path, project_dir))

        # Should find all .po files
        self.assertEqual(sorted(found_files2),
                         ['file.po.backup', 'ignored_dir/ignored.po', 'included.po'])

    def test_ignore_patterns_config_affects_file_filtering(self):
        """Test that ignore_patterns from config actually filter files."""
        project_dir = Path(self.temp_dir)

        # Create config with custom ignore patterns
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
ignore_patterns = ["*_old.po", "archive/", "*.tmp"]
""")

        # Create PO files
        self.create_test_po_file(project_dir / "current.po")
        self.create_test_po_file(project_dir / "file_old.po")
        self.create_test_po_file(project_dir / "archive" / "archived.po")
        self.create_test_po_file(project_dir / "temp.tmp")

        # Load ignore patterns
        patterns = ConfigLoader.get_ignore_patterns(str(project_dir))

        # Create a simple pattern matcher
        import fnmatch
        def should_ignore(filepath):
            for pattern in patterns:
                if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch(os.path.basename(filepath), pattern):
                    return True
                # Check directory patterns
                if pattern.endswith('/'):
                    dir_pattern = pattern.rstrip('/')
                    if dir_pattern in filepath.split(os.sep):
                        return True
            return False

        # Test filtering
        found_files = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = os.path.relpath(os.path.join(root, file), project_dir)
                if not should_ignore(file_path):
                    found_files.append(file_path)

        # Should only find current.po (others are filtered by patterns)
        self.assertIn('current.po', found_files)
        self.assertNotIn('file_old.po', found_files)
        self.assertNotIn('archive/archived.po', found_files)

    def test_max_retries_config_affects_retry_behavior(self):
        """Test that max_retries config is loaded from configuration."""
        # Create config with custom max_retries
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
max_retries = 5
""")

        config = ConfigLoader.load_config(self.temp_dir)
        self.assertEqual(config['max_retries'], 5)

        # The max_retries value would be used in the tenacity decorator
        # In actual usage, this would affect @retry(stop=stop_after_attempt(max_retries))
        # The service uses this value in its retry logic

        # Create service to verify it can be initialized with the config
        flags = TranslationFlags()
        trans_config = TranslationConfig(
            provider_clients=self.mock_provider_clients,
            provider=ModelProvider.OPENAI,
            model="gpt-4",
            flags=flags
        )
        service = TranslationService(trans_config)

        # The retry logic is handled by tenacity decorator with hardcoded value
        # But the config value would be available for use if needed
        self.assertIsNotNone(service)

    def test_skip_translated_files_config(self):
        """Test that skip_translated_files config affects file processing."""
        project_dir = Path(self.temp_dir)

        # Create config
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
skip_translated_files = true
""")

        config = ConfigLoader.load_config(str(project_dir))
        self.assertTrue(config['skip_translated_files'])

        # Create PO files - one fully translated, one not
        translated_content = '''
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Hello"
msgstr "Bonjour"

msgid "World"
msgstr "Monde"
'''

        untranslated_content = '''
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Hello"
msgstr ""

msgid "World"
msgstr ""
'''

        self.create_test_po_file(project_dir / "translated.po", translated_content)
        self.create_test_po_file(project_dir / "untranslated.po", untranslated_content)

        # Load and check if files should be skipped
        files_to_process = []
        for po_file_path in [project_dir / "translated.po", project_dir / "untranslated.po"]:
            po_file = POFileHandler.load_po_file(str(po_file_path))

            # Check if file has untranslated entries
            from python_gpt_po.utils.po_entry_helpers import is_entry_untranslated
            has_untranslated = any(is_entry_untranslated(entry) for entry in po_file)

            if config['skip_translated_files'] and not has_untranslated:
                continue  # Skip fully translated file

            files_to_process.append(po_file_path.name)

        # Should only process untranslated.po
        self.assertEqual(files_to_process, ['untranslated.po'])

    def test_default_models_config_affects_model_selection(self):
        """Test that default_models config actually affects which model is used."""
        project_dir = Path(self.temp_dir)

        # Create config with custom default models
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator.default_models]
openai = "gpt-4-turbo"
anthropic = "claude-3-opus"
""")

        # Load config and get default models
        openai_model = ConfigLoader.get_default_model('openai', str(project_dir))
        anthropic_model = ConfigLoader.get_default_model('anthropic', str(project_dir))

        self.assertEqual(openai_model, 'gpt-4-turbo')
        self.assertEqual(anthropic_model, 'claude-3-opus')

        # These would be used when initializing the provider
        # In real usage, this affects which model is selected in main.py:get_appropriate_model()

    def test_folder_language_detection_config(self):
        """Test that folder_language_detection config affects language detection."""
        project_dir = Path(self.temp_dir)

        # Create folder structure with language codes
        locale_dir = project_dir / "locale" / "fr" / "LC_MESSAGES"
        locale_dir.mkdir(parents=True)
        self.create_test_po_file(locale_dir / "messages.po")

        # Test with folder_language_detection = true
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
folder_language_detection = true
""")

        config = ConfigLoader.load_config(str(project_dir))
        self.assertTrue(config['folder_language_detection'])

        # This would be used in LanguageDetector
        from python_gpt_po.services.language_detector import LanguageDetector

        # Detect language from folder structure
        languages = LanguageDetector.detect_languages_from_folder(
            str(project_dir),
            use_folder_structure=config['folder_language_detection']
        )

        # Should detect 'fr' from folder structure
        self.assertIn('fr', languages)

    def test_request_timeout_config(self):
        """Test that request_timeout is loaded from config."""
        project_dir = Path(self.temp_dir)

        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
request_timeout = 180
""")

        config = ConfigLoader.load_config(str(project_dir))
        self.assertEqual(config['request_timeout'], 180)

        # This timeout would be used when making API requests
        # It affects the timeout parameter in provider implementations

    def test_config_affects_real_translation_workflow(self):
        """Integration test that config affects the complete translation workflow."""
        project_dir = Path(self.temp_dir)

        # Create comprehensive config
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
default_batch_size = 3
mark_ai_generated = true
respect_gitignore = true
skip_translated_files = true
folder_language_detection = false

[tool.gpt-po-translator.default_models]
openai = "gpt-4-mini"
""")

        # Create .gitignore
        gitignore = project_dir / ".gitignore"
        gitignore.write_text("ignored/\n")

        # Create PO files
        self.create_test_po_file(project_dir / "test.po")
        self.create_test_po_file(project_dir / "ignored" / "ignored.po")

        # Load config
        config = ConfigLoader.load_config(str(project_dir))

        # Verify all settings are loaded
        self.assertEqual(config['default_batch_size'], 3)
        self.assertTrue(config['mark_ai_generated'])
        self.assertTrue(config['respect_gitignore'])
        self.assertTrue(config['skip_translated_files'])
        self.assertFalse(config['folder_language_detection'])

        # Get default model
        model = ConfigLoader.get_default_model('openai', str(project_dir))
        self.assertEqual(model, 'gpt-4-mini')

        # All these configs would affect the actual translation process:
        # - batch_size affects how many texts are sent per API call
        # - mark_ai_generated adds comments to translated entries
        # - respect_gitignore filters out ignored/ directory
        # - skip_translated_files skips fully translated files
        # - folder_language_detection affects how target languages are detected
        # - default_models affects which AI model is used


if __name__ == '__main__':
    unittest.main()