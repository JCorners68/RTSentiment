"""
Evidence Migration Framework for the Kanban CLI.

This module provides tools for schema migration, version upgrades, data validation,
rollback capabilities, and comprehensive logging/auditing of migration operations.
"""
import os
import json
import logging
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Callable

from ..models.evidence_schema import EvidenceSchema, SchemaVersion
from ..utils.exceptions import (
    StorageError, ValidationError, MigrationError, 
    EntityNotFoundError, FileOperationError
)
from ..utils.file_handlers import safe_path_join, safe_file_copy, safe_delete_file
from ..utils.checkpoints import CheckpointManager
from ..config.settings import get_project_root, load_config

# Configure logger
logger = logging.getLogger(__name__)


class MigrationLog:
    """
    Handles logging and auditing of migration operations.
    
    This class maintains detailed logs of all schema migrations, including
    success/failure status, affected entities, and rollback information.
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Initialize the migration logger.
        
        Args:
            log_dir: Optional directory for migration logs
        """
        self.config = load_config()
        self.project_root = get_project_root()
        
        # Set up log directory
        if log_dir:
            self.log_dir = log_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.log_dir = data_dir / 'migration_logs'
            
        # Ensure directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up log files
        self.current_log_file = None
        self.migration_history_file = self.log_dir / 'migration_history.json'
        
        # Initialize migration history
        self._ensure_history_file()
    
    def _ensure_history_file(self):
        """Ensure migration history file exists."""
        if not self.migration_history_file.exists():
            with open(self.migration_history_file, 'w') as f:
                json.dump({'migrations': []}, f)
    
    def start_migration_log(self, migration_id: str, description: str, from_version: str, to_version: str) -> Path:
        """
        Start a new migration log.
        
        Args:
            migration_id: Unique identifier for the migration
            description: Human-readable description of the migration
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            Path to the created log file
        """
        timestamp = datetime.now().isoformat().replace(':', '-')
        log_filename = f"{migration_id}_{timestamp}.log"
        self.current_log_file = self.log_dir / log_filename
        
        # Create log file with header
        with open(self.current_log_file, 'w') as f:
            f.write(f"Migration ID: {migration_id}\n")
            f.write(f"Description: {description}\n")
            f.write(f"From Version: {from_version}\n")
            f.write(f"To Version: {to_version}\n")
            f.write(f"Started: {timestamp}\n")
            f.write("-" * 80 + "\n")
        
        # Update migration history
        with open(self.migration_history_file, 'r') as f:
            history = json.load(f)
            
        history['migrations'].append({
            'migration_id': migration_id,
            'description': description,
            'from_version': from_version,
            'to_version': to_version,
            'started_at': timestamp,
            'status': 'in_progress',
            'log_file': str(self.current_log_file),
            'affected_entities': [],
            'errors': []
        })
        
        with open(self.migration_history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        return self.current_log_file
    
    def log_entity_migration(
        self, 
        migration_id: str, 
        entity_id: str, 
        status: str,
        details: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """
        Log a single entity migration event.
        
        Args:
            migration_id: Unique identifier for the migration
            entity_id: ID of the migrated entity
            status: 'success', 'failure', or 'rollback'
            details: Optional details about the migration
            error: Optional error message if status is 'failure'
        """
        if not self.current_log_file:
            raise ValueError("No active migration log. Call start_migration_log first.")
            
        timestamp = datetime.now().isoformat()
        with open(self.current_log_file, 'a') as f:
            f.write(f"\n[{timestamp}] Entity: {entity_id}, Status: {status}\n")
            if details:
                f.write(f"Details: {json.dumps(details, indent=2)}\n")
            if error:
                f.write(f"Error: {error}\n")
        
        # Update migration history
        with open(self.migration_history_file, 'r') as f:
            history = json.load(f)
            
        for migration in history['migrations']:
            if migration['migration_id'] == migration_id:
                if 'affected_entities' not in migration:
                    migration['affected_entities'] = []
                    
                migration['affected_entities'].append({
                    'entity_id': entity_id,
                    'status': status,
                    'timestamp': timestamp,
                    'error': error
                })
                
                if status == 'failure' and error:
                    if 'errors' not in migration:
                        migration['errors'] = []
                    migration['errors'].append({
                        'entity_id': entity_id,
                        'error': error,
                        'timestamp': timestamp
                    })
                
                break
        
        with open(self.migration_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def complete_migration(self, migration_id: str, status: str, summary: Dict):
        """
        Complete a migration log.
        
        Args:
            migration_id: Unique identifier for the migration
            status: 'completed', 'failed', or 'rolled_back'
            summary: Migration summary information
        """
        if not self.current_log_file:
            raise ValueError("No active migration log. Call start_migration_log first.")
            
        timestamp = datetime.now().isoformat()
        with open(self.current_log_file, 'a') as f:
            f.write(f"\n{'-' * 80}\n")
            f.write(f"Migration Completed at: {timestamp}\n")
            f.write(f"Status: {status}\n")
            f.write(f"Summary:\n")
            f.write(f"  Total Entities: {summary.get('total', 0)}\n")
            f.write(f"  Succeeded: {summary.get('succeeded', 0)}\n")
            f.write(f"  Failed: {summary.get('failed', 0)}\n")
            f.write(f"  Rolled Back: {summary.get('rolled_back', 0)}\n")
            if 'error' in summary:
                f.write(f"  Error: {summary['error']}\n")
        
        # Update migration history
        with open(self.migration_history_file, 'r') as f:
            history = json.load(f)
            
        for migration in history['migrations']:
            if migration['migration_id'] == migration_id:
                migration['status'] = status
                migration['completed_at'] = timestamp
                migration['summary'] = summary
                break
        
        with open(self.migration_history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
        self.current_log_file = None
    
    def get_migration_history(self) -> List[Dict]:
        """
        Get the migration history.
        
        Returns:
            List of migration records
        """
        with open(self.migration_history_file, 'r') as f:
            history = json.load(f)
            
        return history['migrations']
    
    def get_migration_log(self, migration_id: str) -> Optional[str]:
        """
        Get the full log for a specific migration.
        
        Args:
            migration_id: Unique identifier for the migration
            
        Returns:
            Full log content as string, or None if not found
        """
        # Find the log file from history
        with open(self.migration_history_file, 'r') as f:
            history = json.load(f)
            
        log_file = None
        for migration in history['migrations']:
            if migration['migration_id'] == migration_id:
                log_file = migration.get('log_file')
                break
                
        if not log_file:
            return None
            
        # Read the log file
        log_path = Path(log_file)
        if not log_path.exists():
            return None
            
        with open(log_path, 'r') as f:
            return f.read()


class MigrationManager:
    """
    Manages schema migrations and version upgrades for the Evidence Management System.
    
    This class provides comprehensive tooling for migrating evidence data between
    schema versions, with validation, rollback capabilities, and detailed logging.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the migration manager.
        
        Args:
            storage_dir: Optional directory for evidence storage
        """
        self.config = load_config()
        self.project_root = get_project_root()
        
        # Set up storage directory
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.storage_dir = data_dir / 'evidence'
            
        # Set up migration log
        self.migration_log = MigrationLog()
        
        # Set up backup directory for rollbacks
        self.backup_dir = self.storage_dir / 'migration_backups'
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def generate_migration_id(self) -> str:
        """
        Generate a unique migration ID.
        
        Returns:
            Migration ID string
        """
        timestamp = int(time.time())
        return f"migration_{timestamp}"
    
    def create_backup(self, entity_id: str, migration_id: str) -> str:
        """
        Create a backup of an entity before migration.
        
        Args:
            entity_id: ID of the entity to back up
            migration_id: ID of the migration operation
            
        Returns:
            Path to the backup file
            
        Raises:
            FileOperationError: If backup fails
            EntityNotFoundError: If entity doesn't exist
        """
        # Ensure migration backup directory exists
        migration_backup_dir = self.backup_dir / migration_id
        os.makedirs(migration_backup_dir, exist_ok=True)
        
        # Source file path
        entity_file = self.storage_dir / f"{entity_id}.json"
        if not entity_file.exists():
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
            
        # Backup file path
        backup_file = migration_backup_dir / f"{entity_id}.json"
        
        try:
            # Copy the file
            shutil.copy2(entity_file, backup_file)
            return str(backup_file)
        except Exception as e:
            raise FileOperationError(f"Failed to create backup for {entity_id}: {str(e)}")
    
    def restore_from_backup(self, entity_id: str, migration_id: str) -> bool:
        """
        Restore an entity from backup.
        
        Args:
            entity_id: ID of the entity to restore
            migration_id: ID of the migration operation
            
        Returns:
            True if restored successfully, False if backup not found
            
        Raises:
            FileOperationError: If restore fails
        """
        # Backup file path
        backup_file = self.backup_dir / migration_id / f"{entity_id}.json"
        if not backup_file.exists():
            return False
            
        # Destination file path
        entity_file = self.storage_dir / f"{entity_id}.json"
        
        try:
            # Copy the backup back to the original location
            shutil.copy2(backup_file, entity_file)
            return True
        except Exception as e:
            raise FileOperationError(f"Failed to restore backup for {entity_id}: {str(e)}")
    
    def get_entity_version(self, entity_id: str) -> Optional[str]:
        """
        Get the schema version of an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            Schema version string, or None if not found
            
        Raises:
            FileOperationError: If reading fails
        """
        entity_file = self.storage_dir / f"{entity_id}.json"
        if not entity_file.exists():
            return None
            
        try:
            with open(entity_file, 'r') as f:
                data = json.load(f)
                
            return data.get('_schema_version', '1.0.0')  # Default to 1.0.0 if not specified
        except Exception as e:
            raise FileOperationError(f"Failed to read entity {entity_id}: {str(e)}")
    
    def migrate_entity(
        self, 
        entity_id: str, 
        from_version: str, 
        to_version: str,
        migration_id: str,
        validation_func: Optional[Callable] = None
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Migrate a single entity to a new schema version.
        
        Args:
            entity_id: ID of the entity to migrate
            from_version: Source schema version
            to_version: Target schema version
            migration_id: ID of the migration operation
            validation_func: Optional function to validate migrated data
            
        Returns:
            Tuple of (success, migrated_data, error_message)
            
        Raises:
            FileOperationError: If file operations fail
            MigrationError: If migration fails
        """
        # Check if entity exists
        entity_file = self.storage_dir / f"{entity_id}.json"
        if not entity_file.exists():
            return False, None, f"Entity not found: {entity_id}"
            
        try:
            # Read the entity data
            with open(entity_file, 'r') as f:
                data = json.load(f)
                
            # Verify current version
            current_version = data.get('_schema_version', from_version)
            if current_version != from_version:
                return False, None, f"Entity version mismatch: expected {from_version}, found {current_version}"
                
            # Create backup
            self.create_backup(entity_id, migration_id)
            
            # Perform migration
            try:
                # Create an evidence schema object and convert back to dict
                # This uses the automatic migration in from_dict/to_dict
                evidence = EvidenceSchema.from_dict(data)
                migrated_data = evidence.to_dict()
                
                # Explicitly set the target schema version
                migrated_data['_schema_version'] = to_version
                
                # Validate if a validation function is provided
                if validation_func:
                    is_valid, validation_errors = validation_func(migrated_data)
                    if not is_valid:
                        error_msg = f"Validation failed: {', '.join(validation_errors)}"
                        return False, None, error_msg
                
                # Write migrated data back to file
                with open(entity_file, 'w') as f:
                    json.dump(migrated_data, f, indent=2)
                    
                return True, migrated_data, None
            except Exception as e:
                # Migration failed, restore from backup
                self.restore_from_backup(entity_id, migration_id)
                return False, None, f"Migration failed: {str(e)}"
                
        except Exception as e:
            return False, None, f"Error processing entity: {str(e)}"
    
    def migrate_all_entities(
        self, 
        from_version: str, 
        to_version: str,
        description: str = "Schema upgrade",
        validation_func: Optional[Callable] = None,
        entity_filter: Optional[Callable] = None,
        batch_size: int = 100,
        dry_run: bool = False
    ) -> Dict:
        """
        Migrate all entities from one schema version to another.
        
        Args:
            from_version: Source schema version
            to_version: Target schema version
            description: Human-readable description of the migration
            validation_func: Optional function to validate migrated data
            entity_filter: Optional function to filter entities to migrate
            batch_size: Number of entities to process in each batch
            dry_run: If True, don't actually modify files
            
        Returns:
            Migration summary
            
        Raises:
            MigrationError: If migration fails catastrophically
        """
        # Generate migration ID
        migration_id = self.generate_migration_id()
        
        # Start migration log
        self.migration_log.start_migration_log(
            migration_id, description, from_version, to_version
        )
        
        # Find all entity files
        entity_files = list(self.storage_dir.glob("*.json"))
        entity_ids = [file.stem for file in entity_files if file.stem != 'metadata']
        
        # Apply filter if provided
        if entity_filter:
            filtered_ids = []
            for entity_id in entity_ids:
                try:
                    # Read the entity data
                    with open(self.storage_dir / f"{entity_id}.json", 'r') as f:
                        data = json.load(f)
                        
                    if entity_filter(data):
                        filtered_ids.append(entity_id)
                except Exception:
                    # Skip entities that can't be read
                    continue
            entity_ids = filtered_ids
        
        # Initialize counters
        total = len(entity_ids)
        succeeded = 0
        failed = 0
        rolled_back = 0
        skipped = 0
        
        # Process entities in batches
        try:
            for i in range(0, total, batch_size):
                batch = entity_ids[i:i+batch_size]
                
                for entity_id in batch:
                    # Check if entity should be migrated
                    entity_version = self.get_entity_version(entity_id)
                    if entity_version != from_version:
                        skipped += 1
                        continue
                    
                    # Skip actual migration if dry run
                    if dry_run:
                        self.migration_log.log_entity_migration(
                            migration_id, entity_id, 'skipped',
                            details={'reason': 'dry_run'}
                        )
                        skipped += 1
                        continue
                    
                    # Perform migration
                    success, migrated_data, error = self.migrate_entity(
                        entity_id, from_version, to_version, migration_id, validation_func
                    )
                    
                    if success:
                        succeeded += 1
                        self.migration_log.log_entity_migration(
                            migration_id, entity_id, 'success',
                            details={'version': to_version}
                        )
                    else:
                        failed += 1
                        if self.restore_from_backup(entity_id, migration_id):
                            rolled_back += 1
                            self.migration_log.log_entity_migration(
                                migration_id, entity_id, 'failure',
                                error=error, details={'rolled_back': True}
                            )
                        else:
                            self.migration_log.log_entity_migration(
                                migration_id, entity_id, 'failure',
                                error=error, details={'rolled_back': False}
                            )
            
            # Complete migration log
            summary = {
                'total': total,
                'succeeded': succeeded,
                'failed': failed,
                'rolled_back': rolled_back,
                'skipped': skipped,
                'dry_run': dry_run
            }
            
            status = 'completed' if failed == 0 else 'completed_with_errors'
            self.migration_log.complete_migration(migration_id, status, summary)
            
            return summary
            
        except Exception as e:
            # Log catastrophic failure
            summary = {
                'total': total,
                'succeeded': succeeded,
                'failed': failed,
                'rolled_back': rolled_back,
                'skipped': skipped,
                'error': str(e),
                'dry_run': dry_run
            }
            
            self.migration_log.complete_migration(migration_id, 'failed', summary)
            raise MigrationError(f"Migration failed: {str(e)}")
    
    def rollback_migration(self, migration_id: str) -> Dict:
        """
        Rollback an entire migration.
        
        Args:
            migration_id: ID of the migration to roll back
            
        Returns:
            Rollback summary
            
        Raises:
            MigrationError: If rollback fails
        """
        # Get migration history
        migrations = self.migration_log.get_migration_history()
        target_migration = None
        
        for migration in migrations:
            if migration['migration_id'] == migration_id:
                target_migration = migration
                break
                
        if not target_migration:
            raise MigrationError(f"Migration not found: {migration_id}")
            
        # Check if migration is completed
        if target_migration['status'] not in ['completed', 'completed_with_errors']:
            raise MigrationError(f"Cannot roll back migration with status: {target_migration['status']}")
            
        # Find affected entities
        affected_entities = target_migration.get('affected_entities', [])
        entity_ids = [entity['entity_id'] for entity in affected_entities 
                     if entity['status'] == 'success']
        
        # Initialize counters
        total = len(entity_ids)
        succeeded = 0
        failed = 0
        
        # Rollback each entity
        for entity_id in entity_ids:
            try:
                if self.restore_from_backup(entity_id, migration_id):
                    succeeded += 1
                    self.migration_log.log_entity_migration(
                        migration_id, entity_id, 'rollback',
                        details={'status': 'success'}
                    )
                else:
                    failed += 1
                    self.migration_log.log_entity_migration(
                        migration_id, entity_id, 'rollback',
                        details={'status': 'failed'},
                        error="Backup not found"
                    )
            except Exception as e:
                failed += 1
                self.migration_log.log_entity_migration(
                    migration_id, entity_id, 'rollback',
                    details={'status': 'failed'},
                    error=str(e)
                )
        
        # Complete rollback log
        summary = {
            'total': total,
            'succeeded': succeeded,
            'failed': failed,
            'original_migration': target_migration['migration_id'],
            'from_version': target_migration['to_version'],
            'to_version': target_migration['from_version']
        }
        
        status = 'rolled_back' if failed == 0 else 'rolled_back_with_errors'
        self.migration_log.complete_migration(
            f"rollback_{migration_id}", status, summary
        )
        
        return summary
    
    def get_available_migrations(self) -> List[Dict]:
        """
        Get available migration paths.
        
        Returns:
            List of available migration paths
        """
        return [
            {'from_version': '1.0.0', 'to_version': '1.1.0', 'description': 'Add hierarchical categories and versioning'},
            # Add more migrations as they become available
        ]
    
    def validate_migration_path(self, from_version: str, to_version: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a migration path is available.
        
        Args:
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        available_migrations = self.get_available_migrations()
        
        for migration in available_migrations:
            if migration['from_version'] == from_version and migration['to_version'] == to_version:
                return True, None
                
        return False, f"No migration path from {from_version} to {to_version}"


# Helper function to create a migration manager
def get_migration_manager() -> MigrationManager:
    """Get a configured migration manager instance."""
    return MigrationManager()
