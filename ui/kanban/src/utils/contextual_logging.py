"""
Enhanced contextual logging for the Kanban CLI.

This module provides a structured logging system with context tracking,
log rotation, and separate error logs with detailed diagnostics.
"""
import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import time
import traceback
from typing import Dict, Any, Optional, List, Union
import uuid
import json

from ..config.settings import get_project_root, load_config

# Dictionary to store context data for each thread/session
_log_context = {}

class ContextualFilter(logging.Filter):
    """
    Logging filter that adds context data to log records.
    """
    def filter(self, record):
        # Add context data to the record
        context_id = getattr(record, 'context_id', None)
        if context_id:
            context = _log_context.get(context_id, {})
            for key, value in context.items():
                setattr(record, key, value)
        
        # Add extra metadata
        if not hasattr(record, 'correlation_id'):
            setattr(record, 'correlation_id', str(uuid.uuid4())[:8])
        
        return True

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add context and other attributes
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                try:
                    # Try to serialize the value to json to ensure it's serializable
                    json.dumps(value)
                    log_record[key] = value
                except (TypeError, OverflowError):
                    # If it can't be serialized, convert to string
                    log_record[key] = str(value)
        
        return json.dumps(log_record)

def create_context(context_id: Optional[str] = None, **context_data) -> str:
    """
    Create a new logging context.
    
    Args:
        context_id: Optional context ID, generated if not provided
        **context_data: Context data as keyword arguments
        
    Returns:
        Context ID
    """
    context_id = context_id or str(uuid.uuid4())
    _log_context[context_id] = context_data
    return context_id

def update_context(context_id: str, **context_data) -> None:
    """
    Update an existing logging context.
    
    Args:
        context_id: Context ID
        **context_data: Context data to update
    """
    if context_id in _log_context:
        _log_context[context_id].update(context_data)
    else:
        _log_context[context_id] = context_data

def clear_context(context_id: str) -> None:
    """
    Clear a logging context.
    
    Args:
        context_id: Context ID
    """
    if context_id in _log_context:
        del _log_context[context_id]

def get_context(context_id: str) -> Dict[str, Any]:
    """
    Get context data for a context ID.
    
    Args:
        context_id: Context ID
        
    Returns:
        Context data dictionary
    """
    return _log_context.get(context_id, {})

def setup_contextual_logging(name: Optional[str] = None, log_level: Optional[str] = None,
                           enable_console: bool = True, enable_json: bool = True,
                           config: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Setup enhanced logging with context tracking and error logs.
    
    Args:
        name: Logger name, defaults to 'kanban'
        log_level: Optional log level override
        enable_console: Enable console output
        enable_json: Enable JSON formatting for file logs
        config: Optional configuration dictionary
        
    Returns:
        Configured logger
    """
    name = name or 'kanban'
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Load config
    config = config or load_config()
    if log_level is None:
        log_level = config.get('app', {}).get('log_level', 'INFO')
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
    logger.setLevel(numeric_level)
    
    # Get log directories
    project_root = get_project_root()
    logs_dir = project_root / config.get('paths', {}).get('logs', 'logs')
    error_logs_dir = logs_dir / 'errors'
    
    # Create log directories
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(error_logs_dir, exist_ok=True)
    
    # Add context filter
    context_filter = ContextualFilter()
    logger.addFilter(context_filter)
    
    # Create handlers
    handlers = []
    
    # Main log file with rotation
    main_handler = logging.handlers.RotatingFileHandler(
        logs_dir / f"{name}.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    main_handler.setLevel(numeric_level)
    handlers.append(main_handler)
    
    # Error log file with rotation (ERROR and above)
    error_handler = logging.handlers.RotatingFileHandler(
        error_logs_dir / f"{name}_error.log",
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    handlers.append(error_handler)
    
    # Daily log file
    timestamp = datetime.now().strftime('%Y%m%d')
    daily_handler = logging.FileHandler(logs_dir / f"{name}_{timestamp}.log")
    daily_handler.setLevel(numeric_level)
    handlers.append(daily_handler)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        handlers.append(console_handler)
    
    # Set formatters
    if enable_json:
        json_formatter = JSONFormatter()
        for handler in [main_handler, error_handler, daily_handler]:
            handler.setFormatter(json_formatter)
    
    # Text formatter for console (always) and optionally for files
    text_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if enable_console:
        console_handler.setFormatter(text_formatter)
    
    if not enable_json:
        for handler in [main_handler, error_handler, daily_handler]:
            handler.setFormatter(text_formatter)
    
    # Add all handlers to logger
    for handler in handlers:
        logger.addHandler(handler)
    
    return logger

class ContextLogger:
    """
    Context manager for logging with context data.
    
    Usage:
        with ContextLogger(logger, operation="create_evidence", entity_id="EVD-123"):
            # Do something
            logger.info("Operation started")
            # Do more things
    """
    def __init__(self, logger: logging.Logger, **context_data):
        """
        Initialize context logger.
        
        Args:
            logger: Logger instance
            **context_data: Context data as keyword arguments
        """
        self.logger = logger
        self.context_id = create_context(**context_data)
        self.context_data = context_data
    
    def __enter__(self):
        # Add context to thread local storage to be picked up by filter
        self.old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.context_id = self.context_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original factory
        logging.setLogRecordFactory(self.old_factory)
        
        # Log exception if any
        if exc_type is not None:
            self.logger.error(
                f"Exception occurred: {exc_type.__name__}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
        
        # Clean up context
        clear_context(self.context_id)
        
        # Don't suppress exception
        return False
    
    def update(self, **context_data):
        """
        Update context data during execution.
        
        Args:
            **context_data: Additional context data
        """
        update_context(self.context_id, **context_data)
        self.context_data.update(context_data)