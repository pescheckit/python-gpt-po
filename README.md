# Python ChatGPT Po File Converter

This script uses the `polib` library for processing `.po` files, `argparse` for command line argument parsing, and `os` for file system operations. It scans the specified input folder and its subfolders for `.po` files, checks if they match the given language, and optionally removes fuzzy entries based on the `--fuzzy` flag.

To use this script:

1. Ensure you have Python installed on your system.
2. Install `polib` via pip: `pip install polib`.
3. Save the script into a file, e.g., `po_scanner.py`.
4. Run the script from the command line, providing the necessary arguments. For example:
   ```
   python po_scanner.py /path/to/your/folder en --fuzzy
   ```

This command would scan for `.po` files in `/path/to/your/folder` that are in English (`en`) and remove fuzzy entries if they exist.