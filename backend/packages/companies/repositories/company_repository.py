from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.repositories.base import BaseRepository
from packages.companies.models.database.company import CompanyEntity
from packages.companies.models.domain.company import Company
from common.core.otel_axiom_exporter import trace_span


class CompanyRepository(BaseRepository[CompanyEntity, Company]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(CompanyEntity, Company, db_session)

    @trace_span
    async def get_by_domain(self, domain: str) -> Optional[Company]:
        """Get company by domain (for SSO)."""
        result = await self.db_session.execute(
            select(CompanyEntity).where(
                CompanyEntity.domain == domain, CompanyEntity.deleted == False
            )
        )
        db_company = result.scalar_one_or_none()
        return self._entity_to_domain(db_company) if db_company else None
