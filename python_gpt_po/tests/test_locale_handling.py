"""Tests for locale code handling in po_file_handler.py"""

import os
import tempfile

import polib

from python_gpt_po.services.po_file_handler import POFileHandler


class TestLocaleHandling:
    """Test suite for locale code normalization and matching"""

    def test_regular_language_codes(self):
        """Test that regular 2-letter ISO codes still work"""
        test_cases = [
            ('fr', 'fr'),
            ('en', 'en'),
            ('de', 'de'),
            ('es', 'es'),
            ('pt', 'pt'),
            ('it', 'it'),
            ('nl', 'nl'),
            ('ja', 'ja'),
            ('zh', 'zh'),
        ]

        for input_code, expected in test_cases:
            result = POFileHandler.normalize_language_code(input_code)
            assert result == expected, f"Failed for {input_code}: got {result}, expected {expected}"

    def test_locale_codes_with_underscore(self):
        """Test locale codes with underscore separator (e.g., fr_CA)"""
        test_cases = [
            ('fr_CA', 'fr'),
            ('fr_FR', 'fr'),
            ('en_US', 'en'),
            ('en_GB', 'en'),
            ('pt_BR', 'pt'),
            ('pt_PT', 'pt'),
            ('es_ES', 'es'),
            ('es_MX', 'es'),
            ('zh_CN', 'zh'),
            ('zh_TW', 'zh'),
        ]

        for input_code, expected in test_cases:
            result = POFileHandler.normalize_language_code(input_code)
            assert result == expected, f"Failed for {input_code}: got {result}, expected {expected}"

    def test_locale_codes_with_dash(self):
        """Test locale codes with dash separator (e.g., fr-CA)"""
        test_cases = [
            ('fr-CA', 'fr'),
            ('fr-FR', 'fr'),
            ('en-US', 'en'),
            ('en-GB', 'en'),
            ('pt-BR', 'pt'),
            ('es-MX', 'es'),
            ('zh-CN', 'zh'),
        ]

        for input_code, expected in test_cases:
            result = POFileHandler.normalize_language_code(input_code)
            assert result == expected, f"Failed for {input_code}: got {result}, expected {expected}"

    def test_language_names(self):
        """Test that language names still work"""
        test_cases = [
            ('French', 'fr'),
            ('English', 'en'),
            ('German', 'de'),
            ('Spanish', 'es'),
            ('Portuguese', 'pt'),
            ('Italian', 'it'),
            ('Dutch', 'nl'),
            ('Japanese', 'ja'),
            ('Chinese', 'zh'),
        ]

        for input_name, expected in test_cases:
            result = POFileHandler.normalize_language_code(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"

    def test_case_insensitive_names(self):
        """Test that language names work regardless of case"""
        test_cases = [
            ('french', 'fr'),
            ('FRENCH', 'fr'),
            ('French', 'fr'),
            ('english', 'en'),
            ('ENGLISH', 'en'),
            ('English', 'en'),
        ]

        for input_name, expected in test_cases:
            result = POFileHandler.normalize_language_code(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"

    def test_invalid_codes(self):
        """Test that invalid codes return None"""
        test_cases = [
            'invalid',
            'xx',
            'xyz',
            '123',
            '',
            None,
            'xx_YY',
            'invalid-CODE',
        ]

        for input_code in test_cases:
            result = POFileHandler.normalize_language_code(input_code)
            assert result is None, f"Expected None for {input_code}, got {result}"

    def test_complex_locale_codes(self):
        """Test more complex locale codes"""
        test_cases = [
            ('fr_CA.UTF-8', 'fr'),  # With encoding
            ('en_US.utf8', 'en'),   # With encoding variant
            ('pt_BR@euro', 'pt'),   # With currency modifier
            ('zh_CN.GB2312', 'zh'),  # With specific encoding
        ]

        for input_code, expected in test_cases:
            # These should extract the base language part
            result = POFileHandler.normalize_language_code(input_code)
            assert result == expected, f"Failed for {input_code}: got {result}, expected {expected}"

    def test_get_file_language_exact_match(self):
        """Test that get_file_language matches exact locale codes"""
        with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as f:
            po_file = polib.POFile()
            po_file.metadata = {'Language': 'fr_CA'}
            po_file.save(f.name)

            # Reload to test
            po_file = POFileHandler.load_po_file(f.name)

            # Test exact match
            result = POFileHandler.get_file_language(f.name, po_file, ['fr_CA'], False)
            assert result == 'fr_CA', f"Expected exact match fr_CA, got {result}"

            # Test hyphen variant
            result = POFileHandler.get_file_language(f.name, po_file, ['fr-CA'], False)
            assert result == 'fr-CA', f"Expected hyphen variant match fr-CA, got {result}"

            # Test base language fallback
            result = POFileHandler.get_file_language(f.name, po_file, ['fr'], False)
            assert result == 'fr', f"Expected base language fallback fr, got {result}"

            # Test no match
            result = POFileHandler.get_file_language(f.name, po_file, ['en'], False)
            assert result is None, f"Expected no match for en, got {result}"

            os.unlink(f.name)

    def test_get_file_language_underscore_hyphen_conversion(self):
        """Test conversion between underscore and hyphen formats"""
        with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as f:
            po_file = polib.POFile()

            # Test file with underscore, request with hyphen
            po_file.metadata = {'Language': 'pt_BR'}
            po_file.save(f.name)
            po_file = POFileHandler.load_po_file(f.name)

            result = POFileHandler.get_file_language(f.name, po_file, ['pt-BR'], False)
            assert result == 'pt-BR', f"Expected pt_BR to match pt-BR, got {result}"

            # Test file with hyphen, request with underscore
            po_file.metadata = {'Language': 'pt-BR'}
            po_file.save(f.name)
            po_file = POFileHandler.load_po_file(f.name)

            result = POFileHandler.get_file_language(f.name, po_file, ['pt_BR'], False)
            assert result == 'pt_BR', f"Expected pt-BR to match pt_BR, got {result}"

            os.unlink(f.name)

    def test_folder_language_detection(self):
        """Test language detection from folder structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test cases: (folder_name, requested_languages, expected_result)
            test_cases = [
                # Exact matches
                ('fr', ['fr'], 'fr'),
                ('fr_CA', ['fr_CA'], 'fr_CA'),
                ('fr-CA', ['fr-CA'], 'fr-CA'),

                # Format conversions
                ('fr_CA', ['fr-CA'], 'fr-CA'),
                ('fr-CA', ['fr_CA'], 'fr_CA'),

                # Base language fallbacks
                ('fr_CA', ['fr'], 'fr'),
                ('fr-CA', ['fr'], 'fr'),
                ('pt_BR', ['pt'], 'pt'),

                # No matches
                ('fr_CA', ['en'], None),
                ('es', ['fr'], None),
            ]

            for folder_name, languages, expected in test_cases:
                # Create folder and po file
                folder_path = os.path.join(tmpdir, folder_name)
                os.makedirs(folder_path, exist_ok=True)
                po_file_path = os.path.join(folder_path, 'test.po')

                po_file = polib.POFile()
                po_file.metadata = {}  # No language metadata
                po_file.save(po_file_path)

                # Test with folder language detection
                po_file = POFileHandler.load_po_file(po_file_path)
                result = POFileHandler.get_file_language(
                    po_file_path, po_file, languages, folder_language=True
                )

                assert result == expected, (
                    f"Folder {folder_name} with languages {languages}: "
                    f"expected {expected}, got {result}"
                )

                # Clean up
                os.unlink(po_file_path)
                os.rmdir(folder_path)

    def test_nested_folder_language_detection(self):
        """Test language detection from nested folder structures"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test nested paths
            test_cases = [
                ('locales/fr_CA', ['fr_CA'], 'fr_CA'),
                ('i18n/fr-CA/LC_MESSAGES', ['fr-CA'], 'fr-CA'),
                ('translations/fr/messages', ['fr'], 'fr'),
                ('locale/pt_BR/LC_MESSAGES', ['pt'], 'pt'),
            ]

            for folder_path, languages, expected in test_cases:
                full_path = os.path.join(tmpdir, folder_path)
                os.makedirs(full_path, exist_ok=True)
                po_file_path = os.path.join(full_path, 'messages.po')

                po_file = polib.POFile()
                po_file.metadata = {}
                po_file.save(po_file_path)

                po_file = POFileHandler.load_po_file(po_file_path)
                result = POFileHandler.get_file_language(
                    po_file_path, po_file, languages, folder_language=True
                )

                assert result == expected, (
                    f"Path {folder_path} with languages {languages}: "
                    f"expected {expected}, got {result}"
                )
