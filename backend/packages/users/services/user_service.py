from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.users.repositories.user_repository import UserRepository
from packages.users.models.domain.user import User, UserCreateModel, UserUpdateModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class UserService:
    """Service for handling user operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.user_repo = UserRepository(db_session)

    @trace_span
    async def create_user(self, user_data: UserCreateModel) -> User:
        """Create a new user."""
        logger.info(f"Creating user: {user_data.email}")

        # Check if user email already exists
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"User with email '{user_data.email}' already exists",
            )

        # Create user
        user = await self.user_repo.create(user_data)

        logger.info(f"Created user with ID: {user.id}")
        return user

    @trace_span
    async def create_sso_user(self, user_data: UserCreateModel) -> User:
        """Create a new SSO user (assumes SSO provider already verified uniqueness)."""
        logger.info(f"Creating SSO user: {user_data.email}")

        # For SSO users, we trust that the SSO provider has already
        # verified uniqueness via get_by_sso check
        user = await self.user_repo.create(user_data)

        logger.info(f"Created SSO user with ID: {user.id}")
        return user

    @trace_span
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return await self.user_repo.get(user_id)

    @trace_span
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repo.get_by_email(email)

    @trace_span
    async def get_by_sso(self, sso_provider: str, sso_user_id: str) -> Optional[User]:
        """Get user by SSO provider and user ID."""
        return await self.user_repo.get_by_sso(sso_provider, sso_user_id)

    @trace_span
    async def get_by_company_id(
        self, company_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get all users for a company."""
        return await self.user_repo.get_by_company_id(company_id, skip, limit)

    @trace_span
    async def get_all_users(self) -> List[User]:
        """Get all users."""
        return await self.user_repo.get_multi()

    @trace_span
    async def update_user(
        self, user_id: int, user_update: UserUpdateModel
    ) -> Optional[User]:
        """Update a user."""
        # Check if user exists
        existing = await self.user_repo.get(user_id)
        if not existing:
            return None

        # Check if new email conflicts with existing users
        if user_update.email is not None:
            email_exists = await self.user_repo.get_by_email(user_update.email)
            if email_exists and email_exists.id != user_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"User with email '{user_update.email}' already exists",
                )

        user = await self.user_repo.update(user_id, user_update)
        if user:
            logger.info(f"Updated user {user_id}")
        return user

    @trace_span
    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        await self.user_repo.update_last_login(user_id)

    @trace_span
    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        success = await self.user_repo.delete(user_id)
        if success:
            logger.info(f"Deleted user {user_id}")
        return success
