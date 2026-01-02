import pytest
from packages.workflows.models.domain.workflow import (
    WorkflowCreateModel,
    WorkflowUpdateModel,
)
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.repositories.workflow_repository import WorkflowRepository
from packages.workflows.models.database.workflow import WorkflowEntity


class TestWorkflowRepository:
    """Test WorkflowRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return WorkflowRepository(test_db)

    async def test_get_workflow_by_id(self, repository, sample_workflow):
        """Test getting a workflow by ID."""
        result = await repository.get(sample_workflow.id)

        assert result is not None
        assert result.id == sample_workflow.id
        assert result.name == "Test Workflow"
        assert result.company_id == sample_workflow.company_id

    async def test_get_workflow_with_company_filter(
        self, repository, sample_workflow, second_company
    ):
        """Test getting workflow with company filtering."""
        # Should not find workflow from different company
        result = await repository.get(sample_workflow.id, company_id=second_company.id)
        assert result is None

        # Should find workflow from correct company
        result = await repository.get(
            sample_workflow.id, company_id=sample_workflow.company_id
        )
        assert result is not None
        assert result.id == sample_workflow.id

    async def test_list_by_company(
        self, repository, sample_workflow, sample_company, second_company
    ):
        """Test listing workflows by company."""
        # Create workflow for second company
        workflow2 = WorkflowEntity(
            name="Second Workflow",
            company_id=second_company.id,
            workspace_id=sample_workflow.workspace_id,
            trigger_type="manual",
            output_type="pdf",
        )
        repository.db_session.add(workflow2)
        await repository.db_session.commit()

        # List workflows for first company
        results = await repository.list_by_company(sample_company.id)

        assert len(results) == 1
        assert results[0].name == "Test Workflow"
        assert results[0].company_id == sample_company.id

    async def test_list_by_company_excludes_deleted(
        self, repository, sample_workflow, sample_company
    ):
        """Test listing workflows excludes soft deleted ones."""
        # Create deleted workflow
        deleted_workflow = WorkflowEntity(
            name="Deleted Workflow",
            company_id=sample_company.id,
            workspace_id=sample_workflow.workspace_id,
            trigger_type="manual",
            output_type="excel",
            deleted=True,
        )
        repository.db_session.add(deleted_workflow)
        await repository.db_session.commit()

        # List workflows (should exclude deleted)
        results = await repository.list_by_company(sample_company.id)
        assert len(results) == 1
        assert results[0].name == "Test Workflow"

    async def test_list_by_workspace(
        self, repository, sample_workflow, sample_workspace, sample_company
    ):
        """Test listing workflows by workspace."""
        results = await repository.list_by_workspace(
            sample_workspace.id, sample_company.id
        )

        assert len(results) == 1
        assert results[0].id == sample_workflow.id
        assert results[0].workspace_id == sample_workspace.id

    async def test_list_by_trigger_type(
        self, repository, sample_workflow, sample_company
    ):
        """Test listing workflows by trigger type."""
        # List manual workflows
        manual_workflows = await repository.list_by_trigger_type(
            "manual", sample_company.id
        )
        assert len(manual_workflows) == 1
        assert manual_workflows[0].trigger_type == "manual"

    async def test_create_workflow(self, repository, sample_workspace, sample_company):
        """Test creating a new workflow."""
        workflow_data = WorkflowCreateModel(
            name="New Workflow",
            description="Created via repository",
            company_id=sample_company.id,
            workspace_id=sample_workspace.id,
            trigger_type="manual",
            output_type="pdf",
        )

        result = await repository.create(workflow_data)

        assert result is not None
        assert result.name == "New Workflow"
        assert result.trigger_type == "manual"
        assert result.output_type == "pdf"

    async def test_update_workflow(self, repository, sample_workflow):
        """Test updating a workflow."""

        update_data = WorkflowUpdateModel(
            name="Updated Workflow Name",
            description="Updated description",
            output_type="docx",
        )

        result = await repository.update(sample_workflow.id, update_data)

        assert result is not None
        assert result.name == "Updated Workflow Name"
        assert result.description == "Updated description"
        assert result.output_type == "docx"

    async def test_delete_workflow(self, repository, sample_workflow):
        """Test deleting a workflow."""
        success = await repository.delete(sample_workflow.id)
        assert success is True

        # Verify workflow is deleted
        result = await repository.get(sample_workflow.id)
        assert result is None
