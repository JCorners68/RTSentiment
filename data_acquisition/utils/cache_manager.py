"""
Cache manager for deduplication and caching data.
"""
import os
import json
import logging
import hashlib
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DeduplicationCache:
    """
    Deduplication cache for preventing duplicate content from being processed.
    Uses a rolling window approach to keep track of seen content.
    """
    
    def __init__(self, cache_file: str, max_age_days: int = 30):
        """
        Initialize deduplication cache.
        
        Args:
            cache_file: Path to the cache file
            max_age_days: Maximum age of cached items in days
        """
        self.cache_file = cache_file
        self.max_age_days = max_age_days
        self.cache = {
            "items": {},
            "last_cleanup": time.time()
        }
        self.loaded = False
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        # Try to load existing cache
        self._load_cache()
    
    def _load_cache(self) -> bool:
        """
        Load existing cache from file.
        
        Returns:
            Success indicator
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache.get('items', {}))} items from cache {self.cache_file}")
                self.loaded = True
                return True
            else:
                logger.info(f"No existing cache file found at {self.cache_file}")
                self.loaded = True
                return False
        except Exception as e:
            logger.error(f"Error loading cache from {self.cache_file}: {e}")
            # Initialize empty cache
            self.cache = {
                "items": {},
                "last_cleanup": time.time()
            }
            self.loaded = True
            return False
    
    def _save_cache(self) -> bool:
        """
        Save cache to file.
        
        Returns:
            Success indicator
        """
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
            logger.debug(f"Saved {len(self.cache.get('items', {}))} items to cache {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache to {self.cache_file}: {e}")
            return False
    
    def _cleanup_cache(self):
        """Clean up old cache entries."""
        # Only cleanup every 24 hours
        if time.time() - self.cache.get("last_cleanup", 0) < 86400:
            return
            
        try:
            items = self.cache.get("items", {})
            now = time.time()
            cutoff = now - (self.max_age_days * 86400)
            
            # Count before cleanup
            before_count = len(items)
            
            # Remove old items
            self.cache["items"] = {
                k: v for k, v in items.items() 
                if v.get("timestamp", 0) > cutoff
            }
            
            # Update cleanup timestamp
            self.cache["last_cleanup"] = now
            
            # Save changes
            self._save_cache()
            
            # Log cleanup results
            after_count = len(self.cache.get("items", {}))
            removed = before_count - after_count
            logger.info(f"Cache cleanup removed {removed} old entries, keeping {after_count} entries")
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    def _get_hash(self, content: str) -> str:
        """
        Generate hash for content.
        
        Args:
            content: Content to hash
            
        Returns:
            MD5 hash of content
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def has_seen(self, item: Dict[str, Any]) -> bool:
        """
        Check if an item has been seen before.
        
        Args:
            item: Item to check
            
        Returns:
            True if item has been seen before, False otherwise
        """
        # Ensure cache is loaded
        if not self.loaded:
            self._load_cache()
        
        # Generate a hash based on relevant fields
        content = f"{item.get('title', '')}{item.get('url', '')}"
        
        # If content is empty, use a fallback approach
        if not content.strip():
            content = str(item)
        
        item_hash = self._get_hash(content)
        
        # Check if item exists in cache
        return item_hash in self.cache.get("items", {})
    
    def mark_seen(self, item: Dict[str, Any]) -> bool:
        """
        Mark an item as seen.
        
        Args:
            item: Item to mark as seen
            
        Returns:
            True if successful, False otherwise
        """
        # Ensure cache is loaded
        if not self.loaded:
            self._load_cache()
        
        # Generate a hash based on relevant fields
        content = f"{item.get('title', '')}{item.get('url', '')}"
        
        # If content is empty, use a fallback approach
        if not content.strip():
            content = str(item)
        
        item_hash = self._get_hash(content)
        
        # Add to cache with timestamp
        self.cache.setdefault("items", {})[item_hash] = {
            "timestamp": time.time(),
            "title": item.get("title", "")[:100]  # Store truncated title for debugging
        }
        
        # Periodically clean up old entries
        self._cleanup_cache()
        
        # Save cache
        return self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "total_items": len(self.cache.get("items", {})),
            "last_cleanup": datetime.fromtimestamp(self.cache.get("last_cleanup", 0)).isoformat(),
            "max_age_days": self.max_age_days
        }