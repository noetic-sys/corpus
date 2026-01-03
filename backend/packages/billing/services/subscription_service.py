"""
Service for managing subscriptions.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from common.core.otel_axiom_exporter import trace_span, get_logger
from common.providers.caching.decorators import cache
from common.providers.caching.factory import get_cache_provider
from packages.billing.cache_keys import subscription_by_company_key
from packages.billing.repositories.subscription_repository import SubscriptionRepository
from packages.billing.models.domain.subscription import (
    Subscription,
    SubscriptionCreateModel,
    SubscriptionUpdateModel,
)
from packages.billing.models.domain.enums import (
    SubscriptionStatus,
    SubscriptionTier,
    PaymentProvider,
)
from packages.billing.providers.metering.factory import get_metering_provider
from packages.billing.providers.payment.factory import get_payment_provider
from packages.companies.services.company_service import CompanyService
from packages.companies.models.domain.company import CompanyUpdateModel

logger = get_logger(__name__)


class SubscriptionService:
    """Service for subscription management."""

    def __init__(self):
        self.subscription_repo = SubscriptionRepository()
        self.company_service = CompanyService()
        self.metering = get_metering_provider()
        self.payment = get_payment_provider()

    @trace_span
    async def create_subscription(
        self,
        company_id: int,
        company_name: str,
        tier: SubscriptionTier,
        billing_email: Optional[str] = None,
    ) -> Subscription:
        """
        Create a new subscription for a company.

        Creates customer in metering and payment (Stripe) platforms.
        """
        logger.info(
            f"Creating subscription for company {company_id}, tier: {tier.value}"
        )

        # Check if subscription already exists
        existing = await self.subscription_repo.get_by_company_id(company_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription already exists for this company",
            )

        # Create customer in metering platform
        metering_result = await self.metering.create_customer(
            company_id=company_id,
            company_name=company_name,
            tier=tier,
            billing_email=billing_email,
        )

        # Calculate billing cycle (monthly, starts today)
        period_start = datetime.utcnow()
        period_end = period_start + timedelta(days=30)

        # Create subscription in database
        subscription_data = SubscriptionCreateModel(
            company_id=company_id,
            tier=tier,
            payment_provider=PaymentProvider.STRIPE,
            current_period_start=period_start,
            current_period_end=period_end,
        )

        subscription = await self.subscription_repo.create(subscription_data)

        logger.info(
            f"Created subscription {subscription.id} for company {company_id}",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "tier": tier.value,
            },
        )

        return subscription

    @trace_span
    @cache(model_type=Subscription, ttl=300, key_generator=subscription_by_company_key)
    async def get_by_company_id(self, company_id: int) -> Optional[Subscription]:
        """Get subscription for a company. Cached for 5 minutes."""
        return await self.subscription_repo.get_by_company_id(company_id)

    @trace_span
    async def update_status(
        self, company_id: int, new_status: SubscriptionStatus
    ) -> Subscription:
        """Update subscription status."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        update_data = SubscriptionUpdateModel(status=new_status)

        # Set lifecycle timestamps based on status
        if new_status == SubscriptionStatus.CANCELLED:
            update_data.cancelled_at = datetime.utcnow()
        elif new_status == SubscriptionStatus.SUSPENDED:
            update_data.suspended_at = datetime.utcnow()

        updated = await self.subscription_repo.update(subscription.id, update_data)

        # Targeted cache invalidation
        cache_key = subscription_by_company_key(company_id)
        await get_cache_provider().delete(cache_key)

        logger.info(
            f"Updated subscription {subscription.id} status to {new_status.value}",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "old_status": subscription.status.value,
                "new_status": new_status.value,
            },
        )

        return updated

    @trace_span
    async def upgrade_tier(
        self, company_id: int, new_tier: SubscriptionTier
    ) -> Subscription:
        """Upgrade subscription tier (DB only)."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        if subscription.tier == new_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Already on this tier"
            )

        # Update tier in database
        update_data = SubscriptionUpdateModel(tier=new_tier)
        updated = await self.subscription_repo.update(subscription.id, update_data)

        # Targeted cache invalidation
        cache_key = subscription_by_company_key(company_id)
        await get_cache_provider().delete(cache_key)

        logger.info(
            f"Upgraded subscription {subscription.id} from {subscription.tier.value} to {new_tier.value}",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "old_tier": subscription.tier.value,
                "new_tier": new_tier.value,
            },
        )

        return updated

    @trace_span
    async def update_subscription_tier(
        self, company_id: int, new_tier: SubscriptionTier
    ) -> Subscription:
        """Update subscription tier via Stripe and DB (paid → paid)."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        if subscription.tier == new_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Already on this tier"
            )

        if not subscription.stripe_subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Stripe subscription found",
            )

        old_tier = subscription.tier

        # Update Stripe subscription in place
        await self.payment.update_subscription_tier(
            subscription_id=subscription.stripe_subscription_id,
            new_tier=new_tier,
            company_id=company_id,
        )

        # Update tier in database
        update_data = SubscriptionUpdateModel(tier=new_tier)
        updated = await self.subscription_repo.update(subscription.id, update_data)

        # Targeted cache invalidation
        cache_key = subscription_by_company_key(company_id)
        await get_cache_provider().delete(cache_key)

        logger.info(
            f"Updated subscription {subscription.id} from {old_tier.value} to {new_tier.value} via Stripe",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "old_tier": old_tier.value,
                "new_tier": new_tier.value,
            },
        )

        return updated

    @trace_span
    async def cancel_subscription(self, company_id: int) -> Subscription:
        """Cancel a subscription and invalidate cache."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        # Cancel in payment platform
        if subscription.stripe_subscription_id:
            await self.payment.cancel_subscription(subscription.stripe_subscription_id)

        # Update status
        return await self.update_status(company_id, SubscriptionStatus.CANCELLED)

    @trace_span
    async def downgrade_to_free(self, company_id: int) -> Subscription:
        """Downgrade from paid tier to FREE tier."""
        subscription = await self.subscription_repo.get_by_company_id(company_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )

        if subscription.tier == SubscriptionTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Already on FREE tier"
            )

        old_tier = subscription.tier

        # Cancel Stripe subscription
        if subscription.stripe_subscription_id:
            await self.payment.cancel_subscription(subscription.stripe_subscription_id)

        # Update to FREE tier and clear Stripe subscription ID
        update_data = SubscriptionUpdateModel(
            tier=SubscriptionTier.FREE,
            stripe_subscription_id=None,
            status=SubscriptionStatus.ACTIVE,
        )
        updated = await self.subscription_repo.update(subscription.id, update_data)

        # Targeted cache invalidation
        cache_key = subscription_by_company_key(company_id)
        await get_cache_provider().delete(cache_key)

        logger.info(
            f"Downgraded subscription {subscription.id} from {old_tier.value} to FREE",
            extra={
                "subscription_id": subscription.id,
                "company_id": company_id,
                "old_tier": old_tier.value,
            },
        )

        return updated

    @trace_span
    async def create_checkout_session(
        self,
        company_id: int,
        company_name: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        billing_email: Optional[str] = None,
        trial_period_days: Optional[int] = None,
    ) -> str:
        """Create payment checkout session."""
        # Get company to check for existing Stripe customer
        company = await self.company_service.get_company(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

        checkout_url, customer_id = await self.payment.create_checkout_session(
            company_id=company_id,
            company_name=company_name,
            tier=tier,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=billing_email,
            trial_period_days=trial_period_days,
            stripe_customer_id=company.stripe_customer_id,
        )

        # Save Stripe customer ID on company if new
        if not company.stripe_customer_id:
            await self.company_service.update_company(
                company_id, CompanyUpdateModel(stripe_customer_id=customer_id)
            )

        logger.info(
            f"Created checkout session for company {company_id}",
            extra={
                "company_id": company_id,
                "tier": tier.value,
                "trial_days": trial_period_days,
            },
        )

        return checkout_url

    @trace_span
    async def create_portal_session(self, company_id: int, return_url: str) -> str:
        """Create customer portal session."""
        # Get stripe_customer_id from company
        company = await self.company_service.get_company(company_id)
        if not company or not company.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No payment information found",
            )

        portal_url = await self.payment.create_customer_portal_session(
            customer_id=company.stripe_customer_id, return_url=return_url
        )

        logger.info(
            f"Created portal session for company {company_id}",
            extra={"company_id": company_id},
        )

        return portal_url
