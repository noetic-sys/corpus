import pytest

from packages.users.repositories.user_repository import UserRepository
from packages.users.models.database.user import UserEntity


class TestUserRepository:
    """Test UserRepository methods."""

    @pytest.fixture
    async def repository(self):
        """Create repository instance."""
        return UserRepository()

    async def test_get_by_email_exists(self, repository, sample_user_entity):
        """Test getting existing user by email."""
        result = await repository.get_by_email("test@example.com")

        assert result is not None
        assert result.id == sample_user_entity.id
        assert result.email == "test@example.com"
        assert result.full_name == "Test User"

    async def test_get_by_email_not_exists(self, repository):
        """Test getting non-existent user by email."""
        result = await repository.get_by_email("nonexistent@example.com")
        assert result is None

    async def test_get_by_email_excludes_deleted(
        self, repository, test_db, sample_company
    ):
        """Test that get_by_email excludes soft deleted users."""
        deleted_user = UserEntity(
            email="deleted@example.com",
            full_name="Deleted User",
            company_id=sample_company.id,
            deleted=True,
        )
        test_db.add(deleted_user)
        await test_db.commit()

        result = await repository.get_by_email("deleted@example.com")
        assert result is None

    async def test_get_by_sso_exists(self, repository, sso_user_entity):
        """Test getting existing user by SSO provider and user ID."""
        result = await repository.get_by_sso("auth0", "auth0|123456")

        assert result is not None
        assert result.id == sso_user_entity.id
        assert result.email == "sso@example.com"
        assert result.sso_provider == "auth0"
        assert result.sso_user_id == "auth0|123456"

    async def test_get_by_sso_not_exists(self, repository):
        """Test getting non-existent user by SSO."""
        result = await repository.get_by_sso("auth0", "nonexistent")
        assert result is None

    async def test_get_by_company_id(self, repository, test_db, sample_company):
        """Test getting users by company ID."""
        users = []
        for i in range(3):
            user = UserEntity(
                email=f"user{i}@company.com",
                full_name=f"User {i}",
                company_id=sample_company.id,
            )
            users.append(user)
        test_db.add_all(users)
        await test_db.commit()

        result = await repository.get_by_company_id(sample_company.id)

        assert len(result) == 3
        emails = [user.email for user in result]
        assert "user0@company.com" in emails
        assert "user1@company.com" in emails
        assert "user2@company.com" in emails

    async def test_get_by_company_id_with_pagination(
        self, repository, test_db, sample_company
    ):
        """Test getting users by company ID with pagination."""
        users = []
        for i in range(5):
            user = UserEntity(
                email=f"user{i}@company.com",
                full_name=f"User {i}",
                company_id=sample_company.id,
            )
            users.append(user)
        test_db.add_all(users)
        await test_db.commit()

        result = await repository.get_by_company_id(sample_company.id, skip=0, limit=2)
        assert len(result) == 2

        result = await repository.get_by_company_id(sample_company.id, skip=2, limit=2)
        assert len(result) == 2

    async def test_update_last_login(self, repository, sample_user_entity):
        """Test updating user's last login timestamp."""
        user = await repository.get(sample_user_entity.id)
        assert user.last_login_at is None

        await repository.update_last_login(sample_user_entity.id)

        updated_user = await repository.get(sample_user_entity.id)
        assert updated_user.last_login_at is not None
