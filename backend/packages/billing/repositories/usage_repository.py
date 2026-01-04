"""
Repository for usage event tracking.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import select, func, text, update

from common.repositories.base import BaseRepository
from packages.billing.models.database.usage import UsageEventEntity
from packages.billing.models.domain.usage import UsageEvent
from packages.billing.models.domain.enums import UsageEventType
from common.core.otel_axiom_exporter import trace_span


class UsageEventRepository(BaseRepository[UsageEventEntity, UsageEvent]):
    """Repository for managing usage events."""

    def __init__(self):
        super().__init__(UsageEventEntity, UsageEvent)

    @trace_span
    async def get_monthly_count(
        self, company_id: int, event_type: UsageEventType, year: int, month: int
    ) -> int:
        """Get sum of quantity for a specific month."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        async with self._get_session() as session:
            result = await session.execute(
                select(func.coalesce(func.sum(UsageEventEntity.quantity), 0)).where(
                    UsageEventEntity.company_id == company_id,
                    UsageEventEntity.event_type == event_type.value,
                    UsageEventEntity.created_at >= start_date,
                    UsageEventEntity.created_at < end_date,
                )
            )
            return result.scalar_one() or 0

    @trace_span
    async def get_period_count(
        self,
        company_id: int,
        event_type: UsageEventType,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """Get sum of quantity for a billing period."""
        async with self._get_session() as session:
            result = await session.execute(
                select(func.coalesce(func.sum(UsageEventEntity.quantity), 0)).where(
                    UsageEventEntity.company_id == company_id,
                    UsageEventEntity.event_type == event_type.value,
                    UsageEventEntity.created_at >= start_date,
                    UsageEventEntity.created_at < end_date,
                )
            )
            return result.scalar_one() or 0

    @trace_span
    async def get_by_user(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> list[UsageEvent]:
        """Get usage events for a specific user."""
        async with self._get_session() as session:
            result = await session.execute(
                select(UsageEventEntity)
                .where(UsageEventEntity.user_id == user_id)
                .order_by(UsageEventEntity.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            db_events = result.scalars().all()
            return [self._entity_to_domain(event) for event in db_events]

    @trace_span
    async def get_by_company_date_range(
        self,
        company_id: int,
        start_date: datetime,
        end_date: datetime,
        event_type: Optional[UsageEventType] = None,
    ) -> list[UsageEvent]:
        """Get usage events for a company within a date range."""
        async with self._get_session() as session:
            query = select(UsageEventEntity).where(
                UsageEventEntity.company_id == company_id,
                UsageEventEntity.created_at >= start_date,
                UsageEventEntity.created_at < end_date,
            )

            if event_type:
                query = query.where(UsageEventEntity.event_type == event_type.value)

            query = query.order_by(UsageEventEntity.created_at.desc())

            result = await session.execute(query)
            db_events = result.scalars().all()
            return [self._entity_to_domain(event) for event in db_events]

    @trace_span
    async def get_storage_bytes_for_period(
        self, company_id: int, start_date: datetime, end_date: datetime
    ) -> int:
        """
        Sum total file size bytes from document upload events for a billing period.

        Uses the file_size_bytes column for fast aggregation.
        Used for quota enforcement based on subscription billing period.
        """
        async with self._get_session() as session:
            result = await session.execute(
                select(
                    func.coalesce(func.sum(UsageEventEntity.file_size_bytes), 0)
                ).where(
                    UsageEventEntity.company_id == company_id,
                    UsageEventEntity.event_type == UsageEventType.STORAGE_UPLOAD.value,
                    UsageEventEntity.created_at >= start_date,
                    UsageEventEntity.created_at < end_date,
                )
            )
            return result.scalar_one() or 0

    @trace_span
    async def get_document_count_for_period(
        self, company_id: int, start_date: datetime, end_date: datetime
    ) -> int:
        """
        Count document upload events for a billing period.

        Each STORAGE_UPLOAD event represents one document upload.
        Used for document count quota enforcement.
        """
        async with self._get_session() as session:
            result = await session.execute(
                select(func.count(UsageEventEntity.id)).where(
                    UsageEventEntity.company_id == company_id,
                    UsageEventEntity.event_type == UsageEventType.STORAGE_UPLOAD.value,
                    UsageEventEntity.created_at >= start_date,
                    UsageEventEntity.created_at < end_date,
                )
            )
            return result.scalar_one() or 0

    @trace_span
    async def acquire_company_quota_lock(self, company_id: int) -> None:
        """
        Acquire an advisory lock for quota operations on a company.

        This serializes quota check + reserve operations for the same company,
        preventing race conditions. The lock is automatically released when
        the transaction commits or rolls back.

        Uses pg_advisory_xact_lock which is transaction-scoped.
        """
        async with self._get_session() as session:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:company_id)"),
                {"company_id": company_id},
            )

    @trace_span
    async def update_event_metadata(self, event_id: int, metadata: dict) -> None:
        """
        Update the event_metadata field for a usage event.

        Args:
            event_id: The usage event ID
            metadata: The new metadata dict to set
        """
        async with self._get_session() as session:
            await session.execute(
                update(UsageEventEntity)
                .where(UsageEventEntity.id == event_id)
                .values(event_metadata=metadata)
            )
