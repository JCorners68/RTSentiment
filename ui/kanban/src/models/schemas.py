"""
Data schemas for the Kanban CLI.

This module defines the core data schemas used in the Kanban CLI application,
including Task, Epic, Board, and Evidence schemas.
"""
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum, auto
from uuid import uuid4

def generate_id(prefix=""):
    """Generate a unique ID with an optional prefix"""
    return f"{prefix}{uuid4()}"

class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    DONE = "Done"

class TaskPriority(str, Enum):
    """Enumeration of possible task priorities."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class TaskSchema:
    """Schema definition for a Task."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        status: Union[TaskStatus, str] = TaskStatus.BACKLOG,
        priority: Union[TaskPriority, str] = TaskPriority.MEDIUM,
        epic_id: str = None,
        assignee: str = None,
        complexity: int = 1,
        tags: List[str] = None,
        due_date: datetime = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        related_evidence_ids: List[str] = None
    ):
        """
        Initialize a task schema.
        
        Args:
            title: Task title
            description: Task description
            status: Current status
            priority: Priority level
            epic_id: ID of parent epic
            assignee: Person assigned to the task
            complexity: Task complexity (1-5)
            tags: List of tags
            due_date: Due date
            id: Unique identifier (auto-generated if not provided)
            created_at: Creation timestamp (defaults to now)
            updated_at: Last update timestamp (defaults to now)
            related_evidence_ids: IDs of evidence related to this task
        """
        self.id = id if id else generate_id("TSK-")
        self.title = title
        self.description = description
        
        # Handle status as string or enum
        if isinstance(status, str):
            try:
                self.status = TaskStatus(status)
            except ValueError:
                self.status = TaskStatus.BACKLOG
        else:
            self.status = status
            
        # Handle priority as string or enum
        if isinstance(priority, str):
            try:
                self.priority = TaskPriority(priority)
            except ValueError:
                self.priority = TaskPriority.MEDIUM
        else:
            self.priority = priority
            
        self.epic_id = epic_id
        self.assignee = assignee
        self.complexity = min(max(1, complexity), 5)  # Ensure 1-5 range
        self.tags = tags or []
        self.due_date = due_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.related_evidence_ids = related_evidence_ids or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "epic_id": self.epic_id,
            "assignee": self.assignee,
            "complexity": self.complexity,
            "tags": self.tags,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "related_evidence_ids": self.related_evidence_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskSchema':
        """Create a TaskSchema instance from a dictionary."""
        if 'due_date' in data and data['due_date']:
            data['due_date'] = datetime.fromisoformat(data['due_date'])
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

class EpicSchema:
    """Schema definition for an Epic (group of related tasks)."""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        status: str = "Open",
        owner: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        related_evidence_ids: List[str] = None
    ):
        """
        Initialize an epic schema.
        
        Args:
            title: Epic title
            description: Epic description
            status: Current status
            owner: Epic owner
            start_date: Planned start date
            end_date: Planned end date
            id: Unique identifier (auto-generated if not provided)
            created_at: Creation timestamp (defaults to now)
            updated_at: Last update timestamp (defaults to now)
            related_evidence_ids: IDs of evidence related to this epic
        """
        self.id = id if id else generate_id("EPC-")
        self.title = title
        self.description = description
        self.status = status
        self.owner = owner
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.related_evidence_ids = related_evidence_ids or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "related_evidence_ids": self.related_evidence_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EpicSchema':
        """Create an EpicSchema instance from a dictionary."""
        if 'start_date' in data and data['start_date']:
            data['start_date'] = datetime.fromisoformat(data['start_date'])
        if 'end_date' in data and data['end_date']:
            data['end_date'] = datetime.fromisoformat(data['end_date'])
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

class BoardSchema:
    """Schema definition for a Kanban Board."""
    
    def __init__(
        self,
        name: str,
        columns: List[str] = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None
    ):
        """
        Initialize a board schema.
        
        Args:
            name: Board name
            columns: List of column names
            id: Unique identifier (auto-generated if not provided)
            created_at: Creation timestamp (defaults to now)
            updated_at: Last update timestamp (defaults to now)
        """
        self.id = id if id else generate_id("BRD-")
        self.name = name
        self.columns = columns or ["Backlog", "Ready", "In Progress", "Review", "Done"]
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "columns": self.columns,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BoardSchema':
        """Create a BoardSchema instance from a dictionary."""
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
