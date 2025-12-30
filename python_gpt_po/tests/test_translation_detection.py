"""
Consolidated tests for translation detection logic.
This replaces multiple overlapping test files with focused, comprehensive tests.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import polib

from python_gpt_po.models.config import TranslationConfig, TranslationFlags
from python_gpt_po.models.enums import ModelProvider
from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.services.translation_service import TranslationService
from python_gpt_po.utils.po_entry_helpers import get_all_untranslated_entries, is_entry_untranslated


class TestTranslationDetection(unittest.TestCase):
    """
    Test translation detection for various PO entry types.
    Consolidates tests from test_duplicate_msgid, test_plural_handling, etc.
    """

    def test_detection_logic_matrix(self):
        """
        Comprehensive test matrix for all entry types and states.
        This single test replaces multiple redundant tests.
        """
        test_cases = [
            # (description, entry_dict, should_need_translation)

            # Regular entries
            ("empty regular entry",
             {"msgid": "Hello", "msgstr": ""},
             True),

            ("translated regular entry",
             {"msgid": "Hello", "msgstr": "Bonjour"},
             False),

            ("whitespace-only msgstr",
             {"msgid": "Hello", "msgstr": "   "},
             True),

            ("no msgid (header)",
             {"msgid": "", "msgstr": "headers here..."},
             False),

            # Plural entries
            ("fully translated plural (2 forms)",
             {"msgid": "1 file", "msgid_plural": "%d files",
              "msgstr_plural": {0: "1 fichier", 1: "%d fichiers"}},
             False),

            ("partially translated plural",
             {"msgid": "1 file", "msgid_plural": "%d files",
              "msgstr_plural": {0: "1 fichier", 1: ""}},
             False),  # Changed: partially translated plurals are NOT untranslated

            ("empty plural forms",
             {"msgid": "1 file", "msgid_plural": "%d files",
              "msgstr_plural": {0: "", 1: ""}},
             True),

            ("3-form plural (Serbian style) - all filled",
             {"msgid": "1 item", "msgid_plural": "%d items",
              "msgstr_plural": {0: "форма1", 1: "форма2", 2: "форма3"}},
             False),

            ("3-form plural - one empty",
             {"msgid": "1 item", "msgid_plural": "%d items",
              "msgstr_plural": {0: "форма1", 1: "", 2: "форма3"}},
             False),  # Changed: partially translated plurals are NOT untranslated
        ]

        for description, entry_dict, expected in test_cases:
            with self.subTest(description=description):
                entry = polib.POEntry(**entry_dict)
                result = is_entry_untranslated(entry)
                self.assertEqual(result, expected,
                                 f"Failed for {description}: expected {expected}, got {result}")

    def test_real_world_po_file_scenarios(self):
        """
        Test with actual PO file content patterns from WordPress, Django, etc.
        """
        po_content = """msgid ""
msgstr ""
"Language: fr\\n"
"Plural-Forms: nplurals=2; plural=(n > 1);\\n"

# Already translated
msgid "Welcome"
msgstr "Bienvenue"

# Needs translation
msgid "Goodbye"
msgstr ""

# Plural - fully translated
msgid "%d comment"
msgid_plural "%d comments"
msgstr[0] "%d commentaire"
msgstr[1] "%d commentaires"

# Plural - needs translation
msgid "%d post"
msgid_plural "%d posts"
msgstr[0] ""
msgstr[1] ""

# Context entry - translated
msgctxt "menu"
msgid "Home"
msgstr "Accueil"

# Context entry - needs translation
msgctxt "button"
msgid "Submit"
msgstr ""
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            f.write(po_content)
            po_path = f.name

        try:
            po_file = POFileHandler.load_po_file(po_path)
            untranslated = get_all_untranslated_entries(po_file)
            untranslated_msgids = [e.msgid for e in untranslated]

            # Should identify exactly these as needing translation
            expected_untranslated = ["Goodbye", "%d post", "Submit"]
            self.assertEqual(sorted(untranslated_msgids), sorted(expected_untranslated))

            # Should NOT include these
            should_not_translate = ["Welcome", "%d comment", "Home"]
            for msgid in should_not_translate:
                self.assertNotIn(msgid, untranslated_msgids)

        finally:
            os.unlink(po_path)


