"""
Custom exceptions for the Kanban CLI.

This module provides specialized exceptions for different error scenarios
in the Kanban CLI application, with appropriate error codes and detailed
error messages.
"""
from typing import Optional, Dict, Any, List


class KanbanError(Exception):
    """Base exception for all Kanban CLI errors."""
    
    def __init__(self, message: str, error_code: str = "E000", details: Optional[Dict[str, Any]] = None):
        """
        Initialize Kanban error.
        
        Args:
            message: Human-readable error message
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(f"[{error_code}] {message}")


class StorageError(KanbanError):
    """Exception for storage-related errors."""
    
    def __init__(self, message: str, error_code: str = "E100", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, error_code, details)


class ValidationError(KanbanError):
    """Exception for data validation errors."""
    
    def __init__(self, message: str, validation_errors: List[str], error_code: str = "E200", details: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable error message
            validation_errors: List of specific validation error messages
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {"validation_errors": validation_errors}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.validation_errors = validation_errors


class FileOperationError(StorageError):
    """Exception for file operation errors."""
    
    def __init__(self, message: str, file_path: str, operation: str, error_code: str = "E110", details: Optional[Dict[str, Any]] = None):
        """
        Initialize file operation error.
        
        Args:
            message: Human-readable error message
            file_path: Path to the file that caused the error
            operation: Type of operation (read, write, delete, etc.)
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {"file_path": file_path, "operation": operation}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.file_path = file_path
        self.operation = operation


class EntityNotFoundError(StorageError):
    """Exception for when an entity is not found."""
    
    def __init__(self, entity_type: str, entity_id: str, error_code: str = "E120", details: Optional[Dict[str, Any]] = None):
        """
        Initialize entity not found error.
        
        Args:
            entity_type: Type of entity (task, epic, evidence, etc.)
            entity_id: ID of the entity that was not found
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        message = f"{entity_type.capitalize()} with ID '{entity_id}' not found"
        combined_details = {"entity_type": entity_type, "entity_id": entity_id}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateEntityError(StorageError):
    """Exception for when trying to create a duplicate entity."""
    
    def __init__(self, entity_type: str, entity_id: str, error_code: str = "E130", details: Optional[Dict[str, Any]] = None):
        """
        Initialize duplicate entity error.
        
        Args:
            entity_type: Type of entity (task, epic, evidence, etc.)
            entity_id: ID of the duplicate entity
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        message = f"{entity_type.capitalize()} with ID '{entity_id}' already exists"
        combined_details = {"entity_type": entity_type, "entity_id": entity_id}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.entity_type = entity_type
        self.entity_id = entity_id


class AttachmentError(StorageError):
    """Exception for attachment-related errors."""
    
    def __init__(self, message: str, attachment_id: Optional[str] = None, evidence_id: Optional[str] = None, 
                 file_path: Optional[str] = None, error_code: str = "E140", details: Optional[Dict[str, Any]] = None):
        """
        Initialize attachment error.
        
        Args:
            message: Human-readable error message
            attachment_id: Optional ID of the attachment
            evidence_id: Optional ID of the related evidence
            file_path: Optional path to the attachment file
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {}
        if attachment_id:
            combined_details["attachment_id"] = attachment_id
        if evidence_id:
            combined_details["evidence_id"] = evidence_id
        if file_path:
            combined_details["file_path"] = file_path
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.attachment_id = attachment_id
        self.evidence_id = evidence_id
        self.file_path = file_path


class ConcurrencyError(StorageError):
    """Exception for concurrency-related errors."""
    
    def __init__(self, message: str, entity_type: str, entity_id: str, error_code: str = "E150", details: Optional[Dict[str, Any]] = None):
        """
        Initialize concurrency error.
        
        Args:
            message: Human-readable error message
            entity_type: Type of entity (task, epic, evidence, etc.)
            entity_id: ID of the entity with concurrency issue
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {"entity_type": entity_type, "entity_id": entity_id}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.entity_type = entity_type
        self.entity_id = entity_id


class IndexError(StorageError):
    """Exception for index-related errors."""
    
    def __init__(self, message: str, index_type: str, error_code: str = "E160", details: Optional[Dict[str, Any]] = None):
        """
        Initialize index error.
        
        Args:
            message: Human-readable error message
            index_type: Type of index (tags, categories, etc.)
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {"index_type": index_type}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.index_type = index_type


class SearchError(KanbanError):
    """Exception for search-related errors."""
    
    def __init__(self, message: str, search_params: Dict[str, Any], error_code: str = "E300", details: Optional[Dict[str, Any]] = None):
        """
        Initialize search error.
        
        Args:
            message: Human-readable error message
            search_params: Dictionary of search parameters
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {"search_params": search_params}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.search_params = search_params


class MigrationError(KanbanError):
    """Exception for schema migration errors."""
    
    def __init__(self, message: str, migration_id: Optional[str] = None, from_version: Optional[str] = None, 
                 to_version: Optional[str] = None, affected_entity: Optional[str] = None,
                 error_code: str = "E400", details: Optional[Dict[str, Any]] = None):
        """
        Initialize migration error.
        
        Args:
            message: Human-readable error message
            migration_id: Optional ID of the migration operation
            from_version: Optional source schema version
            to_version: Optional target schema version
            affected_entity: Optional ID of the affected entity
            error_code: Unique error code for identification and troubleshooting
            details: Optional dictionary with additional error details
        """
        combined_details = {}
        if migration_id:
            combined_details["migration_id"] = migration_id
        if from_version:
            combined_details["from_version"] = from_version
        if to_version:
            combined_details["to_version"] = to_version
        if affected_entity:
            combined_details["affected_entity"] = affected_entity
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.migration_id = migration_id
        self.from_version = from_version
        self.to_version = to_version
        self.affected_entity = affected_entity