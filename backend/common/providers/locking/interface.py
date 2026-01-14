import asyncio
import time
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

    async def acquire_lock_with_retry(
        self,
        resource_key: str,
        lock_ttl_seconds: int = 30,
        acquire_timeout_seconds: float = 5.0,
        retry_interval_ms: int = 50,
    ) -> Optional[str]:
        """
        Acquire a distributed lock with retry logic.

        Retries acquisition until timeout is exceeded.

        Args:
            resource_key: The resource to lock
            lock_ttl_seconds: Lock expiration time (TTL) in seconds
            acquire_timeout_seconds: Max time to wait for lock acquisition
            retry_interval_ms: Milliseconds between retry attempts

        Returns:
            Lock token if acquired, None if timeout exceeded
        """
        end_time = time.time() + acquire_timeout_seconds
        while time.time() < end_time:
            token = await self.acquire_lock(resource_key, lock_ttl_seconds)
            if token:
                return token
            await asyncio.sleep(retry_interval_ms / 1000)
        return None
