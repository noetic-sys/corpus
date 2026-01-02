import pytest
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from packages.auth.services.service_account_service import ServiceAccountService
from packages.auth.models.domain.service_account import (
    ServiceAccountCreate,
    ServiceAccountUpdate,
)
from packages.auth.models.database.service_account import ServiceAccountEntity


class TestServiceAccountService:
    """Test ServiceAccountService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return ServiceAccountService(test_db)

    @pytest.fixture
    async def sample_service_account(self, test_db: AsyncSession, sample_company):
        """Create a sample service account."""

        api_key_hash = hashlib.sha256(b"test_api_key_123").hexdigest()
        account = ServiceAccountEntity(
            name="Test Service Account",
            description="Test description",
            company_id=sample_company.id,
            api_key_hash=api_key_hash,
            is_active=True,
        )
        test_db.add(account)
        await test_db.commit()
        await test_db.refresh(account)
        return account

    async def test_create_service_account(self, service, sample_company):
        """Test creating a service account."""
        account_data = ServiceAccountCreate(
            name="New Service Account",
            description="New test account",
            company_id=sample_company.id,
        )

        result = await service.create_service_account(account_data)

        assert result is not None
        assert result.service_account.name == "New Service Account"
        assert result.service_account.company_id == sample_company.id
        assert result.api_key.startswith("sa_")
        assert len(result.api_key) > 10

    async def test_get_service_account(
        self, service, sample_service_account, sample_company
    ):
        """Test getting a service account by ID."""
        result = await service.get_service_account(
            sample_service_account.id, sample_company.id
        )

        assert result is not None
        assert result.id == sample_service_account.id
        assert result.name == "Test Service Account"

    async def test_get_service_account_wrong_company(
        self, service, sample_service_account, second_company
    ):
        """Test getting service account with wrong company returns None."""
        result = await service.get_service_account(
            sample_service_account.id, second_company.id
        )

        assert result is None

    async def test_get_all_service_accounts(
        self, service, sample_service_account, sample_company, test_db
    ):
        """Test listing all service accounts for a company."""
        # Create another account

        account2 = ServiceAccountEntity(
            name="Second Account",
            company_id=sample_company.id,
            api_key_hash=hashlib.sha256(b"another_key").hexdigest(),
        )
        test_db.add(account2)
        await test_db.commit()

        results = await service.get_all_service_accounts(sample_company.id)

        assert len(results) == 2
        assert any(a.name == "Test Service Account" for a in results)
        assert any(a.name == "Second Account" for a in results)

    async def test_update_service_account(
        self, service, sample_service_account, sample_company
    ):
        """Test updating a service account."""
        update_data = ServiceAccountUpdate(
            name="Updated Name",
            description="Updated description",
        )

        result = await service.update_service_account(
            sample_service_account.id, sample_company.id, update_data
        )

        assert result is not None
        assert result.name == "Updated Name"
        assert result.description == "Updated description"

    async def test_update_service_account_wrong_company(
        self, service, sample_service_account, second_company
    ):
        """Test updating service account with wrong company returns None."""
        update_data = ServiceAccountUpdate(name="Updated")

        result = await service.update_service_account(
            sample_service_account.id, second_company.id, update_data
        )

        assert result is None

    async def test_delete_service_account(
        self, service, sample_service_account, sample_company
    ):
        """Test soft deleting a service account."""
        success = await service.delete_service_account(
            sample_service_account.id, sample_company.id
        )

        assert success is True

        # Verify it's not returned by get
        account = await service.get_service_account(
            sample_service_account.id, sample_company.id
        )
        assert account is None

    async def test_delete_service_account_wrong_company(
        self, service, sample_service_account, second_company
    ):
        """Test deleting service account with wrong company returns False."""
        success = await service.delete_service_account(
            sample_service_account.id, second_company.id
        )

        assert success is False

    async def test_authenticate_api_key(
        self, service, sample_service_account, sample_company
    ):
        """Test authenticating with a valid API key."""
        # We need to create an account with a known API key

        api_key = "sa_test123456789"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Create account with known hash

        account_data = ServiceAccountCreate(
            name="Auth Test Account",
            company_id=sample_company.id,
        )
        result = await service.create_service_account(account_data)

        # Now authenticate with the returned API key
        authenticated = await service.authenticate_api_key(result.api_key)

        assert authenticated is not None
        assert authenticated.user_id == result.service_account.id
        assert authenticated.company_id == sample_company.id

    async def test_authenticate_api_key_invalid_prefix(self, service):
        """Test authenticating with invalid prefix returns None."""
        result = await service.authenticate_api_key("invalid_key")
        assert result is None

    async def test_authenticate_api_key_not_found(self, service):
        """Test authenticating with non-existent key returns None."""
        result = await service.authenticate_api_key("sa_nonexistent123")
        assert result is None
