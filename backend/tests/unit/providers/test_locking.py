import pytest
from unittest.mock import AsyncMock, patch
import redis.asyncio as redis

from common.providers.locking.redis_lock import RedisLock
from common.providers.locking.factory import get_lock_provider


class TestRedisLock:
    """Unit tests for Redis distributed lock."""

    @pytest.fixture
    def redis_lock(self):
        with patch("common.providers.locking.redis_lock.settings") as mock_settings:
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.redis_db = 0
            return RedisLock()

    @pytest.fixture
    def mock_redis_client(self):
        return AsyncMock(spec=redis.Redis)

    async def test_acquire_lock_success(self, redis_lock, mock_redis_client):
        """Test successful lock acquisition."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.set = AsyncMock(return_value=True)

        token = await redis_lock.acquire_lock("test_resource", 30)

        assert token is not None
        assert len(token) == 36  # UUID length
        mock_redis_client.set.assert_called_once_with(
            "lock:test_resource", token, nx=True, ex=30
        )

    async def test_acquire_lock_already_locked(self, redis_lock, mock_redis_client):
        """Test lock acquisition when resource is already locked."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.set = AsyncMock(return_value=False)

        token = await redis_lock.acquire_lock("test_resource", 30)

        assert token is None

    async def test_release_lock_success(self, redis_lock, mock_redis_client):
        """Test successful lock release."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.eval = AsyncMock(return_value=1)

        result = await redis_lock.release_lock("test_resource", "test_token")

        assert result is True
        mock_redis_client.eval.assert_called_once()

    async def test_release_lock_token_mismatch(self, redis_lock, mock_redis_client):
        """Test lock release with wrong token."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.eval = AsyncMock(return_value=0)

        result = await redis_lock.release_lock("test_resource", "wrong_token")

        assert result is False

    async def test_extend_lock_success(self, redis_lock, mock_redis_client):
        """Test successful lock extension."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.eval = AsyncMock(return_value=1)

        result = await redis_lock.extend_lock("test_resource", "test_token", 60)

        assert result is True

    async def test_is_locked_true(self, redis_lock, mock_redis_client):
        """Test checking if resource is locked (true case)."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.exists = AsyncMock(return_value=1)

        result = await redis_lock.is_locked("test_resource")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("lock:test_resource")

    async def test_is_locked_false(self, redis_lock, mock_redis_client):
        """Test checking if resource is locked (false case)."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.exists = AsyncMock(return_value=0)

        result = await redis_lock.is_locked("test_resource")

        assert result is False

    async def test_auto_connect_on_operation(self, redis_lock):
        """Test that operations trigger connection if not connected."""
        with patch.object(redis_lock, "connect") as mock_connect:
            mock_connect.return_value = True
            redis_lock._client = AsyncMock()
            redis_lock._client.set = AsyncMock(return_value=True)

            await redis_lock.acquire_lock("test_resource", 30)

            mock_connect.assert_called_once()


class TestAcquireLockWithRetry:
    """Tests for acquire_lock_with_retry method."""

    @pytest.fixture
    def redis_lock(self):
        with patch("common.providers.locking.redis_lock.settings") as mock_settings:
            mock_settings.redis_host = "localhost"
            mock_settings.redis_port = 6379
            mock_settings.redis_password = None
            mock_settings.redis_db = 0
            return RedisLock()

    @pytest.fixture
    def mock_redis_client(self):
        return AsyncMock(spec=redis.Redis)

    async def test_acquire_with_retry_success_first_try(
        self, redis_lock, mock_redis_client
    ):
        """Test successful acquisition on first try."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.set = AsyncMock(return_value=True)

        token = await redis_lock.acquire_lock_with_retry(
            "test_resource",
            lock_ttl_seconds=30,
            acquire_timeout_seconds=5.0,
            retry_interval_ms=50,
        )

        assert token is not None
        assert len(token) == 36  # UUID length
        # Should only be called once since it succeeded immediately
        assert mock_redis_client.set.call_count == 1

    async def test_acquire_with_retry_success_after_retries(
        self, redis_lock, mock_redis_client
    ):
        """Test successful acquisition after initial failures."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        # Fail twice, then succeed
        mock_redis_client.set = AsyncMock(side_effect=[False, False, True])

        token = await redis_lock.acquire_lock_with_retry(
            "test_resource",
            lock_ttl_seconds=30,
            acquire_timeout_seconds=5.0,
            retry_interval_ms=10,  # Short interval for fast test
        )

        assert token is not None
        assert mock_redis_client.set.call_count == 3

    async def test_acquire_with_retry_timeout(self, redis_lock, mock_redis_client):
        """Test timeout when lock cannot be acquired."""
        redis_lock._client = mock_redis_client
        redis_lock._connected = True
        mock_redis_client.set = AsyncMock(return_value=False)  # Always fail

        token = await redis_lock.acquire_lock_with_retry(
            "test_resource",
            lock_ttl_seconds=30,
            acquire_timeout_seconds=0.1,  # Very short timeout
            retry_interval_ms=20,
        )

        assert token is None
        # Should have tried multiple times before timing out
        assert mock_redis_client.set.call_count >= 2


class TestLockFactory:
    """Test the lock provider factory."""

    def test_get_lock_provider_returns_redis_lock(self):
        """Test that factory returns Redis lock provider."""
        provider = get_lock_provider()
        assert isinstance(provider, RedisLock)

    def test_get_lock_provider_singleton(self):
        """Test that factory returns the same instance (singleton)."""
        provider1 = get_lock_provider()
        provider2 = get_lock_provider()
        assert provider1 is provider2
