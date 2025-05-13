"""
Schema Versioning and Migration Support for Evidence Management System.

This module handles versioning and evolution of evidence schemas,
enabling backward compatibility and seamless data migration.
"""
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SchemaVersion:
    """Represents a specific version of a schema with migration capabilities."""
    
    def __init__(self, version: str, schema_def: Dict[str, Any]):
        """
        Initialize a schema version.
        
        Args:
            version: Version string (e.g., "1.0.0")
            schema_def: Schema definition dictionary
        """
        self.version = version
        self.schema_def = schema_def
        self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the schema version to a dictionary."""
        return {
            "version": self.version,
            "schema_def": self.schema_def,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaVersion':
        """Create a SchemaVersion instance from a dictionary."""
        instance = cls(data["version"], data["schema_def"])
        instance.created_at = data.get("created_at", datetime.now().isoformat())
        return instance


class SchemaMigration:
    """Represents a migration between two schema versions."""
    
    def __init__(
        self, 
        from_version: str, 
        to_version: str,
        migration_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        description: str
    ):
        """
        Initialize a schema migration.
        
        Args:
            from_version: Source schema version
            to_version: Target schema version
            migration_func: Function to perform migration on data
            description: Description of the migration changes
        """
        self.from_version = from_version
        self.to_version = to_version
        self.migration_func = migration_func
        self.description = description
        self.created_at = datetime.now().isoformat()
    
    def migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate data from source version to target version.
        
        Args:
            data: Data in source version format
            
        Returns:
            Data in target version format
        """
        try:
            return self.migration_func(data)
        except Exception as e:
            logger.error(f"Migration failed from {self.from_version} to {self.to_version}: {str(e)}")
            raise ValueError(f"Migration failed: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the migration to a dictionary (without the function)."""
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "description": self.description,
            "created_at": self.created_at
        }


