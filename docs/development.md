# Development

## VSCode Setup

To set up VSCode for development:

1. start the editor with the Python devcontainer

1. install the dependencies:

    ```bash
    # the _version.py file is generated and may need to be removed
    rm python-gpt-po/_version.py

    python -m pip install -e .
    ```

## Running the Tests

```bash
python -m pytest
```
