"""
Tests for language auto-detection from PO files.
"""

import os
import tempfile
import unittest

import polib

from python_gpt_po.services.language_detector import LanguageDetector


class TestLanguageDetector(unittest.TestCase):
    """Test language detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_po_file(self, filename, language=None, locale_code=False):
        """Create a test PO file with optional language metadata."""
        po_file = polib.POFile()

        if language:
            po_file.metadata = {
                'Language': language,
                'Content-Type': 'text/plain; charset=utf-8',
            }
        else:
            po_file.metadata = {
                'Content-Type': 'text/plain; charset=utf-8',
            }

        # Add a sample entry
        entry = polib.POEntry(
            msgid="Hello",
            msgstr=""
        )
        po_file.append(entry)

        # Create subdirectory if needed
        if '/' in filename:
            subdir = os.path.dirname(filename)
            os.makedirs(os.path.join(self.temp_dir, subdir), exist_ok=True)

        po_path = os.path.join(self.temp_dir, filename)
        po_file.save(po_path)
        return po_path

    def test_detect_single_language(self):
        """Test detecting a single language from PO file."""
        self.create_po_file("messages.po", language="fr")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        self.assertEqual(languages, ["fr"])

    def test_detect_multiple_languages(self):
        """Test detecting multiple languages from different PO files."""
        self.create_po_file("french.po", language="fr")
        self.create_po_file("german.po", language="de")
        self.create_po_file("spanish.po", language="es")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        # Should be sorted
        self.assertEqual(languages, ["de", "es", "fr"])

    def test_detect_locale_codes(self):
        """Test detecting locale codes like fr_CA, pt_BR."""
        self.create_po_file("canadian.po", language="fr_CA")
        self.create_po_file("brazilian.po", language="pt_BR")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        # Should include locale codes
        self.assertIn("fr_CA", languages)
        self.assertIn("pt_BR", languages)
        # Should detect exactly what's in the files
        self.assertEqual(sorted(languages), ["fr_CA", "pt_BR"])

    def test_detect_hyphenated_locale_codes(self):
        """Test detecting locale codes with hyphens like en-US."""
        self.create_po_file("american.po", language="en-US")
        self.create_po_file("british.po", language="en-GB")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        # Should handle hyphenated codes
        self.assertIn("en-US", languages)
        self.assertIn("en-GB", languages)
        self.assertEqual(sorted(languages), ["en-GB", "en-US"])

    def test_no_po_files(self):
        """Test error when no PO files found."""
        with self.assertRaises(ValueError) as context:
            LanguageDetector.detect_languages_from_folder(self.temp_dir)

        self.assertIn("No .po files found", str(context.exception))

    def test_no_language_metadata(self):
        """Test error when PO files have no language metadata."""
        self.create_po_file("nolang1.po", language=None)
        self.create_po_file("nolang2.po", language=None)

        with self.assertRaises(ValueError) as context:
            LanguageDetector.detect_languages_from_folder(self.temp_dir)

        self.assertIn("Could not detect any languages", str(context.exception))
        self.assertIn("use -l to specify", str(context.exception))

    def test_mixed_files_with_and_without_language(self):
        """Test detection when some files have language and others don't."""
        self.create_po_file("with_lang.po", language="fr")
        self.create_po_file("without_lang.po", language=None)

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        # Should still detect fr from the file that has it
        self.assertEqual(languages, ["fr"])

    def test_subdirectories(self):
        """Test detecting languages from PO files in subdirectories."""
        self.create_po_file("locales/fr/messages.po", language="fr")
        self.create_po_file("locales/de/messages.po", language="de")
        self.create_po_file("i18n/es.po", language="es")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        self.assertEqual(languages, ["de", "es", "fr"])

    def test_duplicate_languages(self):
        """Test that duplicate languages are only listed once."""
        self.create_po_file("file1.po", language="fr")
        self.create_po_file("file2.po", language="fr")
        self.create_po_file("file3.po", language="fr")

        languages = LanguageDetector.detect_languages_from_folder(self.temp_dir)

        # Should only have one "fr"
        self.assertEqual(languages, ["fr"])

    def test_validate_or_detect_with_lang_arg(self):
        """Test that provided languages are used when specified."""
        # Create files with different languages
        self.create_po_file("french.po", language="fr")
        self.create_po_file("german.po", language="de")

        # But specify different languages via args
        languages = LanguageDetector.validate_or_detect_languages(
            self.temp_dir,
            lang_arg="es,it,pt"
        )

        # Should use the specified languages, not detected ones
        self.assertEqual(languages, ["es", "it", "pt"])

    def test_validate_or_detect_without_lang_arg(self):
        """Test auto-detection when no languages specified."""
        self.create_po_file("french.po", language="fr")
        self.create_po_file("german.po", language="de")

        languages = LanguageDetector.validate_or_detect_languages(
            self.temp_dir,
            lang_arg=None  # No languages specified
        )

        # Should auto-detect
        self.assertEqual(languages, ["de", "fr"])

    def test_empty_language_metadata(self):
        """Test handling of empty language string in metadata."""
        po_file = polib.POFile()
        po_file.metadata = {
            'Language': '',  # Empty string
            'Content-Type': 'text/plain; charset=utf-8',
        }
        po_file.append(polib.POEntry(msgid="Test", msgstr=""))
        po_path = os.path.join(self.temp_dir, "empty_lang.po")
        po_file.save(po_path)

        with self.assertRaises(ValueError) as context:
            LanguageDetector.detect_languages_from_folder(self.temp_dir)

        self.assertIn("Could not detect any languages", str(context.exception))


if __name__ == '__main__':
    unittest.main()
