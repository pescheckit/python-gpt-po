"""
Helper utilities for the PO translator application.
"""

from pkg_resources import DistributionNotFound, get_distribution


def get_version():
    """
    Get package version.

    Returns:
        str: The package version or a default if not found
    """
    # First try to get version from __init__.py
    try:
        from .. import __version__
        return __version__
    except (ImportError, AttributeError):
        # Fall back to package metadata
        try:
            return get_distribution("gpt-po-translator").version
        except DistributionNotFound:
            return "0.0.0"
