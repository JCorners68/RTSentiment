"""
Attachment Optimizer for Evidence Management System.

This module provides optimization features for attachment storage, including
file deduplication, compression, and storage quota management.
"""
import os
import io
import logging
import hashlib
import gzip
import zlib
import time
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, Set, BinaryIO
from datetime import datetime

from ..utils.exceptions import AttachmentError, StorageError
from ..utils.file_handlers import calculate_file_hash, get_mime_type
from ..config.settings import get_project_root, load_config

# Configure module logger
logger = logging.getLogger(__name__)


class DeduplicationManager:
    """
    Manages file deduplication for attachments.
    
    This class maintains a content-addressable storage system where files with
    identical content are stored only once, saving disk space.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the deduplication manager.
        
        Args:
            storage_dir: Optional directory for attachment storage
        """
        self.config = load_config()
        self.project_root = get_project_root()
        
        # Set up storage directory
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            data_dir = self.project_root / self.config['paths'].get('data', 'data')
            self.storage_dir = data_dir / 'evidence' / 'attachments'
            
        # Set up deduplication directory
        self.content_store_dir = self.storage_dir / 'content_store'
        self.manifest_file = self.storage_dir / 'deduplication_manifest.json'
        
        # Ensure directories exist
        os.makedirs(self.content_store_dir, exist_ok=True)
        
        # Initialize manifest
        self.manifest = self._load_manifest()
        
        logger.info(f"Initialized deduplication manager at {self.storage_dir}")
    
    def _load_manifest(self) -> Dict[str, Any]:
        """
        Load the deduplication manifest.
        
        Returns:
            Manifest dictionary
        """
        if not self.manifest_file.exists():
            # Create initial manifest
            manifest = {
                "file_hashes": {},     # Maps hash to file info
                "reference_count": {}, # Maps hash to number of references
                "attachment_map": {},  # Maps attachment_id to hash
                "total_saved_bytes": 0,
                "last_updated": datetime.now().isoformat()
            }
            self._save_manifest(manifest)
            return manifest
        
        try:
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load deduplication manifest: {str(e)}")
            # Return a default manifest if load fails
            return {
                "file_hashes": {},
                "reference_count": {},
                "attachment_map": {},
                "total_saved_bytes": 0,
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        """
        Save the deduplication manifest.
        
        Args:
            manifest: Manifest dictionary to save
        """
        try:
            # Update timestamp
            manifest["last_updated"] = datetime.now().isoformat()
            
            with open(self.manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deduplication manifest: {str(e)}")
    
    def store_file(self, file_path: Union[str, Path], attachment_id: str) -> Tuple[str, bool]:
        """
        Store a file with deduplication.
        
        Args:
            file_path: Path to the file to store
            attachment_id: ID of the attachment
            
        Returns:
            Tuple of (content_hash, is_duplicate)
            
        Raises:
            AttachmentError: If storing the file fails
        """
        try:
            # Calculate hash of file content
            file_path = Path(file_path)
            content_hash = calculate_file_hash(file_path)
            
            # Check if we already have this file
            is_duplicate = content_hash in self.manifest["file_hashes"]
            
            if is_duplicate:
                # File already exists, just update reference count
                if content_hash not in self.manifest["reference_count"]:
                    self.manifest["reference_count"][content_hash] = 0
                
                self.manifest["reference_count"][content_hash] += 1
                self.manifest["attachment_map"][attachment_id] = content_hash
                
                # Calculate saved space
                file_size = file_path.stat().st_size
                self.manifest["total_saved_bytes"] += file_size
                
                logger.info(f"Deduplicated file {file_path.name} ({file_size} bytes) with hash {content_hash}")
            else:
                # New file, store it in content store
                target_path = self.content_store_dir / content_hash
                
                # Copy the file
                shutil.copy2(file_path, target_path)
                
                # Update manifest
                file_size = file_path.stat().st_size
                mime_type = get_mime_type(file_path)
                
                self.manifest["file_hashes"][content_hash] = {
                    "size": file_size,
                    "mime_type": mime_type,
                    "original_name": file_path.name,
                    "created_at": datetime.now().isoformat()
                }
                
                self.manifest["reference_count"][content_hash] = 1
                self.manifest["attachment_map"][attachment_id] = content_hash
                
                logger.info(f"Stored new file {file_path.name} ({file_size} bytes) with hash {content_hash}")
            
            # Save the updated manifest
            self._save_manifest(self.manifest)
            
            return content_hash, is_duplicate
            
        except Exception as e:
            error_msg = f"Failed to store file {file_path}: {str(e)}"
            logger.error(error_msg)
            raise AttachmentError(error_msg, attachment_id=attachment_id, file_path=str(file_path))
    
    def get_file_path(self, content_hash: str) -> Optional[Path]:
        """
        Get the path to a file in the content store.
        
        Args:
            content_hash: Hash of the file content
            
        Returns:
            Path to the file, or None if not found
        """
        if content_hash not in self.manifest["file_hashes"]:
            return None
            
        path = self.content_store_dir / content_hash
        if not path.exists():
            logger.warning(f"File with hash {content_hash} not found in content store")
            return None
            
        return path
    
    def remove_attachment(self, attachment_id: str) -> bool:
        """
        Remove an attachment from the deduplication system.
        
        Args:
            attachment_id: ID of the attachment to remove
            
        Returns:
            True if removed, False if not found
        """
        if attachment_id not in self.manifest["attachment_map"]:
            return False
            
        content_hash = self.manifest["attachment_map"][attachment_id]
        
        # Decrease reference count
        if content_hash in self.manifest["reference_count"]:
            self.manifest["reference_count"][content_hash] -= 1
            
            # If no more references, consider removing the file
            if self.manifest["reference_count"][content_hash] <= 0:
                # Get file size before removing
                if content_hash in self.manifest["file_hashes"]:
                    file_size = self.manifest["file_hashes"][content_hash]["size"]
                    
                    # Update saved bytes counter
                    self.manifest["total_saved_bytes"] -= file_size
                    
                    # Remove file from content store
                    file_path = self.content_store_dir / content_hash
                    if file_path.exists():
                        os.remove(file_path)
                        
                    # Remove from manifest
                    del self.manifest["file_hashes"][content_hash]
                    del self.manifest["reference_count"][content_hash]
        
        # Remove attachment mapping
        del self.manifest["attachment_map"][attachment_id]
        
        # Save the updated manifest
        self._save_manifest(self.manifest)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get deduplication statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_unique_files = len(self.manifest["file_hashes"])
        total_references = sum(self.manifest["reference_count"].values())
        total_saved_bytes = self.manifest["total_saved_bytes"]
        
        return {
            "unique_files": total_unique_files,
            "total_references": total_references,
            "duplicate_files": total_references - total_unique_files,
            "saved_space_bytes": total_saved_bytes,
            "saved_space_mb": total_saved_bytes / (1024 * 1024),
            "last_updated": self.manifest["last_updated"]
        }
    
    def rebuild_manifest(self) -> Dict[str, Any]:
        """
        Rebuild the manifest from the content store.
        This is useful for recovery or if the manifest becomes corrupted.
        
        Returns:
            Rebuilt manifest
        """
        # Create a new manifest
        new_manifest = {
            "file_hashes": {},
            "reference_count": {},
            "attachment_map": {},
            "total_saved_bytes": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        # Scan content store directory
        for file_path in self.content_store_dir.glob("*"):
            if file_path.is_file():
                content_hash = file_path.name
                file_size = file_path.stat().st_size
                mime_type = get_mime_type(file_path)
                
                new_manifest["file_hashes"][content_hash] = {
                    "size": file_size,
                    "mime_type": mime_type,
                    "original_name": "unknown",  # Original name is lost without the attachment map
                    "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                }
                
                # We can't determine reference count without attachment map
                new_manifest["reference_count"][content_hash] = 0
        
        # Save the new manifest
        self._save_manifest(new_manifest)
        
        logger.info(f"Rebuilt deduplication manifest with {len(new_manifest['file_hashes'])} files")
        return new_manifest
