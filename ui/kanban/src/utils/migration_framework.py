"""
Data Migration Framework for Evidence Management System.

This module provides tools to perform safe data migrations with logging,
rollback capabilities, and audit trails.
"""
import os
import json
import shutil
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
import traceback
import hashlib

from ..models.schema_versioning import SchemaRegistry, get_schema_registry

# Configure logger
logger = logging.getLogger(__name__)

class MigrationError(Exception):
    """Exception raised for migration errors."""
    pass

class MigrationLog:
    """Represents a log entry for a migration operation."""
    
    def __init__(self, migration_id: str, from_version: str, to_version: str):
        """
        Initialize a migration log.
        
        Args:
            migration_id: Unique ID for this migration operation
            from_version: Source schema version
            to_version: Target schema version
        """
        self.migration_id = migration_id
        self.from_version = from_version
        self.to_version = to_version
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.status = "in_progress"  # in_progress, completed, failed, rolled_back
        self.affected_items = []
        self.error_message = None
        self.created_backups = []
    
    def complete(self) -> None:
        """Mark the migration as completed."""
        self.end_time = datetime.now().isoformat()
        self.status = "completed"
    
    def fail(self, error_message: str) -> None:
        """Mark the migration as failed."""
        self.end_time = datetime.now().isoformat()
        self.status = "failed"
        self.error_message = error_message
    
    def rollback(self) -> None:
        """Mark the migration as rolled back."""
        self.end_time = datetime.now().isoformat()
        self.status = "rolled_back"
    
    def add_affected_item(self, item_id: str, item_type: str) -> None:
        """
        Add an affected item to the log.
        
        Args:
            item_id: ID of the affected item
            item_type: Type of the affected item
        """
        self.affected_items.append({
            "id": item_id,
            "type": item_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_backup(self, backup_path: str) -> None:
        """
        Add a created backup to the log.
        
        Args:
            backup_path: Path to the backup file
        """
        self.created_backups.append({
            "path": backup_path,
            "timestamp": datetime.now().isoformat()
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the log to a dictionary."""
        return {
            "migration_id": self.migration_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status,
            "affected_items": self.affected_items,
            "error_message": self.error_message,
            "created_backups": self.created_backups
        }


class MigrationManager:
    """Manager for data migrations with logging and rollback."""
    
    def __init__(self, data_dir: Path, schema_registry: Optional[SchemaRegistry] = None):
        """
        Initialize the migration manager.
        
        Args:
            data_dir: Directory for data files
            schema_registry: Optional schema registry to use
        """
        self.data_dir = data_dir
        self.backup_dir = data_dir / "backups"
        self.logs_dir = data_dir / "logs"
        self.schema_registry = schema_registry or get_schema_registry()
        
        # Ensure directories exist
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def generate_migration_id(self) -> str:
        """Generate a unique migration ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_hex = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"migration_{timestamp}_{random_hex}"
    
    def create_backup(self, file_path: Path, migration_id: str) -> str:
        """
        Create a backup of a file.
        
        Args:
            file_path: Path to the file to backup
            migration_id: ID of the migration operation
            
        Returns:
            Path to the backup file
        """
        if not file_path.exists():
            logger.warning(f"Attempted to backup non-existent file: {file_path}")
            return ""
        
        # Create backup filename with timestamp and migration ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}_{migration_id}{file_path.suffix}"
        backup_path = self.backup_dir / backup_filename
        
        # Copy the file
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        
        return str(backup_path)
    
    def restore_backup(self, backup_path: str, original_path: Path) -> bool:
        """
        Restore a file from backup.
        
        Args:
            backup_path: Path to the backup file
            original_path: Path to restore to
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            shutil.copy2(backup_path, original_path)
            logger.info(f"Restored backup from {backup_path} to {original_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {str(e)}")
            return False
    
    def save_log(self, log: MigrationLog) -> None:
        """
        Save a migration log to file.
        
        Args:
            log: MigrationLog object to save
        """
        log_file = self.logs_dir / f"migration_{log.migration_id}.json"
        
        try:
            with open(log_file, 'w') as f:
                json.dump(log.to_dict(), f, indent=2)
            logger.info(f"Migration log saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save migration log: {str(e)}")
    
    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Get all migration logs.
        
        Returns:
            List of migration log dictionaries
        """
        logs = []
        
        for log_file in self.logs_dir.glob("migration_*.json"):
            try:
                with open(log_file, 'r') as f:
                    logs.append(json.load(f))
            except Exception as e:
                logger.error(f"Failed to read log file {log_file}: {str(e)}")
        
        # Sort by start time
        logs.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return logs
    
    def migrate_file(
        self, 
        file_path: Path, 
        from_version: str, 
        to_version: str,
        item_id_field: str = "id",
        item_type_field: str = "type"
    ) -> Tuple[bool, Optional[str]]:
        """
        Migrate a data file from one schema version to another.
        
        Args:
            file_path: Path to the data file
            from_version: Source schema version
            to_version: Target schema version
            item_id_field: Field name for item ID in the data
            item_type_field: Field name for item type in the data
            
        Returns:
            Tuple containing:
                - Boolean indicating success
                - Error message if failed, None otherwise
        """
        migration_id = self.generate_migration_id()
        migration_log = MigrationLog(migration_id, from_version, to_version)
        
        try:
            # Check if file exists
            if not file_path.exists():
                raise MigrationError(f"File not found: {file_path}")
            
            # Create backup
            backup_path = self.create_backup(file_path, migration_id)
            migration_log.add_backup(backup_path)
            
            # Read data file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check if data is a list or dict
            if isinstance(data, list):
                # Migrate each item in the list
                for i, item in enumerate(data):
                    try:
                        # Log affected item
                        item_id = item.get(item_id_field, f"item_{i}")
                        item_type = item.get(item_type_field, "unknown")
                        migration_log.add_affected_item(item_id, item_type)
                        
                        # Migrate the item
                        data[i] = self.schema_registry.migrate_data(item, from_version, to_version)
                    except Exception as e:
                        logger.error(f"Failed to migrate item {i} in {file_path}: {str(e)}")
                        raise MigrationError(f"Failed to migrate item {i}: {str(e)}")
            elif isinstance(data, dict):
                # Handle collection of items in a dictionary
                if "items" in data and isinstance(data["items"], list):
                    for i, item in enumerate(data["items"]):
                        try:
                            item_id = item.get(item_id_field, f"item_{i}")
                            item_type = item.get(item_type_field, "unknown")
                            migration_log.add_affected_item(item_id, item_type)
                            
                            data["items"][i] = self.schema_registry.migrate_data(
                                item, from_version, to_version
                            )
                        except Exception as e:
                            logger.error(f"Failed to migrate item {i} in {file_path}: {str(e)}")
                            raise MigrationError(f"Failed to migrate item {i}: {str(e)}")
                else:
                    # Migrate the whole dict as one item
                    item_id = data.get(item_id_field, "main_item")
                    item_type = data.get(item_type_field, "unknown")
                    migration_log.add_affected_item(item_id, item_type)
                    
                    data = self.schema_registry.migrate_data(data, from_version, to_version)
            else:
                raise MigrationError(f"Unsupported data format in {file_path}")
            
            # Write migrated data back to file
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Mark migration as completed
            migration_log.complete()
            self.save_log(migration_log)
            
            logger.info(f"Successfully migrated {file_path} from version {from_version} to {to_version}")
            return True, None
            
        except Exception as e:
            # Log the error
            error_msg = f"Migration failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            
            # Try to rollback
            if backup_path:
                if self.restore_backup(backup_path, file_path):
                    logger.info(f"Successfully rolled back {file_path} from backup")
                else:
                    logger.error(f"Failed to roll back {file_path} from backup")
            
            # Mark migration as failed
            migration_log.fail(error_msg)
            self.save_log(migration_log)
            
            return False, error_msg
    
    def migrate_directory(
        self, 
        directory_path: Path, 
        file_pattern: str,
        from_version: str, 
        to_version: str,
        item_id_field: str = "id",
        item_type_field: str = "type"
    ) -> Tuple[bool, List[str]]:
        """
        Migrate all matching files in a directory.
        
        Args:
            directory_path: Path to the directory
            file_pattern: Glob pattern to match files
            from_version: Source schema version
            to_version: Target schema version
            item_id_field: Field name for item ID in the data
            item_type_field: Field name for item type in the data
            
        Returns:
            Tuple containing:
                - Boolean indicating overall success
                - List of error messages
        """
        errors = []
        success_count = 0
        fail_count = 0
        
        for file_path in directory_path.glob(file_pattern):
            success, error = self.migrate_file(
                file_path, from_version, to_version, item_id_field, item_type_field
            )
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                errors.append(f"Failed to migrate {file_path}: {error}")
        
        logger.info(f"Migration complete: {success_count} succeeded, {fail_count} failed")
        return fail_count == 0, errors
