# RT Sentiment Analysis Restructuring Prompt

This document serves as a guiding prompt to assist with the restructuring of the RT Sentiment Analysis codebase according to the plan outlined in PROJECT_RESTRUCTURING_PLAN.md.

## Restructuring Goals

Our real-time sentiment analysis system needs a major restructuring to achieve:
1. Clearer code organization with better separation of concerns
2. Distinct environments for SIT (in WSL) and UAT (in Azure)
3. Better organized infrastructure with containerization
4. Separate mobile app for clients and web app for admins
5. Consistent and well-structured testing approach

## Key Guidelines

When working on the restructuring, follow these principles:

### Service Organization

- Each service should be self-contained with its own:
  - `src/` directory for source code
  - `tests/` directory for service-specific tests
  - `Dockerfile` for containerization
  - `requirements.txt` for dependencies
  - `README.md` for service documentation

- Service boundaries should be clear and focused on a single responsibility:
  - `data-acquisition`: Gathering data from various sources
  - `sentiment-analysis`: Processing text to extract sentiment
  - `data-tier`: Managing data storage and access (Iceberg/Dremio)
  - `api`: Providing REST and WebSocket endpoints
  - `auth`: Handling authentication and authorization

### Environment Configuration

- SIT environment (WSL):
  - Should be fully reproducible with a single setup script
  - Includes all necessary configurations for local testing
  - Uses Docker Compose for service orchestration
  - Has environment-specific tests that verify setup and functionality

- UAT environment (Azure):
  - Should be deployed using Infrastructure as Code (Terraform)
  - Includes cloud-specific configurations for Azure services
  - Has environment-specific tests to verify cloud deployment
  - Includes documentation for Azure resource requirements

### UI Development

- Mobile app (client):
  - Focused on displaying sentiment data and notifications
  - Optimized for mobile device interaction
  - Uses Flutter for cross-platform compatibility

- Admin web app:
  - Provides comprehensive management interface
  - Includes detailed analytics and reporting
  - Supports system configuration and monitoring
  - Uses Flutter Web for implementation

### Testing Structure

Every service should have a consistent testing structure:
- `unit/`: Testing individual functions and classes
- `integration/`: Testing interactions between components
- `e2e/`: Testing complete workflows
- `performance/`: Evaluating system performance

### Documentation Requirements

- Each component should have clear documentation including:
  - Purpose and responsibilities
  - API endpoints or interfaces
  - Configuration options
  - Dependencies
  - Testing procedures

## Migration Steps

When migrating code to the new structure:

1. **Start with Copy**: Copy the existing code to the new structure before making changes
2. **Update Imports**: Fix import statements to work with the new directory structure
3. **Update Dependencies**: Ensure requirements files are accurate and complete
4. **Standardize Interfaces**: Ensure consistent API design across services
5. **Verify Functionality**: Run tests to ensure functionality is preserved
6. **Document Changes**: Update documentation to reflect new organization

## Code Review Criteria

When reviewing restructured code, verify:

1. **Correctness**: Code functions as expected with no regressions
2. **Organization**: Code follows the new directory structure
3. **Documentation**: Code is well-documented with purpose and usage
4. **Testing**: Tests are maintained and passing
5. **Dependencies**: Dependencies are clearly defined and minimal

## Initial Tasks

Begin restructuring with these specific tasks:
Step 1:
1. Create the new directory structure according to the plan
2. Set up the documentation framework
3.1. create a minimal docker container and test promote from SIT to UAT using Git actions.  Put the container in a logical place.
Note: follow preferences in CLAUDE.md

Step 2:
3.2. Move the most independent services first (data-acquisition, auth)
4. Update the docker-compose files to reflect the new structure
5. Set up the SIT environment in WSL with a reproducible script
6. Move the data-tier service, including Iceberg/Dremio integration
7. Reorganize the tests according to the new structure
8. Separate the UI components into mobile and admin applications
9. Set up the UAT environment with Azure configuration

## Verification Plan

After each major restructuring step:

1. Run the existing test suite to ensure functionality is preserved
2. Verify service interactions are working correctly
3. Check that data flow is maintained
4. Ensure documentation is updated to reflect changes
5. Validate environment-specific functionality

## Additional Resources

- Review the existing architecture documentation at `/documentation/architecture/architecture_overview.md`
- Reference the data tier plan at `/documentation/future_plans/Definitive Data Tier Plan for Sentiment Analysis.md`
- Consult the UAT procedure at `/P4_UAT/LOCAL_UAT_INSTRUCTIONS.md`
- Examine the current Docker composition at `/docker-compose.yml`

## Request Format

When implementing the restructuring, use this format for each task:

```
# Task: [Short description of the task]

## Current State
[Brief description of the current implementation]

## Desired State
[Description of how it should be organized after restructuring]

## Implementation Steps
1. [Step 1]
2. [Step 2]
3. ...

## Verification Steps
1. [How to verify the restructuring was successful]
2. ...
```