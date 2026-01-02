import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from packages.documents.workflows.activities.chunking_activities import (
    get_chunking_strategy_activity,
    refund_agentic_chunking_credit_activity,
    update_agentic_chunking_metadata_activity,
)
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy
from packages.billing.models.domain.enums import (
    SubscriptionTier,
    SubscriptionStatus,
    PaymentProvider,
    UsageEventType,
)
from packages.billing.models.domain.usage import QuotaReservationResult
from packages.billing.services.usage_service import UsageService
from packages.billing.repositories.usage_repository import UsageEventRepository
from packages.billing.models.database.subscription import SubscriptionEntity


@patch("packages.documents.workflows.activities.chunking_activities.get_db")
class TestGetChunkingStrategyActivity:
    """Unit tests for get_chunking_strategy_activity.

    The activity now atomically checks quota and reserves credit in one operation.
    """

    @pytest.mark.asyncio
    async def test_returns_agentic_when_quota_available(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test returns AGENTIC strategy and reserves credit when quota available."""

        def fresh_db_generator():
            async def gen():
                yield test_db

            return gen()

        mock_get_db.side_effect = fresh_db_generator

        # Create FREE subscription
        subscription = SubscriptionEntity(
            company_id=sample_company.id,
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            payment_provider=PaymentProvider.STRIPE.value,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        test_db.add(subscription)
        await test_db.commit()

        document_id = 123

        # Mock QuotaService to return successful reservation
        with patch(
            "packages.documents.workflows.activities.chunking_activities.QuotaService"
        ) as mock_quota_class:
            mock_quota = MagicMock()
            mock_quota.reserve_agentic_chunking_if_available = AsyncMock(
                return_value=QuotaReservationResult(
                    reserved=True,
                    usage_event_id=999,
                    current_usage=1,
                    limit=3,
                    tier=SubscriptionTier.FREE,
                )
            )
            mock_quota_class.return_value = mock_quota

            result = await get_chunking_strategy_activity(
                sample_company.id, document_id
            )

        assert result["strategy"] == ChunkingStrategy.AGENTIC.value
        assert result["tier"] == SubscriptionTier.FREE.value
        assert result["usage_event_id"] == 999
        assert result["quota_exceeded"] is False

    @pytest.mark.asyncio
    async def test_falls_back_to_sentence_when_quota_exceeded(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test falls back to SENTENCE when quota exceeded."""

        def fresh_db_generator():
            async def gen():
                yield test_db

            return gen()

        mock_get_db.side_effect = fresh_db_generator

        # Create FREE subscription
        subscription = SubscriptionEntity(
            company_id=sample_company.id,
            tier=SubscriptionTier.FREE.value,
            status=SubscriptionStatus.ACTIVE.value,
            payment_provider=PaymentProvider.STRIPE.value,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        test_db.add(subscription)
        await test_db.commit()

        document_id = 123

        # Mock QuotaService to return quota exceeded (no reservation)
        with patch(
            "packages.documents.workflows.activities.chunking_activities.QuotaService"
        ) as mock_quota_class:
            mock_quota = MagicMock()
            mock_quota.reserve_agentic_chunking_if_available = AsyncMock(
                return_value=QuotaReservationResult(
                    reserved=False,
                    usage_event_id=None,
                    current_usage=3,
                    limit=3,
                    tier=SubscriptionTier.FREE,
                )
            )
            mock_quota_class.return_value = mock_quota

            result = await get_chunking_strategy_activity(
                sample_company.id, document_id
            )

        assert result["strategy"] == ChunkingStrategy.SENTENCE.value
        assert result["tier"] == SubscriptionTier.FREE.value
        assert result["usage_event_id"] is None
        assert result["quota_exceeded"] is True

    @pytest.mark.asyncio
    async def test_no_subscription_returns_sentence(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test company without subscription gets SENTENCE strategy."""

        def fresh_db_generator():
            async def gen():
                yield test_db

            return gen()

        mock_get_db.side_effect = fresh_db_generator

        document_id = 123

        # Don't create any subscription - QuotaService returns not reserved
        with patch(
            "packages.documents.workflows.activities.chunking_activities.QuotaService"
        ) as mock_quota_class:
            mock_quota = MagicMock()
            mock_quota.reserve_agentic_chunking_if_available = AsyncMock(
                return_value=QuotaReservationResult(
                    reserved=False,
                    usage_event_id=None,
                    current_usage=0,
                    limit=0,
                    tier=SubscriptionTier.FREE,
                )
            )
            mock_quota_class.return_value = mock_quota

            result = await get_chunking_strategy_activity(
                sample_company.id, document_id
            )

        assert result["strategy"] == ChunkingStrategy.SENTENCE.value
        assert result["tier"] == SubscriptionTier.FREE.value
        assert result["usage_event_id"] is None
        assert result["quota_exceeded"] is True


@patch("packages.documents.workflows.activities.chunking_activities.get_db")
class TestRefundAgenticChunkingCreditActivity:
    """Unit tests for refund_agentic_chunking_credit_activity."""

    @pytest.mark.asyncio
    async def test_creates_negative_usage_event(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test that refunding credit creates a -1 quantity event."""

        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        document_id = 123

        # First create the original reservation
        usage_service = UsageService(test_db)
        original_event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        original_event_id = original_event.id

        # Reset mock for refund call
        mock_get_db.return_value = mock_db_generator()

        refund_event_id = await refund_agentic_chunking_credit_activity(
            company_id=sample_company.id,
            document_id=document_id,
            original_event_id=original_event_id,
        )

        assert refund_event_id is not None
        assert refund_event_id != original_event_id

        # Verify both events exist and net to zero
        usage_repo = UsageEventRepository(test_db)
        now = datetime.now(timezone.utc)
        total = await usage_repo.get_monthly_count(
            sample_company.id,
            UsageEventType.AGENTIC_CHUNKING,
            year=now.year,
            month=now.month,
        )

        assert total == 0  # +1 and -1 = 0

    @pytest.mark.asyncio
    async def test_refund_preserves_audit_trail(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test that refund event references original event."""

        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        document_id = 456

        # Create original reservation
        usage_service = UsageService(test_db)
        original_event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        original_event_id = original_event.id

        # Reset mock for refund call
        mock_get_db.return_value = mock_db_generator()

        await refund_agentic_chunking_credit_activity(
            company_id=sample_company.id,
            document_id=document_id,
            original_event_id=original_event_id,
        )

        # Check both events exist
        usage_repo = UsageEventRepository(test_db)
        now = datetime.now(timezone.utc)
        events = await usage_repo.get_by_company_date_range(
            sample_company.id,
            now - timedelta(minutes=5),
            now + timedelta(minutes=5),
        )

        assert len(events) == 2

        # Find the refund event
        refund_event = next(e for e in events if e.quantity == -1)
        assert refund_event.event_metadata["refund_for_event_id"] == original_event_id
        assert refund_event.event_metadata["reason"] == "chunking_failed"


@patch("packages.documents.workflows.activities.chunking_activities.get_db")
class TestUpdateAgenticChunkingMetadataActivity:
    """Unit tests for update_agentic_chunking_metadata_activity."""

    @pytest.mark.asyncio
    async def test_updates_event_metadata(
        self,
        mock_get_db,
        test_db,
        sample_company,
    ):
        """Test that metadata is updated with chunk count."""

        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        document_id = 789

        # Create usage event first using service
        usage_service = UsageService(test_db)
        event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        event_id = event.id

        # Reset mock for update call
        mock_get_db.return_value = mock_db_generator()

        await update_agentic_chunking_metadata_activity(
            usage_event_id=event_id,
            chunk_count=42,
        )

        # Verify metadata was updated
        usage_repo = UsageEventRepository(test_db)
        now = datetime.now(timezone.utc)
        events = await usage_repo.get_by_company_date_range(
            sample_company.id,
            now - timedelta(minutes=5),
            now + timedelta(minutes=5),
        )
        updated_event = events[0]
        assert updated_event.event_metadata.get("chunk_count") == 42
