import secrets
import hashlib
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth.repositories.service_account_repository import (
    ServiceAccountRepository,
)
from packages.auth.models.domain.service_account import (
    ServiceAccount,
    ServiceAccountCreate,
    ServiceAccountUpdate,
    ServiceAccountWithApiKey,
)
from packages.auth.models.database.service_account import ServiceAccountEntity
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ServiceAccountService:
    """Service for handling service account operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.service_account_repo = ServiceAccountRepository(db_session)

    @staticmethod
    def _generate_api_key() -> str:
        """Generate a secure random API key."""
        # Format: sa_<32 random bytes as hex>
        return f"sa_{secrets.token_hex(32)}"

    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    @trace_span
    async def create_service_account(
        self, account_data: ServiceAccountCreate
    ) -> ServiceAccountWithApiKey:
        """Create a new service account and return it with the plain-text API key."""
        logger.info(
            f"Creating service account: {account_data.name} for company {account_data.company_id}"
        )

        # Generate API key
        api_key = self._generate_api_key()
        api_key_hash = self._hash_api_key(api_key)

        # Create entity with hashed API key
        entity = ServiceAccountEntity(
            name=account_data.name,
            description=account_data.description,
            company_id=account_data.company_id,
            api_key_hash=api_key_hash,
        )

        self.db_session.add(entity)
        await self.db_session.flush()
        await self.db_session.refresh(entity)

        service_account = ServiceAccount.model_validate(entity)

        logger.info(f"Created service account with ID: {service_account.id}")

        return ServiceAccountWithApiKey(
            service_account=service_account, api_key=api_key
        )

    @trace_span
    async def get_service_account(
        self, account_id: int, company_id: int
    ) -> Optional[ServiceAccount]:
        """Get a service account by ID (scoped to company)."""
        account = await self.service_account_repo.get(account_id, company_id=company_id)
        return account

    @trace_span
    async def get_all_service_accounts(
        self, company_id: Optional[int] = None, skip: int = 0, limit: int = 100
    ) -> List[ServiceAccount]:
        """Get all service accounts for a company."""
        return await self.service_account_repo.get_multi(
            skip=skip, limit=limit, company_id=company_id
        )

    @trace_span
    async def update_service_account(
        self, account_id: int, company_id: int, account_update: ServiceAccountUpdate
    ) -> Optional[ServiceAccount]:
        """Update a service account."""
        # Verify account exists and belongs to company
        existing = await self.service_account_repo.get(
            account_id, company_id=company_id
        )
        if not existing:
            return None

        account = await self.service_account_repo.update(account_id, account_update)
        if account:
            logger.info(f"Updated service account {account_id}")
        return account

    @trace_span
    async def delete_service_account(self, account_id: int, company_id: int) -> bool:
        """Soft delete a service account."""
        # Verify account exists and belongs to company
        logger.info("Deleting service account????")
        existing = await self.service_account_repo.get(
            account_id, company_id=company_id
        )
        if not existing:
            return False

        logger.info(f"Found service account with id {existing.id}")
        success = await self.service_account_repo.soft_delete(account_id)
        logger.info(f"Delete success {success}")
        if success:
            logger.info(f"Deleted service account {account_id}")
        return success

    @trace_span
    async def authenticate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        """Authenticate an API key and return authenticated user context."""
        if not api_key.startswith("sa_"):
            return None

        api_key_hash = self._hash_api_key(api_key)
        account = await self.service_account_repo.get_by_api_key_hash(api_key_hash)

        if not account:
            return None

        # Return authenticated user context with service account's company
        # user_id is the service account id
        return AuthenticatedUser(user_id=account.id, company_id=account.company_id)
