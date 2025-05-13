"""
Checkpoint system for the Kanban CLI.

This module provides a robust checkpoint system for multi-step operations
in the Kanban CLI, allowing for recovery from failures and resumption of
interrupted operations.
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import hashlib
import uuid

from ..config.settings import get_project_root, load_config
from .exceptions import KanbanError

# Configure module logger
logger = logging.getLogger(__name__)

class CheckpointError(KanbanError):
    """Exception for checkpoint-related errors."""
    def __init__(self, message: str, checkpoint_id: str = None, error_code: str = "E400", details: Optional[Dict[str, Any]] = None):
        combined_details = {"checkpoint_id": checkpoint_id} if checkpoint_id else {}
        if details:
            combined_details.update(details)
        super().__init__(message, error_code, combined_details)
        self.checkpoint_id = checkpoint_id


class CheckpointManager:
    """
    Manages checkpoints for multi-step operations, allowing for recovery from failures.
    """
    
    def __init__(self, operation_type: str, operation_id: Optional[str] = None, config=None):
        """
        Initialize checkpoint manager.
        
        Args:
            operation_type: Type of operation (e.g., 'evidence_create', 'attachment_add')
            operation_id: Optional unique identifier for the operation
            config: Optional configuration dict
        """
        self.config = config or load_config()
        self.project_root = get_project_root()
        self.state_dir = self.project_root / self.config['paths'].get('state', 'data/state')
        
        # Ensure state directory exists
        os.makedirs(self.state_dir, exist_ok=True)
        
        self.operation_type = operation_type
        self.operation_id = operation_id or f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.checkpoint_file = self.state_dir / f"{operation_type}_{self.operation_id}.json"
        
        # Initialize checkpoint data
        self.checkpoints = {
            "operation_type": operation_type,
            "operation_id": self.operation_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed": False,
            "steps": [],
            "current_step": 0,
            "data": {}
        }
        
        # Load existing checkpoint if available
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    existing_data = json.load(f)
                    self.checkpoints.update(existing_data)
                    logger.info(f"Loaded existing checkpoint for {operation_type} {self.operation_id}")
            except Exception as e:
                logger.error(f"Failed to load checkpoint file {self.checkpoint_file}: {str(e)}")
                # Create a backup of corrupted checkpoint file
                if self.checkpoint_file.exists():
                    backup_file = self.checkpoint_file.with_suffix(f".bak.{int(time.time())}")
                    try:
                        os.rename(self.checkpoint_file, backup_file)
                        logger.info(f"Created backup of corrupted checkpoint file at {backup_file}")
                    except Exception as backup_err:
                        logger.error(f"Failed to create backup of corrupted checkpoint: {str(backup_err)}")
    
    def _save_checkpoint(self):
        """Save checkpoint data to file."""
        try:
            # Update timestamp
            self.checkpoints["updated_at"] = datetime.now().isoformat()
            
            # Use atomic write pattern for better reliability
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoints, f, indent=2)
            
            # Rename is atomic on most filesystems
            os.replace(temp_file, self.checkpoint_file)
            logger.debug(f"Saved checkpoint for {self.operation_type} {self.operation_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint file {self.checkpoint_file}: {str(e)}")
            raise CheckpointError(f"Failed to save checkpoint: {str(e)}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E401", 
                                 details={"file_path": str(self.checkpoint_file)})
    
    def add_step(self, step_name: str, description: str = ""):
        """
        Add a step to the checkpoint.
        
        Args:
            step_name: Unique identifier for the step
            description: Human-readable description of the step
        """
        # Check for duplicate step names
        step_names = [step["name"] for step in self.checkpoints["steps"]]
        if step_name in step_names:
            raise CheckpointError(f"Duplicate step name: {step_name}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E402",
                                 details={"step_name": step_name})
        
        # Add step
        step = {
            "name": step_name,
            "description": description,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "data": {}
        }
        self.checkpoints["steps"].append(step)
        self._save_checkpoint()
    
    def start_step(self, step_name: str, step_data: Optional[Dict[str, Any]] = None):
        """
        Mark a step as started.
        
        Args:
            step_name: Name of the step to start
            step_data: Optional data associated with the step
        """
        # Find step
        step_index = None
        for i, step in enumerate(self.checkpoints["steps"]):
            if step["name"] == step_name:
                step_index = i
                break
        
        if step_index is None:
            raise CheckpointError(f"Step not found: {step_name}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E403",
                                 details={"step_name": step_name})
        
        # Update step
        self.checkpoints["steps"][step_index]["status"] = "in_progress"
        self.checkpoints["steps"][step_index]["started_at"] = datetime.now().isoformat()
        if step_data:
            self.checkpoints["steps"][step_index]["data"] = step_data
        
        # Update current step
        self.checkpoints["current_step"] = step_index
        
        self._save_checkpoint()
    
    def complete_step(self, step_name: str, step_data: Optional[Dict[str, Any]] = None):
        """
        Mark a step as completed.
        
        Args:
            step_name: Name of the step to complete
            step_data: Optional data associated with the step completion
        """
        # Find step
        step_index = None
        for i, step in enumerate(self.checkpoints["steps"]):
            if step["name"] == step_name:
                step_index = i
                break
        
        if step_index is None:
            raise CheckpointError(f"Step not found: {step_name}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E403",
                                 details={"step_name": step_name})
        
        # Update step
        self.checkpoints["steps"][step_index]["status"] = "completed"
        self.checkpoints["steps"][step_index]["completed_at"] = datetime.now().isoformat()
        if step_data:
            # Merge with existing data if any
            if self.checkpoints["steps"][step_index].get("data"):
                self.checkpoints["steps"][step_index]["data"].update(step_data)
            else:
                self.checkpoints["steps"][step_index]["data"] = step_data
        
        # Move to next step if this was the current step
        if self.checkpoints["current_step"] == step_index:
            self.checkpoints["current_step"] = step_index + 1
        
        self._save_checkpoint()
    
    def fail_step(self, step_name: str, error_message: str, error_details: Optional[Dict[str, Any]] = None):
        """
        Mark a step as failed.
        
        Args:
            step_name: Name of the step that failed
            error_message: Description of the error
            error_details: Optional additional error details
        """
        # Find step
        step_index = None
        for i, step in enumerate(self.checkpoints["steps"]):
            if step["name"] == step_name:
                step_index = i
                break
        
        if step_index is None:
            raise CheckpointError(f"Step not found: {step_name}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E403",
                                 details={"step_name": step_name})
        
        # Update step
        self.checkpoints["steps"][step_index]["status"] = "failed"
        self.checkpoints["steps"][step_index]["error"] = {
            "message": error_message,
            "details": error_details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_checkpoint()
        
        logger.error(f"Step '{step_name}' failed: {error_message}")
    
    def set_data(self, key: str, value: Any):
        """
        Store global data in the checkpoint.
        
        Args:
            key: Data key
            value: Data value (must be JSON serializable)
        """
        self.checkpoints["data"][key] = value
        self._save_checkpoint()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve global data from the checkpoint.
        
        Args:
            key: Data key
            default: Default value if key doesn't exist
            
        Returns:
            The stored data value or the default
        """
        return self.checkpoints["data"].get(key, default)
    
    def get_step_data(self, step_name: str, key: str = None, default: Any = None) -> Any:
        """
        Retrieve data from a specific step.
        
        Args:
            step_name: Name of the step
            key: Optional specific data key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The step data (dict) or specific value if key provided
        """
        # Find step
        step_data = None
        for step in self.checkpoints["steps"]:
            if step["name"] == step_name:
                step_data = step.get("data", {})
                break
        
        if step_data is None:
            raise CheckpointError(f"Step not found: {step_name}", 
                                 checkpoint_id=self.operation_id, 
                                 error_code="E403",
                                 details={"step_name": step_name})
        
        if key:
            return step_data.get(key, default)
        return step_data
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """
        Get the current step data.
        
        Returns:
            Current step data or None if all steps are completed
        """
        if self.checkpoints["current_step"] >= len(self.checkpoints["steps"]):
            return None
        
        return self.checkpoints["steps"][self.checkpoints["current_step"]]
    
    def is_step_completed(self, step_name: str) -> bool:
        """
        Check if a step is completed.
        
        Args:
            step_name: Name of the step to check
            
        Returns:
            True if the step is completed, False otherwise
        """
        for step in self.checkpoints["steps"]:
            if step["name"] == step_name:
                return step["status"] == "completed"
        
        raise CheckpointError(f"Step not found: {step_name}", 
                             checkpoint_id=self.operation_id, 
                             error_code="E403",
                             details={"step_name": step_name})
    
    def is_completed(self) -> bool:
        """
        Check if all steps are completed.
        
        Returns:
            True if all steps are completed, False otherwise
        """
        if not self.checkpoints["steps"]:
            return False
        
        return all(step["status"] == "completed" for step in self.checkpoints["steps"])
    
    def mark_completed(self):
        """Mark the entire operation as completed."""
        self.checkpoints["completed"] = True
        self._save_checkpoint()
    
    def cleanup(self):
        """Delete the checkpoint file if operation is completed."""
        if self.checkpoints["completed"]:
            try:
                if self.checkpoint_file.exists():
                    os.remove(self.checkpoint_file)
                    logger.info(f"Removed completed checkpoint file for {self.operation_type} {self.operation_id}")
            except Exception as e:
                logger.error(f"Failed to remove checkpoint file {self.checkpoint_file}: {str(e)}")
    
    @staticmethod
    def list_operations(operation_type: Optional[str] = None, incomplete_only: bool = False, config=None) -> List[Dict[str, Any]]:
        """
        List existing checkpoint operations.
        
        Args:
            operation_type: Optional filter by operation type
            incomplete_only: If True, only return incomplete operations
            config: Optional configuration dict
            
        Returns:
            List of operation summaries
        """
        config = config or load_config()
        project_root = get_project_root()
        state_dir = project_root / config['paths'].get('state', 'data/state')
        
        if not state_dir.exists():
            return []
        
        operations = []
        pattern = f"{operation_type}_*.json" if operation_type else "*.json"
        
        for checkpoint_file in state_dir.glob(pattern):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint_data = json.load(f)
                    
                if incomplete_only and checkpoint_data.get("completed", False):
                    continue
                
                # Create a summary
                current_step_index = checkpoint_data.get("current_step", 0)
                steps = checkpoint_data.get("steps", [])
                current_step = steps[current_step_index] if current_step_index < len(steps) else None
                
                summary = {
                    "operation_type": checkpoint_data.get("operation_type"),
                    "operation_id": checkpoint_data.get("operation_id"),
                    "created_at": checkpoint_data.get("created_at"),
                    "updated_at": checkpoint_data.get("updated_at"),
                    "completed": checkpoint_data.get("completed", False),
                    "total_steps": len(steps),
                    "completed_steps": sum(1 for step in steps if step.get("status") == "completed"),
                    "current_step": current_step.get("name") if current_step else None,
                    "current_step_status": current_step.get("status") if current_step else None,
                    "checkpoint_file": str(checkpoint_file)
                }
                
                operations.append(summary)
            except Exception as e:
                logger.error(f"Failed to load checkpoint file {checkpoint_file}: {str(e)}")
                
        # Sort by updated_at (most recent first)
        operations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return operations
    
    @staticmethod
    def resume_operation(operation_id: str, config=None) -> 'CheckpointManager':
        """
        Resume an existing operation.
        
        Args:
            operation_id: ID of the operation to resume
            config: Optional configuration dict
            
        Returns:
            CheckpointManager instance for the resumed operation
            
        Raises:
            CheckpointError: If operation cannot be resumed
        """
        config = config or load_config()
        project_root = get_project_root()
        state_dir = project_root / config['paths'].get('state', 'data/state')
        
        # Find all checkpoint files
        matching_files = list(state_dir.glob(f"*_{operation_id}.json"))
        
        if not matching_files:
            raise CheckpointError(f"No checkpoint found for operation ID: {operation_id}", 
                                 checkpoint_id=operation_id, 
                                 error_code="E404")
        
        if len(matching_files) > 1:
            raise CheckpointError(f"Multiple checkpoints found for operation ID: {operation_id}", 
                                 checkpoint_id=operation_id, 
                                 error_code="E405",
                                 details={"found_files": [str(f) for f in matching_files]})
        
        # Get operation type from filename
        checkpoint_file = matching_files[0]
        operation_type = checkpoint_file.stem.split('_')[0]
        
        # Create checkpoint manager with existing ID
        manager = CheckpointManager(operation_type, operation_id, config)
        logger.info(f"Resumed operation {operation_type} {operation_id}")
        
        return manager


def with_checkpoint(operation_type: str, operation_id: Optional[str] = None):
    """
    Decorator for functions that should use checkpoints.
    
    Args:
        operation_type: Type of operation
        operation_id: Optional unique identifier for the operation
        
    Usage:
        @with_checkpoint("evidence_create")
        def create_evidence(data):
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create checkpoint manager
            checkpoint_id = kwargs.pop('checkpoint_id', operation_id)
            checkpoint = CheckpointManager(operation_type, checkpoint_id)
            
            # Add checkpoint manager to kwargs
            kwargs['checkpoint'] = checkpoint
            
            try:
                result = func(*args, **kwargs)
                checkpoint.mark_completed()
                checkpoint.cleanup()
                return result
            except Exception as e:
                # If function has error handling that handles checkpoint steps,
                # it should mark them as failed itself
                logger.error(f"Operation {operation_type} failed: {str(e)}")
                raise
                
        return wrapper
    return decorator