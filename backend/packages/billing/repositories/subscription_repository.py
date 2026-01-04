"""
Repository for subscription management.
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select

from common.repositories.base import BaseRepository
from packages.billing.models.database.subscription import SubscriptionEntity
from packages.billing.models.domain.subscription import Subscription
from packages.billing.models.domain.enums import SubscriptionStatus
from common.core.otel_axiom_exporter import trace_span


class SubscriptionRepository(BaseRepository[SubscriptionEntity, Subscription]):
    """Repository for managing company subscriptions."""

    def __init__(self):
        super().__init__(SubscriptionEntity, Subscription)

    @trace_span
    async def get_by_company_id(self, company_id: int) -> Optional[Subscription]:
        """Get active subscription for a company."""
        async with self._get_session() as session:
            result = await session.execute(
                select(SubscriptionEntity).where(
                    SubscriptionEntity.company_id == company_id
                )
            )
            db_subscription = result.scalar_one_or_none()
            return self._entity_to_domain(db_subscription) if db_subscription else None

    @trace_span
    async def get_expiring_soon(self, days: int = 7) -> list[Subscription]:
        """Get subscriptions expiring in the next N days."""
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = cutoff_date + timedelta(days=days)

        async with self._get_session() as session:
            result = await session.execute(
                select(SubscriptionEntity).where(
                    SubscriptionEntity.current_period_end >= cutoff_date,
                    SubscriptionEntity.current_period_end <= end_date,
                    SubscriptionEntity.status == SubscriptionStatus.ACTIVE.value,
                )
            )
            db_subscriptions = result.scalars().all()
            return [self._entity_to_domain(sub) for sub in db_subscriptions]

    @trace_span
    async def get_past_due(self) -> list[Subscription]:
        """Get all subscriptions in past_due status."""
        async with self._get_session() as session:
            result = await session.execute(
                select(SubscriptionEntity).where(
                    SubscriptionEntity.status == SubscriptionStatus.PAST_DUE.value
                )
            )
            db_subscriptions = result.scalars().all()
            return [self._entity_to_domain(sub) for sub in db_subscriptions]
