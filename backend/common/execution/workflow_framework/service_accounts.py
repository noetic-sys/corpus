"""
Service account lifecycle management.

Handles creation and cleanup of service accounts for workflow executions.
"""

from typing import Tuple

from common.db.session import get_db
from packages.auth.services.service_account_service import ServiceAccountService
from packages.auth.models.domain.service_account import ServiceAccountCreate
import logging

logger = logging.getLogger(__name__)


async def create_execution_service_account(
    execution_id: int, company_id: int
) -> Tuple[int, str]:
    """
    Create service account for workflow execution.

    Args:
        execution_id: Workflow execution ID
        company_id: Company ID

    Returns:
        Tuple of (service_account_id, api_key)
    """
    account_with_key = None
    async for db_session in get_db():
        service_account_service = ServiceAccountService(db_session)

        account_with_key = await service_account_service.create_service_account(
            ServiceAccountCreate(
                name=f"Workflow Execution {execution_id}",
                description=f"Service account for workflow execution {execution_id}",
                company_id=company_id,
            )
        )

    if account_with_key is None:
        raise ValueError("Unable to create key")

    return (account_with_key.service_account.id, account_with_key.api_key)


async def cleanup_execution_service_account(
    service_account_id: int, company_id: int
) -> None:
    """
    Cleanup service account after workflow execution.

    Args:
        service_account_id: Service account ID to delete
        company_id: Company ID for authorization
    """
    async for db_session in get_db():
        logger.info("getting service accounts")
        service_account_service = ServiceAccountService(db_session)
        logger.info(await service_account_service.get_all_service_accounts())
        await service_account_service.delete_service_account(
            service_account_id, company_id
        )
