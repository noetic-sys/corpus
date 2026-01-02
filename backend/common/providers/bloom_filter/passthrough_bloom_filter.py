from .interface import BloomFilterInterface
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class PassthroughBloomFilter(BloomFilterInterface):
    """Passthrough bloom filter that disables bloom filter functionality.

    This implementation always assumes items might exist to avoid false negatives,
    effectively disabling bloom filter optimization while maintaining interface compatibility.
    """

    def __init__(self):
        logger.info(
            "Using passthrough bloom filter - bloom filter functionality disabled"
        )

    async def add(self, filter_name: str, value: str) -> bool:
        """Always returns True, pretending the value was added."""
        logger.debug(
            f"Passthrough add '{value}' to bloom filter '{filter_name}' - no-op"
        )
        return True

    async def exists(self, filter_name: str, value: str) -> bool:
        """Always returns True to avoid false negatives."""
        logger.debug(
            f"Passthrough exists check '{value}' in bloom filter '{filter_name}' - always True"
        )
        return True

    async def clear(self, filter_name: str) -> bool:
        """Always returns True, pretending the filter was cleared."""
        logger.debug(f"Passthrough clear bloom filter '{filter_name}' - no-op")
        return True

    async def info(self, filter_name: str) -> dict:
        """Returns basic info indicating this is a passthrough implementation."""
        return {
            "type": "passthrough",
            "name": filter_name,
            "capacity": "unlimited",
            "error_rate": "0.0",
            "items_count": "unknown",
            "description": "Passthrough implementation - no bloom filter functionality",
        }
