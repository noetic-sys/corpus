import pytest
from unittest.mock import patch
from common.execution.workflow_framework.service_accounts import (
    create_execution_service_account,
    cleanup_execution_service_account,
)
from packages.auth.models.database.service_account import ServiceAccountEntity


@patch("common.execution.workflow_framework.service_accounts.get_db")
class TestServiceAccountLifecycle:
    """Tests for service account lifecycle management."""

    @pytest.mark.asyncio
    async def test_create_execution_service_account(
        self, mock_get_db, test_db, sample_company
    ):
        """Test creating a service account for workflow execution."""

        # Mock get_db to yield test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Call the function with real DB
        account_id, api_key = await create_execution_service_account(
            execution_id=456, company_id=sample_company.id
        )

        # Assertions
        assert isinstance(account_id, int)
        assert api_key.startswith("sa_")
        assert len(api_key) > 10

    @pytest.mark.asyncio
    async def test_cleanup_execution_service_account(
        self, mock_get_db, test_db, sample_company
    ):
        """Test cleaning up a service account after execution."""

        # Mock get_db to yield test database session (needs to be fresh each call)
        def make_mock_db_generator():
            async def mock_db_generator():
                yield test_db

            return mock_db_generator()

        mock_get_db.side_effect = make_mock_db_generator

        # First create a service account
        account_id, api_key = await create_execution_service_account(
            execution_id=789, company_id=sample_company.id
        )

        # Refresh to get latest state
        await test_db.refresh(await test_db.get(ServiceAccountEntity, account_id))

        # Now clean it up
        await cleanup_execution_service_account(
            service_account_id=account_id, company_id=sample_company.id
        )

        # Refresh to get the updated deleted status
        await test_db.refresh(await test_db.get(ServiceAccountEntity, account_id))

        # Verify it's deleted (soft delete)
        account = await test_db.get(ServiceAccountEntity, account_id)
        assert account.deleted is True
