"""
Compression Manager for Evidence Attachments.

This module provides compression capabilities for evidence attachments,
optimizing storage space while preserving data integrity.
"""
import os
import io
import logging
import gzip
import zlib
import bz2
import lzma
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple, BinaryIO
import mimetypes

# Configure module logger
logger = logging.getLogger(__name__)


class CompressionManager:
    """
    Manages compression for evidence attachments.
    
    This class provides compression and decompression capabilities for
    attachment files, optimizing storage space based on file types.
    """
    
    # Compression levels
    NONE = 0      # No compression
    LIGHT = 1     # Light compression
    MEDIUM = 6    # Medium compression (default)
    HEAVY = 9     # Heavy compression
    
    # Compression algorithms
    GZIP = "gzip"
    ZLIB = "zlib"
    BZ2 = "bz2"
    LZMA = "lzma"
    
    def __init__(self):
        """Initialize the compression manager."""
        # List of MIME types that should not be compressed
        self.incompressible_types = [
            # Already compressed formats
            "image/jpeg", "image/jpg", "image/png", "image/gif", 
            "application/zip", "application/gzip", "application/x-bzip2",
            "application/x-rar-compressed", "application/x-7z-compressed",
            "application/pdf", "audio/mp3", "audio/mp4", "video/mp4", 
            "video/mpeg", "video/quicktime", "application/octet-stream"
        ]
        
        # Map of file extensions to compression methods
        self.extension_map = {
            # Default text formats - good compression
            ".txt": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".csv": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".xml": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".json": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".html": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".md": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".log": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".sql": {"algorithm": self.GZIP, "level": self.MEDIUM},
            
            # Code files - good compression
            ".py": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".js": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".java": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".c": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".cpp": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".h": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".cs": {"algorithm": self.GZIP, "level": self.MEDIUM},
            ".php": {"algorithm": self.GZIP, "level": self.MEDIUM},
            
            # Document formats - moderate compression
            ".doc": {"algorithm": self.BZ2, "level": self.LIGHT},
            ".docx": {"algorithm": self.ZLIB, "level": self.LIGHT},
            ".xls": {"algorithm": self.BZ2, "level": self.LIGHT},
            ".xlsx": {"algorithm": self.ZLIB, "level": self.LIGHT},
            ".ppt": {"algorithm": self.BZ2, "level": self.LIGHT},
            ".pptx": {"algorithm": self.ZLIB, "level": self.LIGHT},
            
            # Raw data or binary - potentially high compression
            ".dat": {"algorithm": self.LZMA, "level": self.HEAVY},
            ".bin": {"algorithm": self.LZMA, "level": self.HEAVY},
        }
        
        # Default compression settings
        self.default_algorithm = self.GZIP
        self.default_level = self.MEDIUM
        
        logger.info("Initialized compression manager")
    
    def _should_compress(self, file_path: Union[str, Path], mime_type: Optional[str] = None) -> bool:
        """
        Determine if a file should be compressed.
        
        Args:
            file_path: Path to the file
            mime_type: Optional MIME type of the file
            
        Returns:
            True if the file should be compressed, False otherwise
        """
        file_path = Path(file_path)
        
        # Get MIME type if not provided
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(str(file_path))
        
        # Skip compression for incompressible types
        if mime_type and mime_type in self.incompressible_types:
            return False
        
        # Check file size - don't compress very small files
        if file_path.exists() and file_path.stat().st_size < 1024:  # 1KB
            return False
        
        return True
    
    def _get_compression_settings(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get the compression settings for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with compression settings
        """
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        # Use extension-specific settings if available
        if extension in self.extension_map:
            return self.extension_map[extension]
        
        # Otherwise use default settings
        return {
            "algorithm": self.default_algorithm,
            "level": self.default_level
        }
    
    def compress_file(self, input_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Tuple[Path, Dict[str, Any]]:
        """
        Compress a file.
        
        Args:
            input_path: Path to the file to compress
            output_path: Optional path to store the compressed file
            
        Returns:
            Tuple of (output_path, compression_info)
            
        Raises:
            IOError: If compression fails
        """
        input_path = Path(input_path)
        
        # Determine output path if not provided
        if output_path is None:
            output_path = input_path.with_suffix(f"{input_path.suffix}.gz")
        else:
            output_path = Path(output_path)
        
        # Check if we should compress this file
        if not self._should_compress(input_path):
            # Just copy the file if we shouldn't compress it
            with open(input_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    f_out.write(f_in.read())
                    
            return output_path, {
                "compressed": False,
                "original_size": input_path.stat().st_size,
                "compressed_size": output_path.stat().st_size,
                "ratio": 1.0,
                "algorithm": "none"
            }
        
        # Get compression settings
        settings = self._get_compression_settings(input_path)
        algorithm = settings["algorithm"]
        level = settings["level"]
        
        # Get original file size
        original_size = input_path.stat().st_size
        
        try:
            start_time = time.time()
            
            # Compress based on algorithm
            if algorithm == self.GZIP:
                with open(input_path, 'rb') as f_in:
                    with gzip.open(output_path, 'wb', compresslevel=level) as f_out:
                        f_out.write(f_in.read())
            
            elif algorithm == self.ZLIB:
                with open(input_path, 'rb') as f_in:
                    data = f_in.read()
                    compressed = zlib.compress(data, level)
                    with open(output_path, 'wb') as f_out:
                        f_out.write(compressed)
            
            elif algorithm == self.BZ2:
                with open(input_path, 'rb') as f_in:
                    with bz2.open(output_path, 'wb', compresslevel=level) as f_out:
                        f_out.write(f_in.read())
            
            elif algorithm == self.LZMA:
                with open(input_path, 'rb') as f_in:
                    with lzma.open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            else:
                raise ValueError(f"Unknown compression algorithm: {algorithm}")
            
            # Calculate compression time and ratio
            compression_time = time.time() - start_time
            compressed_size = output_path.stat().st_size
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            logger.info(f"Compressed {input_path.name} with {algorithm}: "
                       f"{original_size} -> {compressed_size} bytes "
                       f"(ratio: {compression_ratio:.2f}x, time: {compression_time:.3f}s)")
            
            return output_path, {
                "compressed": True,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "ratio": compression_ratio,
                "algorithm": algorithm,
                "level": level,
                "time": compression_time
            }
        
        except Exception as e:
            logger.error(f"Compression failed for {input_path}: {str(e)}")
            # In case of failure, try to clean up the output file
            if output_path.exists():
                os.remove(output_path)
            raise IOError(f"Failed to compress {input_path}: {str(e)}")
    
    def decompress_file(self, input_path: Union[str, Path], output_path: Union[str, Path], algorithm: str) -> Path:
        """
        Decompress a file.
        
        Args:
            input_path: Path to the compressed file
            output_path: Path to store the decompressed file
            algorithm: Compression algorithm used
            
        Returns:
            Path to the decompressed file
            
        Raises:
            IOError: If decompression fails
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        try:
            # Decompress based on algorithm
            if algorithm == self.GZIP:
                with gzip.open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            elif algorithm == self.ZLIB:
                with open(input_path, 'rb') as f_in:
                    data = f_in.read()
                    decompressed = zlib.decompress(data)
                    with open(output_path, 'wb') as f_out:
                        f_out.write(decompressed)
            
            elif algorithm == self.BZ2:
                with bz2.open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            elif algorithm == self.LZMA:
                with lzma.open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            elif algorithm == "none":
                # No compression, just copy
                with open(input_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        f_out.write(f_in.read())
            
            else:
                raise ValueError(f"Unknown compression algorithm: {algorithm}")
            
            logger.info(f"Decompressed {input_path.name} with {algorithm} to {output_path.name}")
            return output_path
        
        except Exception as e:
            logger.error(f"Decompression failed for {input_path}: {str(e)}")
            # In case of failure, try to clean up the output file
            if output_path.exists():
                os.remove(output_path)
            raise IOError(f"Failed to decompress {input_path}: {str(e)}")
    
    def compress_data(self, data: bytes, algorithm: str = GZIP, level: int = MEDIUM) -> Tuple[bytes, Dict[str, Any]]:
        """
        Compress binary data.
        
        Args:
            data: Binary data to compress
            algorithm: Compression algorithm to use
            level: Compression level
            
        Returns:
            Tuple of (compressed_data, compression_info)
        """
        original_size = len(data)
        
        try:
            start_time = time.time()
            
            # Compress based on algorithm
            if algorithm == self.GZIP:
                compressed = gzip.compress(data, compresslevel=level)
            elif algorithm == self.ZLIB:
                compressed = zlib.compress(data, level)
            elif algorithm == self.BZ2:
                compressed = bz2.compress(data, compresslevel=level)
            elif algorithm == self.LZMA:
                compressed = lzma.compress(data)
            else:
                raise ValueError(f"Unknown compression algorithm: {algorithm}")
            
            # Calculate compression time and ratio
            compression_time = time.time() - start_time
            compressed_size = len(compressed)
            compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
            
            return compressed, {
                "compressed": True,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "ratio": compression_ratio,
                "algorithm": algorithm,
                "level": level,
                "time": compression_time
            }
        
        except Exception as e:
            logger.error(f"Data compression failed: {str(e)}")
            return data, {
                "compressed": False,
                "original_size": original_size,
                "compressed_size": original_size,
                "ratio": 1.0,
                "error": str(e)
            }
    
    def decompress_data(self, data: bytes, algorithm: str) -> bytes:
        """
        Decompress binary data.
        
        Args:
            data: Compressed binary data
            algorithm: Compression algorithm used
            
        Returns:
            Decompressed data
        """
        try:
            # Decompress based on algorithm
            if algorithm == self.GZIP:
                return gzip.decompress(data)
            elif algorithm == self.ZLIB:
                return zlib.decompress(data)
            elif algorithm == self.BZ2:
                return bz2.decompress(data)
            elif algorithm == self.LZMA:
                return lzma.decompress(data)
            elif algorithm == "none":
                return data
            else:
                raise ValueError(f"Unknown compression algorithm: {algorithm}")
        
        except Exception as e:
            logger.error(f"Data decompression failed: {str(e)}")
            raise IOError(f"Failed to decompress data: {str(e)}")
