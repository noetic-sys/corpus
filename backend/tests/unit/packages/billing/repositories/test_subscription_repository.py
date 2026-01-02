"""
Unit tests for SubscriptionRepository.

Tests database operations for subscriptions without mocking the database.
"""

import pytest
from datetime import datetime, timezone, timedelta

from packages.billing.repositories.subscription_repository import SubscriptionRepository
from packages.billing.models.domain.subscription import (
    SubscriptionCreateModel,
    SubscriptionUpdateModel,
)
from packages.billing.models.domain.enums import (
    SubscriptionStatus,
    SubscriptionTier,
    PaymentProvider,
)


@pytest.mark.asyncio
class TestSubscriptionRepository:
    """Tests for SubscriptionRepository."""

    async def test_create_subscription(self, test_db, sample_company):
        """Test creating a subscription."""
        repo = SubscriptionRepository(test_db)

        subscription_data = SubscriptionCreateModel(
            company_id=sample_company.id,
            tier=SubscriptionTier.STARTER,
            payment_provider=PaymentProvider.STRIPE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )

        subscription = await repo.create(subscription_data)

        assert subscription.id is not None
        assert subscription.company_id == sample_company.id
        assert subscription.tier == SubscriptionTier.STARTER
        assert subscription.status == SubscriptionStatus.ACTIVE  # Default status

    async def test_get_by_id(self, test_db, sample_subscription):
        """Test getting subscription by ID."""
        repo = SubscriptionRepository(test_db)

        subscription = await repo.get(sample_subscription.id)

        assert subscription is not None
        assert subscription.id == sample_subscription.id
        assert subscription.company_id == sample_subscription.company_id

    async def test_get_by_company_id(self, test_db, sample_subscription):
        """Test getting subscription by company ID."""
        repo = SubscriptionRepository(test_db)

        subscription = await repo.get_by_company_id(sample_subscription.company_id)

        assert subscription is not None
        assert subscription.company_id == sample_subscription.company_id
        assert subscription.id == sample_subscription.id

    async def test_get_by_company_id_not_found(self, test_db):
        """Test getting subscription for non-existent company."""
        repo = SubscriptionRepository(test_db)

        subscription = await repo.get_by_company_id(999999)

        assert subscription is None

    async def test_update_subscription(self, test_db, sample_subscription):
        """Test updating subscription."""
        repo = SubscriptionRepository(test_db)

        update_data = SubscriptionUpdateModel(
            status=SubscriptionStatus.SUSPENDED,
            suspended_at=datetime.now(timezone.utc),
        )

        updated = await repo.update(sample_subscription.id, update_data)

        assert updated.status == SubscriptionStatus.SUSPENDED
        assert updated.suspended_at is not None

    async def test_update_tier(self, test_db, sample_subscription):
        """Test upgrading subscription tier."""
        repo = SubscriptionRepository(test_db)

        update_data = SubscriptionUpdateModel(tier=SubscriptionTier.PROFESSIONAL)

        updated = await repo.update(sample_subscription.id, update_data)

        assert updated.tier == SubscriptionTier.PROFESSIONAL
        assert updated.company_id == sample_subscription.company_id

    async def test_list_all_subscriptions(
        self, test_db, sample_subscription, second_company
    ):
        """Test listing all subscriptions."""
        repo = SubscriptionRepository(test_db)

        # Create second subscription
        subscription_data = SubscriptionCreateModel(
            company_id=second_company.id,
            tier=SubscriptionTier.ENTERPRISE,
            payment_provider=PaymentProvider.STRIPE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        await repo.create(subscription_data)

        # List all
        subscriptions = await repo.get_multi(limit=100)

        assert len(subscriptions) >= 2
        company_ids = [sub.company_id for sub in subscriptions]
        assert sample_subscription.company_id in company_ids
        assert second_company.id in company_ids

    async def test_delete_subscription(self, test_db, sample_subscription):
        """Test deleting subscription."""
        repo = SubscriptionRepository(test_db)

        deleted = await repo.delete(sample_subscription.id)

        assert deleted is True

        # Verify it's gone
        subscription = await repo.get(sample_subscription.id)
        assert subscription is None
