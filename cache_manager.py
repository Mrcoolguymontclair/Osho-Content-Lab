"""
Caching Layer for API Responses

Provides in-memory caching with TTL (Time To Live) support.

Features:
- Thread-safe caching
- TTL-based expiration
- Size limits
- Cache statistics
- Multiple cache instances
"""

import time
import threading
from typing import Any, Optional, Callable
from collections import OrderedDict
from functools import wraps
from logger import get_logger
from constants import (
    ANALYTICS_CACHE_TTL,
    TRENDS_CACHE_TTL,
    CHANNEL_INFO_CACHE_TTL,
    MAX_CACHE_SIZE
)

logger = get_logger(__name__)


class CacheEntry:
    """Represents a single cache entry with metadata."""

    def __init__(self, value: Any, ttl: int):
        """
        Initialize cache entry.

        Args:
            value: Cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() - self.created_at > self.ttl

    def access(self) -> Any:
        """Access entry and update stats."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class Cache:
    """
    Thread-safe cache with TTL support.

    Uses LRU (Least Recently Used) eviction when size limit is reached.
    """

    def __init__(
        self,
        name: str = "default",
        default_ttl: int = 3600,
        max_size: int = MAX_CACHE_SIZE
    ):
        """
        Initialize cache.

        Args:
            name: Cache name for logging
            default_ttl: Default TTL in seconds
            max_size: Maximum number of entries
        """
        self.name = name
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                return default

            if entry.is_expired():
                self._stats['expirations'] += 1
                del self._cache[key]
                return default

            self._stats['hits'] += 1
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry.access()

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        with self._lock:
            ttl = ttl or self.default_ttl
            entry = CacheEntry(value, ttl)

            # Remove old entry if exists
            if key in self._cache:
                del self._cache[key]

            # Add new entry
            self._cache[key] = entry

            # Evict oldest if over size limit
            if len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats['evictions'] += 1

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self):
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            logger.info(f"Cache '{self.name}' cleared")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats['expirations'] += 1

            if expired_keys:
                logger.debug(
                    f"Cache '{self.name}': Removed {len(expired_keys)} expired entries"
                )

            return len(expired_keys)

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (
                self._stats['hits'] / total_requests
                if total_requests > 0 else 0
            )

            return {
                'name': self.name,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': hit_rate,
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations']
            }

    def __len__(self) -> int:
        """Get number of entries in cache."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None


class CacheManager:
    """
    Manages multiple named caches.

    Provides factory methods for common cache types.
    """

    _instance = None
    _lock = threading.Lock()
    _caches = {}

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance

    def get_cache(
        self,
        name: str,
        default_ttl: Optional[int] = None,
        max_size: Optional[int] = None
    ) -> Cache:
        """
        Get or create named cache.

        Args:
            name: Cache name
            default_ttl: Default TTL for cache
            max_size: Maximum cache size

        Returns:
            Cache instance
        """
        if name not in self._caches:
            self._caches[name] = Cache(
                name=name,
                default_ttl=default_ttl or 3600,
                max_size=max_size or MAX_CACHE_SIZE
            )
        return self._caches[name]

    def get_analytics_cache(self) -> Cache:
        """Get cache for analytics data."""
        return self.get_cache('analytics', default_ttl=ANALYTICS_CACHE_TTL)

    def get_trends_cache(self) -> Cache:
        """Get cache for trends data."""
        return self.get_cache('trends', default_ttl=TRENDS_CACHE_TTL)

    def get_channel_info_cache(self) -> Cache:
        """Get cache for channel info."""
        return self.get_cache('channel_info', default_ttl=CHANNEL_INFO_CACHE_TTL)

    def cleanup_all(self):
        """Clean up expired entries in all caches."""
        total_removed = 0
        for cache in self._caches.values():
            total_removed += cache.cleanup_expired()
        logger.info(f"Cleaned up {total_removed} expired entries across all caches")

    def get_all_stats(self) -> dict:
        """
        Get statistics for all caches.

        Returns:
            Dictionary mapping cache names to stats
        """
        return {
            name: cache.get_stats()
            for name, cache in self._caches.items()
        }

    def clear_all(self):
        """Clear all caches."""
        for cache in self._caches.values():
            cache.clear()
        logger.info("All caches cleared")


# Global instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(
    cache_name: str = 'default',
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching function results.

    Args:
        cache_name: Name of cache to use
        ttl: Optional TTL override
        key_func: Optional function to generate cache key from args

    Example:
        @cached(cache_name='analytics', ttl=3600)
        def get_video_stats(video_id):
            # Expensive API call
            return fetch_stats(video_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache
            cache = get_cache_manager().get_cache(cache_name, default_ttl=ttl)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key from function name and arguments
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ':'.join(key_parts)

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return result

            # Call function
            logger.debug(f"Cache miss for {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods to wrapper
        wrapper.cache_clear = lambda: get_cache_manager().get_cache(cache_name).clear()
        wrapper.cache_stats = lambda: get_cache_manager().get_cache(cache_name).get_stats()

        return wrapper
    return decorator


if __name__ == '__main__':
    # Test cache
    print("Testing Cache Manager")
    print("=" * 70)

    # Create cache
    cache = Cache(name='test', default_ttl=2, max_size=3)

    # Test basic operations
    print("\n1. Testing basic operations:")
    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    print(f"   Get key1: {cache.get('key1')}")
    print(f"   Get key2: {cache.get('key2')}")
    print(f"   Get missing: {cache.get('missing', 'default')}")

    # Test TTL
    print("\n2. Testing TTL expiration:")
    print(f"   Before expiration: {cache.get('key1')}")
    time.sleep(3)
    print(f"   After expiration: {cache.get('key1', 'expired')}")

    # Test size limit
    print("\n3. Testing size limit:")
    cache.set('a', 1)
    cache.set('b', 2)
    cache.set('c', 3)
    print(f"   Cache size: {len(cache)}")
    cache.set('d', 4)  # Should evict oldest
    print(f"   After eviction: {len(cache)}")

    # Test decorator
    print("\n4. Testing cached decorator:")

    @cached(cache_name='test_decorator', ttl=5)
    def expensive_function(x):
        print(f"   Computing {x}...")
        time.sleep(0.1)
        return x * 2

    result1 = expensive_function(5)  # Will compute
    result2 = expensive_function(5)  # Will use cache
    print(f"   Result 1: {result1}")
    print(f"   Result 2: {result2}")

    # Test stats
    print("\n5. Cache statistics:")
    stats = cache.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n[OK] Cache manager test completed")
