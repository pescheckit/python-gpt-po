"""
Helper utilities for the PO translator application.
"""

from pkg_resources import DistributionNotFound, get_distribution

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
    # Fall back to package metadata
    try:
        return get_distribution("gpt-po-translator").version
    except DistributionNotFound:
        return "0.0.0"
