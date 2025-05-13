"""
Data storage functionality for the Kanban CLI.

This module provides a data access layer for storing and retrieving
Kanban entities like tasks, epics, and boards.
"""
import os
import json
import yaml
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
from pathlib import Path

from ..config.settings import get_project_root, load_config
from ..models import schemas
from ..models import validation

class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass

class FileStorage:
    """Base class for file-based storage."""
    
    def __init__(self, config=None):
        """
        Initialize file storage.
        
        Args:
            config: Optional configuration dict, loaded from config file if None
        """
        self.config = config or load_config()
        self.project_root = get_project_root()
        self.data_dir = self.project_root / self.config['paths']['data']
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _ensure_dir(self, directory):
        """Ensure a directory exists."""
        os.makedirs(directory, exist_ok=True)
    
    def _write_yaml(self, file_path: Path, data: Any) -> None:
        """Write data to a YAML file."""
        try:
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        except Exception as e:
            raise StorageError(f"Failed to write YAML file {file_path}: {str(e)}")
    
    def _read_yaml(self, file_path: Path) -> Any:
        """Read data from a YAML file."""
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise StorageError(f"Failed to read YAML file {file_path}: {str(e)}")
    
    def _write_json(self, file_path: Path, data: Any) -> None:
        """Write data to a JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            raise StorageError(f"Failed to write JSON file {file_path}: {str(e)}")
    
    def _read_json(self, file_path: Path) -> Any:
        """Read data from a JSON file."""
        try:
            if not file_path.exists():
                return None
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise StorageError(f"Failed to read JSON file {file_path}: {str(e)}")

class TaskStorage(FileStorage):
    """Storage for task entities."""
    
    def __init__(self, config=None):
        """Initialize task storage."""
        super().__init__(config)
        self.tasks_dir = self.data_dir / 'tasks'
        self._ensure_dir(self.tasks_dir)
        self.index_file = self.tasks_dir / 'index.json'
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure task index file exists."""
        if not self.index_file.exists():
            self._write_json(self.index_file, {'tasks': []})
    
    def create(self, task_data: Dict) -> schemas.TaskSchema:
        """
        Create a new task.
        
        Args:
            task_data: Dictionary with task data
        
        Returns:
            The created TaskSchema object
        
        Raises:
            StorageError: If task validation fails or storage operation fails
        """
        # Validate task data
        is_valid, errors = validation.validate_task(task_data)
        if not is_valid:
            raise StorageError(f"Invalid task data: {', '.join(errors)}")
        
        # Create task object
        task = schemas.TaskSchema(**task_data)
        
        # Save task to file
        task_file = self.tasks_dir / f"{task.id}.json"
        self._write_json(task_file, task.to_dict())
        
        # Update index
        index_data = self._read_json(self.index_file)
        if task.id not in index_data['tasks']:
            index_data['tasks'].append(task.id)
            self._write_json(self.index_file, index_data)
        
        return task
    
    def get(self, task_id: str) -> Optional[schemas.TaskSchema]:
        """
        Get a task by ID.
        
        Args:
            task_id: The task ID to retrieve
        
        Returns:
            TaskSchema object if found, None otherwise
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        task_data = self._read_json(task_file)
        
        if not task_data:
            return None
        
        return schemas.TaskSchema.from_dict(task_data)
    
    def update(self, task_id: str, task_data: Dict) -> Optional[schemas.TaskSchema]:
        """
        Update an existing task.
        
        Args:
            task_id: The task ID to update
            task_data: Dictionary with updated task data
        
        Returns:
            Updated TaskSchema object if found, None otherwise
        
        Raises:
            StorageError: If task validation fails or storage operation fails
        """
        # Check if task exists
        existing_task = self.get(task_id)
        if not existing_task:
            return None
        
        # Update task data with existing values for fields not provided
        existing_dict = existing_task.to_dict()
        for key, value in existing_dict.items():
            if key not in task_data:
                task_data[key] = value
        
        # Set ID to ensure it doesn't change
        task_data['id'] = task_id
        
        # Update timestamp
        task_data['updated_at'] = datetime.now()
        
        # Validate task data
        is_valid, errors = validation.validate_task(task_data)
        if not is_valid:
            raise StorageError(f"Invalid task data: {', '.join(errors)}")
        
        # Create updated task object
        task = schemas.TaskSchema.from_dict(task_data)
        
        # Save task to file
        task_file = self.tasks_dir / f"{task.id}.json"
        self._write_json(task_file, task.to_dict())
        
        return task
    
    def delete(self, task_id: str) -> bool:
        """
        Delete a task by ID.
        
        Args:
            task_id: The task ID to delete
        
        Returns:
            True if the task was deleted, False if not found
        """
        task_file = self.tasks_dir / f"{task_id}.json"
        
        if not task_file.exists():
            return False
        
        # Delete task file
        task_file.unlink()
        
        # Update index
        index_data = self._read_json(self.index_file)
        if task_id in index_data['tasks']:
            index_data['tasks'].remove(task_id)
            self._write_json(self.index_file, index_data)
        
        return True
    
    def list(self, filters: Optional[Dict] = None) -> List[schemas.TaskSchema]:
        """
        List tasks, optionally filtered.
        
        Args:
            filters: Optional dictionary of filter criteria:
                - status: Task status
                - epic_id: ID of parent epic
                - title: Substring match on title
                - description: Substring match on description
                - assignee: Assigned person
                - tags: List of tags (all must match)
        
        Returns:
            List of TaskSchema objects
        """
        # Get all task IDs from index
        index_data = self._read_json(self.index_file)
        task_ids = index_data.get('tasks', [])
        
        # Load all tasks
        tasks = []
        for task_id in task_ids:
            task = self.get(task_id)
            if task:
                tasks.append(task)
        
        # Apply filters if provided
        if filters:
            filtered_tasks = []
            for task in tasks:
                match = True
                
                # Filter by status
                if 'status' in filters and filters['status']:
                    if task.status.value != filters['status']:
                        match = False
                
                # Filter by epic_id
                if 'epic_id' in filters and filters['epic_id']:
                    if task.epic_id != filters['epic_id']:
                        match = False
                
                # Filter by title substring
                if 'title' in filters and filters['title']:
                    if filters['title'].lower() not in task.title.lower():
                        match = False
                
                # Filter by description substring
                if 'description' in filters and filters['description']:
                    if filters['description'].lower() not in task.description.lower():
                        match = False
                
                # Filter by assignee
                if 'assignee' in filters and filters['assignee']:
                    if task.assignee != filters['assignee']:
                        match = False
                
                # Filter by tags (all tags must match)
                if 'tags' in filters and filters['tags']:
                    for tag in filters['tags']:
                        if tag not in task.tags:
                            match = False
                            break
                
                # Filter by related_evidence_ids
                if 'related_evidence_id' in filters and filters['related_evidence_id']:
                    if filters['related_evidence_id'] not in task.related_evidence_ids:
                        match = False
                
                if match:
                    filtered_tasks.append(task)
            
            return filtered_tasks
        
        return tasks

class EpicStorage(FileStorage):
    """Storage for epic entities."""
    
    def __init__(self, config=None):
        """Initialize epic storage."""
        super().__init__(config)
        self.epics_dir = self.data_dir / 'epics'
        self._ensure_dir(self.epics_dir)
        self.index_file = self.epics_dir / 'index.json'
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure epic index file exists."""
        if not self.index_file.exists():
            self._write_json(self.index_file, {'epics': []})
    
    def create(self, epic_data: Dict) -> schemas.EpicSchema:
        """
        Create a new epic.
        
        Args:
            epic_data: Dictionary with epic data
        
        Returns:
            The created EpicSchema object
        
        Raises:
            StorageError: If epic validation fails or storage operation fails
        """
        # Validate epic data
        is_valid, errors = validation.validate_epic(epic_data)
        if not is_valid:
            raise StorageError(f"Invalid epic data: {', '.join(errors)}")
        
        # Create epic object
        epic = schemas.EpicSchema(**epic_data)
        
        # Save epic to file
        epic_file = self.epics_dir / f"{epic.id}.json"
        self._write_json(epic_file, epic.to_dict())
        
        # Update index
        index_data = self._read_json(self.index_file)
        if epic.id not in index_data['epics']:
            index_data['epics'].append(epic.id)
            self._write_json(self.index_file, index_data)
        
        return epic
    
    def get(self, epic_id: str) -> Optional[schemas.EpicSchema]:
        """
        Get an epic by ID.
        
        Args:
            epic_id: The epic ID to retrieve
        
        Returns:
            EpicSchema object if found, None otherwise
        """
        epic_file = self.epics_dir / f"{epic_id}.json"
        epic_data = self._read_json(epic_file)
        
        if not epic_data:
            return None
        
        return schemas.EpicSchema.from_dict(epic_data)
    
    def update(self, epic_id: str, epic_data: Dict) -> Optional[schemas.EpicSchema]:
        """
        Update an existing epic.
        
        Args:
            epic_id: The epic ID to update
            epic_data: Dictionary with updated epic data
        
        Returns:
            Updated EpicSchema object if found, None otherwise
        
        Raises:
            StorageError: If epic validation fails or storage operation fails
        """
        # Check if epic exists
        existing_epic = self.get(epic_id)
        if not existing_epic:
            return None
        
        # Update epic data with existing values for fields not provided
        existing_dict = existing_epic.to_dict()
        for key, value in existing_dict.items():
            if key not in epic_data:
                epic_data[key] = value
        
        # Set ID to ensure it doesn't change
        epic_data['id'] = epic_id
        
        # Update timestamp
        epic_data['updated_at'] = datetime.now()
        
        # Validate epic data
        is_valid, errors = validation.validate_epic(epic_data)
        if not is_valid:
            raise StorageError(f"Invalid epic data: {', '.join(errors)}")
        
        # Create updated epic object
        epic = schemas.EpicSchema.from_dict(epic_data)
        
        # Save epic to file
        epic_file = self.epics_dir / f"{epic.id}.json"
        self._write_json(epic_file, epic.to_dict())
        
        return epic
    
    def delete(self, epic_id: str) -> bool:
        """
        Delete an epic by ID.
        
        Args:
            epic_id: The epic ID to delete
        
        Returns:
            True if the epic was deleted, False if not found
        """
        epic_file = self.epics_dir / f"{epic_id}.json"
        
        if not epic_file.exists():
            return False
        
        # Delete epic file
        epic_file.unlink()
        
        # Update index
        index_data = self._read_json(self.index_file)
        if epic_id in index_data['epics']:
            index_data['epics'].remove(epic_id)
            self._write_json(self.index_file, index_data)
        
        return True
    
    def list(self, filters: Optional[Dict] = None) -> List[schemas.EpicSchema]:
        """
        List epics, optionally filtered.
        
        Args:
            filters: Optional dictionary of filter criteria:
                - status: Epic status
                - owner: Owner person
                - title: Substring match on title
                - description: Substring match on description
        
        Returns:
            List of EpicSchema objects
        """
        # Get all epic IDs from index
        index_data = self._read_json(self.index_file)
        epic_ids = index_data.get('epics', [])
        
        # Load all epics
        epics = []
        for epic_id in epic_ids:
            epic = self.get(epic_id)
            if epic:
                epics.append(epic)
        
        # Apply filters if provided
        if filters:
            filtered_epics = []
            for epic in epics:
                match = True
                
                # Filter by status
                if 'status' in filters and filters['status']:
                    if epic.status != filters['status']:
                        match = False
                
                # Filter by owner
                if 'owner' in filters and filters['owner']:
                    if epic.owner != filters['owner']:
                        match = False
                
                # Filter by title substring
                if 'title' in filters and filters['title']:
                    if filters['title'].lower() not in epic.title.lower():
                        match = False
                
                # Filter by description substring
                if 'description' in filters and filters['description']:
                    if filters['description'].lower() not in epic.description.lower():
                        match = False
                
                # Filter by related_evidence_ids
                if 'related_evidence_id' in filters and filters['related_evidence_id']:
                    if filters['related_evidence_id'] not in epic.related_evidence_ids:
                        match = False
                
                if match:
                    filtered_epics.append(epic)
            
            return filtered_epics
        
        return epics

