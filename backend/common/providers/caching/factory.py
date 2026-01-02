from typing import Optional

from common.core.otel_axiom_exporter import get_logger

from .interface import CacheInterface
from .redis_cache import RedisCache

logger = get_logger(__name__)

# Global instance
_cache_provider: Optional[CacheInterface] = None


def get_cache_provider() -> CacheInterface:
    """
    Get the configured cache provider.

    Returns:
        CacheInterface: The cache provider instance
    """
    global _cache_provider

    if _cache_provider is None:
        # For now, we default to Redis
        # In the future, this could be configurable or you can change it here
        _cache_provider = RedisCache()
        logger.info("Initialized Redis cache provider")

    return _cache_provider