class TestTranslationProcessing(unittest.TestCase):
    """
    Test the actual translation processing logic.
    Consolidates interrupt handling and mode-specific tests.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.config = TranslationConfig(
            provider=ModelProvider.OPENAI,
            model="gpt-3.5-turbo",
            provider_clients={"openai": MagicMock()},
            flags=TranslationFlags(
                bulk_mode=False,
                fuzzy=False,
                fix_fuzzy=False,
                folder_language=False,
                mark_ai_generated=True
            )
        )
        self.service = TranslationService(self.config, batch_size=10)

    def test_duplicate_msgid_handling(self):
        """
        Test that entries with same msgid but different contexts are handled correctly.
        This replaces the entire test_duplicate_msgid.py file.
        """
        po_content = """msgid ""
msgstr ""
"Language: fr\\n"

# Same msgid, different locations
#: page1.php:10
msgid "Save"
msgstr ""

#: page2.php:20
msgid "Save"
msgstr ""

#: page3.php:30
msgid "Cancel"
msgstr ""
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            f.write(po_content)
            po_path = f.name

        try:
            po_file = POFileHandler.load_po_file(po_path)

            # Get entries to translate
            entries_to_translate = [e for e in po_file if is_entry_untranslated(e)]

            # Should have 3 entries (2 "Save" + 1 "Cancel")
            self.assertEqual(len(entries_to_translate), 3)

            # Simulate translating only first "Save"
            entries_to_translate[0].msgstr = "Enregistrer"
            po_file.save(po_path)

            # Reload and check
            po_file = POFileHandler.load_po_file(po_path)
            save_entries = [e for e in po_file if e.msgid == "Save"]

            # One should be translated, one should not
            translated_saves = [e for e in save_entries if e.msgstr.strip()]
            untranslated_saves = [e for e in save_entries if not e.msgstr.strip()]

            self.assertEqual(len(translated_saves), 1)
            self.assertEqual(len(untranslated_saves), 1)

        finally:
            os.unlink(po_path)

    @patch('python_gpt_po.services.translation_service.TranslationService._get_provider_response')
    def test_incremental_save_behavior(self, mock_provider):
        """
        Test that translations are saved incrementally.
        This replaces redundant tests from test_incremental_save.py.
        """
        # Create test PO file
        po_file = polib.POFile()
        po_file.metadata = {"Language": "fr"}
        for i in range(25):
            po_file.append(polib.POEntry(msgid=f"String {i}", msgstr=""))

        with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as f:
            po_file.save(f.name)
            po_path = f.name

        try:
            # Track saves
            save_count = [0]
            original_save = po_file.save

            def track_save(path):
                save_count[0] += 1
                original_save(path)

            # Mock the translation
            mock_provider.return_value = "Translation"

            with patch.object(polib.POFile, 'save', side_effect=track_save):
                # Process file
                self.service.process_po_file(po_path, ["fr"], None)

            # Should have saved multiple times (incremental), not just once
            self.assertGreater(save_count[0], 1,
                               "File should be saved incrementally, not just at the end")

        finally:
            os.unlink(po_path)

    def test_bulk_vs_single_mode_behavior(self):
        """
        Single test comparing bulk vs single mode behavior.
        Replaces multiple redundant bulk/single tests.
        """
        test_entries = ["Hello", "World", "Test"]

        # Test both modes with same data
        for bulk_mode in [True, False]:
            with self.subTest(mode="bulk" if bulk_mode else "single"):
                self.config.flags.bulk_mode = bulk_mode
                service = TranslationService(self.config)

                with patch.object(service, '_get_provider_response') as mock_response:
                    if bulk_mode:
                        # Bulk mode returns JSON array
                        mock_response.return_value = '["Bonjour", "Monde", "Test"]'
                    else:
                        # Single mode returns individual translations
                        mock_response.side_effect = ["Bonjour", "Monde", "Test"]

                    # Create test PO file
                    po_file = polib.POFile()
                    po_file.metadata = {"Language": "fr"}  # Set language metadata
                    for text in test_entries:
                        po_file.append(polib.POEntry(msgid=text, msgstr=""))

                    with tempfile.NamedTemporaryFile(suffix='.po', delete=False) as f:
                        po_file.save(f.name)
                        po_path = f.name

                    try:
                        service.process_po_file(po_path, ["fr"], None)

                        # Verify all were translated regardless of mode
                        result = POFileHandler.load_po_file(po_path)
                        for entry in result:
                            if entry.msgid:  # Skip header
                                self.assertNotEqual(entry.msgstr, "")

                    finally:
                        os.unlink(po_path)


