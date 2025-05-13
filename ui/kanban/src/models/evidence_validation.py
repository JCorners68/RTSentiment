"""
Validation functions for the Evidence Management System.

This module provides specialized validation for the Evidence Management System,
which is a priority feature of the Kanban CLI application.
"""
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import re
import os
from pathlib import Path

from . import evidence_schema

def validate_evidence(evidence_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate evidence data against the EvidenceSchema requirements.
    
    Args:
        evidence_data: Dictionary containing evidence data to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if validation passed
            - List of validation error messages (empty if validation passed)
    """
    errors = []
    
    # Check required fields
    if 'title' not in evidence_data or not evidence_data['title']:
        errors.append("Evidence title is required")
    elif len(evidence_data['title']) < 3:
        errors.append("Evidence title must be at least 3 characters")
    elif len(evidence_data['title']) > 200:
        errors.append("Evidence title must be at most 200 characters")
    
    if 'description' not in evidence_data or not evidence_data['description']:
        errors.append("Evidence description is required")
    
    # Validate category if provided
    if 'category' in evidence_data and evidence_data['category']:
        valid_categories = [category.value for category in evidence_schema.EvidenceCategory]
        if evidence_data['category'] not in valid_categories:
            errors.append(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
    
    # Validate relevance_score if provided
    if 'relevance_score' in evidence_data and evidence_data['relevance_score']:
        valid_scores = [score.value for score in evidence_schema.EvidenceRelevance]
        if evidence_data['relevance_score'] not in valid_scores:
            errors.append(f"Invalid relevance score. Must be one of: {', '.join(valid_scores)}")
    
    # Validate dates if provided
    date_fields = ['date_collected', 'created_at', 'updated_at']
    for field in date_fields:
        if field in evidence_data and evidence_data[field]:
            try:
                if isinstance(evidence_data[field], str):
                    datetime.fromisoformat(evidence_data[field])
            except ValueError:
                errors.append(f"Invalid {field.replace('_', ' ')} format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    # Validate attachments if provided
    if 'attachments' in evidence_data and evidence_data['attachments']:
        if not isinstance(evidence_data['attachments'], list):
            errors.append("Attachments must be a list")
        else:
            for i, attachment in enumerate(evidence_data['attachments']):
                if not isinstance(attachment, dict):
                    errors.append(f"Attachment {i+1} must be a dictionary")
                    continue
                
                att_errors = validate_attachment(attachment)
                if att_errors:
                    for err in att_errors:
                        errors.append(f"Attachment {i+1}: {err}")
    
    # Validate tags if provided
    if 'tags' in evidence_data and evidence_data['tags']:
        if not isinstance(evidence_data['tags'], list):
            errors.append("Tags must be a list")
        else:
            for i, tag in enumerate(evidence_data['tags']):
                if not isinstance(tag, str):
                    errors.append(f"Tag {i+1} must be a string")
                elif len(tag) < 2:
                    errors.append(f"Tag '{tag}' is too short (minimum 2 characters)")
                elif len(tag) > 50:
                    errors.append(f"Tag '{tag}' is too long (maximum 50 characters)")
    
    return len(errors) == 0, errors

def validate_attachment(attachment_data: Dict) -> List[str]:
    """
    Validate attachment data against the AttachmentSchema requirements.
    
    Args:
        attachment_data: Dictionary containing attachment data to validate
        
    Returns:
        List of validation error messages (empty if validation passed)
    """
    errors = []
    
    # Check required fields
    if 'file_path' not in attachment_data or not attachment_data['file_path']:
        errors.append("Attachment file path is required")
    else:
        # Security check: ensure file_path is not absolute or trying to escape
        file_path = attachment_data['file_path']
        if os.path.isabs(file_path):
            errors.append("Attachment file path must be relative, not absolute")
        
        normalized_path = os.path.normpath(file_path)
        if normalized_path.startswith('..') or '/../' in normalized_path:
            errors.append("Invalid file path: cannot navigate outside the attachments directory")
    
    # Validate file size if provided
    if 'file_size' in attachment_data and attachment_data['file_size'] is not None:
        try:
            file_size = int(attachment_data['file_size'])
            if file_size < 0:
                errors.append("File size cannot be negative")
        except (ValueError, TypeError):
            errors.append("File size must be a non-negative number")
    
    # Validate created_at if provided
    if 'created_at' in attachment_data and attachment_data['created_at']:
        try:
            if isinstance(attachment_data['created_at'], str):
                datetime.fromisoformat(attachment_data['created_at'])
        except ValueError:
            errors.append("Invalid created_at format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    return errors

def validate_evidence_search_params(params: Dict) -> Tuple[bool, Dict, List[str]]:
    """
    Validate and normalize evidence search parameters.
    
    Args:
        params: Dictionary containing search parameters
        
    Returns:
        Tuple containing:
            - Boolean indicating if validation passed
            - Dictionary of normalized parameters
            - List of validation error messages (empty if validation passed)
    """
    errors = []
    normalized = {}
    
    # Validate category if provided
    if 'category' in params and params['category']:
        valid_categories = [category.value for category in evidence_schema.EvidenceCategory]
        if params['category'] not in valid_categories:
            errors.append(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        else:
            normalized['category'] = params['category']
    
    # Validate date range if provided
    if 'date_from' in params and params['date_from']:
        try:
            if isinstance(params['date_from'], str):
                normalized['date_from'] = datetime.fromisoformat(params['date_from'])
            else:
                normalized['date_from'] = params['date_from']
        except ValueError:
            errors.append("Invalid date_from format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    if 'date_to' in params and params['date_to']:
        try:
            if isinstance(params['date_to'], str):
                normalized['date_to'] = datetime.fromisoformat(params['date_to'])
            else:
                normalized['date_to'] = params['date_to']
        except ValueError:
            errors.append("Invalid date_to format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    if 'date_from' in normalized and 'date_to' in normalized:
        if normalized['date_to'] < normalized['date_from']:
            errors.append("date_to must be after date_from")
    
    # Validate tags if provided
    if 'tags' in params and params['tags']:
        if isinstance(params['tags'], str):
            # Convert comma-separated string to list
            normalized['tags'] = [tag.strip() for tag in params['tags'].split(',')]
        elif isinstance(params['tags'], list):
            normalized['tags'] = params['tags']
        else:
            errors.append("Tags must be a string or list")
    
    # Validate relevance if provided
    if 'relevance_score' in params and params['relevance_score']:
        valid_scores = [score.value for score in evidence_schema.EvidenceRelevance]
        if params['relevance_score'] not in valid_scores:
            errors.append(f"Invalid relevance score. Must be one of: {', '.join(valid_scores)}")
        else:
            normalized['relevance_score'] = params['relevance_score']
    
    # Copy other valid search parameters
    valid_params = [
        'title', 'description', 'source', 'subcategory',
        'project_id', 'epic_id', 'task_id', 'created_by',
        'text', 'limit', 'offset', 'sort_by', 'sort_order'
    ]
    
    for param in valid_params:
        if param in params and params[param] is not None:
            normalized[param] = params[param]
    
    return len(errors) == 0, normalized, errors
