"""
Stripe implementation of payment provider.
"""

from typing import Optional, Tuple
import stripe

from common.core.config import settings
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.billing.models.domain.enums import SubscriptionTier
from packages.billing.providers.payment.interface import PaymentProviderInterface

logger = get_logger(__name__)


class StripePaymentProvider(PaymentProviderInterface):
    """Stripe-based payment implementation."""

    def __init__(self):
        """Initialize Stripe with API credentials."""
        stripe.api_key = settings.stripe_secret_key

        # Map tiers to Stripe price IDs (configured in Stripe dashboard)
        self.price_ids = {
            SubscriptionTier.STARTER: settings.stripe_price_id_starter,
            SubscriptionTier.PROFESSIONAL: settings.stripe_price_id_professional,
            SubscriptionTier.BUSINESS: settings.stripe_price_id_business,
            SubscriptionTier.ENTERPRISE: settings.stripe_price_id_enterprise,
        }

    @trace_span
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
        Create Stripe checkout session.

        Args:
            company_id: Internal company ID
            company_name: Company name for Stripe customer
            tier: Subscription tier
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            customer_email: Optional customer email
            trial_period_days: Optional trial period
            stripe_customer_id: Existing Stripe customer ID (from company)

        Returns:
            Tuple of (checkout_url, stripe_customer_id)
        """
        try:
            # Reuse existing customer or create new one
            if stripe_customer_id:
                customer_id = stripe_customer_id
                logger.info(
                    "Reusing existing Stripe customer",
                    extra={"company_id": company_id, "customer_id": customer_id},
                )
            else:
                customer = stripe.Customer.create(
                    email=customer_email,
                    name=company_name,
                    metadata={"company_id": str(company_id)},
                )
                customer_id = customer.id
                logger.info(
                    "Created new Stripe customer",
                    extra={"company_id": company_id, "customer_id": customer_id},
                )

            # Build subscription_data with optional trial
            subscription_data = {
                "metadata": {
                    "company_id": company_id,
                    "tier": tier.value,
                }
            }
            if trial_period_days:
                subscription_data["trial_period_days"] = trial_period_days

            # Create checkout session
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": self.price_ids[tier],
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "company_id": str(company_id),
                    "company_name": company_name,
                    "tier": tier.value,
                },
                subscription_data=subscription_data,
            )

            logger.info(
                "Created Stripe checkout session",
                extra={
                    "company_id": company_id,
                    "tier": tier.value,
                    "session_id": session.id,
                },
            )

            return session.url, customer_id

        except Exception as e:
            logger.error(
                f"Failed to create checkout session: {str(e)}",
                extra={"company_id": company_id, "error": str(e)},
            )
            raise

    @trace_span
    async def create_customer(
        self,
        company_id: int,
        company_name: str,
        email: Optional[str] = None,
    ) -> str:
        """Create a Stripe customer."""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=company_name,
                metadata={"company_id": str(company_id)},
            )

            logger.info(
                "Created Stripe customer",
                extra={"company_id": company_id, "customer_id": customer.id},
            )

            return customer.id

        except Exception as e:
            logger.error(
                f"Failed to create Stripe customer: {str(e)}",
                extra={"company_id": company_id, "error": str(e)},
            )
            raise

    @trace_span
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create Stripe customer portal session."""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

            logger.info(
                "Created Stripe portal session", extra={"customer_id": customer_id}
            )

            return session.url

        except Exception as e:
            logger.error(
                f"Failed to create portal session: {str(e)}",
                extra={"customer_id": customer_id, "error": str(e)},
            )
            raise

    @trace_span
    async def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel Stripe subscription."""
        try:
            stripe.Subscription.cancel(subscription_id)

            logger.info(
                "Cancelled Stripe subscription",
                extra={"subscription_id": subscription_id},
            )

        except Exception as e:
            logger.error(
                f"Failed to cancel subscription: {str(e)}",
                extra={"subscription_id": subscription_id, "error": str(e)},
            )
            raise

    @trace_span
    async def update_subscription_tier(
        self,
        subscription_id: str,
        new_tier: SubscriptionTier,
        company_id: int,
    ) -> None:
        """
        Update existing Stripe subscription to a new tier/price.

        Used for paid → paid upgrades/downgrades instead of creating new subscription.
        """
        try:
            # Get current subscription to find the item ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            item_id = subscription["items"]["data"][0]["id"]

            # Update the subscription with the new price
            # Use always_invoice to charge immediately - no free upgrades
            stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": item_id,
                        "price": self.price_ids[new_tier],
                    }
                ],
                metadata={
                    "company_id": str(company_id),
                    "tier": new_tier.value,
                },
                proration_behavior="always_invoice",
                payment_behavior="error_if_incomplete",
            )

            logger.info(
                f"Updated Stripe subscription to {new_tier.value}",
                extra={
                    "subscription_id": subscription_id,
                    "new_tier": new_tier.value,
                    "company_id": company_id,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to update subscription tier: {str(e)}",
                extra={"subscription_id": subscription_id, "error": str(e)},
            )
            raise

    @trace_span
    async def health_check(self) -> bool:
        """Check Stripe health."""
        try:
            # Try to retrieve account to verify API key works
            stripe.Account.retrieve()
            return True
        except Exception as e:
            logger.error(f"Payment health check failed: {e}")
            return False