class TestLocaleHandling(unittest.TestCase):
    """
    Test all locale format variations.
    """

    def test_locale_format_variations(self):
        """
        Test that fr, fr_CA, fr-CA, en-US, pt_BR all work correctly.
        """
        from python_gpt_po.services.po_file_handler import POFileHandler

        test_cases = [
            # (file_language, requested_languages, should_match)

            # Exact matches
            ("fr", ["fr"], "fr"),
            ("fr_CA", ["fr_CA"], "fr_CA"),
            ("fr-CA", ["fr-CA"], "fr-CA"),
            ("en_US", ["en_US"], "en_US"),
            ("pt_BR", ["pt_BR"], "pt_BR"),

            # Format conversion (underscore <-> hyphen)
            ("fr_CA", ["fr-CA"], "fr-CA"),  # File has _, request has -
            ("fr-CA", ["fr_CA"], "fr_CA"),  # File has -, request has _
            ("en_US", ["en-US"], "en-US"),
            ("pt-BR", ["pt_BR"], "pt_BR"),

            # Fallback to base language
            ("fr_CA", ["fr"], "fr"),  # French Canadian falls back to French
            ("en_US", ["en"], "en"),  # US English falls back to English
            ("pt_BR", ["pt"], "pt"),  # Brazilian Portuguese falls back to Portuguese
            ("zh_CN", ["zh"], "zh"),  # Chinese Simplified falls back to Chinese

            # No match scenarios
            ("fr_CA", ["es"], None),  # French Canadian doesn't match Spanish
            ("en_US", ["fr"], None),  # US English doesn't match French
            ("de_DE", ["it"], None),  # German doesn't match Italian

            # Multiple language options
            ("fr_CA", ["es", "en", "fr"], "fr"),  # Should match fr
            ("pt_BR", ["fr", "pt_BR", "es"], "pt_BR"),  # Should match exact
            ("en-US", ["fr", "en_US", "de"], "en_US"),  # Format conversion
        ]

        for file_lang, requested_langs, expected_match in test_cases:
            with self.subTest(file=file_lang, requested=requested_langs):
                # Create mock PO file
                po_file = polib.POFile()
                po_file.metadata = {"Language": file_lang}

                # Test language matching
                result = POFileHandler.get_file_language(
                    "test.po",
                    po_file,
                    requested_langs,
                    folder_language=False
                )

                self.assertEqual(
                    result, expected_match,
                    f"Language {file_lang} with requested {requested_langs} "
                    f"should return {expected_match}, got {result}"
                )

    def test_locale_in_folder_structure(self):
        """
        Test language detection from folder structure.
        """
        from python_gpt_po.services.po_file_handler import POFileHandler

        test_cases = [
            # (file_path, file_language, requested_languages, use_folder, expected)

            # Folder structure detection
            ("/locales/fr_CA/django.po", "", ["fr_CA"], True, "fr_CA"),
            ("/locales/fr-CA/django.po", "", ["fr_CA"], True, "fr_CA"),
            ("/locales/fr/LC_MESSAGES/django.po", "", ["fr"], True, "fr"),
            ("/pt_BR/translations/messages.po", "", ["pt_BR"], True, "pt_BR"),

            # Folder fallback to base language
            ("/locales/fr_CA/django.po", "", ["fr"], True, "fr"),
            ("/locales/en_US/django.po", "", ["en"], True, "en"),

            # Prefer file metadata over folder
            ("/locales/fr/django.po", "es", ["es", "fr"], False, "es"),

            # No folder detection when disabled
            ("/locales/fr_CA/django.po", "", ["fr_CA"], False, None),
        ]

        for file_path, file_lang, requested_langs, use_folder, expected in test_cases:
            with self.subTest(path=file_path, use_folder=use_folder):
                po_file = polib.POFile()
                if file_lang:
                    po_file.metadata = {"Language": file_lang}

                result = POFileHandler.get_file_language(
                    file_path,
                    po_file,
                    requested_langs,
                    folder_language=use_folder
                )

                self.assertEqual(result, expected,
                                 f"Path {file_path} should return {expected}, got {result}")

    def test_real_world_locale_files(self):
        """
        Test with actual locale patterns from WordPress, Django, etc.
        """
        # WordPress style: wp-content/languages/themes/twentytwenty-fr_CA.po
        # Django style: locale/fr/LC_MESSAGES/django.po
        # GNU style: po/fr_CA.po

        test_files = [
            ("fr_CA", "WordPress French Canadian"),
            ("pt_BR", "WordPress Brazilian Portuguese"),
            ("zh_CN", "WordPress Simplified Chinese"),
            ("en_GB", "WordPress British English"),
            ("es_MX", "WordPress Mexican Spanish"),
            ("de_DE_formal", "WordPress German Formal"),  # Special case
        ]

        for locale_code, description in test_files:
            with self.subTest(locale=locale_code):
                # Create test PO file
                po_content = f'''msgid ""
msgstr ""
"Language: {locale_code}\\n"

msgid "Test"
msgstr ""
'''
                with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
                    f.write(po_content)
                    po_path = f.name

                try:
                    po_file = POFileHandler.load_po_file(po_path)

                    # Test exact match
                    result = POFileHandler.get_file_language(
                        po_path, po_file, [locale_code], False
                    )
                    self.assertEqual(result, locale_code, f"{description} exact match failed")

                    # Test base language fallback (except for special cases)
                    if '_' in locale_code and not locale_code.endswith('_formal'):
                        base_lang = locale_code.split('_')[0]
                        result = POFileHandler.get_file_language(
                            po_path, po_file, [base_lang], False
                        )
                        self.assertEqual(result, base_lang, f"{description} fallback failed")

                finally:
                    os.unlink(po_path)


class TestEdgeCases(unittest.TestCase):
    """
    Test edge cases and error conditions.
    """

    def test_malformed_plural_forms(self):
        """Test handling of malformed plural entries."""
        # Entry with msgid_plural but no msgstr_plural
        entry = polib.POEntry(
            msgid="test",
            msgid_plural="tests"
            # Missing msgstr_plural
        )
        # Should handle gracefully
        result = is_entry_untranslated(entry)
        self.assertTrue(result)  # Treat as untranslated if malformed

    def test_empty_po_file(self):
        """Test handling of empty PO files."""
        po_file = polib.POFile()
        untranslated = get_all_untranslated_entries(po_file)
        self.assertEqual(len(untranslated), 0)

    def test_header_only_po_file(self):
        """Test PO file with only header entry."""
        po_file = polib.POFile()
        po_file.metadata = {"Language": "fr"}
        untranslated = get_all_untranslated_entries(po_file)
        self.assertEqual(len(untranslated), 0)


if __name__ == "__main__":
    unittest.main()
