# Real-Time Sentiment Analysis Architecture Documentation

This directory contains the architectural documentation for the Real-Time Sentiment Analysis system. The documentation includes diagrams, component descriptions, and architectural decisions.

## Architecture Documents

### 1. [System Architecture](./system_architecture.html)
   - [Updated System Architecture](./updated_system_architecture.md) (includes Flutter integration)

An overview of the full system architecture, including:
- Data sources and acquisition
- Event ingestion
- Processing tier
- API layer
- Caching
- Database persistence
- Client applications
- Monitoring
- Authentication

This document provides a high-level view of how all components interact in a production environment.

### 2. [Local Development Architecture](./local_development.html)

A detailed view of the local development environment, including:
- Docker Compose setup
- Service dependencies
- Development workflow
- Local testing configuration

This document helps developers understand how to run and develop with the system locally.

### 3. [Testing Architecture](./testing_architecture.html)

A comprehensive overview of the testing strategy, including:
- Unit testing
- Integration testing
- End-to-end testing
- Test data generation
- Mocking strategy
- Test automation

This document explains how the system is tested at various levels of abstraction.

### 4. [Flutter Architecture](./old-flutter_architecture.md)

Details of the Flutter dashboard implementation, including:
- Layered architecture
- State management
- API integration
- Component structure
- Data flow
- UI architecture
- Future enhancements

This document explains how the Flutter dashboard is designed and how it interacts with the backend.

## Architectural Diagrams

The architecture documentation includes several key diagrams:

1. **System Architecture Diagram**: SVG visualization of the overall system
2. **Local Development Diagram**: Mermaid diagram of local environment
3. **Testing Flow Diagram**: Mermaid diagram showing test execution flow
4. **Flutter Component Diagram**: Mermaid diagram of Flutter app architecture
5. **Data Flow Diagram**: Sequence diagram showing data processing flow
6. **Class Diagram**: UML class diagram of key components

## Architectural Decisions

### Separation of Concerns

The system follows a clear separation of concerns with distinct services:
- Data acquisition services
- Event ingestion
- Sentiment analysis processing
- API layer
- Client applications

### Event-Driven Architecture

The core system uses an event-driven architecture with:
- Asynchronous event processing
- Priority-based message queues
- Decoupled components

### Frontend Migration

The frontend is being migrated from Streamlit to Flutter to provide:
- Better performance
- Enhanced UI/UX
- Cross-platform support
- Native mobile capabilities

### API Design

The API follows RESTful design principles with:
- Clearly defined resources
- Standard HTTP methods
- Consistent response formats
- Authentication middleware

## Getting Started

To visualize the architecture diagrams:
1. Open the HTML files in a web browser to view the SVG diagrams
2. For the Mermaid diagrams in markdown files, use a Mermaid-compatible viewer or editor

## Contributing

When making architectural changes:
1. Update the relevant diagrams
2. Document the rationale behind changes
3. Ensure backward compatibility or provide migration paths
4. Update testing strategies to match architectural changes