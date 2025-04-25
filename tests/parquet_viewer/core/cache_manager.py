"""
Cache management module for the Parquet Query Viewer.

This module provides a caching mechanism for query results to improve performance.
"""
import time
import logging
from typing import Dict, Any, Optional, Callable, Tuple, Union, List

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class CacheManager:
    """
    A cache manager for storing and retrieving query results.
    
    This class provides methods for caching and retrieving query results with
    automatic expiration of cached items.
    
    Attributes:
        enabled (bool): Whether caching is enabled
        ttl (int): Time-to-live for cached items in seconds
        _cache (Dict): Dictionary storing cached items with their timestamps
    """
    
    def __init__(self, enabled: bool = True, ttl: int = 3600):
        """
        Initialize the CacheManager.
        
        Args:
            enabled (bool): Whether caching is enabled
            ttl (int): Time-to-live for cached items in seconds
        """
        self.enabled = enabled
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        
        logger.debug(f"Initialized CacheManager (enabled={enabled}, ttl={ttl}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key (str): The cache key
            
        Returns:
            Optional[Any]: The cached value, or None if not found or expired
        """
        if not self.enabled:
            return None
        
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check if the item has expired
        if time.time() - timestamp > self.ttl:
            # Remove expired item
            del self._cache[key]
            logger.debug(f"Cache item expired: {key}")
            return None
        
        logger.debug(f"Cache hit: {key}")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.
        
        Args:
            key (str): The cache key
            value (Any): The value to cache
        """
        if not self.enabled:
            return
        
        # Make a deep copy of the value if it's a pandas DataFrame or Series
        # to prevent modifications to the cached value
        if isinstance(value, (pd.DataFrame, pd.Series)):
            value = value.copy(deep=True)
        
        self._cache[key] = (value, time.time())
        
        # Clean up the cache if it's getting too large
        if len(self._cache) > 1000:
            self._clean_cache()
        
        logger.debug(f"Cache set: {key}")
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key (str): The cache key
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache delete: {key}")
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        self._cache.clear()
        logger.debug("Cache cleared")
    
    def _clean_cache(self) -> None:
        """
        Clean the cache by removing expired items.
        
        This method is called automatically when the cache gets too large.
        """
        current_time = time.time()
        keys_to_delete = []
        
        # Find expired items
        for key, (_, timestamp) in self._cache.items():
            if current_time - timestamp > self.ttl:
                keys_to_delete.append(key)
        
        # Delete expired items
        for key in keys_to_delete:
            del self._cache[key]
        
        logger.debug(f"Cache cleaned: removed {len(keys_to_delete)} expired items")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.
        
        Returns:
            Dict[str, Any]: Dictionary with cache statistics
        """
        current_time = time.time()
        stats = {
            "enabled": self.enabled,
            "ttl": self.ttl,
            "total_items": len(self._cache),
            "active_items": 0,
            "expired_items": 0,
            "memory_usage_estimate": 0,
            "item_types": {},
            "oldest_item_age": 0,
            "newest_item_age": 0
        }
        
        if not self._cache:
            return stats
        
        # Calculate item statistics
        ages = []
        for key, (value, timestamp) in self._cache.items():
            age = current_time - timestamp
            ages.append(age)
            
            # Count active and expired items
            if age <= self.ttl:
                stats["active_items"] += 1
            else:
                stats["expired_items"] += 1
            
            # Count item types
            value_type = type(value).__name__
            if value_type not in stats["item_types"]:
                stats["item_types"][value_type] = 0
            stats["item_types"][value_type] += 1
            
            # Estimate memory usage
            if isinstance(value, pd.DataFrame):
                stats["memory_usage_estimate"] += value.memory_usage(deep=True).sum()
            elif isinstance(value, pd.Series):
                stats["memory_usage_estimate"] += value.memory_usage(deep=True)
        
        # Calculate age statistics
        if ages:
            stats["oldest_item_age"] = max(ages)
            stats["newest_item_age"] = min(ages)
        
        return stats
    
    def memoize(self, func: Callable) -> Callable:
        """
        Decorator to memoize a function.
        
        Args:
            func (Callable): The function to memoize
            
        Returns:
            Callable: The memoized function
        """
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)
            
            # Generate a cache key from the function name and arguments
            key = f"{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            
            # Try to get the result from the cache
            cached_result = self.get(key)
            if cached_result is not None:
                return cached_result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            self.set(key, result)
            
            return result
        
        return wrapper