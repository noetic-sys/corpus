"""
Unit tests for UsageEventRepository.

Tests database operations for usage events without mocking the database.
"""

import pytest
from datetime import datetime, timezone, timedelta

from packages.billing.repositories.usage_repository import UsageEventRepository
from packages.billing.models.domain.usage import UsageEventCreateModel
from packages.billing.models.domain.enums import UsageEventType


@pytest.mark.asyncio
class TestUsageEventRepository:
    """Tests for UsageEventRepository."""

    async def test_create_usage_event(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test creating a usage event."""
        repo = UsageEventRepository(test_db)

        event_data = UsageEventCreateModel(
            company_id=sample_company.id,
            user_id=sample_user_entity.id,
            event_type=UsageEventType.CELL_OPERATION,
            event_metadata={"cell_id": 100, "operation": "create"},
        )

        event = await repo.create(event_data)

        assert event.id is not None
        assert event.company_id == sample_company.id
        assert event.user_id == sample_user_entity.id
        assert event.event_type == UsageEventType.CELL_OPERATION
        assert event.event_metadata["cell_id"] == 100

    async def test_get_monthly_count(self, test_db, sample_company, sample_user_entity):
        """Test getting monthly usage count."""
        repo = UsageEventRepository(test_db)

        # Create several usage events
        now = datetime.now(timezone.utc)
        for i in range(5):
            event_data = UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                event_metadata={"sequence": i},
            )
            await repo.create(event_data)

        # Get monthly count
        count = await repo.get_monthly_count(
            company_id=sample_company.id,
            event_type=UsageEventType.CELL_OPERATION,
            year=now.year,
            month=now.month,
        )

        assert count == 5

    async def test_get_period_count(self, test_db, sample_company, sample_user_entity):
        """Test getting usage count for a billing period."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create several usage events
        for i in range(4):
            event_data = UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_QA,
                event_metadata={"session_id": i},
            )
            await repo.create(event_data)

        # Get period count
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_QA,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 4

    async def test_get_monthly_count_filtered_by_type(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that monthly count filters by event type."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)

        # Create 3 cell operation events
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.CELL_OPERATION,
                    event_metadata={"sequence": i},
                )
            )

        # Create 2 storage upload events
        for i in range(2):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=1000 * (i + 1),
                    event_metadata={"document_id": i},
                )
            )

        # Check counts
        cell_count = await repo.get_monthly_count(
            company_id=sample_company.id,
            event_type=UsageEventType.CELL_OPERATION,
            year=now.year,
            month=now.month,
        )
        storage_count = await repo.get_monthly_count(
            company_id=sample_company.id,
            event_type=UsageEventType.STORAGE_UPLOAD,
            year=now.year,
            month=now.month,
        )

        assert cell_count == 3
        assert storage_count == 2

    async def test_get_storage_bytes_for_period(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test getting total storage bytes for a billing period."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create storage upload events with different file sizes
        file_sizes = [1000, 2000, 3000]
        for i, size in enumerate(file_sizes):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=size,
                    event_metadata={"document_id": i},
                )
            )

        # Get total storage bytes
        total_bytes = await repo.get_storage_bytes_for_period(
            company_id=sample_company.id,
            start_date=period_start,
            end_date=period_end,
        )

        assert total_bytes == sum(file_sizes)  # 6000 bytes

    async def test_get_by_company_date_range(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test getting events by company and date range."""
        repo = UsageEventRepository(test_db)

        # Create events
        for i in range(5):
            event_data = UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                event_metadata={"sequence": i},
            )
            await repo.create(event_data)

        # Get events in date range
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=1)

        events = await repo.get_by_company_date_range(
            company_id=sample_company.id,
            start_date=start_date,
            end_date=end_date,
            event_type=UsageEventType.CELL_OPERATION,
        )

        assert len(events) == 5
        assert all(e.company_id == sample_company.id for e in events)

    async def test_get_by_user(self, test_db, sample_company, sample_user_entity):
        """Test getting events by user."""
        repo = UsageEventRepository(test_db)

        # Create events for user
        for i in range(3):
            event_data = UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.WORKFLOW,
                event_metadata={"workflow_id": i},
            )
            await repo.create(event_data)

        # Get by user
        events = await repo.get_by_user(user_id=sample_user_entity.id, limit=10)

        assert len(events) == 3
        assert all(e.user_id == sample_user_entity.id for e in events)

    async def test_isolation_between_companies(
        self, test_db, sample_company, second_company, sample_user_entity
    ):
        """Test that usage events are properly isolated by company."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)

        # Create events for company 1
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.CELL_OPERATION,
                    event_metadata={"sequence": i},
                )
            )

        # Create events for company 2
        for i in range(5):
            await repo.create(
                UsageEventCreateModel(
                    company_id=second_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.CELL_OPERATION,
                    event_metadata={"sequence": i},
                )
            )

        # Check counts are isolated
        count1 = await repo.get_monthly_count(
            company_id=sample_company.id,
            event_type=UsageEventType.CELL_OPERATION,
            year=now.year,
            month=now.month,
        )
        count2 = await repo.get_monthly_count(
            company_id=second_company.id,
            event_type=UsageEventType.CELL_OPERATION,
            year=now.year,
            month=now.month,
        )

        assert count1 == 3
        assert count2 == 5

    async def test_batch_quantity_tracking(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that quantity field is properly summed for batch operations."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create a batch event with quantity=100 (e.g., 100 cells created at once)
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                quantity=100,
                event_metadata={"batch_id": 1},
            )
        )

        # Create another batch event with quantity=50
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                quantity=50,
                event_metadata={"batch_id": 2},
            )
        )

        # Create a single operation (quantity defaults to 1)
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                event_metadata={"batch_id": 3},
            )
        )

        # Get period count - should be SUM of quantities (100 + 50 + 1 = 151)
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.CELL_OPERATION,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 151  # 100 + 50 + 1

    async def test_monthly_count_with_quantities(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that monthly count properly sums quantities."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)

        # Create events with various quantities
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_QA,
                quantity=25,
                event_metadata={"question_id": 1},
            )
        )
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_QA,
                quantity=75,
                event_metadata={"question_id": 2},
            )
        )

        # Get monthly count
        count = await repo.get_monthly_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_QA,
            year=now.year,
            month=now.month,
        )

        assert count == 100  # 25 + 75

    async def test_negative_quantity_reduces_count(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that negative quantity events reduce the total count (refund pattern)."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 3 agentic chunking events (reservations)
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.AGENTIC_CHUNKING,
                    quantity=1,
                    event_metadata={"document_id": i},
                )
            )

        # Create a refund event with quantity=-1
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_CHUNKING,
                quantity=-1,
                event_metadata={"document_id": 0, "reason": "chunking_failed"},
            )
        )

        # Get period count - should be 3 + (-1) = 2
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 2  # 3 reservations - 1 refund

    async def test_multiple_refunds_reduce_count_correctly(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that multiple refunds correctly reduce the count."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 5 reservations
        for i in range(5):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.AGENTIC_CHUNKING,
                    quantity=1,
                    event_metadata={"document_id": i},
                )
            )

        # Create 3 refunds (3 failed)
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.AGENTIC_CHUNKING,
                    quantity=-1,
                    event_metadata={"document_id": i, "reason": "chunking_failed"},
                )
            )

        # Get period count - should be 5 + (-3) = 2
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 2  # 5 reservations - 3 refunds

    async def test_refund_can_bring_count_to_zero(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that refunds can bring the count back to zero."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Reserve and immediately refund
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_CHUNKING,
                quantity=1,
                event_metadata={"document_id": 1},
            )
        )
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_CHUNKING,
                quantity=-1,
                event_metadata={"document_id": 1, "reason": "chunking_failed"},
            )
        )

        # Get period count - should be 0
        count = await repo.get_period_count(
            company_id=sample_company.id,
            event_type=UsageEventType.AGENTIC_CHUNKING,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 0

    async def test_get_document_count_for_period(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test counting STORAGE_UPLOAD events for document quota."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 5 storage upload events (documents)
        for i in range(5):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=1000 * (i + 1),
                    event_metadata={"document_id": i},
                )
            )

        # Get document count
        count = await repo.get_document_count_for_period(
            company_id=sample_company.id,
            start_date=period_start,
            end_date=period_end,
        )

        # Should count events, not sum quantities or bytes
        assert count == 5

    async def test_get_document_count_excludes_other_event_types(
        self, test_db, sample_company, sample_user_entity
    ):
        """Test that document count only counts STORAGE_UPLOAD events."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 3 storage upload events
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=1000,
                    event_metadata={"document_id": i},
                )
            )

        # Create other event types that should NOT be counted
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.CELL_OPERATION,
                event_metadata={"cell_id": 1},
            )
        )
        await repo.create(
            UsageEventCreateModel(
                company_id=sample_company.id,
                user_id=sample_user_entity.id,
                event_type=UsageEventType.AGENTIC_CHUNKING,
                event_metadata={"document_id": 1},
            )
        )

        # Get document count - should only count STORAGE_UPLOAD events
        count = await repo.get_document_count_for_period(
            company_id=sample_company.id,
            start_date=period_start,
            end_date=period_end,
        )

        assert count == 3

    async def test_get_document_count_isolated_by_company(
        self, test_db, sample_company, second_company, sample_user_entity
    ):
        """Test that document count is properly isolated by company."""
        repo = UsageEventRepository(test_db)

        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=15)
        period_end = now + timedelta(days=15)

        # Create 3 documents for company 1
        for i in range(3):
            await repo.create(
                UsageEventCreateModel(
                    company_id=sample_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=1000,
                    event_metadata={"document_id": i},
                )
            )

        # Create 7 documents for company 2
        for i in range(7):
            await repo.create(
                UsageEventCreateModel(
                    company_id=second_company.id,
                    user_id=sample_user_entity.id,
                    event_type=UsageEventType.STORAGE_UPLOAD,
                    file_size_bytes=2000,
                    event_metadata={"document_id": i},
                )
            )

        # Check counts are isolated
        count1 = await repo.get_document_count_for_period(
            company_id=sample_company.id,
            start_date=period_start,
            end_date=period_end,
        )
        count2 = await repo.get_document_count_for_period(
            company_id=second_company.id,
            start_date=period_start,
            end_date=period_end,
        )

        assert count1 == 3
        assert count2 == 7
