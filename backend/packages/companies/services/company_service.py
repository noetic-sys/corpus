from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.companies.repositories.company_repository import CompanyRepository
from packages.companies.models.domain.company import (
    Company,
    CompanyCreateModel,
    CompanyUpdateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class CompanyService:
    """Service for handling company operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.company_repo = CompanyRepository(db_session)

    @trace_span
    async def create_company(self, company_data: CompanyCreateModel) -> Company:
        """Create a new company."""
        logger.info(f"Creating company: {company_data.name}")

        # Check if company name already exists
        if company_data.domain:
            existing = await self.company_repo.get_by_domain(company_data.domain)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Company with domain '{company_data.domain}' already exists",
                )

        # Create company
        company = await self.company_repo.create(company_data)

        logger.info(f"Created company with ID: {company.id}")
        return company

    @trace_span
    async def create_personal_company(
        self, company_data: CompanyCreateModel
    ) -> Company:
        """Create a personal company (no domain conflict checking)."""
        logger.info(f"Creating personal company: {company_data.name}")

        # Personal companies don't have domains, so no conflict checking needed
        company = await self.company_repo.create(company_data)

        logger.info(f"Created personal company with ID: {company.id}")
        return company

    @trace_span
    async def get_company(self, company_id: int) -> Optional[Company]:
        """Get a company by ID."""
        return await self.company_repo.get(company_id)

    @trace_span
    async def get_by_domain(self, domain: str) -> Optional[Company]:
        """Get company by domain (for SSO)."""
        return await self.company_repo.get_by_domain(domain)

    @trace_span
    async def get_all_companies(self) -> List[Company]:
        """Get all companies."""
        return await self.company_repo.get_multi()

    @trace_span
    async def update_company(
        self, company_id: int, company_update: CompanyUpdateModel
    ) -> Optional[Company]:
        """Update a company."""
        # Check if company exists
        existing = await self.company_repo.get(company_id)
        if not existing:
            return None

        # Check if new domain conflicts with existing companies
        if company_update.domain is not None:
            domain_exists = await self.company_repo.get_by_domain(company_update.domain)
            if domain_exists and domain_exists.id != company_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Company with domain '{company_update.domain}' already exists",
                )

        company = await self.company_repo.update(company_id, company_update)
        if company:
            logger.info(f"Updated company {company_id}")
        return company

    @trace_span
    async def delete_company(self, company_id: int) -> bool:
        """Delete a company."""
        success = await self.company_repo.delete(company_id)
        if success:
            logger.info(f"Deleted company {company_id}")
        return success
