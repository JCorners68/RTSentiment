# CLAUDE.md
## Preferences
- progress in slow incremental steps with progress verified at each step.
- be clear about synthetic data.  it should be stored in a completely separte file system and not comingled with other data.
- user must see at console or in a test file evidence of success that includes verifable data.
- update pip to the latest version to minimize dependency problems.
- keep documentation in sync after successful completion of a phase.
- be clear about verification procedure so that user can verify easily.
- iterate until errors are resolved.


This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands
- Run server: `uvicorn api.main:app --reload --port 8001`
- Run sentiment service: `uvicorn sentiment_service.main:app --reload --port 8000`
- Run all services with Docker: `docker compose up -d`
- Run mock tests: `./run_tests.sh --mock`
- Run integration tests: `./run_tests.sh --integration`
- Run all tests: `./run_tests.sh --all`
- Run tests in running containers: `docker compose exec api pytest`
- Run specific test: `pytest tests/path/to/test_file.py::test_function`
- Run tests with coverage: `pytest tests/ --cov=api --cov=sentiment_service`
- Run only unit tests: `pytest -m unit`
- Lint code: `flake8 .`
- Format code: `black . && isort .`
- Type checking: `mypy .`

## Code Style Guidelines
- Use Google-style docstrings with type annotations
- Follow PEP 8 and Black formatting conventions
- Use snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- Organize imports: stdlib first, third-party second, local modules last
- Use explicit typing annotations (import from typing module)
- Handle exceptions with try/except blocks and appropriate logging
- Use async/await for asynchronous code
- Use dependency injection patterns for better testability
- Document parameters and return values in docstrings
- Use Pydantic models for data validation