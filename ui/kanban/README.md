# Sentimark UI Documentation

This directory contains documentation for the various user interfaces provided by the Sentimark project.

## Available Interfaces

Sentimark offers multiple interface options to accommodate different usage scenarios:

1. **Command Line Interface (CLI)** - For script-based automation and terminal usage

2. **Web UI** - A browser-based interface that connects to the FastAPI backend
   - [Web UI Documentation](kanban_web_ui.md)

3. **Simple App** - A text-based terminal UI for environments without graphical capabilities
   - [Simple App Documentation](simple_app.md)

## Architecture Overview

All interfaces interact with the same underlying data stored in `kanban.json`, allowing seamless switching between interfaces based on your needs and environment.

```
┌────────────────┐   ┌─────────────────┐   ┌───────────────┐
│                │   │                 │   │               │
│  Command Line  │   │    Web UI +     │   │  Simple App   │
│   Interface    │   │  FastAPI Backend│   │ (Terminal UI) │
│                │   │                 │   │               │
└───────┬────────┘   └────────┬────────┘   └───────┬───────┘
        │                     │                    │
        │                     │                    │
        ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                     /kanban_data/kanban.json            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Choosing the Right Interface

- **CLI**: Best for automation, scripting, and integration with other tools
- **Web UI**: Best for visual task management and team collaboration
- **Simple App**: Best for remote SSH sessions and environments without GUI

## Getting Started

See the individual documentation files for detailed setup and usage instructions for each interface.