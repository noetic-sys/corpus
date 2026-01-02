"""
Interface for payment providers.

Abstracts payment processing away from specific platforms (Stripe, PayPal, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
from packages.billing.models.domain.enums import SubscriptionTier


class PaymentProviderInterface(ABC):
    """Abstract interface for payment providers."""

    @abstractmethod
    async def create_checkout_session(
        self,
        company_id: int,
        company_name: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        trial_period_days: Optional[int] = None,
        stripe_customer_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a checkout session for subscription payment.

        Args:
            company_id: Company ID
            company_name: Company name
            tier: Subscription tier to purchase
            success_url: URL to redirect on success
            cancel_url: URL to redirect on cancel
            customer_email: Customer email for receipt
            trial_period_days: Optional trial period in days (1-90)
            stripe_customer_id: Existing customer ID to reuse

        Returns:
            Tuple of (checkout_url, customer_id)
        """
        pass

    @abstractmethod
    async def create_customer(
        self,
        company_id: int,
        company_name: str,
        email: Optional[str] = None,
    ) -> str:
        """
        Create a customer in the payment provider.

        Args:
            company_id: Internal company ID
            company_name: Company name
            email: Customer email

        Returns:
            customer_id: Payment provider customer ID
        """
        pass

    @abstractmethod
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """
        Create a customer portal session for managing subscription.

        Args:
            customer_id: Payment provider customer ID
            return_url: URL to return to after managing subscription

        Returns:
            portal_url: URL to customer portal
        """
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> None:
        """
        Cancel a subscription.

        Args:
            subscription_id: Payment provider subscription ID
        """
        pass

    @abstractmethod
    async def update_subscription_tier(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
        company_id: int,
    ) -> None:
        """
        Update existing subscription to a new tier/price.

        Used for paid → paid upgrades/downgrades.

        Args:
            subscription_id: Payment provider subscription ID
            new_tier: New subscription tier
            company_id: Internal company ID
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the payment backend is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass
