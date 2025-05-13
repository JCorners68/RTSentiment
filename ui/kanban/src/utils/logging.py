"""
Logging utilities for the Kanban CLI.
"""
import os
import logging
from pathlib import Path
from datetime import datetime
import sys

from ..config.settings import get_project_root, load_config

def setup_logging(name=None, log_level=None):
    """
    Setup logging for the application.
    
    Args:
        name: Name for the logger, defaults to 'kanban'
        log_level: Optional log level override, otherwise uses config
    
    Returns:
        logger: Configured logger instance
    """
    name = name or 'kanban'
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Load config
    config = load_config()
    if log_level is None:
        log_level = config.get('app', {}).get('log_level', 'INFO')
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logger.setLevel(numeric_level)
    
    # Create logs directory if it doesn't exist
    logs_dir = get_project_root() / config.get('paths', {}).get('logs', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f"{name}_{timestamp}.log"
    
    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
