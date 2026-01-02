import pytest
from unittest.mock import AsyncMock, patch
from common.providers.bloom_filter.redis_bloom_filter import RedisBloomFilter


class TestRedisBloomFilter:
    """Unit tests for RedisBloomFilter."""

    @pytest.fixture
    def bloom_filter(self):
        """Create a RedisBloomFilter instance."""
        return RedisBloomFilter()

    def test_get_filter_key(self, bloom_filter):
        """Test that _get_filter_key generates correct Redis keys."""
        # Test basic filter name
        assert bloom_filter._get_filter_key("test_filter") == "bf:test_filter"

        # Test filter name with underscores
        assert (
            bloom_filter._get_filter_key("document_checksums")
            == "bf:document_checksums"
        )

        # Test filter name with special characters
        assert bloom_filter._get_filter_key("user-cache_v2") == "bf:user-cache_v2"

        # Test empty filter name (edge case)
        assert bloom_filter._get_filter_key("") == "bf:"

    def test_filter_prefix_consistency(self, bloom_filter):
        """Test that the filter prefix is consistent across the class."""
        expected_prefix = "bf:"
        assert bloom_filter._filter_prefix == expected_prefix

        # Verify the helper method uses the same prefix
        test_name = "test_filter"
        expected_key = f"{expected_prefix}{test_name}"
        assert bloom_filter._get_filter_key(test_name) == expected_key

    @pytest.mark.asyncio
    @patch("redis.asyncio.Redis")
    async def test_connection_short_circuit(self, mock_redis_class, bloom_filter):
        """Test that _ensure_connected short circuits when already connected."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        # First call should establish connection
        await bloom_filter._ensure_connected()
        assert bloom_filter._connected is True
        assert mock_client.ping.call_count == 1

        # Second call should short circuit (no additional ping)
        await bloom_filter._ensure_connected()
        assert bloom_filter._connected is True
        assert mock_client.ping.call_count == 1  # Should still be just 1

    @pytest.mark.asyncio
    @patch("redis.asyncio.Redis")
    async def test_filter_key_used_in_operations(self, mock_redis_class, bloom_filter):
        """Test that the filter key helper is used consistently in operations."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.execute_command.return_value = 1
        mock_redis_class.return_value = mock_client

        filter_name = "test_filter"
        expected_key = bloom_filter._get_filter_key(filter_name)

        # Connect first
        await bloom_filter.connect()

        # Test add operation uses correct key
        await bloom_filter.add(filter_name, "test_value")
        mock_client.execute_command.assert_any_call(
            "BF.ADD", expected_key, "test_value"
        )

        # Test exists operation uses correct key
        await bloom_filter.exists(filter_name, "test_value")
        mock_client.execute_command.assert_any_call(
            "BF.EXISTS", expected_key, "test_value"
        )
