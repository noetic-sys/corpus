from abc import ABC, abstractmethod
from typing import Optional


class DistributedLockInterface(ABC):
    """Interface for distributed lock providers."""

    @abstractmethod
    async def acquire_lock(
        self, resource_key: str, timeout_seconds: int = 30
    ) -> Optional[str]:
        """
        Acquire a distributed lock for a resource.

        Args:
            resource_key: The resource to lock (e.g., "matrix_cell:123")
            timeout_seconds: Lock expiration time in seconds

        Returns:
            Lock token if acquired, None otherwise
        """
        pass

    @abstractmethod
    async def release_lock(self, resource_key: str, lock_token: str) -> bool:
        """
        Release a distributed lock.

        Args:
            resource_key: The locked resource
            lock_token: The token received when acquiring the lock

        Returns:
            True if released, False if token doesn't match or lock doesn't exist
        """
        pass

    @abstractmethod
    async def extend_lock(
        self, resource_key: str, lock_token: str, additional_seconds: int
    ) -> bool:
        """
        Extend the expiration time of a lock.

        Args:
            resource_key: The locked resource
            lock_token: The token received when acquiring the lock
            additional_seconds: Additional seconds to add to expiration

        Returns:
            True if extended, False if token doesn't match or lock doesn't exist
        """
        pass

    @abstractmethod
    async def is_locked(self, resource_key: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_key: The resource to check

        Returns:
            True if locked, False otherwise
        """
        pass
