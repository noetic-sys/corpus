import pytest
from unittest.mock import patch
from pydantic import BaseModel
from testcontainers.redis import RedisContainer

from common.core.config import settings
from common.providers.caching import cache
import common.providers.caching.factory as cache_factory


class TestModel(BaseModel):
    id: int
    name: str


class TestRepository:
    def __init__(self):
        self.call_count = 0
        self.bool_call_count = 0

    @cache(TestModel, ttl=60)
    async def get_model(self, id: int) -> TestModel:
        self.call_count += 1
        return TestModel(id=id, name=f"test_{id}")

    @cache(bool, ttl=60)
    async def exists(self, id: int) -> bool:
        self.bool_call_count += 1
        return id > 0


class TestCaching:
    @pytest.fixture(autouse=True)
    def setup_redis(self):
        """Set up Redis container for all tests in this class."""
        with RedisContainer() as redis:
            with patch.object(settings, "redis_host", redis.get_container_host_ip()):
                with patch.object(settings, "redis_port", redis.get_exposed_port(6379)):
                    with patch.object(settings, "redis_password", None):
                        with patch.object(cache_factory, "_cache_provider", None):
                            yield

    @pytest.mark.asyncio
    async def test_basic_cache_functionality(self):
        """Test that cache stores and retrieves Pydantic models correctly."""
        repo = TestRepository()

        # First call - should execute function (cache miss)
        result1 = await repo.get_model(1)
        assert result1.id == 1
        assert result1.name == "test_1"
        assert repo.call_count == 1

        # Second call - should use cache (cache hit)
        result2 = await repo.get_model(1)
        assert result2.id == 1
        assert result2.name == "test_1"
        assert repo.call_count == 1  # Function not called again

        # Different args - should execute function again
        result3 = await repo.get_model(2)
        assert result3.id == 2
        assert result3.name == "test_2"
        assert repo.call_count == 2

    @pytest.mark.asyncio
    async def test_regular_type_caching(self):
        """Test that cache handles regular types like bool correctly."""
        repo = TestRepository()

        # First call - should execute function
        result1 = await repo.exists(1)
        assert result1 is True
        assert repo.bool_call_count == 1

        # Second call - should use cache
        result2 = await repo.exists(1)
        assert result2 is True
        assert repo.bool_call_count == 1  # Function not called again
