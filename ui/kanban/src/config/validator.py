"""
Configuration Validator

This module provides schema validation for configuration files
and environment checks to ensure the CLI Kanban operates correctly.
"""

import os
import sys
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Union, Set
import logging
import jsonschema
from jsonschema import validators, Draft7Validator

# Setup logger
logger = logging.getLogger(__name__)

# Path to the schema files
SCHEMA_DIR = Path(__file__).parent / "schemas"


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        """
        Initialize ConfigValidationError.
        
        Args:
            message: Error message
            errors: List of specific validation errors
        """
        self.message = message
        self.errors = errors if errors else []
        super().__init__(self.message)


class ConfigValidator:
    """Validates configuration against schemas."""
    
    def __init__(self, schema_name: str = "config_schema.json"):
        """
        Initialize the validator with a schema.
        
        Args:
            schema_name: Name of the schema file in the schemas directory
        """
        self.schema_path = SCHEMA_DIR / schema_name
        self._load_schema()
    
    def _load_schema(self) -> None:
        """Load the schema from file."""
        try:
            if not self.schema_path.exists():
                # Create schemas directory if it doesn't exist
                self.schema_path.parent.mkdir(exist_ok=True, parents=True)
                
                # Create a default schema if none exists
                self._create_default_schema()
            
            with open(self.schema_path, 'r') as f:
                self.schema = json.load(f)
            
            # Validate that the schema itself is valid
            Draft7Validator.check_schema(self.schema)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schema file {self.schema_path}: {e}")
            raise ConfigValidationError(f"Invalid schema file: {e}")
        except Exception as e:
            logger.error(f"Error loading schema {self.schema_path}: {e}")
            raise ConfigValidationError(f"Schema loading error: {e}")
    
    def _create_default_schema(self) -> None:
        """Create a default schema if none exists."""
        default_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "CLI Kanban Configuration Schema",
            "description": "Schema for validating CLI Kanban configuration files",
            "type": "object",
            "required": ["app", "data_paths", "logging"],
            "properties": {
                "app": {
                    "type": "object",
                    "required": ["name", "version"],
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "display_name": {"type": "string"},
                        "description": {"type": "string"}
                    }
                },
                "data_paths": {
                    "type": "object",
                    "required": ["base_dir"],
                    "properties": {
                        "base_dir": {"type": "string"},
                        "tasks_file": {"type": "string"},
                        "epics_file": {"type": "string"},
                        "board_file": {"type": "string"},
                        "evidence_dir": {"type": "string"}
                    }
                },
                "logging": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                        },
                        "file": {"type": "string"},
                        "format": {"type": "string"},
                        "max_size": {"type": "integer"},
                        "backup_count": {"type": "integer"}
                    }
                },
                "ui": {
                    "type": "object",
                    "properties": {
                        "color_theme": {"type": "string"},
                        "table_style": {"type": "string"},
                        "compact": {"type": "boolean"}
                    }
                },
                "server": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "port": {"type": "integer"},
                        "host": {"type": "string"},
                        "webhook_secret": {"type": "string"}
                    }
                },
                "features": {
                    "type": "object",
                    "properties": {
                        "evidence_management": {"type": "boolean"},
                        "auto_checkpoint": {"type": "boolean"},
                        "ai_integration": {"type": "boolean"}
                    }
                }
            }
        }
        
        with open(self.schema_path, 'w') as f:
            json.dump(default_schema, f, indent=2)
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate config against the schema.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        validator = Draft7Validator(self.schema)
        errors = list(validator.iter_errors(config))
        
        if not errors:
            return True, []
        
        # Format error messages
        error_messages = []
        for error in errors:
            path = "/".join(str(p) for p in error.path) if error.path else "root"
            error_messages.append(f"{path}: {error.message}")
        
        return False, error_messages

    def validate_yaml_file(self, file_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """
        Validate a YAML configuration file against the schema.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            return self.validate(config)
        except yaml.YAMLError as e:
            return False, [f"YAML parsing error: {e}"]
        except Exception as e:
            return False, [f"Failed to validate config file: {e}"]


class EnvironmentChecker:
    """Checks the environment for required conditions."""
    
    def __init__(self):
        """Initialize the environment checker."""
        self.issues: List[Dict[str, Any]] = []
    
    def check_python_version(self, min_version: Tuple[int, int, int] = (3, 8, 0)) -> bool:
        """
        Check if Python version meets requirements.
        
        Args:
            min_version: Minimum required Python version
            
        Returns:
            True if Python version is sufficient, False otherwise
        """
        current_version = sys.version_info[:3]
        if current_version < min_version:
            self.issues.append({
                "type": "python_version",
                "severity": "critical",
                "message": f"Python {'.'.join(map(str, current_version))} "
                           f"found, but {'.'.join(map(str, min_version))} or higher required",
                "fixable": False
            })
            return False
        return True
    
    def check_node_version(self, min_version: Tuple[int, int, int] = (14, 0, 0)) -> bool:
        """
        Check if Node.js version meets requirements (for server component).
        
        Args:
            min_version: Minimum required Node.js version
            
        Returns:
            True if Node.js version is sufficient or not needed, False otherwise
        """
        try:
            import subprocess
            result = subprocess.run(['node', '--version'], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
            
            if result.returncode != 0:
                # Node.js not installed
                self.issues.append({
                    "type": "node_missing",
                    "severity": "warning",
                    "message": "Node.js is not installed. Server component will not be available.",
                    "fixable": False
                })
                return False
            
            # Parse version (format is v14.17.0)
            version_str = result.stdout.strip()
            if version_str.startswith('v'):
                version_str = version_str[1:]
            
            version_parts = list(map(int, version_str.split('.')))
            while len(version_parts) < 3:
                version_parts.append(0)
            
            current_version = tuple(version_parts[:3])
            
            if current_version < min_version:
                self.issues.append({
                    "type": "node_version",
                    "severity": "warning",
                    "message": f"Node.js {'.'.join(map(str, current_version))} "
                               f"found, but {'.'.join(map(str, min_version))} or higher recommended",
                    "fixable": False
                })
                return False
            
            return True
        except Exception as e:
            self.issues.append({
                "type": "node_check_failed",
                "severity": "info",
                "message": f"Failed to check Node.js version: {e}",
                "fixable": False
            })
            return False
    
    def check_required_directories(self, config: Dict[str, Any]) -> bool:
        """
        Check if required directories exist and are accessible.
        
        Args:
            config: Configuration dictionary with data_paths section
            
        Returns:
            True if all directories are accessible, False otherwise
        """
        if 'data_paths' not in config:
            self.issues.append({
                "type": "missing_data_paths",
                "severity": "critical",
                "message": "data_paths section missing from configuration",
                "fixable": True,
                "fix_action": "add_default_data_paths"
            })
            return False
        
        data_paths = config['data_paths']
        required_dirs = []
        
        # Get base directory
        base_dir = data_paths.get('base_dir')
        if not base_dir:
            self.issues.append({
                "type": "missing_base_dir",
                "severity": "critical",
                "message": "base_dir not specified in data_paths",
                "fixable": True,
                "fix_action": "add_default_base_dir"
            })
            return False
        
        # Convert to absolute path if relative
        base_dir = Path(base_dir)
        if not base_dir.is_absolute():
            base_dir = Path.cwd() / base_dir
        
        # Check all required directories
        required_dirs = [
            base_dir,
            base_dir / 'evidence' if 'evidence_dir' not in data_paths else Path(data_paths['evidence_dir']),
            base_dir / 'evidence' / 'attachments'
        ]
        
        all_accessible = True
        for directory in required_dirs:
            if not directory.exists():
                self.issues.append({
                    "type": "missing_directory",
                    "severity": "warning",
                    "message": f"Required directory {directory} does not exist",
                    "fixable": True,
                    "fix_action": "create_directory",
                    "directory": str(directory)
                })
                all_accessible = False
            elif not os.access(directory, os.R_OK | os.W_OK):
                self.issues.append({
                    "type": "directory_permissions",
                    "severity": "critical",
                    "message": f"Directory {directory} is not readable/writable",
                    "fixable": True,
                    "fix_action": "fix_permissions",
                    "directory": str(directory)
                })
                all_accessible = False
        
        return all_accessible
    
    def check_disk_space(self, min_space_mb: int = 100) -> bool:
        """
        Check if there's enough disk space.
        
        Args:
            min_space_mb: Minimum required disk space in MB
            
        Returns:
            True if enough disk space is available, False otherwise
        """
        try:
            # Create a temporary file to determine the location
            with tempfile.NamedTemporaryFile() as tmp:
                tmp_path = Path(tmp.name)
                disk_usage = shutil.disk_usage(tmp_path.parent)
            
            # Convert bytes to MB
            free_space_mb = disk_usage.free / (1024 * 1024)
            
            if free_space_mb < min_space_mb:
                self.issues.append({
                    "type": "disk_space",
                    "severity": "warning",
                    "message": f"Only {free_space_mb:.1f} MB free disk space available. "
                               f"Recommended minimum is {min_space_mb} MB",
                    "fixable": False
                })
                return False
            
            return True
        except Exception as e:
            self.issues.append({
                "type": "disk_check_failed",
                "severity": "info",
                "message": f"Failed to check disk space: {e}",
                "fixable": False
            })
            return False
    
    def run_all_checks(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run all environment checks.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of issues found
        """
        self.issues = []
        
        # Run all checks
        self.check_python_version()
        self.check_node_version()
        self.check_required_directories(config)
        self.check_disk_space()
        
        return self.issues


class ConfigHealer:
    """Self-healing for configuration files."""
    
    def __init__(self, config_path: Union[str, Path], schema_name: str = "config_schema.json"):
        """
        Initialize the configuration healer.
        
        Args:
            config_path: Path to the configuration file
            schema_name: Name of the schema file
        """
        self.config_path = Path(config_path)
        self.validator = ConfigValidator(schema_name)
        self.env_checker = EnvironmentChecker()
        self.healing_actions = {
            "add_default_data_paths": self._add_default_data_paths,
            "add_default_base_dir": self._add_default_base_dir,
            "create_directory": self._create_directory,
            "fix_permissions": self._fix_permissions
        }
    
    def heal_configuration(self) -> Tuple[bool, List[str]]:
        """
        Attempt to fix common configuration issues.
        
        Returns:
            Tuple of (success, messages)
        """
        try:
            # Load the configuration
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            if config is None:
                config = {}
            
            # Validate configuration
            is_valid, error_messages = self.validator.validate(config)
            
            # Get environment issues
            issues = self.env_checker.run_all_checks(config)
            
            # List of actions taken
            actions_taken = []
            
            # Try to fix issues
            config_modified = False
            for issue in issues:
                if issue.get("fixable") and "fix_action" in issue:
                    fix_action = issue["fix_action"]
                    if fix_action in self.healing_actions:
                        # Call the healing action
                        fixed, message = self.healing_actions[fix_action](config, issue)
                        if fixed:
                            config_modified = True
                            actions_taken.append(message)
            
            # Save modified configuration if needed
            if config_modified:
                self._backup_config()
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                
                # Re-validate
                is_valid, error_messages = self.validator.validate(config)
            
            if not is_valid:
                return False, [
                    "Configuration healing incomplete. Issues remain:",
                    *error_messages
                ]
            
            return True, actions_taken
        
        except Exception as e:
            return False, [f"Configuration healing failed: {e}"]
    
    def _backup_config(self) -> None:
        """Create a backup of the configuration file."""
        if not self.config_path.exists():
            return
        
        backup_path = self.config_path.with_suffix(f"{self.config_path.suffix}.bak")
        shutil.copy2(self.config_path, backup_path)
    
    def _add_default_data_paths(self, config: Dict[str, Any], issue: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Add default data_paths section to config.
        
        Args:
            config: Configuration dictionary to modify
            issue: Issue dictionary
            
        Returns:
            Tuple of (success, message)
        """
        config['data_paths'] = {
            'base_dir': 'data',
            'tasks_file': 'tasks.yaml',
            'epics_file': 'epics.yaml',
            'board_file': 'board.yaml',
            'evidence_dir': 'evidence'
        }
        return True, "Added default data_paths section to configuration"
    
    def _add_default_base_dir(self, config: Dict[str, Any], issue: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Add default base_dir to data_paths.
        
        Args:
            config: Configuration dictionary to modify
            issue: Issue dictionary
            
        Returns:
            Tuple of (success, message)
        """
        if 'data_paths' not in config:
            config['data_paths'] = {}
        
        config['data_paths']['base_dir'] = 'data'
        return True, "Added default base_dir to data_paths"
    
    def _create_directory(self, config: Dict[str, Any], issue: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Create a missing directory.
        
        Args:
            config: Configuration dictionary (not modified)
            issue: Issue dictionary with directory information
            
        Returns:
            Tuple of (success, message)
        """
        if 'directory' not in issue:
            return False, "Missing directory information in issue"
        
        directory = Path(issue['directory'])
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return True, f"Created directory {directory}"
        except Exception as e:
            return False, f"Failed to create directory {directory}: {e}"
    
    def _fix_permissions(self, config: Dict[str, Any], issue: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Fix directory permissions.
        
        Args:
            config: Configuration dictionary (not modified)
            issue: Issue dictionary with directory information
            
        Returns:
            Tuple of (success, message)
        """
        if 'directory' not in issue:
            return False, "Missing directory information in issue"
        
        directory = Path(issue['directory'])
        if not directory.exists():
            return False, f"Directory {directory} does not exist"
        
        try:
            # This will work on Unix-like systems
            if hasattr(os, 'chmod'):
                # Set to 755 (owner can read/write/execute, others can read/execute)
                os.chmod(directory, 0o755)
                return True, f"Fixed permissions for directory {directory}"
            return False, "Permission fixing not available on this system"
        except Exception as e:
            return False, f"Failed to fix permissions for directory {directory}: {e}"


def validate_config(config_path: Union[str, Path], schema_name: str = "config_schema.json") -> Tuple[bool, List[str]]:
    """
    Validate a configuration file.
    
    Args:
        config_path: Path to the configuration file
        schema_name: Name of the schema file
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = ConfigValidator(schema_name)
    return validator.validate_yaml_file(config_path)


def check_environment(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Check the environment for issues.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of issues found
    """
    checker = EnvironmentChecker()
    return checker.run_all_checks(config)


def heal_configuration(config_path: Union[str, Path], schema_name: str = "config_schema.json") -> Tuple[bool, List[str]]:
    """
    Attempt to fix common configuration issues.
    
    Args:
        config_path: Path to the configuration file
        schema_name: Name of the schema file
        
    Returns:
        Tuple of (success, messages)
    """
    healer = ConfigHealer(config_path, schema_name)
    return healer.heal_configuration()