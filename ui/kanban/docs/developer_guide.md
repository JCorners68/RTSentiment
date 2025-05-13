# Kanban CLI Developer Guide

This guide provides developers with detailed information about the architecture, components, and implementation details of the Kanban CLI application, with particular focus on the Evidence Management System which is a priority feature.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Evidence Management System](#evidence-management-system) (Priority Feature)
- [Testing](#testing)
- [Contributing](#contributing)
- [Future Development](#future-development)

## Architecture Overview

The Kanban CLI application follows a modular architecture with clear separation of concerns:

```
┌───────────────────────┐
│                       │
│   CLI Interface       │
│   (Click Framework)   │
│                       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐     ┌───────────────────────┐
│                       │     │                       │
│   Command Handlers    │◄───►│   Display Components  │
│                       │     │   (Rich Library)      │
│                       │     │                       │
└───────────┬───────────┘     └───────────────────────┘
            │
            ▼
┌───────────────────────┐
│                       │
│   Business Logic      │
│                       │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐     ┌───────────────────────┐
│                       │     │                       │
│   Storage Layer       │◄───►│   File System         │
│                       │     │                       │
└───────────────────────┘     └───────────────────────┘
```

The architecture also includes a local API server component for external integrations:

```
┌───────────────────────┐     ┌───────────────────────┐
│                       │     │                       │
│   CLI Application     │◄───►│   Local API Server    │
│                       │     │   (Express.js)        │
│                       │     │                       │
└───────────────────────┘     └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │                       │
                              │   External Systems    │
                              │   (n8n, Claude AI)    │
                              │                       │
                              └───────────────────────┘
```

## Project Structure

The project follows a structured organization:

```
ui/kanban/
├── src/                 # Source code
│   ├── cli/             # CLI command modules
│   │   ├── __init__.py  # Command group registration
│   │   ├── tasks.py     # Task commands
│   │   ├── board.py     # Board commands
│   │   ├── epics.py     # Epic commands
│   │   └── evidence.py  # Evidence commands (priority)
│   ├── models/          # Data models
│   │   ├── schemas.py   # Core schema classes
│   │   ├── evidence_schema.py # Evidence schemas (priority)
│   │   ├── validation.py # Data validation
│   │   └── evidence_validation.py # Evidence validation (priority)
│   ├── data/            # Data access layer
│   │   ├── storage.py   # Base storage classes
│   │   └── evidence_storage.py # Evidence storage (priority)
│   ├── ui/              # User interface components
│   │   └── display.py   # Rich-based display utilities
│   ├── utils/           # Utility functions
│   │   ├── logging.py   # Logging configuration
│   │   ├── exceptions.py # Custom exceptions
│   │   └── file_handlers.py # File handling utilities
│   ├── config/          # Configuration
│   │   └── settings.py  # Configuration management
│   └── main.py          # Application entry point
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── fixtures/        # Test fixtures
├── data/                # Data storage
│   ├── tasks/           # Task storage
│   ├── epics/           # Epic storage
│   ├── boards/          # Board storage
│   └── evidence/        # Evidence storage (priority)
│       ├── index/       # Evidence indices
│       └── attachments/ # Evidence attachments
├── docs/                # Documentation
│   ├── commands.md      # Command reference
│   ├── data_model.md    # Data model documentation
│   └── developer_guide.md # This guide
├── logs/                # Application logs
├── server/              # Local API server
│   ├── index.js         # Server entry point
│   ├── routes/          # API routes
│   └── middleware/      # Server middleware
└── config.yaml          # Main configuration file
```

## Core Components

### CLI Framework (Click)

The CLI interface is built using the Click framework, which provides a clean way to define commands, arguments, and options. Commands are organized into groups for better structure:

```python
@click.group(name="evidence")
def evidence_group():
    """Evidence management commands."""
    pass

@evidence_group.command(name="list")
@click.option("--category", help="Filter by category")
def list_evidence(category):
    """List evidence items with optional filtering."""
    # Implementation...
```

### Data Models

Data models provide structured representations of application entities:

- **TaskSchema**: Represents individual work items
- **EpicSchema**: Groups related tasks
- **BoardSchema**: Defines board structure
- **EvidenceSchema**: Structured evidence items (priority feature)
- **AttachmentSchema**: Files associated with evidence (priority feature)

### Storage Layer

The storage layer handles persistence and retrieval:

- **FileStorage**: Base class for file-based storage
- **TaskStorage**: Manages task persistence
- **EpicStorage**: Manages epic persistence
- **BoardStorage**: Manages board persistence
- **EvidenceStorage**: Manages evidence persistence (priority feature)

### User Interface

The UI components use the Rich library to provide colorful, formatted terminal output:

- **Console**: Main display interface
- **Tables**: Formatted data display
- **Panels**: Boxed content display
- **Progress**: Progress indicators
- **Formatting**: Color and style utilities

### Configuration Management

The application uses a YAML-based configuration system:

- **config.yaml**: Main configuration file
- **settings.py**: Configuration loading and management
- **Environment variables**: Support for environment-based configuration

## Data Flow

1. **User Input**: User enters a command in the CLI
2. **Command Parsing**: Click framework parses command and options
3. **Command Handling**: Command handler processes the request
4. **Business Logic**: Application logic is applied
5. **Storage Access**: Data is retrieved from or saved to storage
6. **Response Formatting**: Rich library formats the response
7. **Display Output**: Formatted output is shown to the user

## Evidence Management System

> **Priority Feature**: The Evidence Management System is a priority feature of this application.

### Components

The Evidence Management System consists of several key components:

1. **Evidence Schema**: Defines the structure of evidence items
2. **Attachment Schema**: Defines the structure of file attachments
3. **Evidence Validation**: Validates evidence data
4. **Evidence Storage**: Manages persistence of evidence and attachments
5. **Evidence Commands**: CLI commands for evidence management
6. **Search System**: Advanced search capabilities for evidence

### Implementation Details

#### Evidence Schema

The `EvidenceSchema` class provides a comprehensive data model:

```python
class EvidenceSchema:
    def __init__(
        self,
        title: str,
        description: str,
        category: Union[EvidenceCategory, str] = EvidenceCategory.OTHER,
        relevance_score: Union[EvidenceRelevance, str] = EvidenceRelevance.MEDIUM,
        # Additional fields...
    ):
        # Implementation...
```

#### Evidence Storage

The `EvidenceStorage` class handles persistence with advanced features:

1. **Indexing System**: Multiple indices for efficient retrieval
   - Tag-based index
   - Category-based index
   - Relationship index
   - Full-text search index

2. **Attachment Handling**: Secure file storage and retrieval
   - Path sanitization
   - MIME type detection
   - Content preview generation
   - File integrity verification

3. **Search Capabilities**: Multi-faceted search system
   - Text search across title, description, content
   - Category and tag filtering
   - Date range filtering
   - Relationship-based queries

#### CLI Commands

The evidence command module provides a comprehensive interface:

```python
@evidence_group.command(name="search")
@click.option("--text", help="Search for text")
@click.option("--category", help="Filter by category")
# Additional options...
def search_evidence(text, category, ...):
    """Search for evidence with advanced filtering."""
    # Implementation...
```

### Security Considerations

The Evidence Management System implements several security measures:

1. **Path Sanitization**: Prevents directory traversal attacks
2. **Input Validation**: Comprehensive validation of all user inputs
3. **File Type Verification**: Checks file types to prevent security issues
4. **Transaction Support**: Atomic operations with rollback capability

## Testing

The application includes a comprehensive test suite:

1. **Unit Tests**: Test individual components in isolation
   - `test_validation.py`: Tests schema validation
   - `test_storage.py`: Tests storage operations
   - `test_commands.py`: Tests command functionality

2. **Integration Tests**: Test component interactions
   - `test_workflow.py`: Tests complete workflows

3. **Test Fixtures**: Provides sample data for testing
   - `tasks.json`: Sample tasks
   - `epics.json`: Sample epics
   - `evidence.json`: Sample evidence items

## Contributing

### Development Environment

1. **Setup**:
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd ui/kanban
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Running Tests**:
   ```bash
   python -m pytest tests/
   ```

3. **Linting**:
   ```bash
   # Run linting checks
   flake8 src/ tests/
   ```

### Development Guidelines

1. **Code Style**: Follow PEP 8 guidelines for Python code
2. **Documentation**: Add docstrings to all functions and classes
3. **Testing**: Write tests for all new functionality
4. **Commit Messages**: Use clear, descriptive commit messages
5. **Pull Requests**: Create detailed pull requests with proper descriptions

## Future Development

Planned future enhancements:

1. **n8n Integration**: Integrate with n8n automation middleware
2. **Claude AI Integration**: Integrate with Claude for AI-enhanced capabilities
3. **Web UI**: Provide a web-based user interface
4. **Advanced Analytics**: Add reporting and analytics features
5. **Team Collaboration**: Add multi-user support

### Evidence Management System Roadmap

Future enhancements for the Evidence Management System (priority feature):

1. **Advanced Categorization**: Hierarchical category system
2. **AI-Based Tagging**: Automatic tag suggestions using Claude AI
3. **Evidence Visualization**: Graph-based visualization of evidence relationships
4. **External Integrations**: Integration with document management systems
5. **Automated Evidence Collection**: Automated collection from external sources
