#!/usr/bin/env python3
"""
Configuration Validator Demo

This script demonstrates the configuration validation and self-healing capabilities.
"""

import os
import sys
import yaml
from pathlib import Path
import logging
import tempfile
import argparse

# Add the parent directory to sys.path to import modules
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from src.config.validator import (
    validate_config,
    check_environment,
    heal_configuration,
    ConfigValidator,
    EnvironmentChecker,
    ConfigHealer
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_config(output_path: Path, valid: bool = True) -> Path:
    """
    Create a sample configuration file for testing.
    
    Args:
        output_path: Directory to write the file
        valid: Whether to create a valid or invalid config
        
    Returns:
        Path to the created file
    """
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    
    # Sample valid configuration
    config = {
        "app": {
            "name": "cli_kanban",
            "version": "0.1.0",
            "display_name": "CLI Kanban",
            "description": "Command-line Kanban board with evidence management"
        },
        "data_paths": {
            "base_dir": "data",
            "tasks_file": "tasks.yaml",
            "epics_file": "epics.yaml",
            "board_file": "board.yaml",
            "evidence_dir": "evidence"
        },
        "logging": {
            "level": "INFO",
            "file": "logs/kanban.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
    
    # If creating an invalid config, mess it up
    if not valid:
        # Remove a required field
        del config["app"]["version"]
        
        # Add an invalid field (wrong type)
        config["logging"]["level"] = 123
        
        # Remove base_dir
        if "base_dir" in config["data_paths"]:
            del config["data_paths"]["base_dir"]
    
    # Write to a temporary file
    config_file = output_path / ("valid_config.yaml" if valid else "invalid_config.yaml")
    with open(config_file, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_file


def demonstrate_validation(config_file: Path) -> None:
    """
    Demonstrate configuration validation.
    
    Args:
        config_file: Path to the configuration file
    """
    logger.info(f"Validating configuration file: {config_file}")
    is_valid, error_messages = validate_config(config_file)
    
    if is_valid:
        logger.info("✅ Configuration is valid!")
    else:
        logger.error("❌ Configuration validation failed!")
        for error in error_messages:
            logger.error(f"  - {error}")


def demonstrate_environment_checks(config_file: Path) -> None:
    """
    Demonstrate environment checks.
    
    Args:
        config_file: Path to the configuration file
    """
    logger.info(f"Running environment checks with configuration: {config_file}")
    
    # Load the configuration
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    # Run environment checks
    checker = EnvironmentChecker()
    issues = checker.run_all_checks(config)
    
    if not issues:
        logger.info("✅ Environment checks passed!")
    else:
        logger.warning(f"⚠️ Found {len(issues)} environment issues:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  {i}. [{issue['severity']}] {issue['message']}")
            if issue.get("fixable"):
                logger.info(f"     Can be fixed with action: {issue.get('fix_action', 'unknown')}")
            else:
                logger.info(f"     Not automatically fixable")


def demonstrate_self_healing(config_file: Path) -> None:
    """
    Demonstrate self-healing capabilities.
    
    Args:
        config_file: Path to the configuration file
    """
    logger.info(f"Attempting to heal configuration: {config_file}")
    
    # Create a backup
    backup_file = config_file.with_suffix(".bak")
    with open(config_file, "r") as src:
        with open(backup_file, "w") as dst:
            dst.write(src.read())
    
    # Try to heal the configuration
    success, messages = heal_configuration(config_file)
    
    if success:
        logger.info("✅ Configuration healed successfully!")
        for message in messages:
            logger.info(f"  - {message}")
    else:
        logger.error("❌ Configuration healing failed!")
        for message in messages:
            logger.error(f"  - {message}")
    
    # Validate the healed configuration
    demonstrate_validation(config_file)
    
    # Restore from backup if requested
    if not success:
        logger.info(f"Restoring configuration from backup: {backup_file}")
        with open(backup_file, "r") as src:
            with open(config_file, "w") as dst:
                dst.write(src.read())


def main():
    """Main function to demonstrate the validator functionality."""
    parser = argparse.ArgumentParser(description="Configuration Validator Demo")
    parser.add_argument("--valid", action="store_true", help="Create a valid configuration")
    parser.add_argument("--invalid", action="store_true", help="Create an invalid configuration")
    parser.add_argument("--file", type=str, help="Use an existing configuration file")
    parser.add_argument("--heal", action="store_true", help="Attempt to heal the configuration")
    
    args = parser.parse_args()
    
    # Determine the config file to use
    if args.file:
        config_file = Path(args.file)
        if not config_file.exists():
            logger.error(f"Configuration file does not exist: {config_file}")
            return
    else:
        # Create a temp directory
        temp_dir = Path(tempfile.mkdtemp())
        
        # Create a sample config
        valid = not args.invalid
        config_file = create_sample_config(temp_dir, valid)
        logger.info(f"Created {'valid' if valid else 'invalid'} configuration file: {config_file}")
    
    # Demonstrate validation
    demonstrate_validation(config_file)
    
    # Demonstrate environment checks
    demonstrate_environment_checks(config_file)
    
    # Demonstrate self-healing if requested
    if args.heal:
        demonstrate_self_healing(config_file)


if __name__ == "__main__":
    main()