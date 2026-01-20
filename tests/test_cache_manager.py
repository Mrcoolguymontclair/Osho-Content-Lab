"""
Unit tests for cache_manager module
"""

import pytest
import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_manager import Cache, CacheManager


class TestCache:
    """Test cache functionality."""

    def test_cache_set_and_get(self):
        """Test basic cache operations."""
        cache = Cache(name='test', default_ttl=60)
        cache.set('key1', 'value1')
        assert cache.get('key1') == 'value1'

    def test_cache_get_nonexistent_returns_default(self):
        """Test getting nonexistent key returns default."""
        cache = Cache(name='test', default_ttl=60)
        assert cache.get('nonexistent', default='default') == 'default'
        assert cache.get('nonexistent') is None

    def test_cache_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = Cache(name='test', default_ttl=1)  # 1 second TTL
        cache.set('key1', 'value1')

        # Should exist immediately
        assert cache.get('key1') == 'value1'

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        assert cache.get('key1') is None

    def test_cache_size_limit(self):
        """Test that cache respects size limit."""
        cache = Cache(name='test', default_ttl=60, max_size=3)

        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.set('key3', 'value3')
        assert len(cache) == 3

        # Adding 4th should evict oldest
        cache.set('key4', 'value4')
        assert len(cache) == 3
        assert cache.get('key1') is None  # Oldest evicted
        assert cache.get('key4') == 'value4'  # Newest exists

    def test_cache_delete(self):
        """Test deleting cache entries."""
        cache = Cache(name='test', default_ttl=60)
        cache.set('key1', 'value1')

        assert cache.delete('key1') is True
        assert cache.get('key1') is None
        assert cache.delete('nonexistent') is False

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = Cache(name='test', default_ttl=60)
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        cache.clear()
        assert len(cache) == 0
        assert cache.get('key1') is None

    def test_cache_cleanup_expired(self):
        """Test cleaning up expired entries."""
        cache = Cache(name='test', default_ttl=1)
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        time.sleep(1.5)

        removed = cache.cleanup_expired()
        assert removed == 2
        assert len(cache) == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = Cache(name='test', default_ttl=60)

        cache.set('key1', 'value1')
        cache.get('key1')  # Hit
        cache.get('nonexistent')  # Miss

        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1

    def test_cache_contains(self):
        """Test __contains__ magic method."""
        cache = Cache(name='test', default_ttl=60)
        cache.set('key1', 'value1')

        assert 'key1' in cache
        assert 'nonexistent' not in cache


class TestCacheManager:
    """Test cache manager."""

    def test_cache_manager_singleton(self):
        """Test that CacheManager is a singleton."""
        manager1 = CacheManager()
        manager2 = CacheManager()
        assert manager1 is manager2

    def test_get_cache_creates_cache(self):
        """Test getting cache creates it if not exists."""
        manager = CacheManager()
        cache = manager.get_cache('test_cache')
        assert cache is not None
        assert cache.name == 'test_cache'

    def test_get_cache_returns_same_instance(self):
        """Test getting same cache returns same instance."""
        manager = CacheManager()
        cache1 = manager.get_cache('test_cache')
        cache2 = manager.get_cache('test_cache')
        assert cache1 is cache2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
