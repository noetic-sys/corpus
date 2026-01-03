import pytest

from packages.companies.repositories.company_repository import CompanyRepository
from packages.companies.models.database.company import CompanyEntity


class TestCompanyRepository:
    """Test CompanyRepository methods."""

    @pytest.fixture
    async def repository(self):
        """Create repository instance."""
        return CompanyRepository()

    async def test_get_by_domain_exists(self, repository, second_company):
        """Test getting existing company by domain."""
        result = await repository.get_by_domain("second.com")

        assert result is not None
        assert result.id == second_company.id
        assert result.domain == "second.com"
        assert result.name == "Second Test Company"

    async def test_get_by_domain_not_exists(self, repository):
        """Test getting non-existent company by domain."""
        result = await repository.get_by_domain("nonexistent.com")
        assert result is None

    async def test_get_by_domain_excludes_deleted(self, repository, test_db):
        """Test that get_by_domain excludes soft deleted companies."""
        deleted_company = CompanyEntity(
            name="Deleted Company",
            domain="deleted.com",
            deleted=True,
        )
        test_db.add(deleted_company)
        await test_db.commit()

        result = await repository.get_by_domain("deleted.com")
        assert result is None

    async def test_get_by_domain_case_sensitive(self, repository, second_company):
        """Test that domain lookup is case sensitive."""
        result = await repository.get_by_domain("SECOND.COM")
        assert result is None

    async def test_get_company_exists(self, repository, sample_company):
        """Test getting existing company by ID."""
        result = await repository.get(sample_company.id)

        assert result is not None
        assert result.id == sample_company.id
        assert result.name == sample_company.name

    async def test_get_company_not_exists(self, repository):
        """Test getting non-existent company by ID."""
        result = await repository.get(999)
        assert result is None

    async def test_get_excludes_deleted(self, repository, test_db):
        """Test that get excludes soft deleted companies."""
        deleted_company = CompanyEntity(
            name="Deleted Company",
            deleted=True,
        )
        test_db.add(deleted_company)
        await test_db.commit()
        await test_db.refresh(deleted_company)

        result = await repository.get(deleted_company.id)
        assert result is None

    async def test_entity_to_domain_conversion(self, repository, sample_company):
        """Test that entity to domain conversion works correctly."""
        result = await repository.get(sample_company.id)

        assert result is not None
        assert result.id == sample_company.id
        assert result.name == sample_company.name
        assert result.deleted == sample_company.deleted

    async def test_repository_initialization(self):
        """Test repository properly initializes."""
        repository = CompanyRepository()
        assert repository.entity_class is not None

    async def test_multiple_companies_different_domains(self, repository, test_db):
        """Test getting companies with different domains."""
        company1 = CompanyEntity(name="Company 1", domain="company1.com")
        company2 = CompanyEntity(name="Company 2", domain="company2.com")
        test_db.add_all([company1, company2])
        await test_db.commit()

        result1 = await repository.get_by_domain("company1.com")
        result2 = await repository.get_by_domain("company2.com")

        assert result1 is not None
        assert result1.name == "Company 1"
        assert result2 is not None
        assert result2.name == "Company 2"

    async def test_company_without_domain(self, repository, test_db):
        """Test handling company without domain."""
        company = CompanyEntity(name="No Domain Company", domain=None)
        test_db.add(company)
        await test_db.commit()
        await test_db.refresh(company)

        result = await repository.get(company.id)
        assert result is not None
        assert result.domain is None
