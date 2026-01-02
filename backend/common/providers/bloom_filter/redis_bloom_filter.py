from typing import Optional
import redis.asyncio as redis

from common.core.config import settings
from .interface import BloomFilterInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class RedisBloomFilter(BloomFilterInterface):
    """Redis-based bloom filter implementation using RedisBloom module."""

    def __init__(self):
        self.host = settings.redis_host
        self.port = settings.redis_port
        self.password = settings.redis_password
        self.db = settings.redis_db
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._filter_prefix = "bf:"

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
            logger.info("Redis bloom filter provider connected")
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
            logger.info("Redis bloom filter provider disconnected")

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        if self._connected:
            return  # Short circuit - already connected
        await self.connect()

    def _get_filter_key(self, filter_name: str) -> str:
        """Get the Redis key for a bloom filter."""
        return f"{self._filter_prefix}{filter_name}"

    async def _ensure_filter_exists(self, filter_name: str) -> bool:
        """Ensure bloom filter exists, create if it doesn't."""
        await self._ensure_connected()

        filter_key = self._get_filter_key(filter_name)

        try:
            # Check if filter exists
            _ = await self._client.execute_command("BF.EXISTS", filter_key, "test_key")
            return True
        except redis.ResponseError as e:
            if "not found" in str(e).lower():
                # Filter doesn't exist, create it
                try:
                    # Create bloom filter with reasonable defaults:
                    # - Error rate: 0.01 (1%)
                    # - Initial capacity: 100000
                    await self._client.execute_command(
                        "BF.RESERVE", filter_key, "0.01", "100000"
                    )
                    logger.info(f"Created bloom filter: {filter_name}")
                    return True
                except Exception as create_error:
                    logger.error(
                        f"Failed to create bloom filter {filter_name}: {create_error}"
                    )
                    return False
            else:
                logger.error(f"Error checking bloom filter {filter_name}: {e}")
                return False

    async def add(self, filter_name: str, value: str) -> bool:
        """Add a value to the bloom filter."""
        try:
            if not await self._ensure_filter_exists(filter_name):
                logger.warn(f"Bloom filter {filter_name} does not exist")
                return False

            filter_key = self._get_filter_key(filter_name)
            result = await self._client.execute_command("BF.ADD", filter_key, value)

            # BF.ADD returns 1 if item was added, 0 if it already existed
            logger.debug(f"Added '{value}' to bloom filter '{filter_name}': {result}")
            return True
        except Exception as e:
            logger.error(f"Error adding '{value}' to bloom filter '{filter_name}': {e}")
            return False

    async def exists(self, filter_name: str, value: str) -> bool:
        """Check if a value might exist in the bloom filter."""
        try:
            if not await self._ensure_filter_exists(filter_name):
                return False

            filter_key = self._get_filter_key(filter_name)
            result = await self._client.execute_command("BF.EXISTS", filter_key, value)

            # BF.EXISTS returns 1 if item might exist, 0 if it definitely doesn't
            exists = bool(result)
            logger.debug(f"Checked '{value}' in bloom filter '{filter_name}': {exists}")
            return exists
        except Exception as e:
            logger.error(
                f"Error checking '{value}' in bloom filter '{filter_name}': {e}"
            )
            # On error, assume it might exist to be safe
            return True

    async def clear(self, filter_name: str) -> bool:
        """Clear all values from the bloom filter."""
        try:
            await self._ensure_connected()

            filter_key = self._get_filter_key(filter_name)
            await self._client.delete(filter_key)

            logger.info(f"Cleared bloom filter: {filter_name}")
            return True
        except Exception as e:
            logger.error(f"Error clearing bloom filter '{filter_name}': {e}")
            return False

    async def info(self, filter_name: str) -> dict:
        """Get information about the bloom filter."""
        try:
            if not await self._ensure_filter_exists(filter_name):
                return {}

            filter_key = self._get_filter_key(filter_name)
            info_result = await self._client.execute_command("BF.INFO", filter_key)

            # Parse the info result (it comes as a list of key-value pairs)
            info_dict = {}
            for i in range(0, len(info_result), 2):
                key = (
                    info_result[i].decode()
                    if isinstance(info_result[i], bytes)
                    else info_result[i]
                )
                value = info_result[i + 1]
                if isinstance(value, bytes):
                    value = value.decode()
                info_dict[key] = value

            logger.debug(f"Bloom filter info for '{filter_name}': {info_dict}")
            return info_dict
        except Exception as e:
            logger.error(f"Error getting info for bloom filter '{filter_name}': {e}")
            return {}
