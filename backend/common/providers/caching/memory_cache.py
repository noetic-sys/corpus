import time
import fnmatch
from typing import Any, Optional, List, Dict
from dataclasses import dataclass

from .interface import CacheInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached entry with expiration."""

    value: Any
    expires_at: Optional[float] = None

    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MemoryCache(CacheInterface):
    """In-memory cache implementation."""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        logger.info("Memory cache provider initialized")

    async def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if entry.expires_at and entry.expires_at <= current_time
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        entry = self._cache.get(key)

        if entry is None:
            return None

        if entry.is_expired():
            del self._cache[key]
            return None

        return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        try:
            expires_at = None
            if ttl:
                expires_at = time.time() + ttl

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            logger.debug(f"Cached key {key} with TTL {ttl}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a specific key from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted cache key {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            # Clean up expired entries first
            await self._cleanup_expired()

            # Find matching keys
            matching_keys = []
            for key in self._cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    matching_keys.append(key)

            # Delete matching keys
            for key in matching_keys:
                del self._cache[key]

            logger.info(
                f"Deleted {len(matching_keys)} cache keys matching pattern {pattern}"
            )
            return len(matching_keys)

        except Exception as e:
            logger.error(f"Error deleting cache pattern {pattern}: {e}")
            return 0

    async def clear(self) -> bool:
        """Clear all cached data."""
        try:
            self._cache.clear()
            logger.info("Cleared all cache data")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        entry = self._cache.get(key)
        if entry is None:
            return False

        if entry.is_expired():
            del self._cache[key]
            return False

        return True

    async def get_keys(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern."""
        try:
            # Clean up expired entries first
            await self._cleanup_expired()

            matching_keys = []
            for key in self._cache.keys():
                if fnmatch.fnmatch(key, pattern):
                    matching_keys.append(key)

            return matching_keys
        except Exception as e:
            logger.error(f"Error getting cache keys for pattern {pattern}: {e}")
            return []
