"""
Tests for handling plural forms in PO files.
"""

import os
import tempfile
import unittest

import polib

from python_gpt_po.services.po_file_handler import POFileHandler
from python_gpt_po.utils.po_entry_helpers import get_all_untranslated_entries, is_entry_untranslated


class TestPluralHandling(unittest.TestCase):
    """Test handling of plural forms in PO files."""

    def test_regular_entry_untranslated(self):
        """Test that regular entries with empty msgstr are detected as untranslated."""
        entry = polib.POEntry(
            msgid="Hello",
            msgstr=""
        )
        self.assertTrue(is_entry_untranslated(entry))

    def test_regular_entry_translated(self):
        """Test that regular entries with non-empty msgstr are not untranslated."""
        entry = polib.POEntry(
            msgid="Hello",
            msgstr="Bonjour"
        )
        self.assertFalse(is_entry_untranslated(entry))

    def test_plural_entry_fully_translated(self):
        """Test that plural entries with all forms translated are not untranslated."""
        entry = polib.POEntry(
            msgid="%(num)d item",
            msgid_plural="%(num)d items",
            msgstr_plural={
                0: "%(num)d предмет",
                1: "%(num)d предмета",
                2: "%(num)d предмета"
            }
        )
        self.assertFalse(is_entry_untranslated(entry))

    def test_plural_entry_partially_translated(self):
        """Test that plural entries with some filled forms are NOT detected as untranslated."""
        entry = polib.POEntry(
            msgid="%(num)d item",
            msgid_plural="%(num)d items",
            msgstr_plural={
                0: "%(num)d предмет",
                1: "",  # Empty translation
                2: "%(num)d предмета"
            }
        )
        # Changed: Partially translated plurals are considered "good enough"
        self.assertFalse(is_entry_untranslated(entry))

    def test_plural_entry_all_empty(self):
        """Test that plural entries with all empty forms are detected as untranslated."""
        entry = polib.POEntry(
            msgid="%(num)d item",
            msgid_plural="%(num)d items",
            msgstr_plural={
                0: "",
                1: "",
                2: ""
            }
        )
        self.assertTrue(is_entry_untranslated(entry))

    def test_entry_without_msgid(self):
        """Test that entries without msgid are not considered for translation."""
        entry = polib.POEntry(
            msgid="",
            msgstr=""
        )
        self.assertFalse(is_entry_untranslated(entry))

    def test_po_file_with_mixed_entries(self):
        """Test filtering untranslated entries from a PO file with mixed entries."""
        # Create a PO file with various types of entries
        po_file = polib.POFile()

        # Add regular translated entry
        po_file.append(polib.POEntry(
            msgid="Welcome",
            msgstr="Bienvenue"
        ))

        # Add regular untranslated entry
        po_file.append(polib.POEntry(
            msgid="Goodbye",
            msgstr=""
        ))

        # Add plural fully translated entry
        po_file.append(polib.POEntry(
            msgid="%(num)d file",
            msgid_plural="%(num)d files",
            msgstr_plural={
                0: "%(num)d fichier",
                1: "%(num)d fichiers"
            }
        ))

        # Add plural partially translated entry
        po_file.append(polib.POEntry(
            msgid="%(num)d message",
            msgid_plural="%(num)d messages",
            msgstr_plural={
                0: "%(num)d message",
                1: ""  # Missing translation
            }
        ))

        # Get untranslated entries
        untranslated = get_all_untranslated_entries(po_file)

        # Should have 1 untranslated entry: "Goodbye" only
        # The partially translated plural "message" is NOT considered untranslated
        self.assertEqual(len(untranslated), 1)

        # Check that the correct entries are identified
        untranslated_msgids = [e.msgid for e in untranslated]
        self.assertIn("Goodbye", untranslated_msgids)

        # Partially translated plural should NOT be included
        self.assertNotIn("%(num)d message", untranslated_msgids)

        # Translated entries should not be included
        self.assertNotIn("Welcome", untranslated_msgids)
        self.assertNotIn("%(num)d file", untranslated_msgids)

    def test_real_django_plural_entry(self):
        """Test with a real-world Django plural entry format."""
        # Create a test PO file with Django-style plural entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = '''msgid ""
msgstr ""
"Language: sr\\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
"n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\\n"

#, python-format
msgid ""
"Ensure this value has at least %(limit_value)d character (it has "
"%(show_value)d)."
msgid_plural ""
"Ensure this value has at least %(limit_value)d characters (it has "
"%(show_value)d)."
msgstr[0] "Ово поље мора да има најмање %(limit_value)d карактер (тренутно има %(show_value)d)."
msgstr[1] ""
msgstr[2] ""
'''
            f.write(po_content)
            po_file_path = f.name

        try:
            # Load the PO file
            po_file = POFileHandler.load_po_file(po_file_path)

            # Get the plural entry
            entries = list(po_file)
            self.assertEqual(len(entries), 1)

            entry = entries[0]

            # This entry should NOT be detected as untranslated because msgstr[0] is filled
            # (partially translated plurals are considered "good enough")
            self.assertFalse(is_entry_untranslated(entry))

        finally:
            os.unlink(po_file_path)

    def test_fully_translated_django_plural(self):
        """Test with a fully translated Django plural entry."""
        # Create a test PO file with fully translated plural entries
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as f:
            po_content = '''msgid ""
msgstr ""
"Language: sr\\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
"n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);\\n"

#, python-format
msgid "%(num)d year"
msgid_plural "%(num)d years"
msgstr[0] "%(num)d година"
msgstr[1] "%(num)d године"
msgstr[2] "%(num)d година"
'''
            f.write(po_content)
            po_file_path = f.name

        try:
            # Load the PO file
            po_file = POFileHandler.load_po_file(po_file_path)

            # Get the plural entry
            entries = list(po_file)
            self.assertEqual(len(entries), 1)

            entry = entries[0]

            # This entry should NOT be detected as untranslated - all forms are filled
            self.assertFalse(is_entry_untranslated(entry))

        finally:
            os.unlink(po_file_path)


if __name__ == "__main__":
    unittest.main()
