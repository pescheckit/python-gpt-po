"""
Setup script for the gpt-po-translator package.
This script is used to install the package and its dependencies.
"""

from setuptools import find_packages, setup

from python_gpt_po.version import __version__

# Read the contents of README file
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='gpt-po-translator',
    version=__version__,
    author='Bram Mittendorff',
    author_email='bram@pescheck.io',
    description='A CLI tool for translating .po files using GPT models.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pescheckit/python-gpt-po',
    license='LICENSE',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'polib',
        'openai',
        'python-dotenv'
        # Add other dependencies from requirements.txt
    ],
    entry_points={
        'console_scripts': [
            'gpt-po-translator=python_gpt_po.po_translator:main',
        ],
    },
    classifiers=[
        # Choose your license as you wish
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        # Add additional classifiers as needed
    ],
)
