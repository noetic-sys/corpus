import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.repositories.execution_repository import (
    WorkflowExecutionRepository,
)
from packages.workflows.models.domain.execution import (
    WorkflowExecutionCreateModel,
    WorkflowExecutionUpdateModel,
)
from packages.workflows.models.database.workflow import WorkflowExecutionEntity


class TestWorkflowExecutionRepository:
    """Test WorkflowExecutionRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return WorkflowExecutionRepository()

    async def test_get_execution_by_id(self, repository, sample_workflow_execution):
        """Test getting an execution by ID."""
        result = await repository.get(sample_workflow_execution.id)

        assert result is not None
        assert result.id == sample_workflow_execution.id
        assert result.workflow_id == sample_workflow_execution.workflow_id
        assert result.company_id == sample_workflow_execution.company_id
        assert result.status == "pending"

    async def test_list_by_workflow(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test listing executions for a workflow."""
        # Create multiple executions
        execution1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status="completed",
            completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        execution2 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            status="failed",
            completed_at=datetime.now(timezone.utc),
            error_message="Test error",
        )
        execution3 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        test_db.add_all([execution1, execution2, execution3])
        await test_db.commit()

        results = await repository.list_by_workflow(sample_workflow.id)

        # Should be ordered by started_at DESC (most recent first)
        assert len(results) == 3
        assert results[0].status == "running"
        assert results[1].status == "failed"
        assert results[2].status == "completed"

    async def test_list_by_workflow_with_pagination(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test listing executions with pagination."""
        # Create multiple executions
        for i in range(5):
            execution = WorkflowExecutionEntity(
                workflow_id=sample_workflow.id,
                company_id=sample_company.id,
                trigger_type="manual",
                started_at=datetime.now(timezone.utc) - timedelta(hours=i),
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            test_db.add(execution)
        await test_db.commit()

        # Get first page
        page1 = await repository.list_by_workflow(sample_workflow.id, skip=0, limit=2)
        assert len(page1) == 2

        # Get second page
        page2 = await repository.list_by_workflow(sample_workflow.id, skip=2, limit=2)
        assert len(page2) == 2

        # Ensure no overlap
        page1_ids = {e.id for e in page1}
        page2_ids = {e.id for e in page2}
        assert len(page1_ids & page2_ids) == 0

    async def test_get_last_execution(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test getting the most recent execution."""
        # Create executions at different times
        old_execution = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status="completed",
            completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        recent_execution = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        test_db.add_all([old_execution, recent_execution])
        await test_db.commit()
        await test_db.refresh(recent_execution)

        result = await repository.get_last_execution(sample_workflow.id)

        assert result is not None
        assert result.id == recent_execution.id
        assert result.status == "running"

    async def test_get_last_successful_execution(
        self, repository, sample_workflow, sample_company, test_db
    ):
        """Test getting the most recent successful execution."""
        # Create executions with different statuses
        completed1 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=3),
            status="completed",
            completed_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        failed = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status="failed",
            completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
            error_message="Test error",
        )
        completed2 = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        running = WorkflowExecutionEntity(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="running",
        )

        test_db.add_all([completed1, failed, completed2, running])
        await test_db.commit()
        await test_db.refresh(completed2)

        result = await repository.get_last_successful_execution(sample_workflow.id)

        assert result is not None
        assert result.id == completed2.id
        assert result.status == "completed"

    async def test_create_execution(self, repository, sample_workflow, sample_company):
        """Test creating a new execution."""

        execution_data = WorkflowExecutionCreateModel(
            workflow_id=sample_workflow.id,
            company_id=sample_company.id,
            trigger_type="manual",
            started_at=datetime.now(timezone.utc),
            status="pending",
        )

        result = await repository.create(execution_data)

        assert result is not None
        assert result.workflow_id == sample_workflow.id
        assert result.company_id == sample_company.id
        assert result.trigger_type == "manual"
        assert result.status == "pending"

    async def test_update_execution(self, repository, sample_workflow_execution):
        """Test updating an execution."""

        update_data = WorkflowExecutionUpdateModel(
            status="completed",
            completed_at=datetime.now(timezone.utc),
            output_size_bytes=4096,
        )

        result = await repository.update(sample_workflow_execution.id, update_data)

        assert result is not None
        assert result.status == "completed"
        assert result.completed_at is not None
        assert result.output_size_bytes == 4096

    async def test_update_execution_with_error(
        self, repository, sample_workflow_execution
    ):
        """Test updating an execution with error status."""

        update_data = WorkflowExecutionUpdateModel(
            status="failed",
            completed_at=datetime.now(timezone.utc),
            error_message="Something went wrong",
            execution_log={"error": "details"},
        )

        result = await repository.update(sample_workflow_execution.id, update_data)

        assert result is not None
        assert result.status == "failed"
        assert result.error_message == "Something went wrong"
        assert result.execution_log == {"error": "details"}
