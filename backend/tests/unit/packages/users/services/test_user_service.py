import pytest
from fastapi import HTTPException

from packages.users.models.database.user import UserEntity
from packages.users.services.user_service import UserService
from packages.users.models.domain.user import UserCreateModel, UserUpdateModel


class TestUserService:
    """Test UserService methods."""

    @pytest.fixture
    async def service(self):
        """Create service instance."""
        return UserService()

    async def test_create_user_success(self, service, sample_company):
        """Test successful user creation."""
        user_data = UserCreateModel(
            email="newuser@example.com",
            full_name="New User",
            company_id=sample_company.id,
            is_admin=False,
        )

        result = await service.create_user(user_data)

        assert result.email == "newuser@example.com"
        assert result.full_name == "New User"
        assert result.company_id == sample_company.id
        assert result.is_admin is False

    async def test_create_user_duplicate_email(
        self, service, sample_user_entity, sample_company
    ):
        """Test creating user with duplicate email."""
        user_data = UserCreateModel(
            email=sample_user_entity.email,
            full_name="Duplicate User",
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert f"User with email '{sample_user_entity.email}' already exists" in str(
            exc_info.value.detail
        )

    async def test_create_sso_user_success(self, service, sample_company):
        """Test successful SSO user creation without email check."""
        user_data = UserCreateModel(
            email="ssouser@example.com",
            full_name="SSO User",
            company_id=sample_company.id,
            sso_provider="auth0",
            sso_user_id="auth0|test123",
        )

        result = await service.create_sso_user(user_data)

        assert result.email == "ssouser@example.com"
        assert result.full_name == "SSO User"
        assert result.sso_provider == "auth0"
        assert result.sso_user_id == "auth0|test123"

    async def test_get_user_exists(self, service, sample_user_entity):
        """Test getting existing user."""
        result = await service.get_user(sample_user_entity.id)

        assert result is not None
        assert result.id == sample_user_entity.id
        assert result.email == sample_user_entity.email

    async def test_get_user_not_exists(self, service):
        """Test getting non-existent user."""
        result = await service.get_user(999)
        assert result is None

    async def test_get_by_email(self, service, sample_user_entity):
        """Test getting user by email."""
        result = await service.get_by_email(sample_user_entity.email)

        assert result is not None
        assert result.id == sample_user_entity.id
        assert result.email == sample_user_entity.email

    async def test_get_by_sso(self, service, sso_user_entity):
        """Test getting user by SSO."""
        result = await service.get_by_sso("auth0", "auth0|123456")

        assert result is not None
        assert result.id == sso_user_entity.id
        assert result.sso_provider == "auth0"
        assert result.sso_user_id == "auth0|123456"

    async def test_get_by_company_id(self, service, test_db, sample_company):
        """Test getting users by company ID."""

        users = []
        for i in range(3):
            user = UserEntity(
                email=f"companyuser{i}@test.com",
                full_name=f"Company User {i}",
                company_id=sample_company.id,
            )
            users.append(user)
        test_db.add_all(users)
        await test_db.commit()

        result = await service.get_by_company_id(sample_company.id)

        assert len(result) == 3

    async def test_update_user_success(self, service, sample_user_entity):
        """Test successful user update."""
        update_data = UserUpdateModel(
            full_name="Updated Name",
            is_admin=True,
        )

        result = await service.update_user(sample_user_entity.id, update_data)

        assert result is not None
        assert result.full_name == "Updated Name"
        assert result.is_admin is True
        assert result.email == sample_user_entity.email  # Unchanged

    async def test_update_user_email_conflict(self, service, test_db, sample_company):
        """Test updating user email to existing email."""
        # Create two users
        user1 = UserEntity(
            email="user1@test.com",
            full_name="User 1",
            company_id=sample_company.id,
        )
        user2 = UserEntity(
            email="user2@test.com",
            full_name="User 2",
            company_id=sample_company.id,
        )
        test_db.add_all([user1, user2])
        await test_db.commit()
        await test_db.refresh(user1)
        await test_db.refresh(user2)

        update_data = UserUpdateModel(email="user2@test.com")

        with pytest.raises(HTTPException) as exc_info:
            await service.update_user(user1.id, update_data)

        assert exc_info.value.status_code == 400
        assert "User with email 'user2@test.com' already exists" in str(
            exc_info.value.detail
        )

    async def test_update_user_not_found(self, service):
        """Test updating non-existent user."""
        update_data = UserUpdateModel(full_name="Updated")

        result = await service.update_user(999, update_data)
        assert result is None

    async def test_update_last_login(self, service, sample_user_entity):
        """Test updating user's last login."""
        await service.update_last_login(sample_user_entity.id)

        updated_user = await service.get_user(sample_user_entity.id)
        assert updated_user.last_login_at is not None

    async def test_delete_user_success(self, service, sample_user_entity):
        """Test successful user deletion."""
        success = await service.delete_user(sample_user_entity.id)
        assert success is True

        result = await service.get_user(sample_user_entity.id)
        assert result is None

    async def test_delete_user_not_found(self, service):
        """Test deleting non-existent user."""
        success = await service.delete_user(999)
        assert success is False

    async def test_service_initialization(self):
        """Test service properly initializes."""
        service = UserService()
        assert service.user_repo is not None
