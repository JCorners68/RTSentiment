# RT Sentiment Analysis - Architecture Overview

## System Architecture

This document provides an overview of the RT Sentiment Analysis system architecture, describing the main components, their interactions, and the overall system design.

## System Components

The RT Sentiment Analysis system consists of the following main components:

### Data Acquisition Service
- Responsible for gathering data from various sources
- Processes and normalizes incoming data
- Forwards data to the sentiment analysis pipeline

### Sentiment Analysis Service
- Analyzes text to determine sentiment
- Uses NLP models to extract sentiment scores
- Processes data in real-time

### Data Tier Service
- Manages data storage and retrieval
- Implements dual-database architecture:
  - PostgreSQL for development and testing
  - Apache Iceberg for production
- Provides abstraction layer for transparent database access
- Features repository pattern for clean separation between domain logic and data access
- Includes schema synchronization between PostgreSQL and Iceberg

### API Service
- Provides REST and WebSocket endpoints
- Manages client connections
- Delivers real-time updates

### Auth Service
- Handles authentication and authorization
- Manages user sessions
- Controls access to protected resources

## Component Interactions

![Component Interactions Diagram](arch.html)

![Data Tier Architecture Diagram](data_tier_architecture.html)

The components interact through well-defined interfaces:

1. **Repository Interfaces**: Define the contract for data access operations
2. **Service Layer**: Coordinates between business logic and repositories
3. **Factory Pattern**: Dynamically selects appropriate database implementation
4. **Feature Flags**: Controls which database backend is used based on environment

## Data Flow

1. Data is acquired from external sources via the Data Acquisition Service
2. Raw data is processed and sent to the Sentiment Analysis Service
3. Sentiment results are stored in the Data Tier Service
4. Results are made available through the API Service
5. Client applications consume the data via REST or WebSocket connections

## Deployment Architecture

The system is deployed in three distinct environments, each with its own database configuration:

### Development Environment (WSL)
- Local development and testing
- Docker Compose for service orchestration
- PostgreSQL for data storage
- Feature flags set to use PostgreSQL backend

### SIT Environment (Azure)
- System Integration Testing environment
- Azure Container Apps for services
- PostgreSQL Flexible Server for database
- Initial testing of Iceberg implementation with feature flags
- Terraform-based deployment with Azure Storage for state

### UAT Environment (Azure)
- User Acceptance Testing environment
- Azure Kubernetes Service (AKS) for container orchestration
- Full Iceberg implementation on Azure Data Lake Storage
- Feature flags set to use Iceberg backend by default
- Terraform-based deployment with proximate resource placement

## Technology Stack

- **Backend Services:**
  - Python FastAPI for API implementations
  - Repository pattern for data access abstraction
  - Factory pattern for implementation selection

- **Database Technologies:**
  - PostgreSQL for development and testing environments
  - Apache Iceberg for production data lake management
  - Azure Data Lake Storage Gen2 for Iceberg tables
  - Schema synchronization tools for maintaining compatibility

- **Client Applications:**
  - Flutter for cross-platform mobile and web interfaces

- **Infrastructure:**
  - Docker for containerization and local development
  - Azure Container Apps for SIT environment
  - Azure Kubernetes Service (AKS) for UAT environment
  - Terraform for infrastructure as code
  - Feature flags for controlling database backend selection

## Security Architecture

[To be completed]

## Performance Considerations

The dual-database architecture balances development agility with production performance:

### PostgreSQL (Development/Testing)
- Faster development iterations with familiar SQL queries
- Standard ACID transaction support
- Simplified local development with Docker containers
- Lower operational complexity for testing environments

### Apache Iceberg (Production)
- Optimized for analytical workloads with partition pruning
- Schema evolution without table rebuilds
- Time travel capabilities for historical data access
- Integration with big data processing engines
- Efficient storage utilization through file-level operations

### Implementation Considerations
- Repository abstraction adds minimal overhead (~1-2ms per operation)
- Feature flags allow gradual migration between backends
- Both backends implement optimized query patterns for common operations
- Schema synchronization ensures consistency across environments