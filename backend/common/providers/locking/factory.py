from typing import Optional

from common.core.otel_axiom_exporter import get_logger

from .interface import DistributedLockInterface
from .redis_lock import RedisLock

logger = get_logger(__name__)

# Global instance
_lock_provider: Optional[DistributedLockInterface] = None


def get_lock_provider() -> DistributedLockInterface:
    """
    Get the configured distributed lock provider.

    Returns:
        DistributedLockInterface: The lock provider instance
    """
    global _lock_provider

    if _lock_provider is None:
        # For now, we only support Redis
        # In the future, we could check settings.lock_provider_type
        _lock_provider = RedisLock()
        logger.info("Initialized Redis lock provider")

    return _lock_provider
