"""
Query Cache Implementation for Evidence Storage System.

This module provides caching mechanisms for frequent queries to improve performance
in the Evidence Management System.
"""
import time
import logging
import hashlib
import json
from typing import Dict, List, Optional, Union, Any, Tuple, Callable
import threading
from datetime import datetime, timedelta
from functools import lru_cache

# Configure module logger
logger = logging.getLogger(__name__)


class QueryCacheItem:
    """Represents a single cached query result."""
    
    def __init__(self, 
                 query_params: Dict[str, Any], 
                 result: Any, 
                 ttl_seconds: int = 300):
        """
        Initialize a cache item.
        
        Args:
            query_params: The query parameters used to generate the result
            result: The result of the query
            ttl_seconds: Time-to-live in seconds before the cache item expires
        """
        self.query_params = query_params
        self.result = result
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if the cache item has expired."""
        return datetime.now() > self.expires_at
    
    def access(self) -> None:
        """Record an access to this cache item."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class QueryCache:
    """
    Cache manager for evidence queries.
    
    This class provides a thread-safe caching mechanism for evidence queries
    to improve performance for frequent operations.
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        """
        Initialize the query cache.
        
        Args:
            max_size: Maximum number of items to store in the cache
            default_ttl: Default time-to-live in seconds for cache items
        """
        self.cache: Dict[str, QueryCacheItem] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache_hits = 0
        self.cache_misses = 0
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        
        # Statistics
        self.created_at = datetime.now()
        self.last_cleanup = self.created_at
        
        logger.info(f"Initialized query cache with max_size={max_size}, default_ttl={default_ttl}s")
    
    def _generate_key(self, query_params: Dict[str, Any]) -> str:
        """
        Generate a unique key for the query parameters.
        
        Args:
            query_params: Query parameters to hash
            
        Returns:
            Unique string key
        """
        # Sort to ensure consistent ordering
        serialized = json.dumps(query_params, sort_keys=True)
        return hashlib.md5(serialized.encode('utf-8')).hexdigest()
    
    def get(self, query_params: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Get a result from the cache.
        
        Args:
            query_params: Query parameters to look up
            
        Returns:
            Tuple of (cache_hit, result)
        """
        key = self._generate_key(query_params)
        
        with self.lock:
            if key in self.cache:
                cache_item = self.cache[key]
                
                # Check if item has expired
                if cache_item.is_expired():
                    logger.debug(f"Cache miss (expired): {key}")
                    del self.cache[key]
                    self.cache_misses += 1
                    return False, None
                
                # Record access
                cache_item.access()
                self.cache_hits += 1
                logger.debug(f"Cache hit: {key}")
                return True, cache_item.result
            
            logger.debug(f"Cache miss: {key}")
            self.cache_misses += 1
            return False, None
    
    def set(self, query_params: Dict[str, Any], result: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Store a result in the cache.
        
        Args:
            query_params: Query parameters to store
            result: Result to cache
            ttl_seconds: Optional custom TTL in seconds
        """
        key = self._generate_key(query_params)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        
        with self.lock:
            # Check if we need to make room
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_item()
            
            # Store the result
            self.cache[key] = QueryCacheItem(query_params, result, ttl)
            logger.debug(f"Cached result for {key} with TTL {ttl}s")
    
    def invalidate(self, query_params: Optional[Dict[str, Any]] = None) -> int:
        """
        Invalidate cache entries.
        
        Args:
            query_params: Optional query parameters to invalidate specifically,
                          or None to invalidate all entries
        
        Returns:
            Number of invalidated entries
        """
        with self.lock:
            if query_params is None:
                # Invalidate all
                count = len(self.cache)
                self.cache.clear()
                logger.info(f"Invalidated all {count} cache entries")
                return count
            
            # Invalidate specific entry
            key = self._generate_key(query_params)
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Invalidated cache entry: {key}")
                return 1
            
            return 0
    
    def invalidate_by_prefix(self, prefix: str) -> int:
        """
        Invalidate cache entries that match a prefix.
        
        Args:
            prefix: Prefix to match against query parameter keys
            
        Returns:
            Number of invalidated entries
        """
        with self.lock:
            to_remove = []
            
            for key, item in self.cache.items():
                for param_key in item.query_params.keys():
                    if param_key.startswith(prefix):
                        to_remove.append(key)
                        break
            
            for key in to_remove:
                del self.cache[key]
            
            logger.debug(f"Invalidated {len(to_remove)} cache entries with prefix '{prefix}'")
            return len(to_remove)
    
    def _evict_item(self) -> None:
        """
        Evict an item from the cache based on eviction policy.
        Currently uses a simple LRU (Least Recently Used) strategy.
        """
        if not self.cache:
            return
        
        # Find the least recently accessed item
        lru_key = min(self.cache.items(), key=lambda x: x[1].last_accessed)[0]
        del self.cache[lru_key]
        logger.debug(f"Evicted LRU cache item: {lru_key}")
    
    def cleanup(self) -> int:
        """
        Remove expired items from the cache.
        
        Returns:
            Number of items removed
        """
        with self.lock:
            now = datetime.now()
            expired_keys = [key for key, item in self.cache.items() if item.is_expired()]
            
            for key in expired_keys:
                del self.cache[key]
            
            self.last_cleanup = now
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
            return len(expired_keys)
    
    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self.lock:
            total_requests = self.cache_hits + self.cache_misses
            hit_ratio = self.cache_hits / total_requests if total_requests > 0 else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_ratio": hit_ratio,
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "created_at": self.created_at.isoformat(),
                "uptime_seconds": (datetime.now() - self.created_at).total_seconds(),
                "last_cleanup": self.last_cleanup.isoformat()
            }


# Create a decorator for caching query results
def cached_query(cache: QueryCache, ttl_seconds: Optional[int] = None):
    """
    Decorator for caching query results.
    
    Args:
        cache: QueryCache instance to use
        ttl_seconds: Optional custom TTL in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a query parameters dictionary
            query_params = {
                "func": func.__name__,
                "args": args,
                "kwargs": kwargs
            }
            
            # Try to get from cache
            hit, result = cache.get(query_params)
            if hit:
                return result
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Cache the result
            cache.set(query_params, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator


# Global cache instance for convenience
_global_cache = QueryCache()

def get_global_cache() -> QueryCache:
    """Get the global cache instance."""
    return _global_cache

# Global LRU cache for very frequent but stable queries
@lru_cache(maxsize=128)
def cached_compute_hash(data: str) -> str:
    """
    Example of using Python's built-in LRU cache for simple, frequent operations.
    
    Args:
        data: String data to hash
        
    Returns:
        Hash of the data
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
