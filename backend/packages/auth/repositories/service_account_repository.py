from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.repositories.base import BaseRepository
from common.core.otel_axiom_exporter import trace_span
from packages.auth.models.database.service_account import ServiceAccountEntity
from packages.auth.models.domain.service_account import ServiceAccount


class ServiceAccountRepository(BaseRepository[ServiceAccountEntity, ServiceAccount]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(ServiceAccountEntity, ServiceAccount, db_session)

    @trace_span
    async def get_by_api_key_hash(self, api_key_hash: str) -> Optional[ServiceAccount]:
        """Get service account by API key hash."""
        result = await self.db_session.execute(
            select(ServiceAccountEntity).where(
                ServiceAccountEntity.api_key_hash == api_key_hash,
                ServiceAccountEntity.deleted == False,
                ServiceAccountEntity.is_active == True,
            )
        )
        db_account = result.scalar_one_or_none()
        return self._entity_to_domain(db_account) if db_account else None
