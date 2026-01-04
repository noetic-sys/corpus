import pytest
from packages.auth.repositories.service_account_repository import (
    ServiceAccountRepository,
)
from packages.auth.models.database.service_account import ServiceAccountEntity
import hashlib


class TestServiceAccountRepository:
    """Test ServiceAccountRepository methods."""

    @pytest.fixture
    async def repository(self):
        """Create repository instance."""
        return ServiceAccountRepository()

    @pytest.fixture
    async def sample_service_account(self, test_db, sample_company):
        """Create a sample service account."""
        api_key_hash = hashlib.sha256(b"test_api_key").hexdigest()
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

    async def test_get_by_api_key_hash(self, repository, sample_service_account):
        """Test getting a service account by API key hash."""
        api_key_hash = sample_service_account.api_key_hash
        result = await repository.get_by_api_key_hash(api_key_hash)

        assert result is not None
        assert result.id == sample_service_account.id
        assert result.name == "Test Service Account"

    async def test_get_by_api_key_hash_not_found(self, repository):
        """Test getting service account with invalid hash returns None."""
        result = await repository.get_by_api_key_hash("invalid_hash")
        assert result is None

    async def test_get_by_api_key_hash_inactive(
        self, repository, sample_service_account, test_db
    ):
        """Test getting inactive service account returns None."""
        # Deactivate the account
        account = await test_db.get(ServiceAccountEntity, sample_service_account.id)
        account.is_active = False
        await test_db.commit()

        result = await repository.get_by_api_key_hash(
            sample_service_account.api_key_hash
        )
        assert result is None

    async def test_get_by_api_key_hash_deleted(
        self, repository, sample_service_account, test_db
    ):
        """Test getting deleted service account returns None."""
        # Mark as deleted
        account = await test_db.get(ServiceAccountEntity, sample_service_account.id)
        account.deleted = True
        await test_db.commit()

        result = await repository.get_by_api_key_hash(
            sample_service_account.api_key_hash
        )
        assert result is None
