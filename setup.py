"""
Setup script shim for the gpt-po-translator package.
Metadata is defined in pyproject.toml.
This script enables setuptools_scm and handles custom data_files installation.
"""

from setuptools import setup

# Most metadata is defined in pyproject.toml.
# This file primarily enables setuptools_scm and handles non-declarative steps.
setup(
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    # include_package_data=True, # Keep this if needed and not configured elsewhere
)
