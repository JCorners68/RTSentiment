"""
Schema validation module for Iceberg sentiment data.

This module provides comprehensive schema validation for the sentiment
analysis data before it's written to Iceberg tables, as specified in
Phase 2 of the data tier plan.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional, Union

from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, 
    StringType, 
    TimestampType, 
    FloatType, 
    BooleanType, 
    ListType, 
    MapType, 
    StructType
)


class SentimentSchemaValidator:
    """
    Validator for sentiment analysis data schema.
    
    This validator ensures that data conforms to the Iceberg schema
    before it's written, handling type validation, required fields,
    and value ranges.
    """
    
    def __init__(self):
        """Initialize the schema validator."""
        self.logger = logging.getLogger(__name__)
        
        # Instead of defining a full schema, we'll just define the field requirements
        # to avoid compatibility issues with PyIceberg versions
        required_fields = [
            "message_id", "event_timestamp", "ingestion_timestamp", 
            "source_system", "text_content", "sentiment_score",
            "sentiment_magnitude", "primary_emotion", "sarcasm_detection",
            "subjectivity_score", "toxicity_score", "user_intent",
            "processing_version"
        ]
        
        optional_fields = [
            "emotion_intensity_vector", "aspect_target_identification", 
            "aspect_based_sentiment", "entity_recognition", "influence_score",
            "ticker", "article_title", "source_url", "model_name"
        ]
        
        # Map field names to their types for validation
        field_types = {
            "message_id": "string",
            "event_timestamp": "timestamp",
            "ingestion_timestamp": "timestamp",
            "source_system": "string",
            "text_content": "string",
            "sentiment_score": "float",
            "sentiment_magnitude": "float",
            "primary_emotion": "string",
            "sarcasm_detection": "boolean",
            "subjectivity_score": "float",
            "toxicity_score": "float",
            "user_intent": "string",
            "processing_version": "string",
            "emotion_intensity_vector": "map",
            "aspect_target_identification": "list",
            "aspect_based_sentiment": "map",
            "entity_recognition": "list",
            "influence_score": "float",
            "ticker": "string",
            "article_title": "string",
            "source_url": "string",
            "model_name": "string"
        }
        
        # Cache field information by name for faster lookups
        self.field_info = {}
        for field in required_fields:
            self.field_info[field] = {
                'required': True,
                'type': field_types.get(field, 'string')
            }
            
        for field in optional_fields:
            self.field_info[field] = {
                'required': False,
                'type': field_types.get(field, 'string')
            }
        
        # Define value ranges and constraints
        self.constraints = {
            'sentiment_score': {'min': -1.0, 'max': 1.0},
            'sentiment_magnitude': {'min': 0.0, 'max': 1.0},
            'subjectivity_score': {'min': 0.0, 'max': 1.0},
            'toxicity_score': {'min': 0.0, 'max': 1.0},
            'influence_score': {'min': 0.0, 'max': 1.0}
        }
        
        # Define valid enum values
        self.enums = {
            'primary_emotion': [
                'anger', 'disgust', 'fear', 'joy', 'neutral', 
                'sadness', 'surprise', 'positive', 'negative'
            ],
            'user_intent': [
                'information_seeking', 'information_sharing', 
                'opinion_expression', 'recommendation', 
                'question', 'complaint', 'praise'
            ]
        }
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a record against the schema.
        
        Args:
            data: Record to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        for field_name, info in self.field_info.items():
            if info['required'] and field_name not in data:
                errors.append(f"Missing required field: {field_name}")
        
        # Check field types and constraints
        for field_name, value in data.items():
            if field_name in self.field_info:
                field_type = self.field_info[field_name]['type']
                
                # Skip null values for optional fields
                if value is None:
                    if self.field_info[field_name]['required']:
                        errors.append(f"Field {field_name} is required but value is None")
                    continue
                
                # Check field type
                type_error = self._validate_field_type(field_name, value, field_type)
                if type_error:
                    errors.append(type_error)
                
                # Check value constraints
                if field_name in self.constraints and value is not None:
                    constraint = self.constraints[field_name]
                    
                    if not isinstance(value, (int, float)):
                        errors.append(f"Field {field_name} should be numeric but got {type(value).__name__}")
                    elif 'min' in constraint and value < constraint['min']:
                        errors.append(f"Field {field_name} value {value} is below minimum {constraint['min']}")
                    elif 'max' in constraint and value > constraint['max']:
                        errors.append(f"Field {field_name} value {value} is above maximum {constraint['max']}")
                
                # Check enum values
                if field_name in self.enums and value is not None:
                    if value not in self.enums[field_name]:
                        allowed = ', '.join(self.enums[field_name])
                        errors.append(f"Field {field_name} value '{value}' is not in allowed values: {allowed}")
        
        return len(errors) == 0, errors
    
    def _validate_field_type(
        self, field_name: str, value: Any, field_type: str
    ) -> Optional[str]:
        """
        Validate a field's data type.
        
        Args:
            field_name: Name of the field
            value: Field value
            field_type: Expected field type
            
        Returns:
            Optional[str]: Error message if validation fails, None otherwise
        """
        if field_type == 'string':
            if not isinstance(value, str):
                return f"Field {field_name} should be string but got {type(value).__name__}"
        
        elif field_type == 'boolean':
            if not isinstance(value, bool):
                # Special case for database integration: 0/1 integers for boolean fields
                if isinstance(value, int) and value in (0, 1):
                    pass  # Allow 0/1 integers for boolean fields
                else:
                    return f"Field {field_name} should be boolean but got {type(value).__name__}"
        
        elif field_type == 'float':
            if not isinstance(value, (int, float)):
                return f"Field {field_name} should be numeric but got {type(value).__name__}"
        
        elif field_type == 'timestamp':
            if not isinstance(value, (datetime, str)):
                return f"Field {field_name} should be timestamp but got {type(value).__name__}"
            # If string, try to parse as ISO format
            if isinstance(value, str):
                try:
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    return f"Field {field_name} has invalid timestamp format: {value}"
        
        elif field_type == 'map':
            # For maps, we allow both dicts and JSON strings
            if not isinstance(value, (dict, str)):
                return f"Field {field_name} should be dict or JSON string but got {type(value).__name__}"
            # If string, validate it's valid JSON
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if not isinstance(parsed, dict):
                        return f"Field {field_name} JSON string does not decode to dict: {value}"
                except json.JSONDecodeError:
                    return f"Field {field_name} has invalid JSON: {value}"
        
        elif field_type == 'list':
            # For lists, we allow both lists and JSON strings
            if not isinstance(value, (list, str)):
                return f"Field {field_name} should be list or JSON string but got {type(value).__name__}"
            # If string, validate it's valid JSON
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if not isinstance(parsed, list):
                        return f"Field {field_name} JSON string does not decode to list: {value}"
                except json.JSONDecodeError:
                    return f"Field {field_name} has invalid JSON: {value}"
        
        return None
    
    def normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize data to conform to the schema.
        
        This method:
        1. Adds default values for missing required fields
        2. Converts types where possible
        3. Serializes complex types to JSON strings
        
        Args:
            data: Original data record
            
        Returns:
            Dict[str, Any]: Normalized data
        """
        import copy
        import json
        
        normalized = copy.deepcopy(data)
        current_time = datetime.utcnow()
        
        # Set defaults for missing required fields
        normalized.setdefault("message_id", str(data.get("id", uuid.uuid4())))
        normalized.setdefault("event_timestamp", data.get("timestamp", current_time))
        normalized.setdefault("ingestion_timestamp", current_time)
        normalized.setdefault("source_system", "normalized")
        normalized.setdefault("text_content", data.get("text", ""))
        normalized.setdefault("sentiment_score", data.get("sentiment", 0.0))
        normalized.setdefault("sentiment_magnitude", data.get("confidence", 0.5))
        normalized.setdefault("primary_emotion", "neutral")
        normalized.setdefault("sarcasm_detection", False)
        normalized.setdefault("subjectivity_score", 0.0)
        normalized.setdefault("toxicity_score", 0.0)
        normalized.setdefault("user_intent", "information_seeking")
        normalized.setdefault("processing_version", "1.0.0")
        
        # Normalize field types
        for field_name, value in list(normalized.items()):
            if field_name not in self.field_info:
                continue
                
            field_type = self.field_info[field_name]['type']
            
            # Skip null values for optional fields
            if value is None and not self.field_info[field_name]['required']:
                continue
                
            # Convert strings to appropriate types
            if isinstance(value, str):
                if field_type == 'float':
                    try:
                        normalized[field_name] = float(value)
                    except ValueError:
                        normalized[field_name] = 0.0
                        
                elif field_type == 'boolean':
                    if value.lower() in ('true', 'yes', '1', 't', 'y'):
                        normalized[field_name] = True
                    elif value.lower() in ('false', 'no', '0', 'f', 'n'):
                        normalized[field_name] = False
                        
                elif field_type == 'timestamp':
                    try:
                        normalized[field_name] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        normalized[field_name] = current_time
            
            # Ensure complex types are JSON serialized for JDBC
            if field_type.startswith('map<') and isinstance(value, dict):
                normalized[field_name] = json.dumps(value)
                
            elif field_type.startswith('list<') and isinstance(value, list):
                normalized[field_name] = json.dumps(value)
        
        # Ensure values are within constraints
        for field_name, constraint in self.constraints.items():
            if field_name in normalized and normalized[field_name] is not None:
                try:
                    value = float(normalized[field_name])
                    if 'min' in constraint and value < constraint['min']:
                        normalized[field_name] = constraint['min']
                    elif 'max' in constraint and value > constraint['max']:
                        normalized[field_name] = constraint['max']
                except (ValueError, TypeError):
                    # If conversion fails, set to default
                    if field_name == 'sentiment_score':
                        normalized[field_name] = 0.0
                    else:
                        normalized[field_name] = constraint.get('min', 0.0)
        
        # Ensure enum values are valid
        for field_name, valid_values in self.enums.items():
            if field_name in normalized and normalized[field_name] is not None:
                if normalized[field_name] not in valid_values:
                    # Set to first valid value as default
                    normalized[field_name] = valid_values[0]
        
        return normalized