class SchemaRegistry:
    """Registry for schema versions and migrations."""
    
    def __init__(self, registry_file: Optional[Path] = None):
        """
        Initialize the schema registry.
        
        Args:
            registry_file: Optional path to a registry file
        """
        self.versions: Dict[str, SchemaVersion] = {}
        self.migrations: Dict[str, List[SchemaMigration]] = {}
        self.current_version = "0.0.0"
        self.registry_file = registry_file
        
        # Load registry if file provided
        if registry_file and registry_file.exists():
            self.load()
    
    def register_version(self, version: SchemaVersion) -> None:
        """
        Register a new schema version.
        
        Args:
            version: SchemaVersion object to register
        """
        if version.version in self.versions:
            logger.warning(f"Overwriting schema version {version.version}")
            
        self.versions[version.version] = version
        
        # Update current version if this is newer
        if self._compare_versions(version.version, self.current_version) > 0:
            self.current_version = version.version
    
    def register_migration(self, migration: SchemaMigration) -> None:
        """
        Register a migration between schema versions.
        
        Args:
            migration: SchemaMigration object to register
        """
        from_version = migration.from_version
        
        if from_version not in self.migrations:
            self.migrations[from_version] = []
            
        self.migrations[from_version].append(migration)
    
    def get_version(self, version: str) -> Optional[SchemaVersion]:
        """
        Get a specific schema version.
        
        Args:
            version: Version string to retrieve
            
        Returns:
            SchemaVersion object or None if not found
        """
        return self.versions.get(version)
    
    def get_latest_version(self) -> SchemaVersion:
        """
        Get the latest schema version.
        
        Returns:
            Latest SchemaVersion object
        """
        return self.versions[self.current_version]
    
    def find_migration_path(self, from_version: str, to_version: str) -> List[SchemaMigration]:
        """
        Find a migration path between two versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List of migrations to apply in order
            
        Raises:
            ValueError: If no migration path exists
        """
        # If same version, no migration needed
        if from_version == to_version:
            return []
        
        # Simple BFS to find shortest path
        visited = {from_version}
        queue = [(from_version, [])]
        
        while queue:
            current_version, path = queue.pop(0)
            
            if current_version not in self.migrations:
                continue
                
            for migration in self.migrations[current_version]:
                next_version = migration.to_version
                
                if next_version == to_version:
                    return path + [migration]
                    
                if next_version not in visited:
                    visited.add(next_version)
                    queue.append((next_version, path + [migration]))
        
        raise ValueError(f"No migration path from {from_version} to {to_version}")
    
    def migrate_data(self, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate data from one schema version to another.
        
        Args:
            data: Data to migrate
            from_version: Source schema version
            to_version: Target schema version
            
        Returns:
            Migrated data
            
        Raises:
            ValueError: If migration fails
        """
        try:
            # Find migration path
            migrations = self.find_migration_path(from_version, to_version)
            
            # Apply migrations in sequence
            result = data.copy()
            for migration in migrations:
                logger.info(f"Applying migration from {migration.from_version} to {migration.to_version}")
                result = migration.migrate(result)
                
            return result
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise ValueError(f"Migration failed: {str(e)}")
    
    def save(self) -> None:
        """Save the registry to file if registry_file is set."""
        if not self.registry_file:
            logger.warning("No registry file set, cannot save")
            return
            
        try:
            # Create registry data
            registry_data = {
                "current_version": self.current_version,
                "versions": {v: self.versions[v].to_dict() for v in self.versions},
                "migrations": {}
            }
            
            # Convert migrations (without functions)
            for from_version, migrations in self.migrations.items():
                registry_data["migrations"][from_version] = [m.to_dict() for m in migrations]
            
            # Create parent directory if needed
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
            logger.info(f"Schema registry saved to {self.registry_file}")
        except Exception as e:
            logger.error(f"Failed to save schema registry: {str(e)}")
            raise
    
    def load(self) -> None:
        """Load the registry from file if registry_file is set."""
        if not self.registry_file or not self.registry_file.exists():
            logger.warning("Registry file does not exist, nothing to load")
            return
            
        try:
            # Read registry data
            with open(self.registry_file, 'r') as f:
                registry_data = json.load(f)
            
            # Load current version
            self.current_version = registry_data.get("current_version", "0.0.0")
            
            # Load versions
            self.versions = {}
            for version_str, version_data in registry_data.get("versions", {}).items():
                self.versions[version_str] = SchemaVersion.from_dict(version_data)
            
            # Note: Migrations cannot be loaded because functions cannot be serialized
            # They need to be registered again in code
            
            logger.info(f"Schema registry loaded from {self.registry_file}")
        except Exception as e:
            logger.error(f"Failed to load schema registry: {str(e)}")
            raise
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 < v2:
                return -1
            if v1 > v2:
                return 1
                
        return 0


# Create global schema registry
evidence_schema_registry = SchemaRegistry(
    registry_file=Path("data/evidence/schema/registry.json")
)

# Define initial schema version
INITIAL_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "category": {"type": "string"},
        "subcategory": {"type": "string"},
        "relevance_score": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "attachments": {"type": "array"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"}
    },
    "required": ["id", "title"]
}

# Register initial version
evidence_schema_registry.register_version(
    SchemaVersion("1.0.0", INITIAL_SCHEMA)
)

def get_schema_registry() -> SchemaRegistry:
    """Get the global evidence schema registry."""
    return evidence_schema_registry


# Example migration function
def migrate_1_0_to_1_1(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example migration from v1.0.0 to v1.1.0.
    
    Changes:
    - Adds metadata field
    - Converts relevance_score from string to numeric if needed
    """
    result = data.copy()
    
    # Add metadata field if not present
    if "metadata" not in result:
        result["metadata"] = {}
    
    # Convert relevance_score from string to numeric if needed
    if "relevance_score" in result and isinstance(result["relevance_score"], str):
        try:
            if result["relevance_score"] == "Low":
                result["relevance_score"] = 1
            elif result["relevance_score"] == "Medium":
                result["relevance_score"] = 2
            elif result["relevance_score"] == "High":
                result["relevance_score"] = 3
            elif result["relevance_score"] == "Critical":
                result["relevance_score"] = 4
            else:
                result["relevance_score"] = int(result["relevance_score"])
        except ValueError:
            # If conversion fails, set to default
            result["relevance_score"] = 2
    
    return result

# Register migration example
# Note: In real code, you'd register all required migrations
evidence_schema_registry.register_migration(
    SchemaMigration(
        from_version="1.0.0",
        to_version="1.1.0",
        migration_func=migrate_1_0_to_1_1,
        description="Added metadata field and converted relevance_score to numeric"
    )
)
