"""
Retry Mechanism for Failed Batch Operations in Evidence CLI.

This module provides functionality to retry failed operations
in batch processing of evidence commands.
"""
import os
import json
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any, Callable, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.prompt import Confirm
from rich.table import Table

from ..utils.exceptions import StorageError, ValidationError, EntityNotFoundError
from ..config.settings import get_project_root, load_config
from ..ui.display import console, print_success, print_error, print_warning, print_info

# Configure module logger
logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Strategies for retrying failed operations."""
    IMMEDIATE = "immediate"  # Retry immediately
    INCREMENTAL = "incremental"  # Retry with increasing delays
    EXPONENTIAL = "exponential"  # Retry with exponential backoff
    CUSTOM = "custom"  # Custom retry schedule


class OperationStatus(Enum):
    """Status of batch operations."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class BatchOperation:
    """Represents a single operation within a batch."""
    
    def __init__(self, 
                operation_type: str,
                params: Dict[str, Any],
                item_id: Optional[str] = None,
                description: Optional[str] = None):
        """
        Initialize a batch operation.
        
        Args:
            operation_type: Type of operation (e.g., 'create', 'update', 'delete')
            params: Parameters for the operation
            item_id: Optional ID of the item being operated on
            description: Optional human-readable description
        """
        self.operation_type = operation_type
        self.params = params
        self.item_id = item_id
        self.description = description or f"{operation_type.capitalize()} operation"
        
        # Status tracking
        self.status = OperationStatus.PENDING
        self.error = None
        self.result = None
        self.attempt_count = 0
        self.last_attempt = None
        self.next_retry = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_type": self.operation_type,
            "params": self.params,
            "item_id": self.item_id,
            "description": self.description,
            "status": self.status.value,
            "error": self.error,
            "result": self.result,
            "attempt_count": self.attempt_count,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "next_retry": self.next_retry.isoformat() if self.next_retry else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchOperation':
        """Create a BatchOperation instance from a dictionary."""
        operation = cls(
            operation_type=data["operation_type"],
            params=data["params"],
            item_id=data.get("item_id"),
            description=data.get("description")
        )
        
        operation.status = OperationStatus(data.get("status", "pending"))
        operation.error = data.get("error")
        operation.result = data.get("result")
        operation.attempt_count = data.get("attempt_count", 0)
        
        if data.get("last_attempt"):
            operation.last_attempt = datetime.fromisoformat(data["last_attempt"])
            
        if data.get("next_retry"):
            operation.next_retry = datetime.fromisoformat(data["next_retry"])
            
        return operation


