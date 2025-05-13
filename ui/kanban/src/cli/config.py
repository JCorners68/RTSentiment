"""
Configuration Management CLI Commands

This module provides CLI commands for managing configuration.
"""

import os
import sys
import click
import yaml
from pathlib import Path
from typing import Optional

from ..config.validator import (
    validate_config,
    check_environment,
    heal_configuration,
    ConfigValidator,
    EnvironmentChecker,
    ConfigHealer
)
from ..ui.display import display_validation_results, display_environment_issues, display_healing_results
from ..utils.exceptions import ConfigurationError


@click.group(name="config")
def config_group():
    """Configuration management commands."""
    pass


@config_group.command(name="validate")
@click.option("--config-file", "-c", type=click.Path(exists=True), help="Path to the configuration file")
def validate_command(config_file: Optional[str] = None):
    """Validate the configuration file."""
    if not config_file:
        # Try to find the configuration file in the default location
        default_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("kanban.yaml"),
            Path("kanban.yml"),
            Path.home() / ".config" / "kanban" / "config.yaml",
        ]
        
        for path in default_paths:
            if path.exists():
                config_file = str(path)
                break
        
        if not config_file:
            raise click.UsageError(
                "No configuration file specified and no default configuration file found. "
                "Please specify a configuration file with --config-file."
            )
    
    # Validate the configuration
    is_valid, error_messages = validate_config(config_file)
    
    # Display the results
    display_validation_results(is_valid, error_messages, config_file)
    
    # Exit with an error code if validation failed
    if not is_valid:
        sys.exit(1)


@config_group.command(name="check-env")
@click.option("--config-file", "-c", type=click.Path(exists=True), help="Path to the configuration file")
def check_env_command(config_file: Optional[str] = None):
    """Check the environment for issues."""
    # Find the configuration file
    if not config_file:
        # Use the same logic as validate_command
        default_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("kanban.yaml"),
            Path("kanban.yml"),
            Path.home() / ".config" / "kanban" / "config.yaml",
        ]
        
        for path in default_paths:
            if path.exists():
                config_file = str(path)
                break
        
        if not config_file:
            raise click.UsageError(
                "No configuration file specified and no default configuration file found. "
                "Please specify a configuration file with --config-file."
            )
    
    # Load the configuration
    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration file: {e}")
    
    # Check the environment
    checker = EnvironmentChecker()
    issues = checker.run_all_checks(config)
    
    # Display the results
    display_environment_issues(issues, config_file)
    
    # Exit with an error code if there are critical issues
    if any(issue["severity"] == "critical" for issue in issues):
        sys.exit(1)


@config_group.command(name="repair")
@click.option("--config-file", "-c", type=click.Path(exists=True), help="Path to the configuration file")
@click.option("--force", "-f", is_flag=True, help="Force repair without confirmation")
def repair_command(config_file: Optional[str] = None, force: bool = False):
    """Attempt to repair the configuration file."""
    # Find the configuration file
    if not config_file:
        # Use the same logic as validate_command
        default_paths = [
            Path("config.yaml"),
            Path("config.yml"),
            Path("kanban.yaml"),
            Path("kanban.yml"),
            Path.home() / ".config" / "kanban" / "config.yaml",
        ]
        
        for path in default_paths:
            if path.exists():
                config_file = str(path)
                break
        
        if not config_file:
            raise click.UsageError(
                "No configuration file specified and no default configuration file found. "
                "Please specify a configuration file with --config-file."
            )
    
    # Confirm unless --force is used
    if not force:
        if not click.confirm(
            f"This will attempt to repair the configuration file at {config_file}. "
            f"A backup will be created. Continue?"
        ):
            click.echo("Repair cancelled.")
            return
    
    # Try to repair the configuration
    success, messages = heal_configuration(config_file)
    
    # Display the results
    display_healing_results(success, messages, config_file)
    
    # Exit with an error code if repair failed
    if not success:
        sys.exit(1)


@config_group.command(name="init")
@click.option("--output", "-o", type=click.Path(), help="Path to write the configuration file")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing file without confirmation")
def init_command(output: Optional[str] = None, force: bool = False):
    """Initialize a new configuration file with default values."""
    # Determine the output file
    if not output:
        output = "config.yaml"
    
    output_path = Path(output)
    
    # Check if the file exists
    if output_path.exists() and not force:
        if not click.confirm(f"File {output} already exists. Overwrite?"):
            click.echo("Initialization cancelled.")
            return
    
    # Load the default configuration
    script_dir = Path(__file__).resolve().parent.parent
    default_config_path = script_dir / "config" / "examples" / "default_config.yaml"
    
    if not default_config_path.exists():
        raise ConfigurationError(f"Default configuration template not found at {default_config_path}")
    
    try:
        with open(default_config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        raise ConfigurationError(f"Failed to load default configuration template: {e}")
    
    # Write the configuration file
    try:
        with open(output_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        raise ConfigurationError(f"Failed to write configuration file: {e}")
    
    click.echo(f"Configuration file initialized at {output_path}")
    
    # Validate the configuration
    is_valid, error_messages = validate_config(output_path)
    
    if not is_valid:
        click.echo("Warning: The generated configuration is not valid:")
        for error in error_messages:
            click.echo(f"  - {error}")
    else:
        click.echo("The configuration is valid.")


# Register this command group in the CLI
def register_commands(cli):
    """Register the config commands with the CLI."""
    cli.add_command(config_group)