"""
Setup script for the gpt-po-translator package.
This script is used to install the package, dependencies, and the man page.
"""

import os

from setuptools import find_packages, setup

with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt', encoding='utf-8') as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith('#')]


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
    name='gpt-po-translator',
    use_scm_version=True,
    setup_requires=['setuptools-scm==8.1.0'],
    author='Bram Mittendorff',
    author_email='bram@pescheck.io',
    description='A CLI tool for translating .po files using GPT models.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pescheckit/python-gpt-po',
    license='MIT',
    packages=find_packages(),
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
