# Development Guidelines for python-gpt-po

## Commands

- Install: `pip install -e .`
- Run: `python -m python_gpt_po.main --folder <path> --lang <lang-codes>`
- Test: `python -m pytest`
- Test Single: `python -m pytest python_gpt_po/tests/path/to/test.py::test_function_name -v`
- Test Integration: `python -m pytest -m integration`
- Lint: `flake8 python_gpt_po`
- Type Check: `pylint python_gpt_po`
- Build Package: `python -m build --wheel`
- Version Info: `python -m python_gpt_po.main --version`

## Code Style

- Line Length: 120 characters max (configured in both .flake8 and .pylintrc)
- Docstrings: Required for all modules, classes, and functions (Google style with return type docs)
- Imports: Group standard lib, third-party, and local imports (sorted alphabetically)
- Typing: Use type hints for all parameters, return values; use Optional[T] for nullable types
- Versioning: Environment variable > _version.py > Git tags > fallback=0.1.0
- Naming: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- Error Handling: Use specific exceptions with descriptive messages, proper logging
- Logging: Use the logging module instead of print statements for all output
- Tests: Unit tests with descriptive names, integration tests marked with @pytest.mark.integration
- Architecture: Use dataclasses for configuration, follow service/model separation
- PEP 8: Follow with exceptions (W293 for trailing whitespace, see .flake8 and .pylintrc)

## Docker Commands

- Build: `docker build -t gpt-po-translator .`
- Pull: `docker pull ghcr.io/pescheckit/python-gpt-po:latest`
- Run Example: `docker run -v $(pwd):/data -e OPENAI_API_KEY=<key> gpt-po-translator --folder /data --lang fr,es,de`
- Custom Version: `docker build -t gpt-po-translator --build-arg VERSION=1.0.0 .`