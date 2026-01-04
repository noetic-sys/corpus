"""
Unit tests for UsageService.

Tests for usage tracking and refund operations.
"""

import pytest
from datetime import datetime, timezone, timedelta

from packages.billing.services.usage_service import UsageService
from packages.billing.repositories.usage_repository import UsageEventRepository
from packages.billing.models.domain.enums import UsageEventType


@pytest.mark.asyncio
class TestUsageServiceAgenticQA:
    """Tests for agentic QA usage tracking."""

    async def test_track_agentic_qa_creates_event(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that track_agentic_qa creates a usage event."""
        service = UsageService()

        event = await service.track_agentic_qa(
            company_id=sample_company.id,
            quantity=5,
            user_id=sample_user_entity.id,
            question_id=123,
        )

        assert event.id is not None
        assert event.company_id == sample_company.id
        assert event.user_id == sample_user_entity.id
        assert event.event_type == UsageEventType.AGENTIC_QA
        assert event.quantity == 5
        assert event.event_metadata["question_id"] == 123

    async def test_track_agentic_qa_with_event_metadata(
        self, test_db, sample_company
    ):
        """Test that track_agentic_qa correctly handles event_metadata."""
        service = UsageService()

        # This is the correct way to pass matrix_id - via event_metadata
        event = await service.track_agentic_qa(
            company_id=sample_company.id,
            quantity=10,
            event_metadata={"matrix_id": 456},
        )

        assert event.id is not None
        assert event.quantity == 10
        assert event.event_metadata.get("matrix_id") == 456
        # question_id should be None when not provided
        assert event.event_metadata.get("question_id") is None

    async def test_track_agentic_qa_merges_metadata(
        self, test_db, sample_company
    ):
        """Test that question_id and event_metadata are merged correctly."""
        service = UsageService()

        event = await service.track_agentic_qa(
            company_id=sample_company.id,
            quantity=3,
            question_id=789,
            event_metadata={"matrix_id": 111, "extra_field": "value"},
        )

        assert event.event_metadata["question_id"] == 789
        assert event.event_metadata["matrix_id"] == 111
        assert event.event_metadata["extra_field"] == "value"

    async def test_track_agentic_qa_rejects_invalid_kwargs(
        self, test_db, sample_company
    ):
        """Test that passing invalid kwargs (like matrix_id directly) raises TypeError."""
        service = UsageService()

        # This should raise TypeError - matrix_id is not a valid parameter
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await service.track_agentic_qa(
                company_id=sample_company.id,
                quantity=5,
                matrix_id=123,  # This is WRONG - should be in event_metadata
            )


@pytest.mark.asyncio
class TestUsageServiceAgenticChunking:
    """Tests for agentic chunking usage tracking."""

    async def test_track_agentic_chunking_creates_event(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that track_agentic_chunking creates a usage event."""
        service = UsageService()

        event = await service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=123,
            user_id=sample_user_entity.id,
            chunk_count=50,
        )

        assert event.id is not None
        assert event.company_id == sample_company.id
        assert event.user_id == sample_user_entity.id
        assert event.event_type == UsageEventType.AGENTIC_CHUNKING
        assert event.quantity == 1
        assert event.event_metadata["document_id"] == 123
        assert event.event_metadata["chunk_count"] == 50

    async def test_track_agentic_chunking_without_chunk_count(
        self, test_db, sample_company
    ):
        """Test tracking agentic chunking without chunk count (reservation)."""
        service = UsageService()

        event = await service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=456,
        )

        assert event.id is not None
        assert event.quantity == 1
        assert event.event_metadata["document_id"] == 456
        assert event.event_metadata.get("chunk_count") is None


@pytest.mark.asyncio
class TestUsageServiceRefund:
    """Tests for agentic chunking refund operations."""

    async def test_refund_creates_negative_quantity_event(
        self, test_db, sample_company
    ):
        """Test that refund creates an event with quantity=-1."""
        service = UsageService()

        # First create a reservation
        reservation = await service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=789,
        )

        # Now refund it
        refund = await service.refund_agentic_chunking(
            company_id=sample_company.id,
            document_id=789,
            original_event_id=reservation.id,
        )

        assert refund.id is not None
        assert refund.id != reservation.id  # Different event
        assert refund.company_id == sample_company.id
        assert refund.event_type == UsageEventType.AGENTIC_CHUNKING
        assert refund.quantity == -1  # Negative to offset
        assert refund.event_metadata["document_id"] == 789
        assert refund.event_metadata["refund_for_event_id"] == reservation.id
        assert refund.event_metadata["reason"] == "chunking_failed"

    async def test_refund_nets_to_zero_usage(self, test_db, sample_company):
        """Test that reservation + refund nets to zero usage."""
        service = UsageService()
        repo = UsageEventRepository()

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create reservation
        reservation = await service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=100,
        )

        # Check count is 1
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )
        assert count == 1

        # Refund
        await service.refund_agentic_chunking(
            company_id=sample_company.id,
            document_id=100,
            original_event_id=reservation.id,
        )

        # Check count is now 0
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )
        assert count == 0

    async def test_partial_refund_scenario(self, test_db, sample_company):
        """Test scenario where some reservations succeed and some are refunded."""
        service = UsageService()
        repo = UsageEventRepository()

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 5 reservations
        reservations = []
        for i in range(5):
            event = await service.track_agentic_chunking(
                company_id=sample_company.id,
                document_id=i,
            )
            reservations.append(event)

        # Refund 2 of them (documents 0 and 2 failed)
        await service.refund_agentic_chunking(
            company_id=sample_company.id,
            document_id=0,
            original_event_id=reservations[0].id,
        )
        await service.refund_agentic_chunking(
            company_id=sample_company.id,
            document_id=2,
            original_event_id=reservations[2].id,
        )

        # Check count is 3 (5 - 2)
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )
        assert count == 3

    async def test_refund_preserves_audit_trail(self, test_db, sample_company):
        """Test that refund creates a separate event (audit trail preserved)."""
        service = UsageService()
        repo = UsageEventRepository()

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create reservation and refund
        reservation = await service.track_agentic_chunking(
            company_id=sample_company.id,
            document_id=999,
        )
        refund = await service.refund_agentic_chunking(
            company_id=sample_company.id,
            document_id=999,
            original_event_id=reservation.id,
        )

        # Get all events - should have 2 (reservation + refund)
        events = await repo.get_by_company_date_range(
            company_id=sample_company.id,
            start_date=period_start,
            end_date=period_end,
            event_type=UsageEventType.AGENTIC_CHUNKING,
        )

        assert len(events) == 2

        # One should be +1, one should be -1
        quantities = sorted([e.quantity for e in events])
        assert quantities == [-1, 1]
