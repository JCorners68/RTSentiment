"""
Validation functions for Kanban CLI data models.

This module provides validation functionality for the various data schemas
used in the Kanban CLI application.
"""
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import re

from . import schemas
from . import evidence_schema

def validate_task(task_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate task data against the TaskSchema requirements.
    
    Args:
        task_data: Dictionary containing task data to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if validation passed
            - List of validation error messages (empty if validation passed)
    """
    errors = []
    
    # Check required fields
    if 'title' not in task_data or not task_data['title']:
        errors.append("Task title is required")
    elif len(task_data['title']) < 3:
        errors.append("Task title must be at least 3 characters")
    elif len(task_data['title']) > 100:
        errors.append("Task title must be at most 100 characters")
    
    # Validate status if provided
    if 'status' in task_data and task_data['status']:
        valid_statuses = [status.value for status in schemas.TaskStatus]
        if task_data['status'] not in valid_statuses:
            errors.append(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Validate priority if provided
    if 'priority' in task_data and task_data['priority']:
        valid_priorities = [priority.value for priority in schemas.TaskPriority]
        if task_data['priority'] not in valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
    
    # Validate complexity if provided
    if 'complexity' in task_data:
        try:
            complexity = int(task_data['complexity'])
            if complexity < 1 or complexity > 5:
                errors.append("Task complexity must be between 1 and 5")
        except (ValueError, TypeError):
            errors.append("Task complexity must be a number between 1 and 5")
    
    # Validate dates if provided
    if 'due_date' in task_data and task_data['due_date']:
        try:
            if isinstance(task_data['due_date'], str):
                datetime.fromisoformat(task_data['due_date'])
        except ValueError:
            errors.append("Invalid due date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    return len(errors) == 0, errors

def validate_epic(epic_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate epic data against the EpicSchema requirements.
    
    Args:
        epic_data: Dictionary containing epic data to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if validation passed
            - List of validation error messages (empty if validation passed)
    """
    errors = []
    
    # Check required fields
    if 'title' not in epic_data or not epic_data['title']:
        errors.append("Epic title is required")
    elif len(epic_data['title']) < 3:
        errors.append("Epic title must be at least 3 characters")
    elif len(epic_data['title']) > 100:
        errors.append("Epic title must be at most 100 characters")
    
    # Validate dates if provided
    date_fields = ['start_date', 'end_date']
    for field in date_fields:
        if field in epic_data and epic_data[field]:
            try:
                if isinstance(epic_data[field], str):
                    datetime.fromisoformat(epic_data[field])
            except ValueError:
                errors.append(f"Invalid {field.replace('_', ' ')} format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    # Check that end_date is after start_date if both are provided
    if ('start_date' in epic_data and epic_data['start_date'] and 
        'end_date' in epic_data and epic_data['end_date']):
        try:
            start = datetime.fromisoformat(epic_data['start_date']) if isinstance(epic_data['start_date'], str) else epic_data['start_date']
            end = datetime.fromisoformat(epic_data['end_date']) if isinstance(epic_data['end_date'], str) else epic_data['end_date']
            if end < start:
                errors.append("End date must be after start date")
        except ValueError:
            # This will be caught by the previous validation
            pass
    
    return len(errors) == 0, errors

def validate_board(board_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate board data against the BoardSchema requirements.
    
    Args:
        board_data: Dictionary containing board data to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if validation passed
            - List of validation error messages (empty if validation passed)
    """
    errors = []
    
    # Check required fields
    if 'name' not in board_data or not board_data['name']:
        errors.append("Board name is required")
    elif len(board_data['name']) < 3:
        errors.append("Board name must be at least 3 characters")
    elif len(board_data['name']) > 50:
        errors.append("Board name must be at most 50 characters")
    
    # Validate columns if provided
    if 'columns' in board_data and board_data['columns']:
        if not isinstance(board_data['columns'], list):
            errors.append("Board columns must be a list")
        elif len(board_data['columns']) < 2:
            errors.append("Board must have at least 2 columns")
        elif len(board_data['columns']) > 10:
            errors.append("Board must have at most 10 columns")
        else:
            # Check for duplicate column names
            column_names = set()
            for column in board_data['columns']:
                if column in column_names:
                    errors.append(f"Duplicate column name: {column}")
                column_names.add(column)
    
    return len(errors) == 0, errors
