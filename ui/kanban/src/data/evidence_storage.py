"""
Evidence Storage System for the Kanban CLI.

This module provides a robust storage system for evidence items and their attachments,
with advanced searching and indexing capabilities.
"""
import os
import json
import shutil
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import concurrent.futures
import hashlib
import fcntl
import uuid
import re

from ..config.settings import get_project_root, load_config
from ..models import evidence_schema, evidence_validation
from ..utils.exceptions import (
    StorageError, ValidationError, FileOperationError, 
    EntityNotFoundError, AttachmentError, ConcurrencyError, IndexError
)
from ..utils.file_handlers import (
    safe_path_join, safe_file_copy, calculate_file_hash, 
    get_mime_type, generate_text_preview, safe_delete_file, get_attachment_dir
)
from ..utils.checkpoints import CheckpointManager, with_checkpoint
from ..utils.contextual_logging import ContextLogger, setup_contextual_logging

# Configure module logger
logger = logging.getLogger(__name__)

class EvidenceStorage:
    """
    Storage system for evidence entities with advanced search capabilities.
    
    This class provides CRUD operations for evidence items and their attachments,
    with support for advanced searching, categorization, and relationship tracking.
    It implements robust error handling and recovery mechanisms.
    """
    
    def __init__(self, config=None):
        """
        Initialize evidence storage.
        
        Args:
            config: Optional configuration dict, loaded from config file if None
        """
        self.config = config or load_config()
        self.project_root = get_project_root()
        
        # Get base data directory from config
        self.data_dir = self.project_root / self.config['paths'].get('data', 'data')
        
        # Set up specialized directories
        self.evidence_dir = self.data_dir / 'evidence'
        self.attachments_dir = self.evidence_dir / 'attachments'
        self.index_dir = self.evidence_dir / 'index'
        
        # Ensure directories exist
        self._ensure_dirs()
        
        # Set up index files
        self.main_index_file = self.index_dir / 'evidence_index.json'
        self.tag_index_file = self.index_dir / 'tag_index.json'
        self.category_index_file = self.index_dir / 'category_index.json'
        self.relation_index_file = self.index_dir / 'relation_index.json'
        
        # Initialize indices
        self._ensure_indices()
        
        # File lock for concurrent access protection
        self._locks = {}
    
    def _ensure_dirs(self):
        """Ensure all required directories exist."""
        os.makedirs(self.evidence_dir, exist_ok=True)
        os.makedirs(self.attachments_dir, exist_ok=True)
        os.makedirs(self.index_dir, exist_ok=True)
    
    def _ensure_indices(self):
        """Ensure all index files exist and are valid."""
        # Main evidence index
        if not self.main_index_file.exists():
            self._write_json(self.main_index_file, {'evidence': []})
        
        # Tag index
        if not self.tag_index_file.exists():
            self._write_json(self.tag_index_file, {'tags': {}})
        
        # Category index
        if not self.category_index_file.exists():
            self._write_json(self.category_index_file, {'categories': {}})
        
        # Relation index
        if not self.relation_index_file.exists():
            self._write_json(self.relation_index_file, {
                'epic_relations': {},
                'task_relations': {},
                'evidence_relations': {}
            })
    
    def _acquire_lock(self, file_path):
        """
        Acquire a file lock for concurrent access protection.
        
        Args:
            file_path: Path to the file to lock
            
        Returns:
            File lock object
        """
        if file_path not in self._locks:
            lock_path = f"{file_path}.lock"
            lock_file = open(lock_path, 'w+')
            self._locks[file_path] = lock_file
        
        # Acquire exclusive lock
        try:
            fcntl.flock(self._locks[file_path], fcntl.LOCK_EX)
        except IOError as e:
            raise ConcurrencyError(
                f"Failed to acquire lock for {file_path}: {str(e)}",
                entity_type="file",
                entity_id=str(file_path),
                error_code="E151",
                details={"error": str(e)}
            )
    
    def _release_lock(self, file_path):
        """
        Release a file lock.
        
        Args:
            file_path: Path to the file to unlock
        """
        if file_path in self._locks:
            try:
                fcntl.flock(self._locks[file_path], fcntl.LOCK_UN)
            except IOError as e:
                logger.warning(f"Failed to release lock for {file_path}: {str(e)}")
    
    def _close_locks(self):
        """Close all open locks."""
        for path, lock_file in self._locks.items():
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
            except IOError as e:
                logger.warning(f"Failed to close lock for {path}: {str(e)}")
        
        self._locks = {}
    
    def _write_json(self, file_path: Path, data: Any) -> None:
        """
        Write data to a JSON file safely with concurrency protection.
        
        Args:
            file_path: Path to the file
            data: Data to write
            
        Raises:
            FileOperationError: If write fails
        """
        try:
            # Acquire lock
            self._acquire_lock(str(file_path))
            
            # Create temporary file
            temp_file = file_path.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Rename to target file (atomic operation)
            os.replace(temp_file, file_path)
        except FileExistsError:
            # Handle race condition where temp file already exists
            logger.warning(f"Temporary file {temp_file} already exists, removing it")
            try:
                os.remove(temp_file)
                # Try again
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                os.replace(temp_file, file_path)
            except Exception as e:
                raise FileOperationError(
                    f"Failed to write JSON file (retry): {str(e)}",
                    file_path=str(file_path),
                    operation="write_json",
                    error_code="E110",
                    details={"error": str(e)}
                )
        except Exception as e:
            raise FileOperationError(
                f"Failed to write JSON file: {str(e)}",
                file_path=str(file_path),
                operation="write_json",
                error_code="E110",
                details={"error": str(e)}
            )
        finally:
            # Release lock
            self._release_lock(str(file_path))
    
    def _read_json(self, file_path: Path) -> Any:
        """
        Read data from a JSON file safely with concurrency protection.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileOperationError: If read fails
        """
        try:
            # Acquire lock
            self._acquire_lock(str(file_path))
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            # Handle corrupted JSON file
            logger.error(f"Corrupted JSON file {file_path}: {str(e)}")
            
            # Try to restore from backup if available
            backup_file = file_path.with_suffix('.bak')
            if backup_file.exists():
                logger.info(f"Restoring {file_path} from backup")
                try:
                    with open(backup_file, 'r') as f:
                        return json.load(f)
                except Exception as backup_error:
                    logger.error(f"Failed to restore from backup: {str(backup_error)}")
            
            raise FileOperationError(
                f"Failed to read JSON file (corrupted): {str(e)}",
                file_path=str(file_path),
                operation="read_json",
                error_code="E111",
                details={"error": str(e)}
            )
        except Exception as e:
            raise FileOperationError(
                f"Failed to read JSON file: {str(e)}",
                file_path=str(file_path),
                operation="read_json",
                error_code="E111",
                details={"error": str(e)}
            )
        finally:
            # Release lock
            self._release_lock(str(file_path))
    
    def _backup_json(self, file_path: Path) -> bool:
        """
        Create a backup of a JSON file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if backup was created, False if file doesn't exist
            
        Raises:
            FileOperationError: If backup fails
        """
        try:
            if not file_path.exists():
                return False
            
            backup_file = file_path.with_suffix('.bak')
            shutil.copy2(file_path, backup_file)
            return True
        except Exception as e:
            raise FileOperationError(
                f"Failed to create backup: {str(e)}",
                file_path=str(file_path),
                operation="backup_json",
                error_code="E112",
                details={"error": str(e)}
            )
    
    def _update_indices(self, evidence: evidence_schema.EvidenceSchema, is_new: bool = False, is_delete: bool = False):
        """
        Update all indices for an evidence item.
        
        Args:
            evidence: Evidence schema object
            is_new: True if this is a new evidence item
            is_delete: True if the evidence is being deleted
            
        Raises:
            IndexError: If index update fails
        """
        evidence_id = evidence.id
        
        try:
            # Update main index
            main_index = self._read_json(self.main_index_file)
            
            if is_new and evidence_id not in main_index['evidence']:
                main_index['evidence'].append(evidence_id)
                self._write_json(self.main_index_file, main_index)
            elif is_delete and evidence_id in main_index['evidence']:
                main_index['evidence'].remove(evidence_id)
                self._write_json(self.main_index_file, main_index)
            
            # Update tag index
            if evidence.tags:
                tag_index = self._read_json(self.tag_index_file)
                
                if is_delete:
                    # Remove evidence ID from all tags
                    for tag in tag_index['tags']:
                        if evidence_id in tag_index['tags'][tag]:
                            tag_index['tags'][tag].remove(evidence_id)
                else:
                    # Add evidence ID to each tag
                    for tag in evidence.tags:
                        if tag not in tag_index['tags']:
                            tag_index['tags'][tag] = []
                        
                        if evidence_id not in tag_index['tags'][tag]:
                            tag_index['tags'][tag].append(evidence_id)
                
                self._write_json(self.tag_index_file, tag_index)
            
            # Update category index
            category_index = self._read_json(self.category_index_file)
            category = evidence.category.value
            
            if is_delete:
                # Remove evidence ID from its category
                if category in category_index['categories'] and evidence_id in category_index['categories'][category]:
                    category_index['categories'][category].remove(evidence_id)
            else:
                # Add evidence ID to its category
                if category not in category_index['categories']:
                    category_index['categories'][category] = []
                
                if evidence_id not in category_index['categories'][category]:
                    category_index['categories'][category].append(evidence_id)
            
            self._write_json(self.category_index_file, category_index)
            
            # Update relation index
            relation_index = self._read_json(self.relation_index_file)
            
            # Handle epic relations
            if evidence.epic_id:
                if is_delete:
                    # Remove evidence ID from epic relation
                    if evidence.epic_id in relation_index['epic_relations']:
                        if evidence_id in relation_index['epic_relations'][evidence.epic_id]:
                            relation_index['epic_relations'][evidence.epic_id].remove(evidence_id)
                else:
                    # Add evidence ID to epic relation
                    if evidence.epic_id not in relation_index['epic_relations']:
                        relation_index['epic_relations'][evidence.epic_id] = []
                    
                    if evidence_id not in relation_index['epic_relations'][evidence.epic_id]:
                        relation_index['epic_relations'][evidence.epic_id].append(evidence_id)
            
            # Handle task relations
            if evidence.task_id:
                if is_delete:
                    # Remove evidence ID from task relation
                    if evidence.task_id in relation_index['task_relations']:
                        if evidence_id in relation_index['task_relations'][evidence.task_id]:
                            relation_index['task_relations'][evidence.task_id].remove(evidence_id)
                else:
                    # Add evidence ID to task relation
                    if evidence.task_id not in relation_index['task_relations']:
                        relation_index['task_relations'][evidence.task_id] = []
                    
                    if evidence_id not in relation_index['task_relations'][evidence.task_id]:
                        relation_index['task_relations'][evidence.task_id].append(evidence_id)
            
            # Handle evidence relations
            if evidence.related_evidence_ids:
                if is_delete:
                    # Remove this evidence ID from all relation entries
                    for related_id in evidence.related_evidence_ids:
                        if related_id in relation_index['evidence_relations']:
                            if evidence_id in relation_index['evidence_relations'][related_id]:
                                relation_index['evidence_relations'][related_id].remove(evidence_id)
                    
                    # Remove this evidence's relations entry
                    if evidence_id in relation_index['evidence_relations']:
                        del relation_index['evidence_relations'][evidence_id]
                else:
                    # Add bidirectional relations
                    if evidence_id not in relation_index['evidence_relations']:
                        relation_index['evidence_relations'][evidence_id] = []
                    
                    # Add relations from this evidence to others
                    for related_id in evidence.related_evidence_ids:
                        if related_id not in relation_index['evidence_relations'][evidence_id]:
                            relation_index['evidence_relations'][evidence_id].append(related_id)
                        
                        # Add reverse relation
                        if related_id not in relation_index['evidence_relations']:
                            relation_index['evidence_relations'][related_id] = []
                        
                        if evidence_id not in relation_index['evidence_relations'][related_id]:
                            relation_index['evidence_relations'][related_id].append(evidence_id)
            
            self._write_json(self.relation_index_file, relation_index)
            
        except Exception as e:
            operation = "delete" if is_delete else "create" if is_new else "update"
            raise IndexError(
                f"Failed to update indices during {operation}: {str(e)}",
                index_type="evidence",
                error_code="E161",
                details={"error": str(e), "evidence_id": evidence_id}
            )
    
    @with_checkpoint("evidence_create")
    def create(self, evidence_data: Dict, attachment_paths: Optional[List[str]] = None,
              checkpoint: Optional[CheckpointManager] = None) -> evidence_schema.EvidenceSchema:
        """
        Create a new evidence item with optional attachments.
        
        Args:
            evidence_data: Dictionary with evidence data
            attachment_paths: Optional list of file paths to attach
            checkpoint: Optional checkpoint manager (provided by decorator)
            
        Returns:
            The created EvidenceSchema object
            
        Raises:
            ValidationError: If evidence validation fails
            StorageError: If storage operation fails
            AttachmentError: If attachment processing fails
        """
        with ContextLogger(logger, operation="create_evidence", data=evidence_data) as log_ctx:
            try:
                # Initialize checkpoint if needed
                if checkpoint:
                    checkpoint.add_step("validate", "Validate evidence data")
                    checkpoint.add_step("process_attachments", "Process attachments")
                    checkpoint.add_step("create_evidence", "Create evidence item")
                    checkpoint.add_step("update_indices", "Update indices")
                
                # Validate evidence data
                if checkpoint:
                    checkpoint.start_step("validate")
                
                is_valid, errors = evidence_validation.validate_evidence(evidence_data)
                if not is_valid:
                    raise ValidationError(
                        "Invalid evidence data",
                        validation_errors=errors,
                        error_code="E201",
                        details={"evidence_data": evidence_data}
                    )
                
                if checkpoint:
                    checkpoint.complete_step("validate")
                    log_ctx.update(validation="passed")
                
                # Process attachments if provided
                attachments = []
                if attachment_paths:
                    if checkpoint:
                        checkpoint.start_step("process_attachments", {"count": len(attachment_paths)})
                    
                    try:
                        for path in attachment_paths:
                            attachment_obj = self._process_attachment(path)
                            attachments.append(attachment_obj)
                        
                        log_ctx.update(attachments=len(attachments))
                        
                        if checkpoint:
                            checkpoint.complete_step("process_attachments", {
                                "processed": len(attachments),
                                "attachment_ids": [att.id for att in attachments]
                            })
                    except Exception as e:
                        if checkpoint:
                            checkpoint.fail_step("process_attachments", str(e))
                        raise
                
                # Add attachments to evidence data
                if attachments:
                    evidence_data['attachments'] = [att.to_dict() for att in attachments]
                
                # Generate ID if not provided
                if 'id' not in evidence_data:
                    evidence_data['id'] = evidence_schema.generate_id("EVD-")
                
                # Set timestamps
                now = datetime.now()
                if 'created_at' not in evidence_data:
                    evidence_data['created_at'] = now
                if 'updated_at' not in evidence_data:
                    evidence_data['updated_at'] = now
                if 'date_collected' not in evidence_data:
                    evidence_data['date_collected'] = now
                
                # Create evidence object
                evidence = evidence_schema.EvidenceSchema(**evidence_data)
                evidence_id = evidence.id
                
                log_ctx.update(evidence_id=evidence_id)
                
                if checkpoint:
                    checkpoint.set_data("evidence_id", evidence_id)
                    checkpoint.start_step("create_evidence")
                
                # Save evidence to file
                evidence_file = self.evidence_dir / f"{evidence_id}.json"
                
                # Check for existing evidence file
                if evidence_file.exists():
                    raise StorageError(
                        f"Evidence with ID {evidence_id} already exists",
                        error_code="E101",
                        details={"evidence_id": evidence_id}
                    )
                
                self._write_json(evidence_file, evidence.to_dict())
                
                if checkpoint:
                    checkpoint.complete_step("create_evidence")
                    checkpoint.start_step("update_indices")
                
                # Update indices
                try:
                    self._update_indices(evidence, is_new=True)
                    
                    if checkpoint:
                        checkpoint.complete_step("update_indices")
                except Exception as e:
                    # If index update fails, try to delete the evidence file
                    try:
                        if evidence_file.exists():
                            os.remove(evidence_file)
                    except Exception:
                        pass
                    
                    if checkpoint:
                        checkpoint.fail_step("update_indices", str(e))
                    
                    raise
                
                logger.info(f"Created evidence {evidence_id}")
                return evidence
                
            except ValidationError:
                # Re-raise validation errors
                raise
            except AttachmentError:
                # Re-raise attachment errors
                raise
            except Exception as e:
                # Convert unexpected errors to StorageError
                raise StorageError(
                    f"Failed to create evidence: {str(e)}",
                    error_code="E102",
                    details={"error": str(e)}
                )
    
    def get(self, evidence_id: str) -> Optional[evidence_schema.EvidenceSchema]:
        """
        Get an evidence item by ID.
        
        Args:
            evidence_id: The evidence ID to retrieve
            
        Returns:
            EvidenceSchema object if found, None otherwise
        """
        evidence_file = self.evidence_dir / f"{evidence_id}.json"
        evidence_data = self._read_json(evidence_file)
        
        if not evidence_data:
            return None
        
        try:
            return evidence_schema.EvidenceSchema.from_dict(evidence_data)
        except Exception as e:
            logger.error(f"Failed to parse evidence {evidence_id}: {str(e)}")
            raise StorageError(
                f"Failed to parse evidence data: {str(e)}",
                error_code="E103",
                details={"evidence_id": evidence_id, "error": str(e)}
            )
    
    @with_checkpoint("evidence_update")
    def update(self, evidence_id: str, evidence_data: Dict, 
              attachment_paths: Optional[List[str]] = None,
              remove_attachments: Optional[List[str]] = None,
              checkpoint: Optional[CheckpointManager] = None) -> Optional[evidence_schema.EvidenceSchema]:
        """
        Update an existing evidence item.
        
        Args:
            evidence_id: The evidence ID to update
            evidence_data: Dictionary with updated evidence data
            attachment_paths: Optional list of file paths to attach
            remove_attachments: Optional list of attachment IDs to remove
            checkpoint: Optional checkpoint manager (provided by decorator)
            
        Returns:
            Updated EvidenceSchema object if found, None otherwise
            
        Raises:
            ValidationError: If evidence validation fails
            StorageError: If storage operation fails
            AttachmentError: If attachment processing fails
            EntityNotFoundError: If evidence not found
        """
        with ContextLogger(logger, operation="update_evidence", evidence_id=evidence_id) as log_ctx:
            try:
                # Initialize checkpoint if needed
                if checkpoint:
                    checkpoint.add_step("check_exists", "Check if evidence exists")
                    checkpoint.add_step("validate", "Validate updated evidence data")
                    checkpoint.add_step("backup", "Create backup of evidence")
                    checkpoint.add_step("process_attachments", "Process attachments")
                    checkpoint.add_step("update_evidence", "Update evidence item")
                    checkpoint.add_step("update_indices", "Update indices")
                
                # Check if evidence exists
                if checkpoint:
                    checkpoint.start_step("check_exists")
                
                existing_evidence = self.get(evidence_id)
                if not existing_evidence:
                    if checkpoint:
                        checkpoint.fail_step("check_exists", f"Evidence {evidence_id} not found")
                    
                    raise EntityNotFoundError("evidence", evidence_id)
                
                if checkpoint:
                    checkpoint.complete_step("check_exists")
                    checkpoint.set_data("original_evidence", existing_evidence.to_dict())
                
                # Update evidence data with existing values for fields not provided
                existing_dict = existing_evidence.to_dict()
                for key, value in existing_dict.items():
                    if key not in evidence_data:
                        evidence_data[key] = value
                
                # Set ID to ensure it doesn't change
                evidence_data['id'] = evidence_id
                
                # Update timestamp
                evidence_data['updated_at'] = datetime.now()
                
                # Validate evidence data
                if checkpoint:
                    checkpoint.start_step("validate")
                
                is_valid, errors = evidence_validation.validate_evidence(evidence_data)
                if not is_valid:
                    if checkpoint:
                        checkpoint.fail_step("validate", f"Validation failed: {', '.join(errors)}")
                    
                    raise ValidationError(
                        "Invalid evidence data",
                        validation_errors=errors,
                        error_code="E201",
                        details={"evidence_data": evidence_data}
                    )
                
                if checkpoint:
                    checkpoint.complete_step("validate")
                
                # Backup current evidence before changing
                evidence_file = self.evidence_dir / f"{evidence_id}.json"
                
                if checkpoint:
                    checkpoint.start_step("backup")
                
                self._backup_json(evidence_file)
                
                if checkpoint:
                    checkpoint.complete_step("backup")
                
                # Handle attachments
                if remove_attachments or attachment_paths:
                    if checkpoint:
                        checkpoint.start_step("process_attachments", {
                            "add_count": len(attachment_paths) if attachment_paths else 0,
                            "remove_count": len(remove_attachments) if remove_attachments else 0
                        })
                    
                    current_attachments = evidence_data.get('attachments', [])
                    
                    # Remove attachments if specified
                    if remove_attachments:
                        new_attachments = []
                        for att in current_attachments:
                            if isinstance(att, dict) and att.get('id') not in remove_attachments:
                                new_attachments.append(att)
                            elif isinstance(att, evidence_schema.AttachmentSchema) and att.id not in remove_attachments:
                                new_attachments.append(att)
                        
                        evidence_data['attachments'] = new_attachments
                        log_ctx.update(removed_attachments=len(current_attachments) - len(new_attachments))
                    
                    # Add new attachments if provided
                    if attachment_paths:
                        try:
                            new_attachments = []
                            for path in attachment_paths:
                                attachment_obj = self._process_attachment(path)
                                new_attachments.append(attachment_obj)
                            
                            # Convert to dict representation if needed
                            attachment_dicts = [
                                att.to_dict() if isinstance(att, evidence_schema.AttachmentSchema) else att
                                for att in evidence_data.get('attachments', [])
                            ]
                            
                            # Add new attachments
                            for att in new_attachments:
                                attachment_dicts.append(att.to_dict())
                            
                            evidence_data['attachments'] = attachment_dicts
                            log_ctx.update(added_attachments=len(new_attachments))
                            
                        except Exception as e:
                            if checkpoint:
                                checkpoint.fail_step("process_attachments", str(e))
                            raise
                    
                    if checkpoint:
                        checkpoint.complete_step("process_attachments")
                
                # Create updated evidence object
                updated_evidence = evidence_schema.EvidenceSchema.from_dict(evidence_data)
                
                if checkpoint:
                    checkpoint.start_step("update_evidence")
                
                # Save evidence to file
                self._write_json(evidence_file, updated_evidence.to_dict())
                
                if checkpoint:
                    checkpoint.complete_step("update_evidence")
                    checkpoint.start_step("update_indices")
                
                # Update indices
                try:
                    self._update_indices(updated_evidence)
                    
                    if checkpoint:
                        checkpoint.complete_step("update_indices")
                except Exception as e:
                    # If index update fails, try to restore from backup
                    try:
                        backup_file = evidence_file.with_suffix('.bak')
                        if backup_file.exists():
                            shutil.copy2(backup_file, evidence_file)
                    except Exception:
                        pass
                    
                    if checkpoint:
                        checkpoint.fail_step("update_indices", str(e))
                    
                    raise
                
                logger.info(f"Updated evidence {evidence_id}")
                return updated_evidence
                
            except EntityNotFoundError:
                # Re-raise not found errors
                raise
            except ValidationError:
                # Re-raise validation errors
                raise
            except AttachmentError:
                # Re-raise attachment errors
                raise
            except Exception as e:
                # Convert unexpected errors to StorageError
                raise StorageError(
                    f"Failed to update evidence: {str(e)}",
                    error_code="E104",
                    details={"evidence_id": evidence_id, "error": str(e)}
                )
    
    @with_checkpoint("evidence_delete")
    def delete(self, evidence_id: str, delete_attachments: bool = True,
              checkpoint: Optional[CheckpointManager] = None) -> bool:
        """
        Delete an evidence item.
        
        Args:
            evidence_id: The evidence ID to delete
            delete_attachments: If True, also delete attachment files
            checkpoint: Optional checkpoint manager (provided by decorator)
            
        Returns:
            True if the evidence was deleted, False if not found
        """
        with ContextLogger(logger, operation="delete_evidence", evidence_id=evidence_id) as log_ctx:
            try:
                # Initialize checkpoint if needed
                if checkpoint:
                    checkpoint.add_step("check_exists", "Check if evidence exists")
                    checkpoint.add_step("backup", "Create backup of evidence")
                    checkpoint.add_step("update_indices", "Update indices")
                    checkpoint.add_step("delete_evidence", "Delete evidence item")
                    if delete_attachments:
                        checkpoint.add_step("delete_attachments", "Delete attachment files")
                
                evidence_file = self.evidence_dir / f"{evidence_id}.json"
                
                # Check if evidence exists
                if checkpoint:
                    checkpoint.start_step("check_exists")
                
                if not evidence_file.exists():
                    if checkpoint:
                        checkpoint.fail_step("check_exists", f"Evidence {evidence_id} not found")
                    
                    return False
                
                # Load evidence data
                evidence_data = self._read_json(evidence_file)
                if not evidence_data:
                    if checkpoint:
                        checkpoint.fail_step("check_exists", f"Evidence {evidence_id} data is empty or corrupted")
                    
                    return False
                
                evidence = evidence_schema.EvidenceSchema.from_dict(evidence_data)
                
                if checkpoint:
                    checkpoint.complete_step("check_exists")
                    checkpoint.set_data("evidence", evidence.to_dict())
                
                # Create backup
                if checkpoint:
                    checkpoint.start_step("backup")
                
                self._backup_json(evidence_file)
                
                if checkpoint:
                    checkpoint.complete_step("backup")
                
                # Update indices before deleting file
                if checkpoint:
                    checkpoint.start_step("update_indices")
                
                try:
                    self._update_indices(evidence, is_delete=True)
                    
                    if checkpoint:
                        checkpoint.complete_step("update_indices")
                except Exception as e:
                    if checkpoint:
                        checkpoint.fail_step("update_indices", str(e))
                    
                    logger.error(f"Failed to update indices during delete of {evidence_id}: {str(e)}")
                    # Continue with deletion even if index update fails
                
                # Delete attachments if requested
                attachments_deleted = []
                attachments_failed = []
                
                if delete_attachments and evidence.attachments:
                    if checkpoint:
                        checkpoint.start_step("delete_attachments", {
                            "count": len(evidence.attachments)
                        })
                    
                    for attachment in evidence.attachments:
                        try:
                            file_path = self.attachments_dir / attachment.file_path
                            if file_path.exists():
                                os.remove(file_path)
                                attachments_deleted.append(attachment.id)
                        except Exception as e:
                            logger.error(f"Failed to delete attachment {attachment.id}: {str(e)}")
                            attachments_failed.append(attachment.id)
                    
                    if checkpoint:
                        checkpoint.complete_step("delete_attachments", {
                            "deleted": attachments_deleted,
                            "failed": attachments_failed
                        })
                
                # Delete evidence file
                if checkpoint:
                    checkpoint.start_step("delete_evidence")
                
                try:
                    os.remove(evidence_file)
                    
                    if checkpoint:
                        checkpoint.complete_step("delete_evidence")
                    
                    logger.info(f"Deleted evidence {evidence_id}")
                    return True
                except Exception as e:
                    if checkpoint:
                        checkpoint.fail_step("delete_evidence", str(e))
                    
                    raise FileOperationError(
                        f"Failed to delete evidence file: {str(e)}",
                        file_path=str(evidence_file),
                        operation="delete",
                        error_code="E118",
                        details={"evidence_id": evidence_id, "error": str(e)}
                    )
                
            except Exception as e:
                # Convert unexpected errors to StorageError
                raise StorageError(
                    f"Failed to delete evidence: {str(e)}",
                    error_code="E105",
                    details={"evidence_id": evidence_id, "error": str(e)}
                )
    
    def _process_attachment(self, file_path: str) -> evidence_schema.AttachmentSchema:
        """
        Process an attachment file and create an AttachmentSchema.
        
        Args:
            file_path: Path to the attachment file
            
        Returns:
            AttachmentSchema object
            
        Raises:
            AttachmentError: If attachment processing fails
        """
        try:
            # Generate a unique filename to prevent collisions
            original_filename = os.path.basename(file_path)
            timestamp = int(time.time())
            unique_id = uuid.uuid4().hex[:8]
            
            name, ext = os.path.splitext(original_filename)
            safe_filename = f"{name}_{timestamp}_{unique_id}{ext}".replace(' ', '_')
            
            # Copy file to attachments directory
            dest_path, metadata = safe_file_copy(
                file_path, 
                self.attachments_dir, 
                safe_filename
            )
            
            # Generate text preview for text-based files
            content_preview = generate_text_preview(file_path)
            
            # Create attachment object
            attachment_data = {
                'file_path': safe_filename,  # Store relative path
                'file_name': original_filename,
                'file_type': metadata['file_type'],
                'file_size': metadata['file_size'],
                'content_preview': content_preview,
                'description': f"Attached file: {original_filename}"
            }
            
            return evidence_schema.AttachmentSchema(**attachment_data)
            
        except FileOperationError as e:
            # Convert FileOperationError to AttachmentError
            raise AttachmentError(
                f"Failed to process attachment: {str(e)}",
                file_path=file_path,
                error_code="E141",
                details=e.details
            )
        except Exception as e:
            # Handle any other exceptions
            raise AttachmentError(
                f"Failed to process attachment: {str(e)}",
                file_path=file_path,
                error_code="E142",
                details={"error": str(e)}
            )
    
    def get_attachment_file(self, evidence_id: str, attachment_id: str) -> Optional[str]:
        """
        Get the file path for an attachment.
        
        Args:
            evidence_id: ID of the evidence
            attachment_id: ID of the attachment
            
        Returns:
            Absolute path to the attachment file or None if not found
            
        Raises:
            EntityNotFoundError: If evidence or attachment not found
        """
        # Get evidence
        evidence = self.get(evidence_id)
        if not evidence:
            raise EntityNotFoundError("evidence", evidence_id)
        
        # Find attachment
        attachment = None
        for att in evidence.attachments:
            if att.id == attachment_id:
                attachment = att
                break
        
        if not attachment:
            raise EntityNotFoundError("attachment", attachment_id, 
                                     details={"evidence_id": evidence_id})
        
        # Get full path to attachment file
        file_path = self.attachments_dir / attachment.file_path
        
        if not file_path.exists():
            raise AttachmentError(
                f"Attachment file not found on disk",
                attachment_id=attachment_id,
                evidence_id=evidence_id,
                file_path=str(file_path),
                error_code="E143"
            )
        
        return str(file_path)
    
    def list(self, filters: Optional[Dict] = None, 
            sort_by: str = 'updated_at', sort_order: str = 'desc',
            limit: Optional[int] = None, offset: int = 0) -> List[evidence_schema.EvidenceSchema]:
        """
        List evidence items with advanced filtering and sorting.
        
        Args:
            filters: Optional dictionary of filter criteria:
                - title: Substring match on title
                - description: Substring match on description
                - source: Exact match on source
                - category: Match on category
                - subcategory: Match on subcategory
                - relevance_score: Match on relevance score
                - tags: List of tags (all must match)
                - date_from: Minimum date_collected
                - date_to: Maximum date_collected
                - project_id: Match on project_id
                - epic_id: Match on epic_id
                - task_id: Match on task_id
                - created_by: Match on created_by
                - text: Full-text search across all text fields
            sort_by: Field to sort by (default: updated_at)
            sort_order: Sort order, 'asc' or 'desc' (default: desc)
            limit: Maximum number of items to return
            offset: Number of items to skip
            
        Returns:
            List of EvidenceSchema objects
            
        Raises:
            StorageError: If list operation fails
        """
        try:
            # Normalize and validate filters
            if filters:
                is_valid, normalized_filters, errors = evidence_validation.validate_evidence_search_params(filters)
                if not is_valid:
                    raise ValidationError(
                        "Invalid search parameters",
                        validation_errors=errors,
                        error_code="E202",
                        details={"filters": filters}
                    )
                filters = normalized_filters
            
            # Determine the most efficient way to get evidence items based on filters
            evidence_ids = self._get_filtered_evidence_ids(filters)
            
            # Load evidence items
            evidence_items = []
            for evidence_id in evidence_ids:
                evidence = self.get(evidence_id)
                if evidence:
                    evidence_items.append(evidence)
            
            # Apply text search if requested
            if filters and 'text' in filters and filters['text']:
                text_term = filters['text'].lower()
                filtered_items = []
                
                for evidence in evidence_items:
                    if (text_term in evidence.title.lower() or 
                        text_term in evidence.description.lower() or 
                        text_term in evidence.source.lower() or 
                        text_term in evidence.subcategory.lower() or
                        any(text_term in tag.lower() for tag in evidence.tags) or
                        any(hasattr(att, 'description') and text_term in att.description.lower() for att in evidence.attachments)):
                        filtered_items.append(evidence)
                
                evidence_items = filtered_items
            
            # Sort evidence items
            if sort_by:
                reverse = sort_order.lower() == 'desc'
                
                def get_sort_key(item):
                    if sort_by == 'title':
                        return item.title
                    elif sort_by == 'category':
                        return item.category.value
                    elif sort_by == 'relevance_score':
                        return item.relevance_score.value
                    elif sort_by == 'date_collected':
                        return item.date_collected
                    elif sort_by == 'created_at':
                        return item.created_at
                    elif sort_by == 'updated_at':
                        return item.updated_at
                    else:
                        return getattr(item, sort_by, '')
                
                evidence_items.sort(key=get_sort_key, reverse=reverse)
            
            # Apply pagination
            if offset > 0:
                evidence_items = evidence_items[offset:]
            
            if limit is not None:
                evidence_items = evidence_items[:limit]
            
            return evidence_items
            
        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Convert unexpected errors to StorageError
            raise StorageError(
                f"Failed to list evidence: {str(e)}",
                error_code="E106",
                details={"filters": filters, "error": str(e)}
            )
    
    def _get_filtered_evidence_ids(self, filters: Optional[Dict] = None) -> List[str]:
        """
        Get evidence IDs filtered by specified criteria.
        
        Args:
            filters: Optional dictionary of filter criteria
            
        Returns:
            List of evidence IDs matching the filters
        """
        if not filters:
            # Return all evidence IDs from main index
            main_index = self._read_json(self.main_index_file)
            return main_index.get('evidence', [])
        
        # Start with potentially the most restrictive filter
        
        # If filtering by tag, use tag index
        if 'tags' in filters and filters['tags']:
            tag_index = self._read_json(self.tag_index_file)
            tag_sets = []
            
            for tag in filters['tags']:
                tag_set = set(tag_index.get('tags', {}).get(tag, []))
                tag_sets.append(tag_set)
            
            # Intersection of all tag sets (evidence must have all tags)
            evidence_ids = set.intersection(*tag_sets) if tag_sets else set()
        
        # If filtering by category, use category index
        elif 'category' in filters and filters['category']:
            category_index = self._read_json(self.category_index_file)
            evidence_ids = set(category_index.get('categories', {}).get(filters['category'], []))
        
        # If filtering by epic_id, use relation index
        elif 'epic_id' in filters and filters['epic_id']:
            relation_index = self._read_json(self.relation_index_file)
            evidence_ids = set(relation_index.get('epic_relations', {}).get(filters['epic_id'], []))
        
        # If filtering by task_id, use relation index
        elif 'task_id' in filters and filters['task_id']:
            relation_index = self._read_json(self.relation_index_file)
            evidence_ids = set(relation_index.get('task_relations', {}).get(filters['task_id'], []))
        
        # Otherwise, start with all evidence IDs
        else:
            main_index = self._read_json(self.main_index_file)
            evidence_ids = set(main_index.get('evidence', []))
        
        # Convert to list
        evidence_ids = list(evidence_ids)
        
        # Apply other filters that require loading the evidence
        if any(key in filters for key in ['title', 'description', 'source', 'subcategory', 
                                          'relevance_score', 'date_from', 'date_to', 
                                          'created_by', 'project_id']):
            # Need to load evidence items for these filters
            filtered_ids = []
            
            for evidence_id in evidence_ids:
                evidence = self.get(evidence_id)
                if not evidence:
                    continue
                
                match = True
                
                # Filter by title substring
                if 'title' in filters and filters['title']:
                    if filters['title'].lower() not in evidence.title.lower():
                        match = False
                
                # Filter by description substring
                if match and 'description' in filters and filters['description']:
                    if filters['description'].lower() not in evidence.description.lower():
                        match = False
                
                # Filter by source
                if match and 'source' in filters and filters['source']:
                    if filters['source'].lower() != evidence.source.lower():
                        match = False
                
                # Filter by subcategory
                if match and 'subcategory' in filters and filters['subcategory']:
                    if filters['subcategory'].lower() != evidence.subcategory.lower():
                        match = False
                
                # Filter by relevance_score
                if match and 'relevance_score' in filters and filters['relevance_score']:
                    if evidence.relevance_score.value != filters['relevance_score']:
                        match = False
                
                # Filter by date range
                if match and 'date_from' in filters and filters['date_from']:
                    if evidence.date_collected < filters['date_from']:
                        match = False
                
                if match and 'date_to' in filters and filters['date_to']:
                    if evidence.date_collected > filters['date_to']:
                        match = False
                
                # Filter by created_by
                if match and 'created_by' in filters and filters['created_by']:
                    if evidence.created_by != filters['created_by']:
                        match = False
                
                # Filter by project_id
                if match and 'project_id' in filters and filters['project_id']:
                    if evidence.project_id != filters['project_id']:
                        match = False
                
                if match:
                    filtered_ids.append(evidence_id)
            
            return filtered_ids
        
        return evidence_ids
    
    def get_related_evidence(self, entity_type: str, entity_id: str) -> List[evidence_schema.EvidenceSchema]:
        """
        Get evidence items related to a specific entity.
        
        Args:
            entity_type: Type of entity ('epic', 'task', or 'evidence')
            entity_id: ID of the entity
            
        Returns:
            List of related EvidenceSchema objects
        """
        try:
            relation_index = self._read_json(self.relation_index_file)
            
            if entity_type == 'epic':
                evidence_ids = relation_index.get('epic_relations', {}).get(entity_id, [])
            elif entity_type == 'task':
                evidence_ids = relation_index.get('task_relations', {}).get(entity_id, [])
            elif entity_type == 'evidence':
                evidence_ids = relation_index.get('evidence_relations', {}).get(entity_id, [])
            else:
                raise ValueError(f"Invalid entity type: {entity_type}")
            
            # Load evidence items
            evidence_items = []
            for evidence_id in evidence_ids:
                evidence = self.get(evidence_id)
                if evidence:
                    evidence_items.append(evidence)
            
            return evidence_items
            
        except Exception as e:
            raise StorageError(
                f"Failed to get related evidence: {str(e)}",
                error_code="E107",
                details={"entity_type": entity_type, "entity_id": entity_id, "error": str(e)}
            )
    
    def get_tags(self) -> Dict[str, int]:
        """
        Get all tags with their frequency.
        
        Returns:
            Dictionary mapping tag to frequency
        """
        try:
            tag_index = self._read_json(self.tag_index_file)
            
            tag_counts = {}
            for tag, evidence_ids in tag_index.get('tags', {}).items():
                tag_counts[tag] = len(evidence_ids)
            
            return tag_counts
            
        except Exception as e:
            raise StorageError(
                f"Failed to get tags: {str(e)}",
                error_code="E108",
                details={"error": str(e)}
            )
    
    def get_categories(self) -> Dict[str, int]:
        """
        Get all categories with their frequency.
        
        Returns:
            Dictionary mapping category to frequency
        """
        try:
            category_index = self._read_json(self.category_index_file)
            
            category_counts = {}
            for category, evidence_ids in category_index.get('categories', {}).items():
                category_counts[category] = len(evidence_ids)
            
            return category_counts
            
        except Exception as e:
            raise StorageError(
                f"Failed to get categories: {str(e)}",
                error_code="E109",
                details={"error": str(e)}
            )
    
    def rebuild_indices(self) -> Tuple[bool, Optional[str]]:
        """
        Rebuild all indices from evidence files.
        
        Returns:
            Tuple containing:
                - Boolean indicating success
                - Optional error message
        """
        with ContextLogger(logger, operation="rebuild_indices") as log_ctx:
            try:
                # Create new empty indices
                main_index = {'evidence': []}
                tag_index = {'tags': {}}
                category_index = {'categories': {}}
                relation_index = {
                    'epic_relations': {},
                    'task_relations': {},
                    'evidence_relations': {}
                }
                
                # Find all evidence files
                evidence_files = list(self.evidence_dir.glob('EVD-*.json'))
                log_ctx.update(evidence_count=len(evidence_files))
                
                # Process each evidence file
                for evidence_file in evidence_files:
                    try:
                        evidence_data = self._read_json(evidence_file)
                        if not evidence_data:
                            continue
                        
                        evidence = evidence_schema.EvidenceSchema.from_dict(evidence_data)
                        evidence_id = evidence.id
                        
                        # Update main index
                        if evidence_id not in main_index['evidence']:
                            main_index['evidence'].append(evidence_id)
                        
                        # Update tag index
                        for tag in evidence.tags:
                            if tag not in tag_index['tags']:
                                tag_index['tags'][tag] = []
                            
                            if evidence_id not in tag_index['tags'][tag]:
                                tag_index['tags'][tag].append(evidence_id)
                        
                        # Update category index
                        category = evidence.category.value
                        if category not in category_index['categories']:
                            category_index['categories'][category] = []
                        
                        if evidence_id not in category_index['categories'][category]:
                            category_index['categories'][category].append(evidence_id)
                        
                        # Update relation indices
                        
                        # Epic relations
                        if evidence.epic_id:
                            if evidence.epic_id not in relation_index['epic_relations']:
                                relation_index['epic_relations'][evidence.epic_id] = []
                            
                            if evidence_id not in relation_index['epic_relations'][evidence.epic_id]:
                                relation_index['epic_relations'][evidence.epic_id].append(evidence_id)
                        
                        # Task relations
                        if evidence.task_id:
                            if evidence.task_id not in relation_index['task_relations']:
                                relation_index['task_relations'][evidence.task_id] = []
                            
                            if evidence_id not in relation_index['task_relations'][evidence.task_id]:
                                relation_index['task_relations'][evidence.task_id].append(evidence_id)
                        
                        # Evidence relations
                        if evidence.related_evidence_ids:
                            if evidence_id not in relation_index['evidence_relations']:
                                relation_index['evidence_relations'][evidence_id] = []
                            
                            for related_id in evidence.related_evidence_ids:
                                # Add relation from this evidence to related
                                if related_id not in relation_index['evidence_relations'][evidence_id]:
                                    relation_index['evidence_relations'][evidence_id].append(related_id)
                                
                                # Add reverse relation
                                if related_id not in relation_index['evidence_relations']:
                                    relation_index['evidence_relations'][related_id] = []
                                
                                if evidence_id not in relation_index['evidence_relations'][related_id]:
                                    relation_index['evidence_relations'][related_id].append(evidence_id)
                        
                    except Exception as e:
                        logger.error(f"Failed to process evidence file {evidence_file}: {str(e)}")
                
                # Backup current indices
                self._backup_json(self.main_index_file)
                self._backup_json(self.tag_index_file)
                self._backup_json(self.category_index_file)
                self._backup_json(self.relation_index_file)
                
                # Write new indices
                self._write_json(self.main_index_file, main_index)
                self._write_json(self.tag_index_file, tag_index)
                self._write_json(self.category_index_file, category_index)
                self._write_json(self.relation_index_file, relation_index)
                
                logger.info("Successfully rebuilt indices")
                return True, None
                
            except Exception as e:
                error_message = f"Failed to rebuild indices: {str(e)}"
                logger.error(error_message)
                return False, error_message
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self._close_locks()