class RetryManager:
    """
    Manages retries for failed batch operations.
    
    This class provides functionality to track, persist, and retry
    failed operations with configurable retry strategies.
    """
    
    def __init__(self, 
                batch_id: str,
                storage_dir: Optional[Path] = None,
                max_retries: int = 3,
                retry_strategy: RetryStrategy = RetryStrategy.INCREMENTAL,
                retry_delays: Optional[List[int]] = None):
        """
        Initialize the retry manager.
        
        Args:
            batch_id: ID of the batch operation
            storage_dir: Optional directory for retry data storage
            max_retries: Maximum number of retry attempts
            retry_strategy: Strategy for calculating retry delays
            retry_delays: Optional list of retry delays (in seconds)
        """
        self.batch_id = batch_id
        self.max_retries = max_retries
        self.retry_strategy = retry_strategy
        
        # Set up retry delays based on strategy
        if retry_delays:
            self.retry_delays = retry_delays
        else:
            if retry_strategy == RetryStrategy.IMMEDIATE:
                self.retry_delays = [0] * max_retries
            elif retry_strategy == RetryStrategy.INCREMENTAL:
                self.retry_delays = [5 * (i + 1) for i in range(max_retries)]
            elif retry_strategy == RetryStrategy.EXPONENTIAL:
                self.retry_delays = [2 ** i for i in range(max_retries)]
            else:
                self.retry_delays = [5, 15, 30]  # Default delays
        
        # Set up storage directory
        self.config = load_config()
        self.project_root = get_project_root()
        
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.storage_dir = data_dir / 'retry_data'
            
        # Ensure directory exists
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Batch storage file
        self.batch_file = self.storage_dir / f"{batch_id}.json"
        
        # Initialize operations list
        self.operations: List[BatchOperation] = []
        
        # Load existing batch if available
        self._load_batch()
        
        logger.info(f"Initialized retry manager for batch {batch_id} with {len(self.operations)} operations")
    
    def _load_batch(self) -> None:
        """Load batch operations from file."""
        if not self.batch_file.exists():
            return
            
        try:
            with open(self.batch_file, 'r') as f:
                data = json.load(f)
                
            batch_id = data.get("batch_id")
            if batch_id != self.batch_id:
                logger.warning(f"Batch ID mismatch: {batch_id} != {self.batch_id}")
                
            self.operations = [
                BatchOperation.from_dict(op_data)
                for op_data in data.get("operations", [])
            ]
            
            logger.info(f"Loaded {len(self.operations)} operations from {self.batch_file}")
        except Exception as e:
            logger.error(f"Failed to load batch operations: {str(e)}")
    
    def _save_batch(self) -> None:
        """Save batch operations to file."""
        try:
            data = {
                "batch_id": self.batch_id,
                "timestamp": datetime.now().isoformat(),
                "operations": [op.to_dict() for op in self.operations]
            }
            
            with open(self.batch_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved {len(self.operations)} operations to {self.batch_file}")
        except Exception as e:
            logger.error(f"Failed to save batch operations: {str(e)}")
    
    def add_operation(self, operation: BatchOperation) -> None:
        """
        Add an operation to the batch.
        
        Args:
            operation: Batch operation to add
        """
        self.operations.append(operation)
        self._save_batch()
        
        logger.debug(f"Added operation: {operation.operation_type} ({operation.description})")
    
    def update_operation(self, index: int, status: OperationStatus, 
                       error: Optional[str] = None, 
                       result: Optional[Any] = None) -> None:
        """
        Update an operation's status.
        
        Args:
            index: Index of the operation
            status: New status
            error: Optional error message
            result: Optional operation result
        """
        if index < 0 or index >= len(self.operations):
            logger.error(f"Invalid operation index: {index}")
            return
            
        operation = self.operations[index]
        operation.status = status
        
        if error is not None:
            operation.error = error
            
        if result is not None:
            operation.result = result
            
        operation.last_attempt = datetime.now()
        operation.attempt_count += 1
        
        # Calculate next retry time if failed
        if status == OperationStatus.FAILURE and operation.attempt_count < self.max_retries:
            retry_delay = self.retry_delays[min(operation.attempt_count - 1, len(self.retry_delays) - 1)]
            operation.next_retry = datetime.now().timestamp() + retry_delay
            operation.status = OperationStatus.RETRYING
            
            logger.info(f"Scheduled retry for operation {index} in {retry_delay} seconds")
        
        self._save_batch()
        
        logger.debug(f"Updated operation {index} status to {status.value}")
    
    def get_operations(self, 
                     status: Optional[Union[OperationStatus, List[OperationStatus]]] = None) -> List[Tuple[int, BatchOperation]]:
        """
        Get operations, optionally filtered by status.
        
        Args:
            status: Optional status or list of statuses to filter by
            
        Returns:
            List of (index, operation) tuples
        """
        if status is None:
            return [(i, op) for i, op in enumerate(self.operations)]
            
        if isinstance(status, OperationStatus):
            statuses = [status]
        else:
            statuses = status
            
        return [
            (i, op) for i, op in enumerate(self.operations)
            if op.status in statuses
        ]
    
    def get_operation(self, index: int) -> Optional[BatchOperation]:
        """
        Get an operation by index.
        
        Args:
            index: Operation index
            
        Returns:
            BatchOperation or None if not found
        """
        if index < 0 or index >= len(self.operations):
            return None
            
        return self.operations[index]
    
    def get_pending_retries(self) -> List[Tuple[int, BatchOperation]]:
        """
        Get operations that are due for retry.
        
        Returns:
            List of (index, operation) tuples
        """
        now = datetime.now().timestamp()
        return [
            (i, op) for i, op in enumerate(self.operations)
            if op.status == OperationStatus.RETRYING and op.next_retry and op.next_retry <= now
        ]
    
    def get_batch_status(self) -> Dict[str, int]:
        """
        Get batch status summary.
        
        Returns:
            Dictionary with status counts
        """
        status_counts = {status.value: 0 for status in OperationStatus}
        
        for op in self.operations:
            status_counts[op.status.value] += 1
            
        status_counts["total"] = len(self.operations)
        
        return status_counts
    
    def execute_operation(self, 
                         index: int, 
                         execute_func: Callable[[BatchOperation], Tuple[bool, Any, Optional[str]]]) -> bool:
        """
        Execute an operation.
        
        Args:
            index: Operation index
            execute_func: Function to execute the operation
                          Takes a BatchOperation and returns (success, result, error)
            
        Returns:
            True if operation was successful, False otherwise
        """
        operation = self.get_operation(index)
        if not operation:
            logger.error(f"Invalid operation index: {index}")
            return False
            
        try:
            logger.info(f"Executing operation {index}: {operation.description}")
            
            # Execute the operation
            success, result, error = execute_func(operation)
            
            # Update operation status
            if success:
                self.update_operation(index, OperationStatus.SUCCESS, result=result)
                return True
            else:
                self.update_operation(index, OperationStatus.FAILURE, error=error)
                return False
                
        except Exception as e:
            logger.exception(f"Error executing operation {index}")
            self.update_operation(index, OperationStatus.FAILURE, error=str(e))
            return False
    
    def retry_failed_operations(self, 
                              execute_func: Callable[[BatchOperation], Tuple[bool, Any, Optional[str]]],
                              interactive: bool = True,
                              progress: Optional[Progress] = None) -> Dict[str, int]:
        """
        Retry failed operations.
        
        Args:
            execute_func: Function to execute operations
            interactive: Whether to prompt for confirmation
            progress: Optional Rich progress object
            
        Returns:
            Dictionary with retry results
        """
        # Get operations due for retry
        pending_retries = self.get_pending_retries()
        
        if not pending_retries:
            logger.info("No operations due for retry")
            return {"total": 0, "retried": 0, "succeeded": 0, "failed": 0}
            
        # Show retry information
        if interactive:
            table = Table(title=f"Pending Retries ({len(pending_retries)})")
            table.add_column("Index", style="dim")
            table.add_column("Type", style="bold")
            table.add_column("Description")
            table.add_column("Attempts", style="cyan")
            table.add_column("Last Error", style="red")
            
            for i, op in pending_retries:
                table.add_row(
                    str(i),
                    op.operation_type,
                    op.description,
                    str(op.attempt_count),
                    op.error or ""
                )
                
            console.print(table)
            
            if not Confirm.ask("Retry these operations?"):
                logger.info("Retry cancelled by user")
                return {"total": len(pending_retries), "retried": 0, "succeeded": 0, "failed": 0}
        
        # Track results
        results = {
            "total": len(pending_retries),
            "retried": 0,
            "succeeded": 0,
            "failed": 0
        }
        
        # Create progress bar if not provided
        local_progress = False
        if progress is None and interactive:
            progress = Progress()
            local_progress = True
            
        # Start progress tracking
        task_id = None
        if progress:
            task_id = progress.add_task("Retrying operations...", total=len(pending_retries))
            
        # Start progress context if needed
        progress_context = progress if local_progress else None
        progress_cm = progress_context or nullcontext()
        
        with progress_cm:
            # Retry each operation
            for i, op in pending_retries:
                logger.info(f"Retrying operation {i}: {op.description} (attempt {op.attempt_count + 1})")
                
                results["retried"] += 1
                
                # Execute the operation
                success = self.execute_operation(i, execute_func)
                
                if success:
                    results["succeeded"] += 1
                    logger.info(f"Retry succeeded for operation {i}")
                    
                    if interactive:
                        print_success(f"Retry succeeded: {op.description}")
                else:
                    results["failed"] += 1
                    logger.warning(f"Retry failed for operation {i}: {op.error}")
                    
                    if interactive:
                        print_error(f"Retry failed: {op.description}")
                        print_info(f"Error: {op.error}")
                
                # Update progress
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)
        
        # Show summary
        if interactive:
            print_info(f"Retry summary: {results['succeeded']} succeeded, {results['failed']} failed")
            
        logger.info(f"Retry results: {results}")
        return results
    
    def retry_all_failed(self, 
                        execute_func: Callable[[BatchOperation], Tuple[bool, Any, Optional[str]]],
                        interactive: bool = True) -> Dict[str, int]:
        """
        Retry all failed operations, regardless of timing.
        
        Args:
            execute_func: Function to execute operations
            interactive: Whether to prompt for confirmation
            
        Returns:
            Dictionary with retry results
        """
        # Get all failed operations
        failed_ops = self.get_operations(OperationStatus.FAILURE)
        
        if not failed_ops:
            logger.info("No failed operations to retry")
            return {"total": 0, "retried": 0, "succeeded": 0, "failed": 0}
            
        # Reset retry timing for all failed operations
        for i, op in failed_ops:
            op.next_retry = datetime.now().timestamp()
            op.status = OperationStatus.RETRYING
            
        self._save_batch()
        
        # Retry operations
        return self.retry_failed_operations(execute_func, interactive)
    
    def clear_batch(self) -> None:
        """Clear the batch operations."""
        self.operations = []
        
        # Remove the batch file if it exists
        if self.batch_file.exists():
            os.remove(self.batch_file)
            
        logger.info(f"Cleared batch {self.batch_id}")
    
    def show_batch_status(self, show_all: bool = False) -> None:
        """
        Display batch status information.
        
        Args:
            show_all: Whether to show all operations or just summary
        """
        # Get batch status
        status = self.get_batch_status()
        
        # Create summary panel
        summary = (
            f"Batch ID: {self.batch_id}\n"
            f"Total Operations: {status['total']}\n"
            f"Pending: {status['pending']}\n"
            f"Succeeded: {status['success']}\n"
            f"Failed: {status['failure']}\n"
            f"Retrying: {status['retrying']}\n"
            f"Skipped: {status['skipped']}"
        )
        
        console.print(Panel(summary, title="Batch Status", border_style="blue"))
        
        # Show operations if requested
        if show_all and self.operations:
            table = Table(title="Operations")
            table.add_column("Index", style="dim")
            table.add_column("Type", style="bold")
            table.add_column("Description")
            table.add_column("Status", style="cyan")
            table.add_column("Attempts", style="cyan")
            table.add_column("Error", style="red")
            
            for i, op in enumerate(self.operations):
                # Determine status style
                status_style = {
                    OperationStatus.PENDING: "yellow",
                    OperationStatus.SUCCESS: "green",
                    OperationStatus.FAILURE: "red",
                    OperationStatus.RETRYING: "blue",
                    OperationStatus.SKIPPED: "dim"
                }.get(op.status, "white")
                
                table.add_row(
                    str(i),
                    op.operation_type,
                    op.description,
                    f"[{status_style}]{op.status.value}[/{status_style}]",
                    str(op.attempt_count),
                    op.error or ""
                )
                
            console.print(table)


# Helper context manager for cases when no progress bar is used
class nullcontext:
    """Context manager that does nothing."""
    
    def __enter__(self):
        return self
        
    def __exit__(self, *excinfo):
        pass


# Helper function to create a retry manager with default settings
def get_retry_manager(batch_id: str) -> RetryManager:
    """Get a retry manager with default settings."""
    return RetryManager(batch_id)
