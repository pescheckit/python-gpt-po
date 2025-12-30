"""
Tests for AI-generated tagging functionality.
"""
import tempfile
from pathlib import Path

import polib

from python_gpt_po.services.po_file_handler import POFileHandler


class TestAIGeneratedTagging:
    """Test cases for AI-generated comment tagging."""

    def test_update_po_entry_with_ai_tag(self):
        """Test that update_po_entry adds AI-generated comment when enabled."""
        # Create a test PO file
        po = polib.POFile()
        entry = polib.POEntry(msgid="Hello", msgstr="")
        po.append(entry)

        # Update with AI tagging enabled
        POFileHandler.update_po_entry(po, "Hello", "Bonjour", mark_ai_generated=True)

        # Check that the comment was added
        updated_entry = po.find("Hello")
        assert updated_entry.msgstr == "Bonjour"
        assert updated_entry.comment == "AI-generated"

    def test_update_po_entry_without_ai_tag(self):
        """Test that update_po_entry doesn't add comment when disabled."""
        # Create a test PO file
        po = polib.POFile()
        entry = polib.POEntry(msgid="Hello", msgstr="")
        po.append(entry)

        # Update with AI tagging disabled
        POFileHandler.update_po_entry(po, "Hello", "Bonjour", mark_ai_generated=False)

        # Check that no comment was added
        updated_entry = po.find("Hello")
        assert updated_entry.msgstr == "Bonjour"
        assert not updated_entry.comment

    def test_update_po_entry_preserves_existing_comment(self):
        """Test that existing comments are preserved when adding AI tag."""
        # Create a test PO file with existing comment
        po = polib.POFile()
        entry = polib.POEntry(msgid="Hello", msgstr="", comment="Existing comment")
        po.append(entry)

        # Update with AI tagging enabled
        POFileHandler.update_po_entry(po, "Hello", "Bonjour", mark_ai_generated=True)

        # Check that both comments are present
        updated_entry = po.find("Hello")
        assert updated_entry.msgstr == "Bonjour"
        assert "Existing comment" in updated_entry.comment
        assert "AI-generated" in updated_entry.comment
        assert updated_entry.comment == "Existing comment\nAI-generated"

    def test_update_po_entry_doesnt_duplicate_ai_tag(self):
        """Test that AI-generated comment isn't duplicated."""
        # Create a test PO file with existing AI-generated comment
        po = polib.POFile()
        entry = polib.POEntry(msgid="Hello", msgstr="Old", comment="AI-generated")
        po.append(entry)

        # Update again with AI tagging enabled
        POFileHandler.update_po_entry(po, "Hello", "Bonjour", mark_ai_generated=True)

        # Check that AI-generated appears only once
        updated_entry = po.find("Hello")
        assert updated_entry.msgstr == "Bonjour"
        assert updated_entry.comment == "AI-generated"
        assert updated_entry.comment.count("AI-generated") == 1

    def test_get_ai_generated_entries(self):
        """Test getting all AI-generated entries from a PO file."""
        # Create a test PO file with mixed entries
        po = polib.POFile()
        po.append(polib.POEntry(msgid="Hello", msgstr="Bonjour", comment="AI-generated"))
        po.append(polib.POEntry(msgid="World", msgstr="Monde", comment="Human translation"))
        po.append(polib.POEntry(msgid="Test", msgstr="Test", comment="Some comment\nAI-generated"))
        po.append(polib.POEntry(msgid="No comment", msgstr="Sans commentaire"))

        # Get AI-generated entries
        ai_entries = POFileHandler.get_ai_generated_entries(po)

        # Check results
        assert len(ai_entries) == 2
        assert ai_entries[0].msgid == "Hello"
        assert ai_entries[1].msgid == "Test"

    def test_remove_ai_generated_comments(self):
        """Test removing AI-generated comments from entries."""
        # Create a test PO file with AI-generated comments
        po = polib.POFile()
        po.append(polib.POEntry(msgid="Hello", msgstr="Bonjour", comment="AI-generated"))
        po.append(polib.POEntry(msgid="World", msgstr="Monde", comment="Human comment\nAI-generated"))
        po.append(polib.POEntry(msgid="Test", msgstr="Test", comment="Only human comment"))

        # Remove AI-generated comments
        POFileHandler.remove_ai_generated_comments(po)

        # Check results
        entry1 = po.find("Hello")
        assert entry1.comment is None

        entry2 = po.find("World")
        assert entry2.comment == "Human comment"
        assert "AI-generated" not in entry2.comment

        entry3 = po.find("Test")
        assert entry3.comment == "Only human comment"

    def test_po_file_persistence_with_ai_tags(self):
        """Test that AI-generated comments persist when saving and loading PO files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create and save a PO file with AI-generated comments
            po = polib.POFile()
            po.metadata = {'Language': 'fr'}
            entry = polib.POEntry(msgid="Hello", msgstr="")
            po.append(entry)

            # Update with AI tag
            POFileHandler.update_po_entry(po, "Hello", "Bonjour", mark_ai_generated=True)
            po.save(tmp_path)

            # Load the file back
            loaded_po = POFileHandler.load_po_file(tmp_path)
            loaded_entry = loaded_po.find("Hello")

            # Verify the comment persisted
            assert loaded_entry.msgstr == "Bonjour"
            assert loaded_entry.comment == "AI-generated"

        finally:
            # Clean up
            Path(tmp_path).unlink(missing_ok=True)
