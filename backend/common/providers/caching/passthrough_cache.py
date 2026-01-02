from typing import Any, Optional, List

from .interface import CacheInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class PassthroughCache(CacheInterface):
    """Passthrough cache implementation that does nothing (for disabling cache)."""

    def __init__(self):
        logger.info("Passthrough cache provider initialized (caching disabled)")

    async def get(self, key: str) -> Optional[Any]:
        """Always return None (cache miss)."""
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Always return True but don't actually cache."""
        return True

    async def delete(self, key: str) -> bool:
        """Always return True but don't actually delete."""
        return True

    async def delete_pattern(self, pattern: str) -> int:
        """Always return 0 (nothing deleted)."""
        return 0

    async def clear(self) -> bool:
        """Always return True but don't actually clear."""
        return True

    async def exists(self, key: str) -> bool:
        """Always return False (key doesn't exist)."""
        return False

    async def get_keys(self, pattern: str) -> List[str]:
        """Always return empty list."""
        return []
