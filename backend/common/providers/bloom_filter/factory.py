from common.core.otel_axiom_exporter import get_logger

from .interface import BloomFilterInterface
from .passthrough_bloom_filter import PassthroughBloomFilter

logger = get_logger(__name__)


def get_bloom_filter_provider() -> BloomFilterInterface:
    return PassthroughBloomFilter()
