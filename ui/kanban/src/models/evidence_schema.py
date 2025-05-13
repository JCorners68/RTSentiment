"""
Evidence System Schema for the Kanban CLI.

This module defines the data schemas for the Evidence Management System, 
which was prioritized as the most important enhancement. It includes
schemas for evidence items and attachments, with support for hierarchical 
categorization, versioning, and schema evolution.
"""
from datetime import datetime
from typing import Dict, List, Optional, Union, Any, Set, TypedDict
from enum import Enum
from uuid import uuid4
from pathlib import Path
import os
import copy
import json

# Import relationship models
from .relationship_models import (
    RelationshipType, RelationshipStrength, RelationshipMetadata,
    RelationshipRegistry, ImpactAnalyzer, NetworkVisualizer
)

def generate_id(prefix=""):
    """Generate a unique ID with an optional prefix"""
    return f"{prefix}{uuid4()}"

class CategoryNode:
    """Represents a node in the hierarchical category system"""
    
    def __init__(self, name: str, parent: Optional['CategoryNode'] = None):
        self.name = name
        self.parent = parent
        self.children: List['CategoryNode'] = []
        
    def add_child(self, child_name: str) -> 'CategoryNode':
        """Add a child category and return the new node"""
        child = CategoryNode(child_name, self)
        self.children.append(child)
        return child
        
    def get_path(self) -> List[str]:
        """Get the full path from root to this category node"""
        if self.parent is None:
            return [self.name]
        else:
            return self.parent.get_path() + [self.name]
            
    def get_path_string(self, separator: str = "/") -> str:
        """Get the full path as a string with the given separator"""
        return separator.join(self.get_path())
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "children": [child.to_dict() for child in self.children]
        }
        
    @classmethod
    def from_dict(cls, data: Dict, parent: Optional['CategoryNode'] = None) -> 'CategoryNode':
        """Create a CategoryNode from a dictionary"""
        node = cls(data["name"], parent)
        for child_data in data.get("children", []):
            child = cls.from_dict(child_data, node)
            node.children.append(child)
        return node


