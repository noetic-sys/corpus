from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, update

from common.repositories.base import BaseRepository
from common.providers.caching import cache
from packages.users.models.database.user import UserEntity
from packages.users.models.domain.user import User
from packages.users.cache_keys import user_by_sso_key
from common.core.otel_axiom_exporter import trace_span


class UserRepository(BaseRepository[UserEntity, User]):
    def __init__(self):
        super().__init__(UserEntity, User)

    @trace_span
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        async with self._get_session() as session:
            result = await session.execute(
                select(UserEntity).where(
                    UserEntity.email == email, UserEntity.deleted == False
                )
            )
            db_user = result.scalar_one_or_none()
            return self._entity_to_domain(db_user) if db_user else None

    @trace_span
    @cache(User, ttl=7200, key_generator=user_by_sso_key)
    async def get_by_sso(self, sso_provider: str, sso_user_id: str) -> Optional[User]:
        """Get user by SSO provider and user ID."""
        async with self._get_session() as session:
            result = await session.execute(
                select(UserEntity).where(
                    UserEntity.sso_provider == sso_provider,
                    UserEntity.sso_user_id == sso_user_id,
                    UserEntity.deleted == False,
                )
            )
            db_user = result.scalar_one_or_none()
            return self._entity_to_domain(db_user) if db_user else None

    @trace_span
    async def get_by_company_id(
        self, company_id: int, skip: int = 0, limit: int = 100
    ) -> List[User]:
        """Get all users for a company."""
        async with self._get_session() as session:
            result = await session.execute(
                select(UserEntity)
                .where(UserEntity.company_id == company_id, UserEntity.deleted == False)
                .offset(skip)
                .limit(limit)
            )
            db_users = result.scalars().all()
            return self._entities_to_domain(db_users)

    @trace_span
    async def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        async with self._get_session() as session:
            await session.execute(
                update(UserEntity)
                .where(UserEntity.id == user_id)
                .values(last_login_at=datetime.now(timezone.utc))
            )
