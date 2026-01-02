import uuid
from typing import Optional
import redis.asyncio as redis

from common.core.config import settings
from .interface import DistributedLockInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class RedisLock(DistributedLockInterface):
    """Redis-based distributed lock implementation."""

    def __init__(self):
        self.host = settings.redis_host
        self.port = settings.redis_port
        self.password = settings.redis_password
        self.db = settings.redis_db
        self._client: Optional[redis.Redis] = None
        self._lock_prefix = "lock:"
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis lock provider connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis lock provider disconnected")

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        if not self._connected:
            await self.connect()

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
        await self._ensure_connected()

        lock_key = f"{self._lock_prefix}{resource_key}"
        lock_token = str(uuid.uuid4())

        try:
            # Try to acquire lock atomically using SET NX EX
            acquired = await self._client.set(
                lock_key,
                lock_token,
                nx=True,  # Only set if not exists
                ex=timeout_seconds,  # Expiration time
            )

            if acquired:
                logger.info(f"Acquired lock for {resource_key} with token {lock_token}")
                return lock_token
            else:
                logger.debug(
                    f"Failed to acquire lock for {resource_key} - already locked"
                )
                return None
        except Exception as e:
            logger.error(f"Error acquiring lock for {resource_key}: {e}")
            return None

    async def release_lock(self, resource_key: str, lock_token: str) -> bool:
        """
        Release a distributed lock.

        Args:
            resource_key: The locked resource
            lock_token: The token received when acquiring the lock

        Returns:
            True if released, False if token doesn't match or lock doesn't exist
        """
        await self._ensure_connected()

        lock_key = f"{self._lock_prefix}{resource_key}"

        try:
            # Use Lua script for atomic check-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """

            result = await self._client.eval(lua_script, 1, lock_key, lock_token)

            if result:
                logger.info(f"Released lock for {resource_key}")
                return True
            else:
                logger.warning(
                    f"Cannot release lock for {resource_key} - token mismatch or lock expired"
                )
                return False
        except Exception as e:
            logger.error(f"Error releasing lock for {resource_key}: {e}")
            return False

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
        await self._ensure_connected()

        lock_key = f"{self._lock_prefix}{resource_key}"

        try:
            # Use Lua script for atomic check-and-extend
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """

            result = await self._client.eval(
                lua_script, 1, lock_key, lock_token, additional_seconds
            )

            if result:
                logger.info(
                    f"Extended lock for {resource_key} by {additional_seconds} seconds"
                )
                return True
            else:
                logger.warning(
                    f"Cannot extend lock for {resource_key} - token mismatch or lock expired"
                )
                return False
        except Exception as e:
            logger.error(f"Error extending lock for {resource_key}: {e}")
            return False

    async def is_locked(self, resource_key: str) -> bool:
        """
        Check if a resource is currently locked.

        Args:
            resource_key: The resource to check

        Returns:
            True if locked, False otherwise
        """
        await self._ensure_connected()

        lock_key = f"{self._lock_prefix}{resource_key}"

        try:
            exists = await self._client.exists(lock_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Error checking lock for {resource_key}: {e}")
            return False
