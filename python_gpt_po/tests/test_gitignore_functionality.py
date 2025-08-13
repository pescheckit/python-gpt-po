"""
Tests for gitignore functionality.
"""
import tempfile
import unittest
from pathlib import Path

from python_gpt_po.utils.config_loader import ConfigLoader
from python_gpt_po.utils.gitignore import GitignoreParser, create_gitignore_parser


class TestGitignoreParser(unittest.TestCase):
    """Test gitignore pattern parsing and filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_default_patterns_ignore_venv(self):
        """Test that .venv directories are ignored by default."""
        # Create directory structure
        venv_dir = self.temp_path / ".venv" / "lib" / "python3.12"
        venv_dir.mkdir(parents=True)

        regular_dir = self.temp_path / "src"
        regular_dir.mkdir()

        # Create parser
        parser = GitignoreParser(str(self.temp_path))

        # Test ignoring
        self.assertTrue(parser.should_ignore(str(venv_dir), is_directory=True))
        self.assertFalse(parser.should_ignore(str(regular_dir), is_directory=True))

    def test_default_patterns_ignore_node_modules(self):
        """Test that node_modules directories are ignored by default."""
        # Create directory structure
        node_modules_dir = self.temp_path / "node_modules"
        node_modules_dir.mkdir()

        src_dir = self.temp_path / "src"
        src_dir.mkdir()

        # Create parser
        parser = GitignoreParser(str(self.temp_path))

        # Test ignoring
        self.assertTrue(parser.should_ignore(str(node_modules_dir), is_directory=True))
        self.assertFalse(parser.should_ignore(str(src_dir), is_directory=True))

    def test_gitignore_file_parsing(self):
        """Test parsing of .gitignore files."""
        # Create .gitignore file
        gitignore_content = """
# Comments should be ignored
*.pyc
__pycache__/
build/
.env

# Negation pattern
!important.pyc
"""
        gitignore_path = self.temp_path / ".gitignore"
        gitignore_path.write_text(gitignore_content)

        # Create test files
        (self.temp_path / "test.pyc").touch()
        (self.temp_path / "important.pyc").touch()

        build_dir = self.temp_path / "build"
        build_dir.mkdir()

        # Create parser
        parser = GitignoreParser(str(self.temp_path))

        # Test pattern matching
        self.assertTrue(parser.should_ignore(str(self.temp_path / "test.pyc"), is_directory=False))
        self.assertFalse(parser.should_ignore(str(self.temp_path / "important.pyc"), is_directory=False))  # Negated
        self.assertTrue(parser.should_ignore(str(build_dir), is_directory=True))

    def test_respect_gitignore_override(self):
        """Test that gitignore can be disabled via override."""
        # Create .gitignore file
        gitignore_path = self.temp_path / ".gitignore"
        gitignore_path.write_text("*.pyc\n")

        # Create test file
        test_file = self.temp_path / "test.pyc"
        test_file.touch()

        # Test with gitignore enabled (default)
        parser_enabled = GitignoreParser(str(self.temp_path), respect_gitignore=True)
        self.assertTrue(parser_enabled.should_ignore(str(test_file), is_directory=False))

        # Test with gitignore disabled
        parser_disabled = GitignoreParser(str(self.temp_path), respect_gitignore=False)
        # Should still ignore due to default config patterns, but not gitignore patterns
        # Since *.pyc is in default config, let's test with a pattern only in .gitignore
        gitignore_path.write_text("custom_pattern.txt\n")
        custom_file = self.temp_path / "custom_pattern.txt"
        custom_file.touch()

        parser_enabled = GitignoreParser(str(self.temp_path), respect_gitignore=True)
        parser_disabled = GitignoreParser(str(self.temp_path), respect_gitignore=False)

        self.assertTrue(parser_enabled.should_ignore(str(custom_file), is_directory=False))
        self.assertFalse(parser_disabled.should_ignore(str(custom_file), is_directory=False))

    def test_filter_walk_results(self):
        """Test filtering of os.walk results."""
        # Create directory structure
        (self.temp_path / ".venv").mkdir()
        (self.temp_path / "src").mkdir()
        (self.temp_path / "node_modules").mkdir()

        # Create files
        (self.temp_path / "src" / "test.py").touch()
        (self.temp_path / "src" / "test.pyc").touch()
        (self.temp_path / ".venv" / "ignored.py").touch()

        parser = GitignoreParser(str(self.temp_path))

        # Test filtering
        dirs = [".venv", "src", "node_modules"]
        files = ["readme.txt"]

        filtered_dirs, filtered_files = parser.filter_walk_results(str(self.temp_path), dirs, files)

        # .venv and node_modules should be removed from dirs
        self.assertIn("src", dirs)  # Should remain
        self.assertNotIn(".venv", dirs)  # Should be removed
        self.assertNotIn("node_modules", dirs)  # Should be removed

    def test_create_gitignore_parser_function(self):
        """Test the convenience function for creating parsers."""
        parser = create_gitignore_parser(str(self.temp_path))
        self.assertIsInstance(parser, GitignoreParser)

        parser_disabled = create_gitignore_parser(str(self.temp_path), respect_gitignore=False)
        self.assertIsInstance(parser_disabled, GitignoreParser)


class TestConfigLoader(unittest.TestCase):
    """Test configuration loading functionality."""

    def test_should_respect_gitignore_override(self):
        """Test gitignore override functionality."""
        # Test default behavior
        self.assertTrue(ConfigLoader.should_respect_gitignore())

        # Test override
        self.assertFalse(ConfigLoader.should_respect_gitignore(override=False))
        self.assertTrue(ConfigLoader.should_respect_gitignore(override=True))


if __name__ == '__main__':
    unittest.main()