class BoardStorage(FileStorage):
    """Storage for board entities."""
    
    def __init__(self, config=None):
        """Initialize board storage."""
        super().__init__(config)
        self.boards_dir = self.data_dir / 'boards'
        self._ensure_dir(self.boards_dir)
        self.index_file = self.boards_dir / 'index.json'
        self._ensure_index()
    
    def _ensure_index(self):
        """Ensure board index file exists."""
        if not self.index_file.exists():
            self._write_json(self.index_file, {'boards': []})
    
    def create(self, board_data: Dict) -> schemas.BoardSchema:
        """
        Create a new board.
        
        Args:
            board_data: Dictionary with board data
        
        Returns:
            The created BoardSchema object
        
        Raises:
            StorageError: If board validation fails or storage operation fails
        """
        # Validate board data
        is_valid, errors = validation.validate_board(board_data)
        if not is_valid:
            raise StorageError(f"Invalid board data: {', '.join(errors)}")
        
        # Create board object
        board = schemas.BoardSchema(**board_data)
        
        # Save board to file
        board_file = self.boards_dir / f"{board.id}.json"
        self._write_json(board_file, board.to_dict())
        
        # Update index
        index_data = self._read_json(self.index_file)
        if board.id not in index_data['boards']:
            index_data['boards'].append(board.id)
            self._write_json(self.index_file, index_data)
        
        return board
    
    def get(self, board_id: str) -> Optional[schemas.BoardSchema]:
        """
        Get a board by ID.
        
        Args:
            board_id: The board ID to retrieve
        
        Returns:
            BoardSchema object if found, None otherwise
        """
        board_file = self.boards_dir / f"{board_id}.json"
        board_data = self._read_json(board_file)
        
        if not board_data:
            return None
        
        return schemas.BoardSchema.from_dict(board_data)
    
    def update(self, board_id: str, board_data: Dict) -> Optional[schemas.BoardSchema]:
        """
        Update an existing board.
        
        Args:
            board_id: The board ID to update
            board_data: Dictionary with updated board data
        
        Returns:
            Updated BoardSchema object if found, None otherwise
        
        Raises:
            StorageError: If board validation fails or storage operation fails
        """
        # Check if board exists
        existing_board = self.get(board_id)
        if not existing_board:
            return None
        
        # Update board data with existing values for fields not provided
        existing_dict = existing_board.to_dict()
        for key, value in existing_dict.items():
            if key not in board_data:
                board_data[key] = value
        
        # Set ID to ensure it doesn't change
        board_data['id'] = board_id
        
        # Update timestamp
        board_data['updated_at'] = datetime.now()
        
        # Validate board data
        is_valid, errors = validation.validate_board(board_data)
        if not is_valid:
            raise StorageError(f"Invalid board data: {', '.join(errors)}")
        
        # Create updated board object
        board = schemas.BoardSchema.from_dict(board_data)
        
        # Save board to file
        board_file = self.boards_dir / f"{board.id}.json"
        self._write_json(board_file, board.to_dict())
        
        return board
    
    def delete(self, board_id: str) -> bool:
        """
        Delete a board by ID.
        
        Args:
            board_id: The board ID to delete
        
        Returns:
            True if the board was deleted, False if not found
        """
        board_file = self.boards_dir / f"{board_id}.json"
        
        if not board_file.exists():
            return False
        
        # Delete board file
        board_file.unlink()
        
        # Update index
        index_data = self._read_json(self.index_file)
        if board_id in index_data['boards']:
            index_data['boards'].remove(board_id)
            self._write_json(self.index_file, index_data)
        
        return True
    
    def list(self) -> List[schemas.BoardSchema]:
        """
        List all boards.
        
        Returns:
            List of BoardSchema objects
        """
        # Get all board IDs from index
        index_data = self._read_json(self.index_file)
        board_ids = index_data.get('boards', [])
        
        # Load all boards
        boards = []
        for board_id in board_ids:
            board = self.get(board_id)
            if board:
                boards.append(board)
        
        return boards
