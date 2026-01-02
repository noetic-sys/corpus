import pytest
import asyncio
from unittest.mock import patch
import os

from common.providers.locking.redis_lock import RedisLock


@pytest.fixture
async def redis_lock():
    """
    Provide a Redis lock for integration tests.
    Requires Redis to be running (e.g., via docker-compose).
    """
    # Override settings for test environment
    with patch.dict(
        os.environ,
        {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
            "REDIS_DB": "1",  # Use DB 1 for tests
        },
    ):
        lock = RedisLock()

        # Try to connect - skip test if Redis is not available
        try:
            connected = await lock.connect()
            if not connected:
                pytest.skip("Redis is not available for integration tests")
        except Exception as e:
            pytest.skip(f"Redis is not available: {e}")

        yield lock

        # Cleanup
        try:
            await lock.disconnect()
        except Exception:
            pass


@pytest.mark.asyncio
class TestRedisLockIntegration:
    """Integration tests for Redis distributed lock with real Redis instance."""

    async def test_acquire_and_release_lock(self, redis_lock):
        """Test basic lock acquisition and release."""
        resource_key = "test_resource_1"

        # Acquire lock
        token = await redis_lock.acquire_lock(resource_key, 30)
        assert token is not None

        # Verify lock exists
        is_locked = await redis_lock.is_locked(resource_key)
        assert is_locked is True

        # Release lock
        released = await redis_lock.release_lock(resource_key, token)
        assert released is True

        # Verify lock is gone
        is_locked = await redis_lock.is_locked(resource_key)
        assert is_locked is False

    async def test_lock_prevents_double_acquisition(self, redis_lock):
        """Test that a locked resource cannot be locked again."""
        resource_key = "test_resource_2"

        # First lock should succeed
        token1 = await redis_lock.acquire_lock(resource_key, 30)
        assert token1 is not None

        # Second lock should fail
        token2 = await redis_lock.acquire_lock(resource_key, 30)
        assert token2 is None

        # Release first lock
        await redis_lock.release_lock(resource_key, token1)

        # Now second lock should succeed
        token3 = await redis_lock.acquire_lock(resource_key, 30)
        assert token3 is not None

        # Cleanup
        await redis_lock.release_lock(resource_key, token3)

    async def test_lock_expires_automatically(self, redis_lock):
        """Test that locks expire after timeout."""
        resource_key = "test_resource_3"

        # Acquire lock with short timeout
        token = await redis_lock.acquire_lock(resource_key, 1)  # 1 second
        assert token is not None

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Lock should be expired and acquirable again
        new_token = await redis_lock.acquire_lock(resource_key, 30)
        assert new_token is not None
        assert new_token != token

        # Cleanup
        await redis_lock.release_lock(resource_key, new_token)

    async def test_extend_lock(self, redis_lock):
        """Test lock extension functionality."""
        resource_key = "test_resource_4"

        # Acquire lock
        token = await redis_lock.acquire_lock(resource_key, 2)  # 2 seconds
        assert token is not None

        # Wait most of the timeout
        await asyncio.sleep(1.5)

        # Extend lock
        extended = await redis_lock.extend_lock(resource_key, token, 30)
        assert extended is True

        # Should still be locked after original timeout
        await asyncio.sleep(1)
        is_locked = await redis_lock.is_locked(resource_key)
        assert is_locked is True

        # Cleanup
        await redis_lock.release_lock(resource_key, token)

    async def test_wrong_token_cannot_release_lock(self, redis_lock):
        """Test that wrong token cannot release a lock."""
        resource_key = "test_resource_5"

        # Acquire lock
        token = await redis_lock.acquire_lock(resource_key, 30)
        assert token is not None

        # Try to release with wrong token
        released = await redis_lock.release_lock(resource_key, "wrong_token")
        assert released is False

        # Lock should still exist
        is_locked = await redis_lock.is_locked(resource_key)
        assert is_locked is True

        # Release with correct token
        released = await redis_lock.release_lock(resource_key, token)
        assert released is True

    async def test_concurrent_lock_acquisition(self, redis_lock):
        """Test concurrent lock acquisition from multiple 'workers'."""
        resource_key = "test_resource_6"

        # Simulate multiple workers trying to acquire the same lock
        async def try_acquire():
            return await redis_lock.acquire_lock(resource_key, 30)

        # Start multiple acquisition attempts concurrently
        tasks = [try_acquire() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # Only one should succeed
        successful_tokens = [token for token in results if token is not None]
        assert len(successful_tokens) == 1

        # Cleanup
        await redis_lock.release_lock(resource_key, successful_tokens[0])

    async def test_lock_cleanup_on_disconnect(self, redis_lock):
        """Test that disconnect cleans up properly."""
        resource_key = "test_resource_7"

        # Acquire lock
        token = await redis_lock.acquire_lock(resource_key, 30)
        assert token is not None

        # Disconnect (simulating worker crash)
        await redis_lock.disconnect()

        # Reconnect
        await redis_lock.connect()

        # Lock should still exist (not cleaned up automatically)
        is_locked = await redis_lock.is_locked(resource_key)
        assert is_locked is True

        # But we can still release it
        released = await redis_lock.release_lock(resource_key, token)
        assert released is True
