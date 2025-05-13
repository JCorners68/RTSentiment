"""
File handling utilities for the Kanban CLI.

This module provides utilities for secure and robust file operations,
particularly for handling evidence attachments.
"""
import os
import shutil
import hashlib
import magic
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, BinaryIO
import mimetypes
import tempfile
import traceback

from ..config.settings import get_project_root, load_config
from .exceptions import FileOperationError, AttachmentError

# Configure module logger
logger = logging.getLogger(__name__)

# Initialize mime type detection
mimetypes.init()
try:
    # Try to use python-magic for better mime type detection
    mime_magic = magic.Magic(mime=True)
    def get_mime_type(file_path: str) -> str:
        """Get MIME type of file using python-magic."""
        try:
            return mime_magic.from_file(file_path)
        except Exception as e:
            logger.warning(f"Failed to detect MIME type with python-magic: {str(e)}")
            return mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
except ImportError:
    # Fall back to mimetypes
    def get_mime_type(file_path: str) -> str:
        """Get MIME type of file using mimetypes module."""
        return mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

def safe_path_join(base_dir: Path, *paths: str) -> Path:
    """
    Safely join paths, preventing directory traversal attacks.
    
    Args:
        base_dir: Base directory
        *paths: Path components to join
        
    Returns:
        Resolved absolute path that is guaranteed to be within base_dir
        
    Raises:
        FileOperationError: If the resulting path would be outside base_dir
    """
    # Convert base_dir to absolute path
    base_dir = os.path.abspath(base_dir)
    
    # Join paths and normalize
    joined_path = os.path.normpath(os.path.join(base_dir, *paths))
    
    # Ensure resulting path is still within base_dir
    if not joined_path.startswith(base_dir):
        raise FileOperationError(
            f"Path traversal attempt detected",
            file_path=joined_path,
            operation="path_join",
            error_code="E111",
            details={"base_dir": base_dir, "paths": paths}
        )
    
    return Path(joined_path)

def safe_file_copy(source_path: str, dest_dir: Path, dest_filename: Optional[str] = None) -> Tuple[Path, Dict[str, Any]]:
    """
    Safely copy a file to a destination directory.
    
    Args:
        source_path: Source file path
        dest_dir: Destination directory
        dest_filename: Optional custom filename for destination
        
    Returns:
        Tuple containing:
            - Path object of the destination file
            - Dictionary with file metadata
            
    Raises:
        FileOperationError: If file copying fails
    """
    # Check source file exists
    source_path = os.path.abspath(source_path)
    if not os.path.isfile(source_path):
        raise FileOperationError(
            f"Source file does not exist",
            file_path=source_path,
            operation="file_copy",
            error_code="E112"
        )
    
    # Ensure destination directory exists
    os.makedirs(dest_dir, exist_ok=True)
    
    # Determine destination filename
    if dest_filename is None:
        dest_filename = os.path.basename(source_path)
    
    # Create a unique filename if needed
    dest_path = dest_dir / dest_filename
    if dest_path.exists():
        name, ext = os.path.splitext(dest_filename)
        timestamp = os.path.getmtime(source_path)
        dest_filename = f"{name}_{int(timestamp)}{ext}"
        dest_path = dest_dir / dest_filename
    
    # Calculate file hash for integrity verification
    file_hash = calculate_file_hash(source_path)
    
    # Get file metadata
    try:
        file_size = os.path.getsize(source_path)
        file_type = get_mime_type(source_path)
        
        # Copy file using temp file for atomicity
        with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False) as tmp_file:
            tmp_path = tmp_file.name
            try:
                shutil.copyfile(source_path, tmp_path)
                
                # Verify copied file hash
                copied_hash = calculate_file_hash(tmp_path)
                if copied_hash != file_hash:
                    raise FileOperationError(
                        f"File integrity check failed after copy",
                        file_path=source_path,
                        operation="file_copy",
                        error_code="E113",
                        details={"source_hash": file_hash, "dest_hash": copied_hash}
                    )
                
                # Rename temp file to final destination
                os.replace(tmp_path, dest_path)
            except Exception as e:
                # Delete temp file if it exists
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    pass
                
                # Re-raise the original error
                raise FileOperationError(
                    f"Failed to copy file: {str(e)}",
                    file_path=source_path,
                    operation="file_copy",
                    error_code="E114",
                    details={"error": str(e), "traceback": traceback.format_exc()}
                )
    except FileOperationError:
        # Re-raise FileOperationError as is
        raise
    except Exception as e:
        raise FileOperationError(
            f"Failed to process file: {str(e)}",
            file_path=source_path,
            operation="file_copy",
            error_code="E115",
            details={"error": str(e), "traceback": traceback.format_exc()}
        )
    
    # Return metadata
    metadata = {
        "file_path": dest_filename,  # Relative path for storage
        "file_name": os.path.basename(source_path),
        "file_type": file_type,
        "file_size": file_size,
        "file_hash": file_hash
    }
    
    return dest_path, metadata

def calculate_file_hash(file_path: str, algorithm='sha256') -> str:
    """
    Calculate file hash for integrity checking.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use
        
    Returns:
        Hexadecimal hash digest
    """
    try:
        hasher = getattr(hashlib, algorithm)()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        raise FileOperationError(
            f"Failed to calculate file hash: {str(e)}",
            file_path=file_path,
            operation="hash_calculation",
            error_code="E116",
            details={"error": str(e), "algorithm": algorithm}
        )

def generate_text_preview(file_path: str, max_length: int = 500) -> Optional[str]:
    """
    Generate a text preview for text-based files.
    
    Args:
        file_path: Path to the file
        max_length: Maximum preview length in characters
        
    Returns:
        Text preview or None if file is not text-based
    """
    try:
        mime_type = get_mime_type(file_path)
        
        # Check if this is a text-based file
        if not mime_type.startswith('text/') and not mime_type in [
            'application/json', 
            'application/javascript',
            'application/xml'
        ]:
            return None
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read(max_length + 1)
        
        # Truncate if needed
        if len(content) > max_length:
            content = content[:max_length] + '...'
            
        return content
    except UnicodeDecodeError:
        # File is not valid text despite mime type
        return None
    except Exception as e:
        logger.warning(f"Failed to generate text preview for {file_path}: {str(e)}")
        return None

def safe_delete_file(file_path: Path) -> bool:
    """
    Safely delete a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if file was deleted, False if it doesn't exist
        
    Raises:
        FileOperationError: If deletion fails
    """
    try:
        if not file_path.exists():
            return False
        
        file_path.unlink()
        return True
    except Exception as e:
        raise FileOperationError(
            f"Failed to delete file: {str(e)}",
            file_path=str(file_path),
            operation="file_delete",
            error_code="E117",
            details={"error": str(e)}
        )

def get_attachment_dir(config=None) -> Path:
    """
    Get the attachments directory.
    
    Args:
        config: Optional configuration dict
        
    Returns:
        Path to attachments directory
    """
    config = config or load_config()
    project_root = get_project_root()
    attachments_dir = project_root / config['paths'].get('evidence_attachments', 'data/evidence/attachments')
    
    # Ensure directory exists
    os.makedirs(attachments_dir, exist_ok=True)
    
    return attachments_dir