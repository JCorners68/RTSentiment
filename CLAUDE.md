# CLAUDE.md
## Preferences
- progress in slow incremental steps with progress verified at each step.
- be clear about synthetic data.  it should be stored in a completely separte file system and not comingled with other data.
- user must see at console or in a test file evidence of success that includes verifable data.
- update pip to the latest version to minimize dependency problems.
- keep documentation in sync after successful completion of a phase.
- be clear about verification procedure so that user can verify easily.
- iterate until errors are resolved.
- files referenced or created should use entire path so I can find them. 
- do not store files in the root directory of the project.


This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build/Lint/Test Commands
### Running Services
- Run API service: `cd services/api && uvicorn src.main:app --reload --port 8001`
- Run sentiment analysis service: `cd services/sentiment-analysis && uvicorn src.main:app --reload --port 8000`
- Run data acquisition service: `cd services/data-acquisition && uvicorn src.main:app --reload --port 8002` 
- Run auth service: `cd services/auth && uvicorn src.main:app --reload --port 8003`
- Run data tier service: `cd services/data-tier && uvicorn src.main:app --reload --port 8004`

### Docker Commands
- Run all services with Docker: `cd infrastructure && docker compose up -d`
- Run monitoring stack: `cd infrastructure && docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d`
- Run development setup: `cd infrastructure && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`

### Environment Setup
- Setup SIT environment: `cd environments/sit && ./setup.sh`
- Setup UAT environment: `cd environments/uat && ./setup.sh`
- Verify environment setup: `cd environments/sit/tests && pytest`

### Testing
- Run service-specific tests: `cd services/[service-name] && pytest tests/`
- Run mock tests: `./scripts/ci/run_tests.sh --mock`
- Run integration tests: `./scripts/ci/run_tests.sh --integration`
- Run all tests: `./scripts/ci/run_tests.sh --all`
- Run tests in running containers: `docker compose exec [service-name] pytest`
- Run specific test: `cd services/[service-name] && pytest tests/path/to/test_file.py::test_function`
- Run tests with coverage: `cd services/[service-name] && pytest tests/ --cov=src`
- Run only unit tests: `cd services/[service-name] && pytest tests/unit -m unit`
- Run performance tests: `cd services/[service-name] && pytest tests/performance`

### Code Quality
- Lint code: `cd services/[service-name] && flake8 src tests`
- Format code: `cd services/[service-name] && black src tests && isort src tests`
- Type checking: `cd services/[service-name] && mypy src tests`

### UI Development
- Run mobile app: `cd ui/mobile && flutter run`
- Run admin web app: `cd ui/admin && flutter run -d web`

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