# Development Guidelines for python-gpt-po

## Commands

- Install: `pip install -e .`
- Run: `python -m python_gpt_po.main --folder <path> --lang <lang-codes>`
- Test: `python -m pytest`
- Test Single: `python -m pytest python_gpt_po/tests/path/to/test.py::test_function_name -v`
- Test Integration: `python -m pytest -m integration`
- Lint: `flake8`
- Type Check: `pylint python_gpt_po/`

## Docker Commands

- Build Image: `docker build -t gpt-po-translator .`
- Pull Image: `docker pull ghcr.io/pescheckit/python-gpt-po:latest`
- Run with Tag: `docker run -v $(pwd):/data ghcr.io/pescheckit/python-gpt-po:latest --folder /data --lang fr`
- Run Container: 
  - Current Dir: `docker run -v $(pwd):/data -e OPENAI_API_KEY=<key> gpt-po-translator --folder /data --lang <lang-codes>`
  - Absolute Path: `docker run -v /absolute/path/to/files:/custom/path -e OPENAI_API_KEY=<key> gpt-po-translator --folder /custom/path --lang <lang-codes>`
  - Windows Path: `docker run -v D:/projects/locales:/locales -e OPENAI_API_KEY=<key> gpt-po-translator --folder /locales --lang <lang-codes>`
  - Multiple Volumes: `docker run -v /source:/input -v /output:/output -e OPENAI_API_KEY=<key> gpt-po-translator --folder /input --lang <lang-codes>`

## Code Style

- Line Length: 120 characters max
- Docstrings: Required for all modules, classes, and functions (Google style)
- Imports: Group standard lib, third-party, and local imports (sorted alphabetically)
- Typing: Use type hints for all function parameters and return values
- Naming: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- Error Handling: Specific exceptions with descriptive messages
- Logging: Use the logging module, not print statements
- Tests: Unit tests required with descriptive names, mocks for external services
- Use dataclasses for configuration objects
- Follow PEP 8 with the exceptions noted in .flake8 and .pylintrc