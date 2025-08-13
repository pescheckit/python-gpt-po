"""
Tests for configuration loading from pyproject.toml files.
"""

import os
import tempfile
import unittest
from pathlib import Path

from python_gpt_po.utils.config_loader import ConfigLoader


class TestConfigLoader(unittest.TestCase):
    """Test configuration loading from pyproject.toml."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

    def tearDown(self):
        """Clean up test fixtures."""
        os.chdir(self.original_cwd)
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_default_config_when_no_pyproject_toml(self):
        """Test that default configuration is loaded when no pyproject.toml exists."""
        # Change to temp directory with no pyproject.toml
        os.chdir(self.temp_dir)

        config = ConfigLoader.load_config(self.temp_dir)

        # Check that default values are loaded
        self.assertEqual(config['default_verbosity'], 1)
        self.assertEqual(config['default_batch_size'], 50)
        self.assertEqual(config['default_bulk_mode'], False)
        self.assertTrue(config['mark_ai_generated'])
        self.assertTrue(config['respect_gitignore'])
        self.assertFalse(config['folder_language_detection'])
        self.assertEqual(config['max_retries'], 3)
        self.assertEqual(config['request_timeout'], 120)

    def test_load_config_from_pyproject_toml(self):
        """Test that configuration is loaded from pyproject.toml when it exists."""
        # Create a pyproject.toml with custom configuration
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_content = """
[tool.gpt-po-translator]
respect_gitignore = false
default_batch_size = 100
mark_ai_generated = false
folder_language_detection = true
max_retries = 5
request_timeout = 180
custom_setting = "test_value"

[tool.gpt-po-translator.default_models]
openai = "gpt-4"
anthropic = "claude-3-opus"
"""
        pyproject_path.write_text(pyproject_content)

        config = ConfigLoader.load_config(self.temp_dir)

        # Check that custom values override defaults
        self.assertFalse(config['respect_gitignore'])
        self.assertEqual(config['default_batch_size'], 100)
        self.assertFalse(config['mark_ai_generated'])
        self.assertTrue(config['folder_language_detection'])
        self.assertEqual(config['max_retries'], 5)
        self.assertEqual(config['request_timeout'], 180)
        self.assertEqual(config['custom_setting'], 'test_value')

        # Check that non-overridden defaults are still present
        self.assertEqual(config['default_verbosity'], 1)  # Not overridden
        self.assertEqual(config['default_bulk_mode'], False)  # Not overridden

    def test_load_config_from_parent_directory(self):
        """Test that configuration is loaded from parent directory's pyproject.toml."""
        # Create parent directory with pyproject.toml
        parent_pyproject = Path(self.temp_dir) / "pyproject.toml"
        parent_pyproject.write_text("""
[tool.gpt-po-translator]
default_batch_size = 75
parent_config = true
""")

        # Create subdirectory
        subdir = Path(self.temp_dir) / "subdir" / "nested"
        subdir.mkdir(parents=True)

        # Load config from subdirectory
        config = ConfigLoader.load_config(str(subdir))

        # Should find parent's pyproject.toml
        self.assertEqual(config['default_batch_size'], 75)
        self.assertTrue(config['parent_config'])

    def test_config_precedence_closer_overrides_parent(self):
        """Test that closer pyproject.toml takes precedence over parent directory config."""
        # Create parent directory with pyproject.toml
        parent_pyproject = Path(self.temp_dir) / "pyproject.toml"
        parent_pyproject.write_text("""
[tool.gpt-po-translator]
default_batch_size = 75
mark_ai_generated = false
parent_only = "parent_value"
""")

        # Create subdirectory with its own pyproject.toml
        subdir = Path(self.temp_dir) / "subdir"
        subdir.mkdir()
        child_pyproject = subdir / "pyproject.toml"
        child_pyproject.write_text("""
[tool.gpt-po-translator]
default_batch_size = 25
mark_ai_generated = false
child_only = "child_value"
parent_only = "child_override"
""")

        # Load config from subdirectory
        config = ConfigLoader.load_config(str(subdir))

        # Child config should be used (closer file takes precedence)
        self.assertEqual(config['default_batch_size'], 25)
        self.assertFalse(config['mark_ai_generated'])
        self.assertEqual(config['child_only'], 'child_value')
        self.assertEqual(config['parent_only'], 'child_override')

        # Now test with subdir that has no pyproject.toml
        subdir2 = Path(self.temp_dir) / "subdir2"
        subdir2.mkdir()

        # Load config from subdir2 (should find parent's config)
        config2 = ConfigLoader.load_config(str(subdir2))

        # Should use parent's config
        self.assertEqual(config2['default_batch_size'], 75)
        self.assertFalse(config2['mark_ai_generated'])
        self.assertEqual(config2['parent_only'], 'parent_value')

    def test_ignore_patterns_from_config(self):
        """Test that ignore patterns are loaded from configuration."""
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
ignore_patterns = ["*.backup", "temp_*", "old/"]
""")

        patterns = ConfigLoader.get_ignore_patterns(self.temp_dir)

        # Should include both default and custom patterns
        self.assertIn("*.backup", patterns)
        self.assertIn("temp_*", patterns)
        self.assertIn("old/", patterns)
        # Default patterns should still be included
        self.assertIn("__pycache__/", patterns)
        self.assertIn(".git/", patterns)

    def test_respect_gitignore_from_config(self):
        """Test that respect_gitignore setting is loaded from configuration."""
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"

        # Test with gitignore disabled in config
        pyproject_path.write_text("""
