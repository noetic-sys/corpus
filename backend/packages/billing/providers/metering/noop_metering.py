"""
No-op metering provider.

Used when external metering is not needed.
All quota enforcement and usage tracking happens locally via QuotaService and UsageService.
"""

from typing import Optional

from packages.billing.providers.metering.interface import MeteringProviderInterface
from packages.billing.models.domain.enums import SubscriptionTier


class NoOpMeteringProvider(MeteringProviderInterface):
    """
    No-op metering provider that does nothing.

    Quota enforcement is handled locally via QuotaService and UsageEventRepository.
    Usage tracking is handled locally via UsageService.
    """

    async def create_customer(
        self,
        company_id: int,
        company_name: str,
        tier: SubscriptionTier,
        billing_email: Optional[str] = None,
    ) -> dict:
        """No external customer creation needed."""
        return {
            "customer_id": None,
            "subscription_id": None,
        }

    async def get_customer_usage(self, company_id: int) -> dict:
        """Usage is tracked locally. Return empty."""
        return {}

    async def update_subscription(
        self, subscription_id: str, new_tier: SubscriptionTier
    ) -> dict:
        """No external subscription to update."""
        return {}

    async def cancel_subscription(self, subscription_id: str) -> None:
        """No external subscription to cancel."""
        pass

    async def health_check(self) -> bool:
        """Always healthy since there's no external dependency."""
        return True
