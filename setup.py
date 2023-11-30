from setuptools import find_packages, setup

setup(
    name='gpt-po-translator',
    version='0.1.3',
    author='Bram Mittendorff',
    author_email='bram@pescheck.io',
    description='A CLI tool for translating .po files using GPT models.',
    long_description=open('README.md').read(),
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
