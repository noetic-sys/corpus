from abc import ABC, abstractmethod
from typing import Any, Optional, List


class CacheInterface(ABC):
    """Interface for cache providers."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: The cache key

        Returns:
            The cached value if exists, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds

        Returns:
            True if set successfully, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a specific key from cache.

        Args:
            key: The cache key to delete

        Returns:
            True if deleted, False if key didn't exist
        """
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: The pattern to match (e.g., "ai_model:*")

        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all cached data.

        Returns:
            True if cleared successfully
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: The cache key to check

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def get_keys(self, pattern: str) -> List[str]:
        """
        Get all keys matching a pattern.

        Args:
            pattern: The pattern to match (e.g., "ai_model:*")

        Returns:
            List of matching keys
        """
        pass
