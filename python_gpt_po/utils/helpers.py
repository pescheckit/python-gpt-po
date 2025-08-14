"""
Helper utilities for the PO translator application.
"""

# Import version with fallback to avoid circular imports
try:
    from .. import __version__
except (ImportError, AttributeError):
    __version__ = None


def get_version():
    """
    Get package version.

    Returns:
        str: The package version or a default if not found
    """
    # First check if version is available from the top-level import
    if __version__ is not None:
        return __version__

    # Fall back to modern package metadata approach
    try:
        # Use importlib.metadata (Python 3.8+) or importlib_metadata (fallback)
        try:
            from importlib.metadata import version
        except ImportError:
            from importlib_metadata import version
        return version("gpt-po-translator")
    except Exception:
        # Final fallback if all else fails
        return "0.0.0"
