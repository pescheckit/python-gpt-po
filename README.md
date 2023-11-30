# Python GPT-4 PO File Translator

This script offers an efficient method for translating `.po` files using OpenAI's GPT-4 model. It is designed to support both bulk and individual translation modes, catering to different project sizes and `.po` file types.

## Features

- **Bulk Translation**: Allows for translating multiple entries at once for increased efficiency.
- **Individual Translation**: Option to translate each entry separately, providing more control.
- **Adjustable Batch Size**: Customize the number of translations processed in each batch during bulk translation.
- **Detailed Logging**: Provides comprehensive logging to monitor progress and troubleshoot.
- **Fuzzy Entry Handling**: Includes an option to exclude 'fuzzy' entries in `.po` files.
- **Flexible API Key Input**: Choose to input your OpenAI API key either via command line or through a `.env` file.

## Requirements

- Python 3.x
- `polib` library
- `openai` Python package

## Installation

1. Clone the repository:
   ```
   git clone [repository URL]
   ```
2. Install the required Python packages:
   ```
   pip install polib openai
   ```

## Configuration

You can provide your OpenAI API key in one of two ways:

1. **Via Command Line Argument**: Directly pass the API key when running the script.
2. **Using a `.env` File**:
   - Create a `.env` file in the root directory of the project.
   - Add your OpenAI API key to this file:
     ```
     OPENAI_API_KEY='your_api_key_here'
     ```

## Usage

Run the script from the command line with the necessary arguments:

```
python po_translator.py --folder [path_to_po_files] --lang [language_codes] [--api_key [your_openai_api_key]] [--fuzzy] [--bulk] [--bulksize [batch_size]]
```

- `--folder`: Path to the folder containing `.po` files.
- `--lang`: Comma-separated language codes for filtering `.po` files.
- `--api_key`: (Optional) Your OpenAI API key. If not provided, the script will look for it in the `.env` file.
- `--fuzzy`: (Optional) Flag to ignore entries marked as 'fuzzy'.
- `--bulk`: (Optional) Flag to use bulk translation mode.
- `--bulksize`: (Optional) Number of translations to process per batch (default is 50).

Example:

```
python po_translator.py --folder ./locales --lang de,fr --api_key 'your_api_key_here' --bulk --bulksize 100
```

This command will translate all `.po` files in the `./locales` folder to German and French using your provided OpenAI API key, processing 100 translations per batch in bulk mode.

## Logging

The script logs its progress and any errors encountered. The logs detail information about the files being processed, the number of translations, and the current batch in bulk mode.

## License

[MIT](LICENSE)
