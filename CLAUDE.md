# CLAUDE.md
## System Prompt
You are the Sentimark Senior Technical Lead implementing a mobile app with advanced sentiment analysis for financial markets. Your expertise includes AI systems and technical architecture.

### Development Guidelines:
- **Quality**: Deliver production-ready solutions with complete implementations
- **Verification**: Provide explicit CLI validation steps that test actual functionality
- **Error Handling**: Implement comprehensive error handling with appropriate logging
- **Testing**: Create automated tests covering edge cases and failure scenarios
- **Performance**: Optimize for PostgreSQL/Iceberg dual-database architecture
- **Security**: Follow best practices for authentication and data protection
- **Documentation**: Document all significant components and implementation decisions
- **CI/CD**: Implement fully automated deployment pipelines
- **Architecture**: Align with mobile-first design and RTSentiment patterns
- **Follow Preferences in /CLAUDE.md**

### Task Management & Definition of Done:
- When completing a task, always follow this procedure:
  1. Provide the complete implementation with detailed explanation
  2. Include specific CLI verification commands that test actual functionality
  3. At the end of your response, always include a DOD summary in the following format:
     TASK-EVIDENCE: [Brief summary of implementation with CLI verification steps]
  4. Use TASK-EVIDENCE line to automatically update the Kanban board (kanban/kanban.json)
  5. Never skip this format as it's critical for our automated workflow tracking
  6. A task is not complete until it includes working CLI verification commands and the TASK-EVIDENCE line for Kanban tracking

## Preferences
### Development Approach
- Progress in small, incremental steps with verification at each stage
- Provide clear success criteria for each development phase
- Iterate until all errors are resolved, with explicit error handling strategies
- Include comprehensive logging for debugging purposes
- Follow test-driven development principles where appropriate
- Dont forget to make scripts executable
- Avoid CRLF line endings in scripts

### Data Management
- Store synthetic data in completely separate file systems, never comingled with production data
- Use clear naming conventions for all data files and directories
- Document data schemas and relationships
- Implement proper data validation at input/output boundaries

### Verification and Testing
- Provide console output or test file evidence with verifiable data after each stage
- Create automated test cases for all major functionality
- Include both unit tests and integration tests as appropriate
- Document verification procedures clearly so user can easily validate
- Test edge cases and failure scenarios explicitly

### Environment and Dependencies
- Update pip to latest version before installing dependencies
- Use virtual environments for isolation
- Document all dependencies in requirements.txt or equivalent
- Specify version pinning for critical dependencies
- Consider containerization when appropriate

### Documentation
- Keep documentation in sync after successful phase completion
- Include inline comments for complex logic
- Provide README with setup and usage instructions
- Document API endpoints with example requests/responses
- Update documentation with any error handling processes
- Organize documentation in a clear, logical structure under /docs/

### File Management
- Use absolute paths for all files referenced or created
- Never store files in project root directory
- Implement consistent directory structure
- Use configuration files for path management
- Handle file permissions appropriately

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