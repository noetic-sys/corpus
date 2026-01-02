import json
from typing import Any, Optional, List
import redis.asyncio as redis

from common.core.config import settings
from .interface import CacheInterface
from common.core.otel_axiom_exporter import (
    get_logger,
    trace_span,
    create_span_with_context,
)

logger = get_logger(__name__)


class RedisCache(CacheInterface):
    """Redis-based cache implementation with production-safe pattern matching."""

    def __init__(self):
        self.host = settings.redis_host
        self.port = settings.redis_port
        self.password = settings.redis_password
        self.db = settings.redis_db
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._index_prefix = "cache_index:"

    @trace_span
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
            logger.info("Redis cache provider connected")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis cache: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis cache provider disconnected")

    @trace_span
    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is active."""
        if self._connected:
            return  # Short circuit - already connected
        await self.connect()

    def _get_index_key(self, pattern: str) -> str:
        """Get the index key for a given pattern."""
        # Convert pattern like "ai_model:*" to "ai_model" for indexing
        base_pattern = pattern.rstrip("*").rstrip(":")
        return f"{self._index_prefix}{base_pattern}"

    def _get_pattern_base(self, key: str) -> str:
        """Extract the base pattern from a cache key for indexing."""
        # For key "ai_model:get:123", return "ai_model"
        parts = key.split(":")
        return parts[0] if parts else key

    async def _add_to_index(self, key: str) -> None:
        """Add a key to its pattern index."""
        try:
            base_pattern = self._get_pattern_base(key)
            index_key = f"{self._index_prefix}{base_pattern}"
            await self._client.sadd(index_key, key)
        except Exception as e:
            logger.warning(f"Failed to add key {key} to index: {e}")

    async def _remove_from_index(self, key: str) -> None:
        """Remove a key from its pattern index."""
        try:
            base_pattern = self._get_pattern_base(key)
            index_key = f"{self._index_prefix}{base_pattern}"
            await self._client.srem(index_key, key)
        except Exception as e:
            logger.warning(f"Failed to remove key {key} from index: {e}")

    @trace_span
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        await self._ensure_connected()

        try:
            value = await self._client.get(key)
            if value is None:
                return None

            # Deserialize JSON
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize cached value for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None

    @trace_span
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        await self._ensure_connected()

        with create_span_with_context("set_value"):
            try:
                # Serialize to JSON
                serialized_value = json.dumps(value, default=str)

                # Set the value with TTL
                if ttl:
                    success = await self._client.setex(key, ttl, serialized_value)
                else:
                    success = await self._client.set(key, serialized_value)

                if success:
                    # Add to index for pattern matching
                    with create_span_with_context("set_index"):
                        await self._add_to_index(key)
                        logger.debug(f"Cached key {key} with TTL {ttl}")
                        return True
                return False

            except Exception as e:
                logger.error(f"Error setting cache key {key}: {e}")
                return False

    @trace_span
    async def delete(self, key: str) -> bool:
        """Delete a specific key from cache."""
        await self._ensure_connected()

        try:
            deleted = await self._client.delete(key)
            if deleted:
                # Remove from index
                await self._remove_from_index(key)
                logger.debug(f"Deleted cache key {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
            return False

    @trace_span
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern using index-based approach."""
        await self._ensure_connected()

        try:
            # Get keys from index instead of using KEYS command
            keys = await self.get_keys(pattern)

            if not keys:
                return 0

            # Delete all matching keys
            deleted_count = await self._client.delete(*keys)

            # Remove from indices
            for key in keys:
                await self._remove_from_index(key)

            logger.info(
                f"Deleted {deleted_count} cache keys matching pattern {pattern}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting cache pattern {pattern}: {e}")
            return 0

    @trace_span
    async def clear(self) -> bool:
        """Clear all cached data."""
        await self._ensure_connected()

        try:
            # Clear all cache data and indices
            await self._client.flushdb()
            logger.info("Cleared all cache data")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    @trace_span
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        await self._ensure_connected()

        try:
            exists = await self._client.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Error checking if cache key {key} exists: {e}")
            return False

    @trace_span
    async def get_keys(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern using index-based approach."""
        await self._ensure_connected()

        try:
            # Convert pattern to index lookup
            if pattern.endswith("*"):
                # For patterns like "ai_model:*", get from index
                base_pattern = pattern.rstrip("*").rstrip(":")
                index_key = f"{self._index_prefix}{base_pattern}"
                keys = await self._client.smembers(index_key)

                # Filter keys that still exist (handle expired keys)
                existing_keys = []
                if keys:
                    # Check which keys still exist
                    pipeline = self._client.pipeline()
                    for key in keys:
                        pipeline.exists(key)
                    results = await pipeline.execute()

                    # Keep only existing keys and clean up index
                    for key, exists in zip(keys, results):
                        if exists:
                            existing_keys.append(key)
                        else:
                            # Remove expired key from index
                            await self._remove_from_index(key)

                return existing_keys
            else:
                # Exact key match
                if await self.exists(pattern):
                    return [pattern]
                return []

        except Exception as e:
            logger.error(f"Error getting cache keys for pattern {pattern}: {e}")
            return []
