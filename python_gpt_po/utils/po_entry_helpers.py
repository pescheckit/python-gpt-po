"""
Helper functions for working with PO entries.
"""


def is_entry_untranslated(entry):
    """
    Check if a PO entry needs translation.

    This function properly handles both regular entries and plural entries.

    Args:
        entry: A polib.POEntry object

    Returns:
        bool: True if the entry needs translation, False otherwise
    """
    # Entry must have a msgid to be translatable
    if not entry.msgid:
        return False

    # Check if this is a plural entry
    if hasattr(entry, 'msgstr_plural') and entry.msgstr_plural:
        # For plural entries, check if ALL forms are empty
        # Only consider it untranslated if ALL plural forms are empty
        # This avoids translating partially translated entries
        all_empty = True
        for _, translation in entry.msgstr_plural.items():
            if translation and translation.strip():
                all_empty = False
                break
        return all_empty

    # For regular entries, check if msgstr is empty
    return not entry.msgstr or not entry.msgstr.strip()


def get_all_untranslated_entries(po_file):
    """
    Get all untranslated entries from a PO file.

    Args:
        po_file: A polib.POFile object

    Returns:
        list: List of POEntry objects that need translation
    """
    return [entry for entry in po_file if is_entry_untranslated(entry)]


def add_ai_generated_comment(entry):
    """
    Add AI-generated comment to a PO entry if not already present.

    Args:
        entry: A polib.POEntry object to add comment to
    """
    ai_comment = "AI-generated"
    if not entry.comment or ai_comment not in entry.comment:
        if entry.comment:
            entry.comment = f"{entry.comment}\n{ai_comment}"
        else:
            entry.comment = ai_comment
