"""
Utility functions for handling plural forms in .po files.

Different languages have different numbers of plural forms:
- English/Dutch/German: 2 forms (singular, plural)
- Russian/Polish: 3 forms (singular, few, many)
- Arabic: 6 forms (zero, one, two, few, many, other)
"""

import re
from typing import List, Optional

# Default plural counts for common languages (ISO 639-1 codes)
DEFAULT_PLURAL_COUNTS = {
    # 2 forms (singular, plural)
    'en': 2, 'de': 2, 'fr': 2, 'es': 2, 'it': 2, 'pt': 2, 'nl': 2,
    'sv': 2, 'da': 2, 'no': 2, 'fi': 2, 'et': 2, 'el': 2, 'he': 2,
    'hu': 2, 'tr': 2, 'bg': 2, 'ca': 2,
    # 3 forms (singular, few, many)
    'ru': 3, 'uk': 3, 'pl': 3, 'cs': 3, 'hr': 3, 'sr': 3, 'sk': 3,
    'lt': 3, 'lv': 3, 'ro': 3,
    # 6 forms (zero, one, two, few, many, other)
    'ar': 6,
    # No plurals (1 form only)
    'ja': 1, 'ko': 1, 'zh': 1, 'vi': 1, 'th': 1, 'id': 1, 'ms': 1,
}

# Descriptive names for plural forms based on count
PLURAL_FORM_NAMES = {
    1: ["singular"],
    2: ["singular", "plural"],
    3: ["singular", "few", "many"],
    4: ["singular", "few", "many", "other"],
    5: ["zero", "one", "two", "few", "many"],
    6: ["zero", "one", "two", "few", "many", "other"]
}


def get_plural_count(po_file, language_code: Optional[str] = None) -> int:
    """
    Get the number of plural forms for a language.

    Tries to parse nplurals from the Plural-Forms header in the po_file.
    Falls back to DEFAULT_PLURAL_COUNTS based on language_code if header is missing.

    Args:
        po_file: polib.POFile object
        language_code: ISO 639-1 language code (e.g., 'en', 'ru', 'ar')

    Returns:
        Number of plural forms (1-6)
    """
    # Try to extract from Plural-Forms header
    if hasattr(po_file, 'metadata') and po_file.metadata:
        plural_forms = po_file.metadata.get('Plural-Forms', '')
        if plural_forms:
            # Parse "nplurals=N; plural=..."
            match = re.search(r'nplurals\s*=\s*(\d+)', plural_forms)
            if match:
                try:
                    count = int(match.group(1))
                    if 1 <= count <= 6:
                        return count
                except ValueError:
                    pass

    # Fall back to default based on language code
    if language_code:
        lang_code = language_code.lower().split('_')[0].split('-')[0]  # Extract base code
        if lang_code in DEFAULT_PLURAL_COUNTS:
            return DEFAULT_PLURAL_COUNTS[lang_code]

    # Ultimate fallback: 2 forms (most common)
    return 2


def get_plural_form_names(count: int) -> List[str]:
    """
    Get descriptive names for plural forms based on count.

    Args:
        count: Number of plural forms (1-6)

    Returns:
        List of descriptive names (e.g., ["singular", "plural"])
    """
    if count in PLURAL_FORM_NAMES:
        return PLURAL_FORM_NAMES[count]

    # Fallback for unexpected counts
    if count == 1:
        return ["singular"]
    return ["singular"] + [f"form_{i}" for i in range(1, count)]


def is_plural_entry(entry) -> bool:
    """
    Check if a po entry has plural forms.

    Args:
        entry: polib.POEntry object

    Returns:
        True if entry has msgid_plural, False otherwise
    """
    return hasattr(entry, 'msgid_plural') and entry.msgid_plural is not None and entry.msgid_plural != ''
