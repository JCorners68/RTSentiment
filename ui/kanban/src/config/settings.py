"""
Configuration management for the Kanban CLI.
"""
import os
import yaml
from pathlib import Path

def get_project_root():
    """Return the absolute path to the project root directory."""
    # The project root is assumed to be the parent of the src directory
    current_file = Path(__file__)
    src_dir = current_file.parent.parent
    project_root = src_dir.parent
    return project_root

def load_config(config_path=None):
    """
    Load configuration from the YAML file.
    
    Args:
        config_path: Optional path to the config file.
                    If not provided, defaults to config.yaml in project root.
    
    Returns:
        dict: Configuration settings
    """
    if config_path is None:
        config_path = get_project_root() / "config.yaml"
    
    try:
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
            
        # Process environment variable substitutions
        process_env_vars(config)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing configuration file: {e}")

def process_env_vars(config_dict):
    """
    Process any environment variable references in the config.
    
    Args:
        config_dict: Configuration dictionary to process
    """
    if isinstance(config_dict, dict):
        for key, value in config_dict.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]
                config_dict[key] = os.environ.get(env_var, f"ENV_VAR_{env_var}_NOT_SET")
            elif isinstance(value, (dict, list)):
                process_env_vars(value)
    elif isinstance(config_dict, list):
        for i, item in enumerate(config_dict):
            if isinstance(item, (dict, list)):
                process_env_vars(item)

def get_data_dir():
    """Return the absolute path to the data directory."""
    config = load_config()
    data_dir = get_project_root() / config['paths']['data']
    return data_dir

def get_evidence_dir():
    """
    Return the absolute path to the evidence directory.
    This supports the priority feature: Evidence Management System.
    """
    config = load_config()
    evidence_dir = get_project_root() / config['paths']['evidence']['root']
    return evidence_dir
