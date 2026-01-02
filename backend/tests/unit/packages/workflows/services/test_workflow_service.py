import pytest
from packages.workflows.models.domain.workflow import WorkflowCreateModel
from packages.workflows.models.domain.workflow import WorkflowUpdateModel
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from packages.workflows.services.workflow_service import WorkflowService
from packages.workflows.models.database.workflow import WorkflowEntity


class TestWorkflowService:
    """Test WorkflowService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return WorkflowService(test_db)

    async def test_create_workflow(self, service, sample_workspace, sample_company):
        """Test creating a workflow."""

        workflow_data = WorkflowCreateModel(
            company_id=sample_company.id,
            name="Test Workflow",
            description="Test workflow description",
            trigger_type="manual",
            workspace_id=sample_workspace.id,
            output_type="excel",
        )

        result = await service.create_workflow(workflow_data)

        assert result is not None
        assert result.name == "Test Workflow"
        assert result.company_id == sample_company.id
        assert result.workspace_id == sample_workspace.id

    async def test_create_workflow_missing_name(
        self, service, sample_company, sample_workspace
    ):
        """Test creating workflow without name raises error."""

        workflow_data = WorkflowCreateModel(
            company_id=sample_company.id,
            name="",
            trigger_type="manual",
            workspace_id=sample_workspace.id,
            output_type="excel",
        )

        with pytest.raises(HTTPException, match="must have a name"):
            await service.create_workflow(workflow_data)

    async def test_get_workflow(self, service, sample_workflow, sample_company):
        """Test getting a workflow by ID."""
        result = await service.get_workflow(sample_workflow.id, sample_company.id)

        assert result is not None
        assert result.id == sample_workflow.id
        assert result.company_id == sample_company.id

    async def test_get_workflow_wrong_company(
        self, service, sample_workflow, second_company
    ):
        """Test getting workflow with wrong company returns None."""
        result = await service.get_workflow(sample_workflow.id, second_company.id)

        assert result is None

    async def test_get_workflow_not_found(self, service, sample_company):
        """Test getting nonexistent workflow returns None."""
        result = await service.get_workflow(999, sample_company.id)

        assert result is None

    async def test_update_workflow(self, service, sample_workflow, sample_company):
        """Test updating a workflow."""

        update_data = WorkflowUpdateModel(
            name="Updated Workflow Name",
            description="Updated description",
        )

        result = await service.update_workflow(
            sample_workflow.id, update_data, sample_company.id
        )

        assert result is not None
        assert result.name == "Updated Workflow Name"
        assert result.description == "Updated description"

    async def test_update_workflow_wrong_company(
        self, service, sample_workflow, second_company
    ):
        """Test updating workflow with wrong company raises error."""

        update_data = WorkflowUpdateModel(name="Updated Name")

        with pytest.raises(HTTPException, match="Workflow not found"):
            await service.update_workflow(
                sample_workflow.id, update_data, second_company.id
            )

    async def test_delete_workflow(self, service, sample_workflow, sample_company):
        """Test soft deleting a workflow."""
        success = await service.delete_workflow(sample_workflow.id, sample_company.id)

        assert success is True

        # Verify it's not returned by get (filtered out)
        workflow = await service.get_workflow(sample_workflow.id, sample_company.id)
        assert workflow is None

    async def test_delete_workflow_wrong_company(
        self, service, sample_workflow, second_company
    ):
        """Test deleting workflow with wrong company raises error."""

        with pytest.raises(HTTPException, match="Workflow not found"):
            await service.delete_workflow(sample_workflow.id, second_company.id)

    async def test_list_workflows(
        self, service, sample_workflow, sample_company, test_db
    ):
        """Test listing workflows for a company."""
        # Create another workflow
        workflow2 = WorkflowEntity(
            name="Second Workflow",
            company_id=sample_company.id,
            workspace_id=sample_workflow.workspace_id,
            trigger_type="manual",
            output_type="pdf",
        )
        test_db.add(workflow2)
        await test_db.commit()

        workflows = await service.list_workflows(sample_company.id)

        assert len(workflows) == 2

    async def test_list_workflows_excludes_deleted(
        self, service, sample_workflow, sample_company, test_db
    ):
        """Test listing workflows excludes soft deleted ones."""
        # Create and delete a workflow
        workflow2 = WorkflowEntity(
            name="Deleted Workflow",
            company_id=sample_company.id,
            workspace_id=sample_workflow.workspace_id,
            trigger_type="manual",
            output_type="pdf",
            deleted=True,
        )
        test_db.add(workflow2)
        await test_db.commit()

        workflows = await service.list_workflows(sample_company.id)

        assert len(workflows) == 1
        assert workflows[0].id == sample_workflow.id

    async def test_list_workflows_by_workspace(
        self, service, sample_workflow, sample_company, sample_workspace
    ):
        """Test listing workflows by workspace."""
        workflows = await service.list_workflows_by_workspace(
            sample_workspace.id, sample_company.id
        )

        assert len(workflows) == 1
        assert workflows[0].id == sample_workflow.id

    async def test_list_workflows_by_workspace_wrong_company(
        self, service, sample_workflow, sample_workspace, second_company
    ):
        """Test listing workflows by workspace with wrong company returns empty."""
        workflows = await service.list_workflows_by_workspace(
            sample_workspace.id, second_company.id
        )

        assert len(workflows) == 0
