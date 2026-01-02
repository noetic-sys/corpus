"""
Interface for metering providers.

Abstracts customer/subscription management away from specific platforms.
Usage tracking is handled locally via UsageService.
"""

from abc import ABC, abstractmethod
from typing import Optional
from packages.billing.models.domain.enums import SubscriptionTier


class MeteringProviderInterface(ABC):
    """Abstract interface for metering providers."""

    @abstractmethod
    async def create_customer(
        self,
        company_id: int,
        company_name: str,
        tier: SubscriptionTier,
        billing_email: Optional[str] = None,
    ) -> dict:
        """
        Create a customer and subscription in the metering platform.

        Args:
            company_id: Company ID (becomes external_customer_id)
            company_name: Company name
            tier: Subscription tier
            billing_email: Email for invoices

        Returns:
            dict with customer and subscription details
        """
        pass

    @abstractmethod
    async def get_customer_usage(self, company_id: int) -> dict:
        """
        Get current usage stats.

        Args:
            company_id: Company ID

        Returns:
            dict with usage stats by metric
        """
        pass

    @abstractmethod
    async def update_subscription(
        self, subscription_id: str, new_tier: SubscriptionTier
    ) -> dict:
        """
        Update subscription tier.

        Args:
            subscription_id: Platform subscription ID
            new_tier: New subscription tier

        Returns:
            Updated subscription details
        """
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> None:
        """
        Cancel a subscription.

        Args:
            subscription_id: Platform subscription ID
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the metering backend is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass
