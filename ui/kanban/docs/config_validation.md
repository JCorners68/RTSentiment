# Configuration Validation System

This document describes the configuration validation system in CLI Kanban. The system ensures that configuration files are valid, checks the environment for potential issues, and provides self-healing capabilities for common configuration problems.

## Overview

The configuration validation system consists of three main components:

1. **Schema Validation**: Validates configuration files against a JSON schema
2. **Environment Checks**: Verifies that the environment meets requirements
3. **Self-Healing**: Automatically fixes common configuration issues

These components work together to provide a robust configuration management system that prevents errors and improves user experience.

## Schema Validation

The schema validation component ensures that configuration files have the correct structure and data types. It uses JSON Schema (Draft 7) to define the expected structure and validate configuration files against it.

### Configuration Schema

The configuration schema is defined in `src/config/schemas/config_schema.json`. It specifies the required fields, field types, and constraints for the configuration file. The schema includes validation for:

- Application settings
- Data paths
- Logging configuration
- UI settings
- Server configuration
- Feature flags
- N8n integration settings
- Checkpoint configuration
- Environment requirements
- Security settings

### Validation Process

Configuration validation happens in several places:

1. During CLI Kanban startup
2. When using the `kanban config validate` command
3. Before any operation that relies on specific configuration settings

If validation fails, the system provides detailed error messages that help users identify and fix the issues.

### Example Validation

```python
from src.config.validator import validate_config

# Validate a configuration file
is_valid, error_messages = validate_config("/path/to/config.yaml")

if not is_valid:
    print("Configuration validation failed:")
    for error in error_messages:
        print(f"  - {error}")
```

## Environment Checks

The environment checks component verifies that the system environment meets the requirements for running CLI Kanban. It checks for:

1. **Python Version**: Ensures that the Python version is sufficient
2. **Node.js Version**: Checks if Node.js is installed and meets version requirements (for the server component)
3. **Directory Structure**: Verifies that required directories exist and are accessible
4. **Disk Space**: Checks if there's enough disk space for normal operation

### Environment Check Process

Environment checks are performed:

1. During CLI Kanban startup
2. When using the `kanban config check-env` command
3. Before operations that have specific environment requirements

When issues are detected, they are categorized by severity (critical, warning, info) and marked as fixable or not fixable.

### Example Environment Check

```python
from src.config.validator import check_environment

# Load configuration from somewhere
config = {...}

# Check the environment
issues = check_environment(config)

if not issues:
    print("Environment checks passed!")
else:
    print(f"Found {len(issues)} environment issues:")
    for issue in issues:
        print(f"[{issue['severity']}] {issue['message']}")
        if issue.get("fixable"):
            print(f"  Can be fixed with action: {issue.get('fix_action')}")
```

## Self-Healing Capabilities

The self-healing component automatically fixes common configuration issues. This includes:

1. **Missing Sections**: Adds default sections if they're missing
2. **Missing Directories**: Creates required directories if they don't exist
3. **Permission Issues**: Fixes permissions for directories if they're not accessible
4. **Default Values**: Provides default values for missing required fields

### Self-Healing Process

Self-healing can be triggered:

1. During CLI Kanban startup (with the `--auto-fix` flag)
2. Using the `kanban config repair` command
3. Programmatically through the API

Before making any changes, the system creates a backup of the original configuration file to ensure that no data is lost.

### Example Self-Healing

```python
from src.config.validator import heal_configuration

# Attempt to heal a configuration file
success, messages = heal_configuration("/path/to/config.yaml")

if success:
    print("Configuration healed successfully!")
    for message in messages:
        print(f"  - {message}")
else:
    print("Configuration healing failed:")
    for message in messages:
        print(f"  - {message}")
```

## Command Line Interface

The configuration validation system is accessible through the CLI Kanban command-line interface:

```bash
# Validate a configuration file
python -m src.main config validate [--config-file path/to/config.yaml]

# Check the environment
python -m src.main config check-env [--config-file path/to/config.yaml]

# Repair a configuration file
python -m src.main config repair [--config-file path/to/config.yaml]
```

## Demonstration Script

A demonstration script is provided at `src/config/demo_validator.py` to showcase the capabilities of the configuration validation system. It can be used to:

1. Create valid or invalid sample configurations
2. Validate configurations
3. Run environment checks
4. Demonstrate self-healing

### Using the Demonstration Script

```bash
# Create and validate a valid configuration
./src/config/demo_validator.py --valid

# Create and validate an invalid configuration
./src/config/demo_validator.py --invalid

# Try to heal an invalid configuration
./src/config/demo_validator.py --invalid --heal

# Use an existing configuration file
./src/config/demo_validator.py --file path/to/config.yaml
```

## Best Practices

### Validation during Development

During development, it's recommended to validate the configuration before using it. This can be done using the `validate_config` function:

```python
from src.config.validator import validate_config

def my_function(config_path):
    # Validate the configuration
    is_valid, error_messages = validate_config(config_path)
    if not is_valid:
        # Handle validation errors
        for error in error_messages:
            print(f"Configuration error: {error}")
        return
    
    # Proceed with the function
    ...
```

### Environment Checks before Critical Operations

Before performing critical operations, it's a good practice to check the environment:

```python
from src.config.validator import check_environment

def critical_operation(config):
    # Check the environment
    issues = check_environment(config)
    critical_issues = [i for i in issues if i["severity"] == "critical"]
    
    if critical_issues:
        # Handle critical issues
        for issue in critical_issues:
            print(f"Critical issue: {issue['message']}")
        return
    
    # Proceed with the operation
    ...
```

### Self-Healing with User Consent

When automatically fixing configuration issues, it's important to get user consent:

```python
from src.config.validator import heal_configuration

def fix_config(config_path):
    print(f"Configuration at {config_path} has issues.")
    response = input("Do you want to try to fix them? (y/n): ")
    
    if response.lower() == 'y':
        success, messages = heal_configuration(config_path)
        if success:
            print("Configuration fixed successfully!")
        else:
            print("Failed to fix configuration.")
    else:
        print("Configuration not modified.")
```

## Integration with Other Components

### Configuration Settings Module

The validation system integrates with the configuration settings module (`src/config/settings.py`) to ensure that the configuration is validated before it's used.

### CLI Commands

The validation system is exposed through CLI commands in the CLI Kanban main module, making it accessible to users.

### Logging System

The validation system uses the logging system to log validation errors, environment issues, and self-healing actions, providing a record of all configuration-related operations.

## Error Handling

The validation system includes robust error handling:

1. **Validation Errors**: Detailed error messages that point to the specific issue
2. **Environment Issues**: Categorized by severity with clear messages
3. **Self-Healing Failures**: Descriptive error messages and automatic backup of the original configuration

All errors are logged and, when appropriate, displayed to the user with suggestions for how to fix them.

## Summary

The configuration validation system provides a robust framework for ensuring that CLI Kanban is properly configured and running in a suitable environment. It combines schema validation, environment checks, and self-healing capabilities to provide a seamless user experience and prevent configuration-related errors.