class CategoryHierarchy:
    """Manager for hierarchical categories"""
    
    def __init__(self):
        # Create root categories
        self.root_categories: Dict[str, CategoryNode] = {}
        
        # Initialize the hierarchy with the basic categories
        for category in [
            "Requirement", "Bug", "Design", "Test", "Result", 
            "Reference", "User Feedback", "Decision", "Other"
        ]:
            self.root_categories[category] = CategoryNode(category)
            
        # Add some example subcategories
        self.root_categories["Requirement"].add_child("Functional")
        self.root_categories["Requirement"].add_child("Non-Functional")
        self.root_categories["Design"].add_child("Architecture")
        self.root_categories["Design"].add_child("UI/UX")
        self.root_categories["Test"].add_child("Unit")
        self.root_categories["Test"].add_child("Integration")
        self.root_categories["Test"].add_child("System")
    
    def add_category_path(self, path: List[str]) -> Optional[CategoryNode]:
        """Add a category path, creating any missing nodes"""
        if not path:
            return None
            
        # Get or create root category
        root_name = path[0]
        if root_name not in self.root_categories:
            self.root_categories[root_name] = CategoryNode(root_name)
            
        # Start from the root
        current = self.root_categories[root_name]
        
        # Create or navigate the path
        for i in range(1, len(path)):
            name = path[i]
            
            # Try to find existing child
            found = False
            for child in current.children:
                if child.name == name:
                    current = child
                    found = True
                    break
                    
            # If not found, create new child
            if not found:
                current = current.add_child(name)
                
        return current
    
    def get_category_path(self, path: List[str]) -> Optional[CategoryNode]:
        """Get a category node from a path if it exists"""
        if not path:
            return None
            
        # Get root category
        root_name = path[0]
        if root_name not in self.root_categories:
            return None
            
        # Start from the root
        current = self.root_categories[root_name]
        
        # Navigate the path
        for i in range(1, len(path)):
            name = path[i]
            
            # Try to find child
            found = False
            for child in current.children:
                if child.name == name:
                    current = child
                    found = True
                    break
                    
            # If not found, return None
            if not found:
                return None
                
        return current
        
    def to_dict(self) -> Dict:
        """Convert hierarchy to dictionary for serialization"""
        return {
            "categories": {name: node.to_dict() for name, node in self.root_categories.items()}
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'CategoryHierarchy':
        """Create a CategoryHierarchy from a dictionary"""
        hierarchy = cls()
        hierarchy.root_categories = {}
        
        for name, node_data in data.get("categories", {}).items():
            hierarchy.root_categories[name] = CategoryNode.from_dict(node_data)
            
        return hierarchy


class EvidenceCategory(str, Enum):
    """Enumeration of possible evidence categories."""
    REQUIREMENT = "Requirement"
    BUG = "Bug"
    DESIGN = "Design"
    TEST = "Test"
    RESULT = "Result"
    REFERENCE = "Reference"
    USER_FEEDBACK = "User Feedback"
    DECISION = "Decision"
    OTHER = "Other"
    
    @classmethod
    def get_hierarchy(cls) -> CategoryHierarchy:
        """Get the default category hierarchy"""
        return CategoryHierarchy()

class EvidenceRelevance(str, Enum):
    """Enumeration of evidence relevance levels."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class AttachmentSchema:
    """Schema definition for Evidence Attachments."""
    
    def __init__(
        self,
        file_path: str,
        file_name: Optional[str] = None,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        content_preview: Optional[str] = None,
        description: str = "",
        id: str = None,
        created_at: datetime = None,
        uploaded_by: str = None
    ):
        """
        Initialize an attachment schema.
        
        Args:
            file_path: Path to the attachment file (relative to attachments dir)
            file_name: Original filename
            file_type: File MIME type
            file_size: File size in bytes
            content_preview: Plain text preview of content (if applicable)
            description: Description of the attachment
            id: Unique identifier (auto-generated if not provided)
            created_at: Creation timestamp (defaults to now)
            uploaded_by: User who uploaded the attachment
        """
        self.id = id if id else generate_id("ATT-")
        
        # Sanitize file path for security
        if os.path.isabs(file_path):
            raise ValueError("Attachment file_path must be relative, not absolute")
            
        self.file_path = file_path
        self.file_name = file_name or os.path.basename(file_path)
        
        # Determine file type from extension if not provided
        if not file_type:
            ext = os.path.splitext(self.file_name)[1].lower()
            mime_types = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.py': 'text/x-python',
                '.js': 'text/javascript',
                '.json': 'application/json',
                '.html': 'text/html',
                '.csv': 'text/csv',
                '.md': 'text/markdown'
            }
            self.file_type = mime_types.get(ext, 'application/octet-stream')
        else:
            self.file_type = file_type
            
        self.file_size = file_size
        self.content_preview = content_preview
        self.description = description
        self.created_at = created_at or datetime.now()
        self.uploaded_by = uploaded_by
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "content_preview": self.content_preview,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "uploaded_by": self.uploaded_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AttachmentSchema':
        """Create an AttachmentSchema instance from a dictionary."""
        if 'created_at' in data and data['created_at']:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)

class SchemaVersion:
    """Represents a version of the evidence schema for migration and evolution"""
    
    CURRENT_VERSION = "1.1.0"  # Current schema version
    
    def __init__(self, version: str):
        self.version = version
        
    @staticmethod
    def is_compatible(version1: str, version2: str) -> bool:
        """Check if two schema versions are compatible"""
        # Parse versions as major.minor.patch
        v1_parts = [int(p) for p in version1.split('.')]
        v2_parts = [int(p) for p in version2.split('.')]
        
        # Major version must match for compatibility
        return v1_parts[0] == v2_parts[0]
    
    @staticmethod
    def to_dict(obj: Any) -> Dict:
        """Convert an object to a dictionary with schema version"""
        if hasattr(obj, 'to_dict'):
            result = obj.to_dict()
        elif isinstance(obj, dict):
            result = obj.copy()
        else:
            raise ValueError(f"Cannot convert {type(obj)} to dictionary")
            
        # Add schema version
        result["_schema_version"] = SchemaVersion.CURRENT_VERSION
        return result


class SchemaMigration:
    """Handles schema migrations between different versions"""
    
    def __init__(self):
        # Register migration handlers
        self.migration_handlers = {
            "1.0.0_to_1.1.0": self._migrate_1_0_0_to_1_1_0
        }
    
    def migrate(self, data: Dict, from_version: str, to_version: str) -> Dict:
        """Migrate data from one schema version to another"""
        # If versions are the same, no migration needed
        if from_version == to_version:
            return data
            
        # Check if we can handle this migration
        migration_key = f"{from_version}_to_{to_version}"
        if migration_key in self.migration_handlers:
            # Direct migration available
            return self.migration_handlers[migration_key](data)
        else:
            # Need to find migration path
            # For now, we'll just raise an error
            raise ValueError(f"No migration path from {from_version} to {to_version}")
    
    def _migrate_1_0_0_to_1_1_0(self, data: Dict) -> Dict:
        """Migrate from version 1.0.0 to 1.1.0"""
        # Copy data to avoid modifying the original
        result = copy.deepcopy(data)
        
        # In 1.1.0 we added category_path and version_info fields
        
        # Convert subcategory to category_path
        if "subcategory" in result and result["subcategory"]:
            category = result.get("category", "Other")
            subcategory = result["subcategory"]
            result["category_path"] = [category, subcategory]
        else:
            category = result.get("category", "Other")
            result["category_path"] = [category]
        
        # Add version info
        result["version_info"] = {
            "version": 1,
            "created_at": result.get("created_at", datetime.now().isoformat()),
            "updated_at": result.get("updated_at", datetime.now().isoformat()),
            "changes": []
        }
        
        # Update schema version
        result["_schema_version"] = "1.1.0"
        
        return result


class EvidenceSchema:
    """Schema definition for Evidence Items in the Evidence Management System."""
    
    def __init__(
        self,
        title: str,
        description: str,
        source: str = "",
        category: Union[EvidenceCategory, str] = EvidenceCategory.OTHER,
        subcategory: str = "",
        category_path: List[str] = None,  # New field for hierarchical categories
        relevance_score: Union[EvidenceRelevance, str] = EvidenceRelevance.MEDIUM,
        date_collected: Optional[datetime] = None,
        tags: List[str] = None,
        project_id: str = None,
        epic_id: str = None,
        task_id: str = None,
        related_evidence_ids: List[str] = None,
        # Enhanced relationship tracking fields
        relationship_metadata: Dict[str, Dict] = None,  # {target_id: relationship_metadata_dict}
        attachments: List[Union[AttachmentSchema, Dict]] = None,
        id: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        created_by: str = None,
        metadata: Dict[str, Any] = None,
        schema_version: str = SchemaVersion.CURRENT_VERSION,  # Schema version
        version_info: Dict[str, Any] = None,  # Versioning info for the evidence item
        previous_versions: List[Dict] = None  # Previous versions of this item
    ):
        """
        Initialize an evidence schema.
        
        Args:
            title: Evidence title
            description: Evidence description
            source: Source of the evidence (e.g., interview, document, system)
            category: Primary category
            subcategory: More specific categorization
            relevance_score: Importance/relevance level
            date_collected: When the evidence was collected
            tags: List of tags for filtering
            project_id: ID of related project
            epic_id: ID of related epic
            task_id: ID of related task
            related_evidence_ids: IDs of related evidence items
            attachments: List of attachment objects or dicts
            id: Unique identifier (auto-generated if not provided)
            created_at: Creation timestamp (defaults to now)
            updated_at: Last update timestamp (defaults to now)
            created_by: User who created the evidence
            metadata: Additional metadata as key-value pairs
        """
        self.id = id if id else generate_id("EV-")
        self.title = title
        self.description = description
        self.source = source
        
        # Handle category as string or enum
        if isinstance(category, str):
            try:
                self.category = EvidenceCategory(category)
            except ValueError:
                self.category = EvidenceCategory.OTHER
        else:
            self.category = category
            
        self.subcategory = subcategory
        
        # Set up category path (hierarchical categorization)
        if category_path:
            self.category_path = category_path
        elif subcategory:
            # Create from category and subcategory
            self.category_path = [self.category.value, subcategory]
        else:
            # Just use the main category
            self.category_path = [self.category.value]
        
        # Handle relevance as string or enum
        if isinstance(relevance_score, str):
            try:
                self.relevance_score = EvidenceRelevance(relevance_score)
            except ValueError:
                self.relevance_score = EvidenceRelevance.MEDIUM
        else:
            self.relevance_score = relevance_score
            
        self.date_collected = date_collected or datetime.now()
        self.tags = tags or []
        self.project_id = project_id
        self.epic_id = epic_id
        self.task_id = task_id
        self.related_evidence_ids = related_evidence_ids or []
        
        # Process attachments
        self.attachments = []
        if attachments:
            for att in attachments:
                if isinstance(att, AttachmentSchema):
                    self.attachments.append(att)
                elif isinstance(att, dict):
                    self.attachments.append(AttachmentSchema.from_dict(att))
        
        # Handle versioning
        self.schema_version = schema_version
        
        # Set up version info if not provided
        if version_info is None:
            self.version_info = {
                "version": 1,  # Start at version 1
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "changes": []  # Empty change log initially
            }
        else:
            self.version_info = version_info
            
        # Previous versions of this evidence item
        self.previous_versions = previous_versions or []
        
        # Enhanced relationship tracking
        self.relationship_metadata = {}
        if relationship_metadata:
            for target_id, metadata_dict in relationship_metadata.items():
                if isinstance(metadata_dict, dict):
                    self.relationship_metadata[target_id] = RelationshipMetadata.from_dict(metadata_dict)
                elif isinstance(metadata_dict, RelationshipMetadata):
                    self.relationship_metadata[target_id] = metadata_dict
        
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.created_by = created_by
        self.metadata = metadata or {}
    
    def create_new_version(self, changes: Dict[str, Any], change_comment: str = "") -> 'EvidenceSchema':
        """Create a new version of this evidence item with specified changes.
        
        Args:
            changes: Dictionary of fields to change with their new values
            change_comment: Optional comment describing the changes
            
        Returns:
            A new EvidenceSchema object with updated version information
        """
        # First save the current state as a previous version
        current_version = self.to_dict()
        
        # Create a clone of the current state
        new_version_data = copy.deepcopy(current_version)
        
        # Update the version info
        current_version_num = self.version_info["version"]
        new_version_data["version_info"] = {
            "version": current_version_num + 1,
            "previous_version": current_version_num,
            "created_at": current_version["created_at"],  # Keep original creation time
            "updated_at": datetime.now().isoformat(),
            "changes": self.version_info.get("changes", []) + [{
                "timestamp": datetime.now().isoformat(),
                "comment": change_comment,
                "fields_changed": list(changes.keys())
            }]
        }
        
        # Add the current version to previous versions
        if "previous_versions" not in new_version_data:
            new_version_data["previous_versions"] = []
        new_version_data["previous_versions"].append(current_version)
        
        # Apply the changes
        for field, value in changes.items():
            if field not in ["id", "created_at", "version_info", "previous_versions", "schema_version"]:
                new_version_data[field] = value
        
        # Create new evidence item from the updated data
        return EvidenceSchema.from_dict(new_version_data)
    
    def update_category_path(self, category_path: List[str]) -> None:
        """Update the hierarchical category path.
        
        Args:
            category_path: New category path as a list of strings (from root to leaf)
        """
        if not category_path:
            return
            
        self.category_path = category_path
        
        # Update category and subcategory for backwards compatibility
        if len(category_path) > 0:
            try:
                self.category = EvidenceCategory(category_path[0])
            except ValueError:
                self.category = EvidenceCategory.OTHER
                
        if len(category_path) > 1:
            self.subcategory = category_path[1]
        else:
            self.subcategory = ""
            
        self.updated_at = datetime.now()
        
        # Record this change in version info
        if hasattr(self, "version_info") and self.version_info:
            self.version_info["updated_at"] = datetime.now().isoformat()
            if "changes" in self.version_info:
                self.version_info["changes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "comment": "Updated category path",
                    "fields_changed": ["category_path", "category", "subcategory"]
                })
    
    def compare_with_version(self, version_num: int) -> Dict[str, Dict[str, Any]]:
        """Compare this evidence item with a specified previous version.
        
        Args:
            version_num: The version number to compare with
            
        Returns:
            Dictionary of differences with fields as keys and values showing
            {'current': current_value, 'previous': previous_value}
        
        Raises:
            ValueError: If the specified version doesn't exist
        """
        # Get the current version number
        current_version_num = self.version_info.get("version", 1)
        
        # Check if we're looking for a valid previous version
        if version_num >= current_version_num:
            raise ValueError(f"Version {version_num} is not a previous version of {current_version_num}")
            
        # Find the requested version in previous_versions
        target_version = None
        for version in self.previous_versions:
            if version.get("version_info", {}).get("version") == version_num:
                target_version = version
                break
                
        if not target_version:
            raise ValueError(f"Version {version_num} not found in version history")
            
        # Compare fields and track differences
        differences = {}
        current_dict = self.to_dict()
        
        # Fields to compare (excluding version-related metadata)
        fields_to_compare = [
            "title", "description", "source", "category", "subcategory", "category_path",
            "relevance_score", "date_collected", "tags", "project_id", "epic_id", "task_id",
            "related_evidence_ids", "metadata"
        ]
        
        for field in fields_to_compare:
            current_val = current_dict.get(field)
            previous_val = target_version.get(field)
            
            # Check if values are different
            if current_val != previous_val:
                differences[field] = {
                    "current": current_val,
                    "previous": previous_val
                }
                
        return differences
    
    def add_attachment(self, attachment: Union[AttachmentSchema, Dict]) -> str:
        """Add an attachment to this evidence item."""
        if isinstance(attachment, dict):
            attachment = AttachmentSchema.from_dict(attachment)
        
        self.attachments.append(attachment)
        self.updated_at = datetime.now()
        
        # Record this change in version info
        if hasattr(self, "version_info") and self.version_info:
            self.version_info["updated_at"] = datetime.now().isoformat()
            if "changes" in self.version_info:
                self.version_info["changes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "comment": f"Added attachment {attachment.id}",
                    "fields_changed": ["attachments"]
                })
                
        return attachment.id
    
    def remove_attachment(self, attachment_id: str) -> bool:
        """Remove an attachment by ID."""
        for i, att in enumerate(self.attachments):
            if att.id == attachment_id:
                del self.attachments[i]
                self.updated_at = datetime.now()
                
                # Record this change in version info
                if hasattr(self, "version_info") and self.version_info:
                    self.version_info["updated_at"] = datetime.now().isoformat()
                    if "changes" in self.version_info:
                        self.version_info["changes"].append({
                            "timestamp": datetime.now().isoformat(),
                            "comment": f"Removed attachment {attachment_id}",
                            "fields_changed": ["attachments"]
                        })
                        
                return True
        return False
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to this evidence item."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
            
            # Record this change in version info
            if hasattr(self, "version_info") and self.version_info:
                self.version_info["updated_at"] = datetime.now().isoformat()
                if "changes" in self.version_info:
                    self.version_info["changes"].append({
                        "timestamp": datetime.now().isoformat(),
                        "comment": f"Added tag '{tag}'",
                        "fields_changed": ["tags"]
                    })
    
    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from this evidence item."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
            
            # Record this change in version info
            if hasattr(self, "version_info") and self.version_info:
                self.version_info["updated_at"] = datetime.now().isoformat()
                if "changes" in self.version_info:
                    self.version_info["changes"].append({
                        "timestamp": datetime.now().isoformat(),
                        "comment": f"Removed tag '{tag}'",
                        "fields_changed": ["tags"]
                    })
                    
            return True
        return False
        
    # Enhanced relationship management methods
    
    def add_relationship(
        self,
        target_id: str,
        relationship_type: Union[RelationshipType, str] = RelationshipType.RELATES_TO,
        strength: Union[RelationshipStrength, str] = RelationshipStrength.MODERATE,
        description: str = "",
        impact_score: int = 50
    ) -> RelationshipMetadata:
        """Add or update a relationship with enhanced metadata.
        
        Args:
            target_id: ID of the target entity (evidence, epic, task, etc.)
            relationship_type: Type of relationship
            strength: Strength of the relationship
            description: Description of the relationship
            impact_score: Impact score (0-100)
            
        Returns:
            RelationshipMetadata object
        """
        # Add to basic related_evidence_ids for backward compatibility
        if target_id.startswith("EV-") and target_id not in self.related_evidence_ids:
            self.related_evidence_ids.append(target_id)
            
        # Handle relationship_type as string or enum
        if isinstance(relationship_type, str):
            try:
                relationship_type = RelationshipType(relationship_type)
            except ValueError:
                relationship_type = RelationshipType.RELATES_TO
                
        # Handle strength as string or enum
        if isinstance(strength, str):
            try:
                strength = RelationshipStrength(strength)
            except ValueError:
                strength = RelationshipStrength.MODERATE
                
        # Create relationship metadata
        metadata = RelationshipMetadata(
            relationship_type=relationship_type,
            strength=strength,
            description=description,
            impact_score=impact_score
        )
        
        # Store relationship metadata
        self.relationship_metadata[target_id] = metadata
        
        # Update timestamps
        self.updated_at = datetime.now()
        
        # Record this change in version info
        if hasattr(self, "version_info") and self.version_info:
            self.version_info["updated_at"] = datetime.now().isoformat()
            if "changes" in self.version_info:
                self.version_info["changes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "comment": f"Added relationship to {target_id} ({relationship_type.value})",
                    "fields_changed": ["relationship_metadata", "related_evidence_ids"]
                })
                
        return metadata
    
    def update_relationship(
        self,
        target_id: str,
        relationship_type: Optional[Union[RelationshipType, str]] = None,
        strength: Optional[Union[RelationshipStrength, str]] = None,
        description: Optional[str] = None,
        impact_score: Optional[int] = None
    ) -> Optional[RelationshipMetadata]:
        """Update an existing relationship's metadata.
        
        Args:
            target_id: ID of the target entity (evidence, epic, task, etc.)
            relationship_type: Type of relationship (optional)
            strength: Strength of the relationship (optional)
            description: Description of the relationship (optional)
            impact_score: Impact score (0-100) (optional)
            
        Returns:
            Updated RelationshipMetadata or None if relationship doesn't exist
        """
        if target_id not in self.relationship_metadata:
            return None
            
        metadata = self.relationship_metadata[target_id]
        
        # Update relationship type if provided
        if relationship_type is not None:
            if isinstance(relationship_type, str):
                try:
                    metadata.relationship_type = RelationshipType(relationship_type)
                except ValueError:
                    metadata.relationship_type = RelationshipType.RELATES_TO
            else:
                metadata.relationship_type = relationship_type
                
        # Update strength if provided
        if strength is not None:
            if isinstance(strength, str):
                try:
                    metadata.strength = RelationshipStrength(strength)
                except ValueError:
                    metadata.strength = RelationshipStrength.MODERATE
            else:
                metadata.strength = strength
                
        # Update description if provided
        if description is not None:
            metadata.description = description
            
        # Update impact score if provided
        if impact_score is not None:
            metadata.impact_score = min(100, max(0, impact_score))
            
        # Update timestamps
        metadata.updated_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Record this change in version info
        if hasattr(self, "version_info") and self.version_info:
            self.version_info["updated_at"] = datetime.now().isoformat()
            if "changes" in self.version_info:
                self.version_info["changes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "comment": f"Updated relationship to {target_id}",
                    "fields_changed": ["relationship_metadata"]
                })
                
        return metadata
    
    def remove_relationship(self, target_id: str) -> bool:
        """Remove a relationship and its metadata.
        
        Args:
            target_id: ID of the target entity (evidence, epic, task, etc.)
            
        Returns:
            True if relationship was removed, False if not found
        """
        # Remove from basic related_evidence_ids for backward compatibility
        if target_id in self.related_evidence_ids:
            self.related_evidence_ids.remove(target_id)
            
        # Remove from relationship metadata
        removed = False
        if target_id in self.relationship_metadata:
            del self.relationship_metadata[target_id]
            removed = True
            
        if removed:
            # Update timestamps
            self.updated_at = datetime.now()
            
            # Record this change in version info
            if hasattr(self, "version_info") and self.version_info:
                self.version_info["updated_at"] = datetime.now().isoformat()
                if "changes" in self.version_info:
                    self.version_info["changes"].append({
                        "timestamp": datetime.now().isoformat(),
                        "comment": f"Removed relationship to {target_id}",
                        "fields_changed": ["relationship_metadata", "related_evidence_ids"]
                    })
                    
        return removed
    
    def get_relationship(self, target_id: str) -> Optional[RelationshipMetadata]:
        """Get metadata for a relationship with a specific entity.
        
        Args:
            target_id: ID of the target entity (evidence, epic, task, etc.)
            
        Returns:
            RelationshipMetadata object or None if relationship doesn't exist
        """
        return self.relationship_metadata.get(target_id)
    
    def get_all_relationships(self) -> Dict[str, RelationshipMetadata]:
        """Get all relationships for this evidence item.
        
        Returns:
            Dictionary of {target_id: RelationshipMetadata}
        """
        return self.relationship_metadata
    
    def get_relationships_by_type(self, relationship_type: Union[RelationshipType, str]) -> Dict[str, RelationshipMetadata]:
        """Get all relationships of a specific type.
        
        Args:
            relationship_type: Type of relationship to filter by
            
        Returns:
            Dictionary of {target_id: RelationshipMetadata} for matching relationships
        """
        # Handle relationship_type as string or enum
        if isinstance(relationship_type, str):
            try:
                relationship_type = RelationshipType(relationship_type)
            except ValueError:
                relationship_type = RelationshipType.RELATES_TO
                
        return {
            target_id: metadata
            for target_id, metadata in self.relationship_metadata.items()
            if metadata.relationship_type == relationship_type
        }
    
    def get_relationships_by_strength(self, strength: Union[RelationshipStrength, str]) -> Dict[str, RelationshipMetadata]:
        """Get all relationships of a specific strength.
        
        Args:
            strength: Strength of relationship to filter by
            
        Returns:
            Dictionary of {target_id: RelationshipMetadata} for matching relationships
        """
        # Handle strength as string or enum
        if isinstance(strength, str):
            try:
                strength = RelationshipStrength(strength)
            except ValueError:
                strength = RelationshipStrength.MODERATE
                
        return {
            target_id: metadata
            for target_id, metadata in self.relationship_metadata.items()
            if metadata.strength == strength
        }
    
    def analyze_impact(self) -> Dict[str, Any]:
        """Analyze the impact of changes to this evidence item.
        
        Returns:
            Dictionary with impact analysis results
        """
        # Create a temporary registry with all relationships
        registry = RelationshipRegistry()
        
        # Register all relationships
        for target_id, metadata in self.relationship_metadata.items():
            registry.register_relationship(
                self.id,
                target_id,
                metadata.relationship_type,
                metadata.strength,
                metadata.description,
                metadata.impact_score
            )
            
        # Perform impact analysis
        analyzer = ImpactAnalyzer(registry)
        return analyzer.analyze_impact(self.id)
    
    def analyze_propagation(self, max_depth: int = 3) -> Dict[str, Any]:
        """Analyze how changes propagate through the relationship network.
        
        Args:
            max_depth: Maximum depth for propagation analysis
            
        Returns:
            Dictionary with propagation analysis results
        """
        # Create a temporary registry with all relationships
        registry = RelationshipRegistry()
        
        # Register all relationships
        for target_id, metadata in self.relationship_metadata.items():
            registry.register_relationship(
                self.id,
                target_id,
                metadata.relationship_type,
                metadata.strength,
                metadata.description,
                metadata.impact_score
            )
            
        # Perform propagation analysis
        analyzer = ImpactAnalyzer(registry)
        return analyzer.analyze_propagation(self.id, max_depth)
    
    def generate_network_plot(
        self, 
        max_depth: int = 2, 
        figsize: Tuple[int, int] = (10, 8),
        show_labels: bool = True,
        output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate a network visualization plot.
        
        Args:
            max_depth: Maximum depth of relationships to include
            figsize: Figure size as (width, height) in inches
            show_labels: Whether to show node labels
            output_path: Optional path to save the figure
            
        Returns:
            Bytes of the PNG image if output_path is None, else None
        """
        # Create a temporary registry with all relationships
        registry = RelationshipRegistry()
        
        # Register all relationships
        for target_id, metadata in self.relationship_metadata.items():
            registry.register_relationship(
                self.id,
                target_id,
                metadata.relationship_type,
                metadata.strength,
                metadata.description,
                metadata.impact_score
            )
            
        # Generate network plot
        visualizer = NetworkVisualizer(registry)
        return visualizer.generate_network_plot(
            self.id, max_depth, figsize, show_labels, output_path
        )
    
    def get_network_statistics(self, max_depth: int = 2) -> Dict[str, Any]:
        """Get statistics about the relationship network.
        
        Args:
            max_depth: Maximum depth of relationships to include
            
        Returns:
            Dictionary with network statistics
        """
        # Create a temporary registry with all relationships
        registry = RelationshipRegistry()
        
        # Register all relationships
        for target_id, metadata in self.relationship_metadata.items():
            registry.register_relationship(
                self.id,
                target_id,
                metadata.relationship_type,
                metadata.strength,
                metadata.description,
                metadata.impact_score
            )
            
        # Get network statistics
        visualizer = NetworkVisualizer(registry)
        return visualizer.get_network_statistics(self.id, max_depth)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "category": self.category.value,
            "subcategory": self.subcategory,
            "relevance_score": self.relevance_score.value,
            "date_collected": self.date_collected.isoformat(),
            "tags": self.tags,
            "project_id": self.project_id,
            "epic_id": self.epic_id,
            "task_id": self.task_id,
            "related_evidence_ids": self.related_evidence_ids,
            "attachments": [att.to_dict() for att in self.attachments],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "metadata": self.metadata,
            "_schema_version": self.schema_version
        }
        
        # Add relationship metadata if available
        if hasattr(self, "relationship_metadata") and self.relationship_metadata:
            result["relationship_metadata"] = {
                target_id: metadata.to_dict() 
                for target_id, metadata in self.relationship_metadata.items()
            }
        
        # Add hierarchical categorization if available
        if hasattr(self, "category_path"):
            result["category_path"] = self.category_path
            
        # Add version info if available
        if hasattr(self, "version_info") and self.version_info:
            result["version_info"] = self.version_info
            
        # Add previous versions if available
        if hasattr(self, "previous_versions") and self.previous_versions:
            result["previous_versions"] = self.previous_versions
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EvidenceSchema':
        """Create an EvidenceSchema instance from a dictionary."""
        # Handle schema version migration if needed
        schema_version = data.get("_schema_version", "1.0.0")
        if schema_version != SchemaVersion.CURRENT_VERSION:
            # Migrate the data to the current schema version
            migration = SchemaMigration()
            try:
                data = migration.migrate(data, schema_version, SchemaVersion.CURRENT_VERSION)
            except ValueError as e:
                # Log migration error but continue with best effort
                # In production code, you might want to handle this differently
                print(f"Warning: Schema migration error: {str(e)}")
        
        # Make a copy to avoid modifying the original
        data_copy = copy.deepcopy(data)
        
        # Handle datetime fields
        for date_field in ['date_collected', 'created_at', 'updated_at']:
            if date_field in data_copy and data_copy[date_field]:
                if isinstance(data_copy[date_field], str):
                    data_copy[date_field] = datetime.fromisoformat(data_copy[date_field])
        
        # Handle attachments
        if 'attachments' in data_copy and data_copy['attachments']:
            data_copy['attachments'] = [AttachmentSchema.from_dict(att) for att in data_copy['attachments']]
        
        # Handle version info timestamps
        if 'version_info' in data_copy and data_copy['version_info']:
            # Convert timestamp strings to datetime objects where needed for processing
            # but keep them as strings in the data
            if 'created_at' in data_copy['version_info'] and isinstance(data_copy['version_info']['created_at'], str):
                try:
                    # Just validate the timestamp format, don't convert
                    datetime.fromisoformat(data_copy['version_info']['created_at'])
                except ValueError:
                    data_copy['version_info']['created_at'] = datetime.now().isoformat()
            
            if 'updated_at' in data_copy['version_info'] and isinstance(data_copy['version_info']['updated_at'], str):
                try:
                    # Just validate the timestamp format, don't convert
                    datetime.fromisoformat(data_copy['version_info']['updated_at'])
                except ValueError:
                    data_copy['version_info']['updated_at'] = datetime.now().isoformat()
        
        return cls(**data_copy)
