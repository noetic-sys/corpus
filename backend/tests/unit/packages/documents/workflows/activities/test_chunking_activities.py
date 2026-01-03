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


class TestGetChunkingStrategyActivity:
    """Unit tests for get_chunking_strategy_activity.

    The activity checks document.use_agentic_chunking preference:
    - If False: returns sentence chunking (default, no quota check)
    - If True: checks quota, returns agentic if available, raises exception if exceeded
    """

    @pytest.mark.asyncio
    async def test_returns_sentence_when_use_agentic_false(
        self,
        test_db,
        sample_company,
    ):
        """Test returns SENTENCE strategy when document.use_agentic_chunking=False."""

        document_id = 123

        # Mock document service to return document with use_agentic_chunking=False
        with patch(
            "packages.documents.workflows.activities.chunking_activities.get_document_service"
        ) as mock_get_doc_service:
            mock_doc_service = MagicMock()
            mock_document = MagicMock()
            mock_document.use_agentic_chunking = False
            mock_doc_service.get_document = AsyncMock(return_value=mock_document)
            mock_get_doc_service.return_value = mock_doc_service

            result = await get_chunking_strategy_activity(
                sample_company.id, document_id
            )

        assert result["strategy"] == ChunkingStrategy.SENTENCE.value
        assert result["tier"] is None
        assert result["usage_event_id"] is None
        assert result["quota_exceeded"] is False

    @pytest.mark.asyncio
    async def test_returns_agentic_when_opted_in_and_quota_available(
        self,
        test_db,
        sample_company,
    ):
        """Test returns AGENTIC strategy when opted in and quota available."""

        document_id = 123

        # Mock document service to return document with use_agentic_chunking=True
        with patch(
            "packages.documents.workflows.activities.chunking_activities.get_document_service"
        ) as mock_get_doc_service, patch(
            "packages.documents.workflows.activities.chunking_activities.QuotaService"
        ) as mock_quota_class:
            mock_doc_service = MagicMock()
            mock_document = MagicMock()
            mock_document.use_agentic_chunking = True
            mock_doc_service.get_document = AsyncMock(return_value=mock_document)
            mock_get_doc_service.return_value = mock_doc_service

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
    async def test_raises_exception_when_opted_in_but_quota_exceeded(
        self,
        test_db,
        sample_company,
    ):
        """Test raises exception when opted in but quota exceeded."""

        document_id = 123

        # Mock document service to return document with use_agentic_chunking=True
        with patch(
            "packages.documents.workflows.activities.chunking_activities.get_document_service"
        ) as mock_get_doc_service, patch(
            "packages.documents.workflows.activities.chunking_activities.QuotaService"
        ) as mock_quota_class:
            mock_doc_service = MagicMock()
            mock_document = MagicMock()
            mock_document.use_agentic_chunking = True
            mock_doc_service.get_document = AsyncMock(return_value=mock_document)
            mock_get_doc_service.return_value = mock_doc_service

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

            with pytest.raises(Exception) as exc_info:
                await get_chunking_strategy_activity(sample_company.id, document_id)

            assert "quota exceeded" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_raises_exception_when_document_not_found(
        self,
        test_db,
        sample_company,
    ):
        """Test raises exception when document not found."""

        document_id = 999

        # Mock document service to return None
        with patch(
            "packages.documents.workflows.activities.chunking_activities.get_document_service"
        ) as mock_get_doc_service:
            mock_doc_service = MagicMock()
            mock_doc_service.get_document = AsyncMock(return_value=None)
            mock_get_doc_service.return_value = mock_doc_service

            with pytest.raises(Exception) as exc_info:
                await get_chunking_strategy_activity(sample_company.id, document_id)

            assert "not found" in str(exc_info.value).lower()


class TestRefundAgenticChunkingCreditActivity:
    """Unit tests for refund_agentic_chunking_credit_activity."""

    @pytest.mark.asyncio
    async def test_creates_negative_usage_event(
        self,
        test_db,
        sample_company,
    ):
        """Test that refunding credit creates a -1 quantity event."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        document_id = 123

        # First create the original reservation
        usage_service = UsageService()
        original_event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        original_event_id = original_event.id

        refund_event_id = await refund_agentic_chunking_credit_activity(
            company_id=sample_company.id,
            document_id=document_id,
            original_event_id=original_event_id,
        )

        assert refund_event_id is not None
        assert refund_event_id != original_event_id

        # Verify both events exist and net to zero
        usage_repo = UsageEventRepository()
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
        test_db,
        sample_company,
    ):
        """Test that refund event references original event."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        document_id = 456

        # Create original reservation
        usage_service = UsageService()
        original_event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        original_event_id = original_event.id

        await refund_agentic_chunking_credit_activity(
            company_id=sample_company.id,
            document_id=document_id,
            original_event_id=original_event_id,
        )

        # Check both events exist
        usage_repo = UsageEventRepository()
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


class TestUpdateAgenticChunkingMetadataActivity:
    """Unit tests for update_agentic_chunking_metadata_activity."""

    @pytest.mark.asyncio
    async def test_updates_event_metadata(
        self,
        test_db,
        sample_company,
    ):
        """Test that metadata is updated with chunk count."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        document_id = 789

        # Create usage event first using service
        usage_service = UsageService()
        event = await usage_service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=document_id,
        )
        await test_db.commit()
        event_id = event.id

        await update_agentic_chunking_metadata_activity(
            usage_event_id=event_id,
            chunk_count=42,
        )

        # Verify metadata was updated
        usage_repo = UsageEventRepository()
        now = datetime.now(timezone.utc)
        events = await usage_repo.get_by_company_date_range(
            sample_company.id,
            now - timedelta(minutes=5),
            now + timedelta(minutes=5),
        )
        updated_event = events[0]
        assert updated_event.event_metadata.get("chunk_count") == 42
