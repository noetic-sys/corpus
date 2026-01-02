"""
Factory for getting metering provider instance.
"""

from packages.billing.providers.metering.interface import MeteringProviderInterface
from packages.billing.providers.metering.noop_metering import NoOpMeteringProvider


def get_metering_provider() -> MeteringProviderInterface:
    """
    Get metering provider instance.

    Currently uses no-op provider since quota enforcement is handled locally.
    This abstraction allows swapping to external metering providers in the future if needed.

    Returns:
        MeteringProviderInterface: Configured metering provider
    """
    return NoOpMeteringProvider()