[tool.gpt-po-translator]
respect_gitignore = false
""")

        should_respect = ConfigLoader.should_respect_gitignore(self.temp_dir)
        self.assertFalse(should_respect)

        # Test with gitignore enabled in config
        pyproject_path.write_text("""
[tool.gpt-po-translator]
respect_gitignore = true
""")

        should_respect = ConfigLoader.should_respect_gitignore(self.temp_dir)
        self.assertTrue(should_respect)

        # Test override parameter
        should_respect = ConfigLoader.should_respect_gitignore(self.temp_dir, override=False)
        self.assertFalse(should_respect)

    def test_get_default_model_from_config(self):
        """Test that default models are loaded from configuration."""
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator.default_models]
openai = "gpt-4-turbo"
anthropic = "claude-3-sonnet"
custom_provider = "custom-model"
""")

        # Test getting models for different providers
        openai_model = ConfigLoader.get_default_model('openai', self.temp_dir)
        self.assertEqual(openai_model, 'gpt-4-turbo')

        anthropic_model = ConfigLoader.get_default_model('anthropic', self.temp_dir)
        self.assertEqual(anthropic_model, 'claude-3-sonnet')

        custom_model = ConfigLoader.get_default_model('custom_provider', self.temp_dir)
        self.assertEqual(custom_model, 'custom-model')

        # Test non-existent provider returns None
        none_model = ConfigLoader.get_default_model('nonexistent', self.temp_dir)
        self.assertIsNone(none_model)

    def test_empty_tool_section_uses_defaults(self):
        """Test that empty [tool.gpt-po-translator] section uses defaults."""
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator]
# Empty section
""")

        config = ConfigLoader.load_config(self.temp_dir)

        # Should still have all defaults
        self.assertEqual(config['default_verbosity'], 1)
        self.assertEqual(config['default_batch_size'], 50)
        self.assertTrue(config['respect_gitignore'])

    def test_invalid_toml_file_uses_defaults(self):
        """Test that invalid TOML file doesn't crash and uses defaults."""
        pyproject_path = Path(self.temp_dir) / "pyproject.toml"
        pyproject_path.write_text("""
[tool.gpt-po-translator
This is invalid TOML
""")

        config = ConfigLoader.load_config(self.temp_dir)

        # Should fall back to defaults
        self.assertEqual(config['default_batch_size'], 50)

    def test_config_in_real_project_structure(self):
        """Test configuration loading in a realistic project structure."""
        # Create a project structure
        project_root = Path(self.temp_dir) / "my_project"
        project_root.mkdir()

        # Create project pyproject.toml
        (project_root / "pyproject.toml").write_text("""
[project]
name = "my-project"
version = "0.1.0"

[tool.gpt-po-translator]
default_batch_size = 30
mark_ai_generated = true
project_specific = "yes"
""")

        # Create locale directory structure
        locale_dir = project_root / "locale" / "fr" / "LC_MESSAGES"
        locale_dir.mkdir(parents=True)

        # Create a PO file
        po_file = locale_dir / "messages.po"
        po_file.write_text("""
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Hello"
msgstr ""
""")

        # Load config from the locale directory
        config = ConfigLoader.load_config(str(locale_dir))

        # Should find the project root's pyproject.toml
        self.assertEqual(config['default_batch_size'], 30)
        self.assertTrue(config['mark_ai_generated'])
        self.assertEqual(config['project_specific'], 'yes')

    def test_docker_volume_paths_detection(self):
        """Test that Docker volume paths are detected correctly."""
        # Test various Docker volume paths
        self.assertTrue(ConfigLoader._is_docker_volume_path(Path("/data")))
        self.assertTrue(ConfigLoader._is_docker_volume_path(Path("/workspace")))
        self.assertTrue(ConfigLoader._is_docker_volume_path(Path("/translations")))
        self.assertTrue(ConfigLoader._is_docker_volume_path(Path("/locales")))

        # Test non-Docker paths
        self.assertFalse(ConfigLoader._is_docker_volume_path(Path("/home/user")))
        self.assertFalse(ConfigLoader._is_docker_volume_path(Path("/usr/local")))

    def test_scan_folder_and_use_its_config(self):
        """Test the main use case: scanning a folder and using its config."""
        # This simulates the actual usage where we scan a folder for PO files
        # and want to use the configuration from that folder's pyproject.toml

        # Create a project with custom config
        project_dir = Path(self.temp_dir) / "translation_project"
        project_dir.mkdir()

        # Create custom configuration
        (project_dir / "pyproject.toml").write_text("""
[tool.gpt-po-translator]
respect_gitignore = false
default_batch_size = 100
mark_ai_generated = false
skip_translated_files = false
show_progress = false

[tool.gpt-po-translator.default_models]
openai = "gpt-4"
""")

        # Create PO files structure
        po_dir = project_dir / "translations"
        po_dir.mkdir()
        (po_dir / "messages.po").write_text("""
msgid ""
msgstr ""
"Language: fr\\n"

msgid "Test"
msgstr ""
""")

        # Simulate scanning from po_dir and loading its config
        config = ConfigLoader.load_config(str(po_dir))

        # Verify that the configuration from project root is used
        self.assertFalse(config['respect_gitignore'])
        self.assertEqual(config['default_batch_size'], 100)
        self.assertFalse(config['mark_ai_generated'])
        self.assertFalse(config['skip_translated_files'])
        self.assertFalse(config['show_progress'])

        # Verify model configuration
        model = ConfigLoader.get_default_model('openai', str(po_dir))
        self.assertEqual(model, 'gpt-4')


if __name__ == '__main__':
    unittest.main()