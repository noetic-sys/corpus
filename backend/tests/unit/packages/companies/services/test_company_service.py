import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.companies.services.company_service import CompanyService
from packages.companies.models.domain.company import (
    CompanyCreateModel,
    CompanyUpdateModel,
)
from packages.companies.models.database.company import CompanyEntity


class TestCompanyService:
    """Test CompanyService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return CompanyService(test_db)

    async def test_create_company_success(self, service):
        """Test successful company creation."""
        company_data = CompanyCreateModel(
            name="New Company",
            domain="new.com",
            description="A new company",
        )

        result = await service.create_company(company_data)

        assert result.name == "New Company"
        assert result.domain == "new.com"
        assert result.description == "A new company"

    async def test_create_company_duplicate_domain(self, service, second_company):
        """Test creating company with duplicate domain."""
        company_data = CompanyCreateModel(
            name="Another Company",
            domain=second_company.domain,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_company(company_data)

        assert exc_info.value.status_code == 400
        assert f"Company with domain '{second_company.domain}' already exists" in str(
            exc_info.value.detail
        )

    async def test_create_company_without_domain(self, service):
        """Test creating company without domain."""
        company_data = CompanyCreateModel(
            name="No Domain Company",
            domain=None,
        )

        result = await service.create_company(company_data)

        assert result.name == "No Domain Company"
        assert result.domain is None

    async def test_create_personal_company_success(self, service):
        """Test successful personal company creation."""
        company_data = CompanyCreateModel(
            name="Personal Company",
            domain=None,
            description="Personal account",
        )

        result = await service.create_personal_company(company_data)

        assert result.name == "Personal Company"
        assert result.domain is None
        assert result.description == "Personal account"

    async def test_get_company_exists(self, service, sample_company):
        """Test getting existing company."""
        result = await service.get_company(sample_company.id)

        assert result is not None
        assert result.id == sample_company.id
        assert result.name == sample_company.name

    async def test_get_company_not_exists(self, service):
        """Test getting non-existent company."""
        result = await service.get_company(999)
        assert result is None

    async def test_get_by_domain(self, service, second_company):
        """Test getting company by domain."""
        result = await service.get_by_domain("second.com")

        assert result is not None
        assert result.id == second_company.id
        assert result.domain == "second.com"

    async def test_get_by_domain_not_exists(self, service):
        """Test getting company by non-existent domain."""
        result = await service.get_by_domain("nonexistent.com")
        assert result is None

    async def test_get_all_companies(self, service, test_db):
        """Test getting all companies."""

        companies = []
        for i in range(3):
            company = CompanyEntity(name=f"Test Company {i}", domain=f"test{i}.com")
            companies.append(company)
        test_db.add_all(companies)
        await test_db.commit()

        result = await service.get_all_companies()

        assert len(result) >= 3

    async def test_update_company_success(self, service, sample_company):
        """Test successful company update."""
        update_data = CompanyUpdateModel(
            name="Updated Company Name",
            description="Updated description",
        )

        result = await service.update_company(sample_company.id, update_data)

        assert result is not None
        assert result.name == "Updated Company Name"
        assert result.description == "Updated description"

    async def test_update_company_domain_conflict(
        self, service, sample_company, second_company
    ):
        """Test updating company domain to existing domain."""
        update_data = CompanyUpdateModel(domain=second_company.domain)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_company(sample_company.id, update_data)

        assert exc_info.value.status_code == 400
        assert f"Company with domain '{second_company.domain}' already exists" in str(
            exc_info.value.detail
        )

    async def test_update_company_not_found(self, service):
        """Test updating non-existent company."""
        update_data = CompanyUpdateModel(name="Updated")

        result = await service.update_company(999, update_data)
        assert result is None

    async def test_delete_company_success(self, service, test_db):
        """Test successful company deletion."""

        company = CompanyEntity(name="To Delete", domain="delete.com")
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)

        success = await service.delete_company(company.id)
        assert success is True

        result = await service.get_company(company.id)
        assert result is None

    async def test_delete_company_not_found(self, service):
        """Test deleting non-existent company."""
        success = await service.delete_company(999)
        assert success is False

    async def test_service_initialization(self, test_db):
        """Test service properly initializes."""
        service = CompanyService(test_db)
        assert service.db_session == test_db
        assert service.company_repo is not None

    async def test_create_company_minimal_data(self, service):
        """Test creating company with minimal required data."""
        company_data = CompanyCreateModel(name="Minimal Company")

        result = await service.create_company(company_data)

        assert result.name == "Minimal Company"
        assert result.domain is None
        assert result.description is None

    async def test_update_company_partial(self, service, sample_company):
        """Test partial company update."""
        update_data = CompanyUpdateModel(description="Only description updated")

        result = await service.update_company(sample_company.id, update_data)

        assert result is not None
        assert result.description == "Only description updated"
        assert result.name == sample_company.name  # Unchanged
