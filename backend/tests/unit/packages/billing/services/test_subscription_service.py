"""
Unit tests for SubscriptionService.

Tests business logic with mocked external providers.
Database interactions are NOT mocked.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException

from packages.billing.models.domain.enums import (
    SubscriptionStatus,
    SubscriptionTier,
    PaymentProvider,
)
from packages.billing.models.domain.subscription import SubscriptionCreateModel
from packages.billing.repositories.subscription_repository import SubscriptionRepository
from packages.billing.services.subscription_service import SubscriptionService
from packages.companies.models.database.company import CompanyEntity


@pytest.fixture
def mock_metering_provider():
    """Create a mocked metering provider."""
    provider = AsyncMock()
    provider.create_customer = AsyncMock(
        return_value={
            "customer_id": None,
            "subscription_id": None,
        }
    )
    provider.update_subscription = AsyncMock(return_value=True)
    provider.cancel_subscription = AsyncMock(return_value=True)
    provider.get_customer_usage = AsyncMock(return_value={})
    return provider


@pytest.fixture
def mock_payment_provider():
    """Create a mocked payment provider (Stripe)."""
    provider = AsyncMock()
    provider.create_checkout_session = AsyncMock(
        return_value=("https://checkout.stripe.com/mock", "cus_mock123")
    )
    provider.create_customer_portal_session = AsyncMock(
        return_value="https://billing.stripe.com/mock"
    )
    provider.cancel_subscription = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def subscription_service(mock_metering_provider, mock_payment_provider):
    """Create SubscriptionService with mocked providers."""
    with patch(
        "packages.billing.services.subscription_service.get_metering_provider",
        return_value=mock_metering_provider,
    ), patch(
        "packages.billing.services.subscription_service.get_payment_provider",
        return_value=mock_payment_provider,
    ):
        return SubscriptionService()


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestSubscriptionService:
    """Tests for SubscriptionService."""

    @pytest.mark.asyncio
    async def test_create_subscription(
        self,
        mock_start_span,
        subscription_service,
        mock_metering_provider,
        sample_company,
    ):
        """Test creating a subscription."""
        subscription = await subscription_service.create_subscription(
            company_id=sample_company.id,
            company_name=sample_company.name,
            tier=SubscriptionTier.STARTER,
            billing_email="test@example.com",
        )

        # Verify subscription was created
        assert subscription.id is not None
        assert subscription.company_id == sample_company.id
        assert subscription.tier == SubscriptionTier.STARTER
        assert subscription.status == SubscriptionStatus.ACTIVE

        # Verify metering provider was called
        mock_metering_provider.create_customer.assert_called_once()
        call_args = mock_metering_provider.create_customer.call_args
        assert call_args.kwargs["company_id"] == sample_company.id
        assert call_args.kwargs["tier"] == SubscriptionTier.STARTER

    @pytest.mark.asyncio
    async def test_create_subscription_duplicate_fails(
        self,
        mock_start_span,
        subscription_service,
        sample_subscription,
    ):
        """Test that creating duplicate subscription raises error."""
        with pytest.raises(HTTPException) as exc_info:
            await subscription_service.create_subscription(
                company_id=sample_subscription.company_id,
                company_name="Test Company",
                tier=SubscriptionTier.STARTER,
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_by_company_id(
        self,
        mock_start_span,
        subscription_service,
        sample_subscription,
    ):
        """Test getting subscription by company ID."""
        subscription = await subscription_service.get_by_company_id(
            sample_subscription.company_id
        )

        assert subscription is not None
        assert subscription.id == sample_subscription.id
        assert subscription.company_id == sample_subscription.company_id

    @pytest.mark.asyncio
    async def test_update_status(
        self,
        mock_start_span,
        subscription_service,
        sample_subscription,
    ):
        """Test updating subscription status."""
        updated = await subscription_service.update_status(
            company_id=sample_subscription.company_id,
            new_status=SubscriptionStatus.SUSPENDED,
        )

        assert updated.status == SubscriptionStatus.SUSPENDED
        assert updated.suspended_at is not None

    @pytest.mark.asyncio
    async def test_upgrade_tier(
        self,
        mock_start_span,
        subscription_service,
        mock_metering_provider,
        sample_subscription,
    ):
        """Test upgrading subscription tier."""
        updated = await subscription_service.upgrade_tier(
            company_id=sample_subscription.company_id,
            new_tier=SubscriptionTier.PROFESSIONAL,
        )

        assert updated.tier == SubscriptionTier.PROFESSIONAL

    @pytest.mark.asyncio
    async def test_upgrade_to_same_tier_fails(
        self,
        mock_start_span,
        subscription_service,
        sample_subscription,
    ):
        """Test that upgrading to same tier raises error."""
        with pytest.raises(HTTPException) as exc_info:
            await subscription_service.upgrade_tier(
                company_id=sample_subscription.company_id,
                new_tier=sample_subscription.tier,
            )

        assert exc_info.value.status_code == 400
        assert "Already on this tier" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_cancel_subscription(
        self,
        mock_start_span,
        subscription_service,
        mock_metering_provider,
        mock_payment_provider,
        sample_subscription,
    ):
        """Test cancelling a subscription."""
        cancelled = await subscription_service.cancel_subscription(
            sample_subscription.company_id
        )

        assert cancelled.status == SubscriptionStatus.CANCELLED
        assert cancelled.cancelled_at is not None

        # Verify Stripe was notified
        mock_payment_provider.cancel_subscription.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_checkout_session(
        self,
        mock_start_span,
        subscription_service,
        mock_payment_provider,
        sample_company,
    ):
        """Test creating Stripe checkout session."""
        checkout_url = await subscription_service.create_checkout_session(
            company_id=sample_company.id,
            company_name=sample_company.name,
            tier=SubscriptionTier.STARTER,
            success_url="http://localhost:3000/success",
            cancel_url="http://localhost:3000/cancel",
            billing_email="test@example.com",
        )

        assert checkout_url == "https://checkout.stripe.com/mock"
        mock_payment_provider.create_checkout_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_portal_session(
        self,
        mock_start_span,
        subscription_service,
        mock_payment_provider,
        sample_subscription,
    ):
        """Test creating Stripe customer portal session."""
        portal_url = await subscription_service.create_portal_session(
            company_id=sample_subscription.company_id,
            return_url="http://localhost:3000/billing",
        )

        assert portal_url == "https://billing.stripe.com/mock"
        mock_payment_provider.create_customer_portal_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_portal_session_no_stripe_customer_fails(
        self,
        mock_start_span,
        subscription_service,
        test_db,
    ):
        """Test that portal session fails if no Stripe customer ID."""
        # Create a company WITHOUT stripe_customer_id
        company_no_stripe = CompanyEntity(name="No Stripe Company")
        test_db.add(company_no_stripe)
        await test_db.commit()
        await test_db.refresh(company_no_stripe)

        # Create subscription for this company
        repo = SubscriptionRepository()
        await repo.create(
            SubscriptionCreateModel(
                company_id=company_no_stripe.id,
                tier=SubscriptionTier.STARTER,
                payment_provider=PaymentProvider.STRIPE,
                current_period_start=datetime.now(timezone.utc),
                current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await subscription_service.create_portal_session(
                company_id=company_no_stripe.id,
                return_url="http://localhost:3000/billing",
            )

        assert exc_info.value.status_code == 404
