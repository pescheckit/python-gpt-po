"""
Tests for Django makemessages/compilemessages compatibility with AI-generated comments.
"""
import subprocess
import tempfile
from pathlib import Path

import polib
import pytest

from python_gpt_po.services.po_file_handler import POFileHandler


class TestDjangoCompatibility:
    """Test cases for Django compatibility with AI-generated comments."""

    def test_po_file_with_ai_comments_compiles_with_msgfmt(self):
        """Test that PO files with AI-generated comments can be compiled with msgfmt."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
            # Create a PO file with AI-generated comments
            po = polib.POFile()
            po.metadata = {'Language': 'es', 'Content-Type': 'text/plain; charset=UTF-8'}

            # Add entries with AI-generated comments
            entry1 = polib.POEntry(msgid="Hello", msgstr="Hola", comment="AI-generated")
            entry2 = polib.POEntry(msgid="Welcome", msgstr="Bienvenido", comment="AI-generated")
            entry3 = polib.POEntry(msgid="Goodbye", msgstr="Adiós")  # No AI comment

            po.append(entry1)
            po.append(entry2)
            po.append(entry3)
            po.save(tmp.name)

            # Try to compile with msgfmt (what Django uses)
            mo_file = tmp.name.replace('.po', '.mo')
            result = subprocess.run(
                ['msgfmt', '-o', mo_file, tmp.name],
                capture_output=True,
                text=True
            )

            # Check compilation succeeded
            assert result.returncode == 0, f"msgfmt failed: {result.stderr}"
            assert Path(mo_file).exists()
            assert Path(mo_file).stat().st_size > 0

            # Clean up
            Path(tmp.name).unlink()
            Path(mo_file).unlink()

    def test_django_makemessages_removes_translator_comments(self):
        """Test that Django makemessages removes translator comments (including AI comments)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create original PO file with AI comments (simulating Django structure)
            original_po = tmppath / "django.po"
            po_content = '''# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Language: es\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

#. AI-generated
msgid "Hello"
msgstr "Hola"

#. AI-generated
msgid "Welcome"
msgstr "Bienvenido"
'''
            original_po.write_text(po_content)

            # Verify AI comments are there
            assert '#. AI-generated' in po_content
            assert po_content.count('#. AI-generated') == 2

            # Create a POT template (simulating Django makemessages extraction)
            pot_file = tmppath / "django.pot"
            pot_content = '''# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr ""

msgid "Welcome"
msgstr ""

msgid "New string"
msgstr ""
'''
            pot_file.write_text(pot_content)

            # Run msgmerge (what Django makemessages uses internally)
            result = subprocess.run(
                ['msgmerge', '--quiet', '--update', '--backup=none',
                 str(original_po), str(pot_file)],
                capture_output=True,
                text=True
            )

            # Check merge succeeded
            assert result.returncode == 0, f"msgmerge failed: {result.stderr}"

            # Read updated content
            updated_content = original_po.read_text()

            # Verify translations are preserved but AI comments are removed
            assert 'msgstr "Hola"' in updated_content
            assert 'msgstr "Bienvenido"' in updated_content

            # AI comments should be gone (this is Django's behavior)
            ai_comments_after = updated_content.count('#. AI-generated')
            assert ai_comments_after == 0, "Django makemessages removes translator comments"

            # Load with polib to verify structure
            merged_po = POFileHandler.load_po_file(str(original_po))
            hello_entry = merged_po.find("Hello")
            assert hello_entry.msgstr == "Hola"  # Translation preserved
            assert not hello_entry.comment  # Comment removed

    def test_django_po_format_with_ai_comments(self):
        """Test that our AI comments work with Django-style PO files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
            # Create a Django-style PO file
            django_po_content = '''# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2024-01-01 00:00+0000\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: es\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

#: myapp/views.py:10
msgid "Welcome to our site"
msgstr ""

#: myapp/views.py:20
msgid "Please login"
msgstr ""
'''
            tmp.write(django_po_content)
            tmp.flush()

            # Load with polib and add AI translations
            po = POFileHandler.load_po_file(tmp.name)

            # Update entries with AI translations
            for entry in po:
                if entry.msgid == "Welcome to our site":
                    POFileHandler.update_po_entry(po, entry.msgid, "Bienvenido a nuestro sitio", mark_ai_generated=True)
                elif entry.msgid == "Please login":
                    POFileHandler.update_po_entry(po, entry.msgid, "Por favor inicie sesión", mark_ai_generated=True)

            po.save(tmp.name)

            # Read back and verify
            saved_content = Path(tmp.name).read_text()

            # Check that AI comments are present
            assert '#. AI-generated' in saved_content
            assert saved_content.count('#. AI-generated') == 2

            # Check that Django location comments are preserved
            assert '#: myapp/views.py:10' in saved_content
            assert '#: myapp/views.py:20' in saved_content

            # Verify the file can still be compiled
            mo_file = tmp.name.replace('.po', '.mo')
            result = subprocess.run(
                ['msgfmt', '-o', mo_file, tmp.name],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0

            # Clean up
            Path(tmp.name).unlink()
            Path(mo_file).unlink()

    def test_mixed_translator_comments(self):
        """Test that AI comments work alongside other translator comments."""
        po = polib.POFile()
        po.metadata = {'Language': 'es'}

        # Entry with existing translator comment
        entry = polib.POEntry(
            msgid="Dashboard",
            msgstr="",
            comment="Translators: Main navigation menu item"
        )
        po.append(entry)

        # Add AI translation
        POFileHandler.update_po_entry(po, "Dashboard", "Tablero", mark_ai_generated=True)

        # Check both comments are present
        updated_entry = po.find("Dashboard")
        assert "Translators: Main navigation menu item" in updated_entry.comment
        assert "AI-generated" in updated_entry.comment
        assert updated_entry.msgstr == "Tablero"

    @pytest.mark.skipif(
        subprocess.run(['msgfmt', '--version'], capture_output=True).returncode != 0,
        reason="msgfmt not available"
    )
    def test_gettext_tools_compatibility(self):
        """Test compatibility with various gettext tools."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False) as tmp:
            # Create PO file with AI comments
            po = polib.POFile()
            po.metadata = {'Language': 'es', 'Content-Type': 'text/plain; charset=UTF-8'}

            entry = polib.POEntry(msgid="Test", msgstr="Prueba", comment="AI-generated")
            po.append(entry)
            po.save(tmp.name)

            # Test msgfmt
            mo_file = tmp.name.replace('.po', '.mo')
            result = subprocess.run(['msgfmt', '-o', mo_file, tmp.name], capture_output=True)
            assert result.returncode == 0

            # Test msgcat (concatenate and merge PO files)
            result = subprocess.run(['msgcat', tmp.name], capture_output=True, text=True)
            assert result.returncode == 0
            assert '#. AI-generated' in result.stdout

            # Clean up
            Path(tmp.name).unlink()
            if Path(mo_file).exists():
                Path(mo_file).unlink()
