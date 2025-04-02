"""
Setup script for the gpt-po-translator package.
This script is used to install the package, dependencies, and the man page.
"""

import os
import subprocess
from typing import Optional

from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', encoding='utf-8') as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]


def get_pep440_version() -> Optional[str]:
    """
    Get version from environment or git, ensuring it's PEP 440 compliant.

    Returns:
        Optional[str]: PEP 440 compliant version string or None to defer to setuptools_scm
    """

    # First check environment variable (highest priority for containers)
    if 'PACKAGE_VERSION' in os.environ:
        raw_version = os.environ.get('PACKAGE_VERSION')
        # Make version PEP 440 compliant
        if '-' in raw_version and '+' not in raw_version:
            # Convert something like "1.2.3-test" to "1.2.3+test" for PEP 440
            version = raw_version.replace('-', '+', 1)
        else:
            version = raw_version
        print(f"Using version from environment: {version}")
        return version

    # Then try getting from git
    try:
        # Get version from git describe, but normalize it to be PEP 440 compliant
        version = subprocess.check_output(
            ['git', 'describe', '--tags', '--always'],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()

        # Handle version format from git describe
        if '-' in version:
            # Format like v0.3.5-5-gd9775d7, convert to 0.3.5.dev5+gd9775d7
            tag, commits, commit_hash = version.lstrip('v').split('-')
            version = f"{tag}.dev{commits}+{commit_hash}"
        elif version.startswith('v'):
            # Just a tagged version like v0.3.5
            version = version[1:]

        print(f"Using git version: {version}")
        return version
    except (subprocess.SubprocessError, FileNotFoundError):
        # Defer to setuptools_scm
        print("Deferring to setuptools_scm for version")
        return None


# Get version using our custom function
package_version = get_pep440_version()


def install_man_pages():
    """
    Locate the man page and include it in the installation if it exists.

    Returns:
        list: A list containing the path to the man page for installation.
    """
    man_page = "man/gpt-po-translator.1"
    if os.path.exists(man_page):
        return [("share/man/man1", [man_page])]
    return []


setup(
    name='gpt_po_translator',
    version=package_version,  # Will be None if PACKAGE_VERSION is not set, triggering setuptools_scm
    author='Bram Mittendorff',
    author_email='bram@pescheck.io',
    description='A CLI tool for translating .po files using GPT models.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pescheckit/python-gpt-po',
    license='MIT',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "*.__pycache__", "*.__pycache__.*"]),
    include_package_data=True,
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'gpt-po-translator=python_gpt_po.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Internationalization',
        'Topic :: Software Development :: Localization',
        'Topic :: Text Processing :: Linguistic',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'Natural Language :: English',
        'Natural Language :: Dutch',
        'Environment :: Console',
        'Typing :: Typed'
    ],
    python_requires='>=3.8',
    data_files=install_man_pages(),
)
