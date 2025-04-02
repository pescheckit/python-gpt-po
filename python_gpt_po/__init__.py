"""
GPT-PO Translator - A tool for translating PO files using GPT language models.
This package provides utilities to translate gettext PO files to multiple languages
with support for multiple AI providers including OpenAI and Anthropic.
"""

import os
import subprocess
from typing import Optional


def _get_version_from_git() -> Optional[str]:
    """
    Try to get version from git.

    Returns:
        Optional[str]: Git version or None if not available
    """
    try:
        # Check if we're in a git repo
        is_git_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        ).returncode == 0
        if is_git_repo:
            # Get version from git describe
            return subprocess.check_output(
                ["git", "describe", "--tags"],
                stderr=subprocess.STDOUT,
                text=True
            ).strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


# Version priority:
# 1. Environment variable PACKAGE_VERSION (for Docker/CI environments)
# 2. _version.py from setuptools_scm (for installed packages)
# 3. Git describe (for development environments)
# 4. Fallback to "0.1.0"
if 'PACKAGE_VERSION' in os.environ:
    __version__ = os.environ.get('PACKAGE_VERSION')
else:
    try:
        from ._version import version as __version__  # noqa
    except ImportError:
        git_version = _get_version_from_git()
        if git_version:
            __version__ = git_version
        else:
            __version__ = "0.1.0"
