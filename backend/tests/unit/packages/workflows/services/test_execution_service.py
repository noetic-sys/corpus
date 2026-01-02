import pytest
from packages.workflows.models.domain.execution import (
    WorkflowExecutionUpdateModel,
)
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.services.execution_service import WorkflowExecutionService
from packages.workflows.models.database.workflow import (
    WorkflowEntity,
    WorkflowExecutionEntity,
)


class TestWorkflowExecutionService:
    """Test WorkflowExecutionService methods."""

    @pytest.fixture
    def mock_temporal_client(self):
        """Create mock Temporal client."""
        mock = AsyncMock()
        mock.start_workflow = AsyncMock()
        return mock

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return WorkflowExecutionService(test_db)

    async def test_trigger_execution(
        self, service, sample_workflow, sample_company, test_db, mock_temporal_client
    ):
        """Test triggering a workflow execution."""
        with patch(
            "packages.workflows.services.execution_service.Client.connect",
            return_value=mock_temporal_client,
        ):
            execution = await service.trigger_execution(
                workflow_id=sample_workflow.id,
                user_id=1,
                company_id=sample_company.id,
            )

            assert execution is not None
            assert execution.workflow_id == sample_workflow.id
            assert execution.company_id == sample_company.id
            assert execution.status == "pending"
            mock_temporal_client.start_workflow.assert_called_once()

    async def test_trigger_execution_nonexistent_workflow(
        self, service, sample_company, mock_temporal_client
    ):
        """Test triggering execution for nonexistent workflow raises error."""
        with patch(
            "packages.workflows.services.execution_service.Client.connect",
            return_value=mock_temporal_client,
        ):
            with pytest.raises(ValueError, match="not found"):
                await service.trigger_execution(
                    workflow_id=999,
                    user_id=1,
                    company_id=sample_company.id,
                )

    async def test_trigger_execution_wrong_company(
        self, service, sample_workflow, second_company, mock_temporal_client
    ):
        """Test triggering execution for workflow from different company raises error."""
        with patch(
            "packages.workflows.services.execution_service.Client.connect",
            return_value=mock_temporal_client,
        ):
            with pytest.raises(ValueError, match="not found"):
                await service.trigger_execution(
                    workflow_id=sample_workflow.id,
                    user_id=1,
                    company_id=second_company.id,
                )

    async def test_trigger_execution_deleted_workflow(
        self, service, sample_workflow, sample_company, test_db, mock_temporal_client
    ):
        """Test triggering execution for deleted workflow raises error (not found)."""
        # Mark workflow as deleted at DB level
        workflow_entity = await test_db.get(WorkflowEntity, sample_workflow.id)
        workflow_entity.deleted = True
        await test_db.commit()

        with patch(
            "packages.workflows.services.execution_service.Client.connect",
            return_value=mock_temporal_client,
        ):
            with pytest.raises(ValueError, match="not found"):
                await service.trigger_execution(
                    workflow_id=sample_workflow.id,
                    user_id=1,
                    company_id=sample_company.id,
                )

    async def test_get_execution(
        self, service, sample_workflow_execution, sample_company
    ):
        """Test getting an execution by ID."""
        execution = await service.get_execution(
            sample_workflow_execution.id, sample_company.id
        )

        assert execution is not None
        assert execution.id == sample_workflow_execution.id
        assert execution.company_id == sample_company.id

    async def test_get_execution_wrong_company(
        self, service, sample_workflow_execution, second_company
    ):
        """Test getting execution with wrong company returns None."""
        execution = await service.get_execution(
            sample_workflow_execution.id, second_company.id
        )

        assert execution is None

    async def test_list_executions(
        self, service, sample_workflow, sample_company, test_db
    ):
        """Test listing executions for a workflow."""
        # Create multiple executions
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        execution2 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="failed",
        )
        test_db.add_all([execution1, execution2])
        await test_db.commit()

        executions = await service.list_executions(
            sample_workflow.id, sample_company.id
        )

        assert len(executions) == 2

    async def test_list_executions_wrong_company(
        self, service, sample_workflow, sample_company, second_company, test_db
    ):
        """Test listing executions with wrong company returns empty."""
        # Create execution for first company
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        test_db.add(execution1)
        await test_db.commit()

        # Try to list with different company
        executions = await service.list_executions(
            sample_workflow.id, second_company.id
        )

        assert len(executions) == 0

    async def test_get_last_execution(
        self, service, sample_workflow, sample_company, test_db
    ):
        """Test getting the last execution for a workflow."""
        # Create executions
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        test_db.add(execution1)
        await test_db.commit()
        await test_db.refresh(execution1)

        last_execution = await service.get_last_execution(
            sample_workflow.id, sample_company.id
        )

        assert last_execution is not None
        assert last_execution.id == execution1.id

    async def test_get_last_execution_wrong_company(
        self, service, sample_workflow, sample_company, second_company, test_db
    ):
        """Test getting last execution with wrong company returns None."""
        # Create execution for first company
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        test_db.add(execution1)
        await test_db.commit()

        # Try to get with different company
        last_execution = await service.get_last_execution(
            sample_workflow.id, second_company.id
        )

        assert last_execution is None

    async def test_get_last_successful_execution(
        self, service, sample_workflow, sample_company, test_db
    ):
        """Test getting the last successful execution."""
        # Create completed execution
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="completed",
        )
        test_db.add(execution1)
        await test_db.commit()
        await test_db.refresh(execution1)

        last_successful = await service.get_last_successful_execution(
            sample_workflow.id, sample_company.id
        )

        assert last_successful is not None
        assert last_successful.id == execution1.id
        assert last_successful.status == "completed"

    async def test_update_execution(
        self, service, sample_workflow_execution, sample_company
    ):
        """Test updating an execution."""

        update_data = WorkflowExecutionUpdateModel(
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )

        updated = await service.update_execution(
            sample_workflow_execution.id,
            sample_company.id,
            update_data,
        )

        assert updated is not None
        assert updated.status == "completed"
        assert updated.completed_at is not None

    async def test_update_execution_wrong_company(
        self, service, sample_workflow_execution, second_company
    ):
        """Test updating execution with wrong company returns None."""

        update_data = WorkflowExecutionUpdateModel(
            status="completed",
        )

        updated = await service.update_execution(
            sample_workflow_execution.id,
            second_company.id,
            update_data,
        )

        assert updated is None
