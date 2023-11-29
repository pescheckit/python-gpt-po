# Python GPT-4 PO File Translator

This script provides an efficient way to translate `.po` files using OpenAI's GPT-4 model. It supports both bulk and one-by-one translation modes, making it versatile for different sizes and types of `.po` files.

## Features

- **Bulk Translation**: Translate multiple entries at once for efficiency.
- **One-by-One Translation**: Translate each entry separately for greater control.
- **Adjustable Batch Size**: Control the number of translations processed in each batch during bulk translation.
- **Logging**: Detailed logging for tracking progress and debugging.
- **Fuzzy Entry Handling**: Option to ignore 'fuzzy' entries in `.po` files.

## Requirements

- Python 3.x
- `polib` library
- `openai` Python package
- An API key from OpenAI

## Installation

1. Clone the repository:
   ```
   git clone [repository URL]
   ```
2. Install the required Python packages:
   ```
   pip install polib openai python-dotenv
   ```

## Configuration

1. Create a `.env` file in the root directory of the project.
2. Add your OpenAI API key to the `.env` file:
   ```
   OPENAI_API_KEY='your_api_key_here'
   ```

## Usage

Run the script from the command line, providing the necessary arguments:

```
python po_translator.py --folder [path_to_po_files] --lang [language_codes] [--fuzzy] [--bulk] [--bulksize [batch_size]]
```

- `--folder`: The path to the folder containing `.po` files.
- `--lang`: Comma-separated language codes to filter `.po` files for translation.
- `--fuzzy`: (Optional) Set this flag to ignore entries marked as 'fuzzy'.
- `--bulk`: (Optional) Set this flag to use bulk translation mode.
- `--bulksize`: (Optional) Specify the number of translations to process in each batch (default is 50).

Example:

```
python po_translator.py --folder ./locales --lang de,fr --bulk --bulksize 100
```

This will translate all `.po` files in the `./locales` folder to German and French in bulk mode, processing 100 translations per batch.

## Logging

The script logs its progress and any errors encountered. Logs provide details about the files being processed, the number of translations, and the current batch in bulk mode.

## License

(MIT)[LICENSE]
