"""
Storage Quota Management for Evidence Attachments.

This module provides storage quota management capabilities for the Evidence
Management System, controlling attachment storage usage per project or user.
"""
import os
import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from datetime import datetime

from ..utils.exceptions import StorageError, AttachmentError
from ..config.settings import get_project_root, load_config

# Configure module logger
logger = logging.getLogger(__name__)


class QuotaManager:
    """
    Manages storage quotas for evidence attachments.
    
    This class provides quota management capabilities for the Evidence Management
    System, controlling attachment storage usage per project or user.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the quota manager.
        
        Args:
            storage_dir: Optional directory for quota data storage
        """
        self.config = load_config()
        self.project_root = get_project_root()
        
        # Set up storage directory
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.storage_dir = data_dir / 'evidence'
            
        # Set up quota data directory
        self.quota_dir = self.storage_dir / 'quotas'
        os.makedirs(self.quota_dir, exist_ok=True)
        
        # Load default quotas from config
        self.default_quotas = self.config.get('quotas', {})
        if not self.default_quotas:
            # Set sensible defaults if not in config
            self.default_quotas = {
                "project": {
                    "max_bytes": 1073741824,  # 1 GB per project
                    "max_files": 1000         # 1000 files per project
                },
                "user": {
                    "max_bytes": 536870912,   # 512 MB per user
                    "max_files": 500          # 500 files per user
                }
            }
        
        # Load quota data
        self.quota_file = self.quota_dir / 'quota_usage.json'
        self.quota_data = self._load_quota_data()
        
        logger.info(f"Initialized quota manager with default project quota: "\
                  f"{self._format_size(self.default_quotas['project']['max_bytes'])}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    
    def _load_quota_data(self) -> Dict[str, Any]:
        """
        Load quota usage data.
        
        Returns:
            Dictionary with quota usage data
        """
        if not self.quota_file.exists():
            # Create initial quota data
            quota_data = {
                "projects": {},
                "users": {},
                "last_updated": datetime.now().isoformat()
            }
            self._save_quota_data(quota_data)
            return quota_data
        
        try:
            with open(self.quota_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load quota data: {str(e)}")
            # Return a default structure if load fails
            return {
                "projects": {},
                "users": {},
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_quota_data(self, quota_data: Dict[str, Any]) -> None:
        """
        Save quota usage data.
        
        Args:
            quota_data: Dictionary with quota usage data
        """
        try:
            # Update timestamp
            quota_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.quota_file, 'w') as f:
                json.dump(quota_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quota data: {str(e)}")
    
    def get_project_quota(self, project_id: str) -> Dict[str, Any]:
        """
        Get quota for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Dictionary with quota information
        """
        # Initialize project in quota data if not exists
        if project_id not in self.quota_data["projects"]:
            self.quota_data["projects"][project_id] = {
                "used_bytes": 0,
                "file_count": 0,
                "max_bytes": self.default_quotas["project"]["max_bytes"],
                "max_files": self.default_quotas["project"]["max_files"],
                "last_updated": datetime.now().isoformat()
            }
            self._save_quota_data(self.quota_data)
        
        project_quota = self.quota_data["projects"][project_id]
        
        # Calculate percentage used
        bytes_used_pct = (project_quota["used_bytes"] / project_quota["max_bytes"]) * 100
        files_used_pct = (project_quota["file_count"] / project_quota["max_files"]) * 100
        
        return {
            "project_id": project_id,
            "used_bytes": project_quota["used_bytes"],
            "used_bytes_formatted": self._format_size(project_quota["used_bytes"]),
            "max_bytes": project_quota["max_bytes"],
            "max_bytes_formatted": self._format_size(project_quota["max_bytes"]),
            "bytes_used_percent": bytes_used_pct,
            "file_count": project_quota["file_count"],
            "max_files": project_quota["max_files"],
            "files_used_percent": files_used_pct,
            "last_updated": project_quota["last_updated"]
        }
    
    def get_user_quota(self, user_id: str) -> Dict[str, Any]:
        """
        Get quota for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with quota information
        """
        # Initialize user in quota data if not exists
        if user_id not in self.quota_data["users"]:
            self.quota_data["users"][user_id] = {
                "used_bytes": 0,
                "file_count": 0,
                "max_bytes": self.default_quotas["user"]["max_bytes"],
                "max_files": self.default_quotas["user"]["max_files"],
                "last_updated": datetime.now().isoformat()
            }
            self._save_quota_data(self.quota_data)
        
        user_quota = self.quota_data["users"][user_id]
        
        # Calculate percentage used
        bytes_used_pct = (user_quota["used_bytes"] / user_quota["max_bytes"]) * 100
        files_used_pct = (user_quota["file_count"] / user_quota["max_files"]) * 100
        
        return {
            "user_id": user_id,
            "used_bytes": user_quota["used_bytes"],
            "used_bytes_formatted": self._format_size(user_quota["used_bytes"]),
            "max_bytes": user_quota["max_bytes"],
            "max_bytes_formatted": self._format_size(user_quota["max_bytes"]),
            "bytes_used_percent": bytes_used_pct,
            "file_count": user_quota["file_count"],
            "max_files": user_quota["max_files"],
            "files_used_percent": files_used_pct,
            "last_updated": user_quota["last_updated"]
        }
    
    def update_quota(self, size_bytes: int, file_count: int = 1, 
                    project_id: Optional[str] = None, 
                    user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Update quota usage.
        
        Args:
            size_bytes: Size in bytes to add (positive) or remove (negative)
            file_count: Number of files to add (positive) or remove (negative)
            project_id: Optional project ID
            user_id: Optional user ID
            
        Returns:
            Dictionary with updated quota information
            
        Raises:
            QuotaExceededError: If this update would exceed the quota
        """
        result = {}
        
        # Update project quota if specified
        if project_id:
            # Initialize project if not exists
            if project_id not in self.quota_data["projects"]:
                self.quota_data["projects"][project_id] = {
                    "used_bytes": 0,
                    "file_count": 0,
                    "max_bytes": self.default_quotas["project"]["max_bytes"],
                    "max_files": self.default_quotas["project"]["max_files"],
                    "last_updated": datetime.now().isoformat()
                }
            
            project_quota = self.quota_data["projects"][project_id]
            
            # Check if this update would exceed quota
            if size_bytes > 0:
                new_bytes = project_quota["used_bytes"] + size_bytes
                if new_bytes > project_quota["max_bytes"]:
                    raise AttachmentError(
                        f"Project quota exceeded: {self._format_size(new_bytes)} > "
                        f"{self._format_size(project_quota['max_bytes'])}",
                        evidence_id=None,
                        details={"project_id": project_id}
                    )
            
            if file_count > 0:
                new_files = project_quota["file_count"] + file_count
                if new_files > project_quota["max_files"]:
                    raise AttachmentError(
                        f"Project file count exceeded: {new_files} > {project_quota['max_files']}",
                        evidence_id=None,
                        details={"project_id": project_id}
                    )
            
            # Update quota
            project_quota["used_bytes"] += size_bytes
            project_quota["file_count"] += file_count
            project_quota["last_updated"] = datetime.now().isoformat()
            
            # Ensure values don't go below zero
            project_quota["used_bytes"] = max(0, project_quota["used_bytes"])
            project_quota["file_count"] = max(0, project_quota["file_count"])
            
            result["project"] = self.get_project_quota(project_id)
        
        # Update user quota if specified
        if user_id:
            # Initialize user if not exists
            if user_id not in self.quota_data["users"]:
                self.quota_data["users"][user_id] = {
                    "used_bytes": 0,
                    "file_count": 0,
                    "max_bytes": self.default_quotas["user"]["max_bytes"],
                    "max_files": self.default_quotas["user"]["max_files"],
                    "last_updated": datetime.now().isoformat()
                }
            
            user_quota = self.quota_data["users"][user_id]
            
            # Check if this update would exceed quota
            if size_bytes > 0:
                new_bytes = user_quota["used_bytes"] + size_bytes
                if new_bytes > user_quota["max_bytes"]:
                    raise AttachmentError(
                        f"User quota exceeded: {self._format_size(new_bytes)} > "
                        f"{self._format_size(user_quota['max_bytes'])}",
                        evidence_id=None,
                        details={"user_id": user_id}
                    )
            
            if file_count > 0:
                new_files = user_quota["file_count"] + file_count
                if new_files > user_quota["max_files"]:
                    raise AttachmentError(
                        f"User file count exceeded: {new_files} > {user_quota['max_files']}",
                        evidence_id=None,
                        details={"user_id": user_id}
                    )
            
            # Update quota
            user_quota["used_bytes"] += size_bytes
            user_quota["file_count"] += file_count
            user_quota["last_updated"] = datetime.now().isoformat()
            
            # Ensure values don't go below zero
            user_quota["used_bytes"] = max(0, user_quota["used_bytes"])
            user_quota["file_count"] = max(0, user_quota["file_count"])
            
            result["user"] = self.get_user_quota(user_id)
        
        # Save quota data
        self._save_quota_data(self.quota_data)
        
        return result
    
    def set_quota_limit(self, max_bytes: Optional[int] = None, max_files: Optional[int] = None,
                       project_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Set quota limits for a project or user.
        
        Args:
            max_bytes: Maximum bytes allowed
            max_files: Maximum files allowed
            project_id: Optional project ID
            user_id: Optional user ID
            
        Returns:
            Dictionary with updated quota information
        """
        result = {}
        
        # Update project quota if specified
        if project_id:
            # Initialize project if not exists
            if project_id not in self.quota_data["projects"]:
                self.quota_data["projects"][project_id] = {
                    "used_bytes": 0,
                    "file_count": 0,
                    "max_bytes": self.default_quotas["project"]["max_bytes"],
                    "max_files": self.default_quotas["project"]["max_files"],
                    "last_updated": datetime.now().isoformat()
                }
            
            # Update limits
            if max_bytes is not None:
                self.quota_data["projects"][project_id]["max_bytes"] = max_bytes
            
            if max_files is not None:
                self.quota_data["projects"][project_id]["max_files"] = max_files
            
            self.quota_data["projects"][project_id]["last_updated"] = datetime.now().isoformat()
            
            result["project"] = self.get_project_quota(project_id)
        
        # Update user quota if specified
        if user_id:
            # Initialize user if not exists
            if user_id not in self.quota_data["users"]:
                self.quota_data["users"][user_id] = {
                    "used_bytes": 0,
                    "file_count": 0,
                    "max_bytes": self.default_quotas["user"]["max_bytes"],
                    "max_files": self.default_quotas["user"]["max_files"],
                    "last_updated": datetime.now().isoformat()
                }
            
            # Update limits
            if max_bytes is not None:
                self.quota_data["users"][user_id]["max_bytes"] = max_bytes
            
            if max_files is not None:
                self.quota_data["users"][user_id]["max_files"] = max_files
            
            self.quota_data["users"][user_id]["last_updated"] = datetime.now().isoformat()
            
            result["user"] = self.get_user_quota(user_id)
        
        # Save quota data
        self._save_quota_data(self.quota_data)
        
        return result
    
    def get_all_quotas(self) -> Dict[str, Any]:
        """
        Get all quota information.
        
        Returns:
            Dictionary with all quota information
        """
        projects = {}
        for project_id in self.quota_data["projects"]:
            projects[project_id] = self.get_project_quota(project_id)
        
        users = {}
        for user_id in self.quota_data["users"]:
            users[user_id] = self.get_user_quota(user_id)
        
        return {
            "projects": projects,
            "users": users,
            "defaults": self.default_quotas,
            "last_updated": self.quota_data["last_updated"]
        }
    
    def check_quota(self, size_bytes: int, project_id: Optional[str] = None, 
                   user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if an operation would exceed quota.
        
        Args:
            size_bytes: Size in bytes to check
            project_id: Optional project ID
            user_id: Optional user ID
            
        Returns:
            Tuple of (would_exceed, quota_info)
        """
        result = {"would_exceed": False, "quotas": {}}
        
        # Check project quota if specified
        if project_id:
            project_quota = self.get_project_quota(project_id)
            new_bytes = project_quota["used_bytes"] + size_bytes
            would_exceed = new_bytes > project_quota["max_bytes"]
            
            result["quotas"]["project"] = {
                "current_bytes": project_quota["used_bytes"],
                "max_bytes": project_quota["max_bytes"],
                "new_bytes": new_bytes,
                "would_exceed": would_exceed,
                "remaining_bytes": project_quota["max_bytes"] - project_quota["used_bytes"]
            }
            
            if would_exceed:
                result["would_exceed"] = True
        
        # Check user quota if specified
        if user_id:
            user_quota = self.get_user_quota(user_id)
            new_bytes = user_quota["used_bytes"] + size_bytes
            would_exceed = new_bytes > user_quota["max_bytes"]
            
            result["quotas"]["user"] = {
                "current_bytes": user_quota["used_bytes"],
                "max_bytes": user_quota["max_bytes"],
                "new_bytes": new_bytes,
                "would_exceed": would_exceed,
                "remaining_bytes": user_quota["max_bytes"] - user_quota["used_bytes"]
            }
            
            if would_exceed:
                result["would_exceed"] = True
        
        return result["would_exceed"], result
    
    def recalculate_usage(self, attachment_storage: Any, 
                         project_id: Optional[str] = None, 
                         user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Recalculate storage usage from actual data.
        
        Args:
            attachment_storage: Attachment storage system object
            project_id: Optional project ID to recalculate
            user_id: Optional user ID to recalculate
            
        Returns:
            Dictionary with recalculated usage information
        """
        # This method depends on the attachment storage interface
        # It scans all attachments and recalculates actual usage
        # Implementation details would depend on the attachment storage system
        
        # Example implementation (pseudo-code):
        # if project_id:
        #     attachments = attachment_storage.list_attachments(project_id=project_id)
        #     total_size = sum(att.size for att in attachments)
        #     self.quota_data["projects"][project_id]["used_bytes"] = total_size
        #     self.quota_data["projects"][project_id]["file_count"] = len(attachments)
        
        # For now, just return current quota info
        result = {}
        
        if project_id:
            result["project"] = self.get_project_quota(project_id)
        
        if user_id:
            result["user"] = self.get_user_quota(user_id)
        
        return result
