import pytest
from httpx import AsyncClient
from api.main import app
from packages.workflows.models.database.workflow import WorkflowEntity
from packages.auth.dependencies import get_current_active_user, get_subscribed_user
from unittest.mock import patch, AsyncMock
from io import BytesIO


@pytest.fixture(autouse=True)
def require_subscription(sample_subscription):
    """Ensure all route tests have an active subscription."""
    pass


class TestWorkflowEndpoints:
    """Unit tests for workflow API endpoints."""

    async def test_create_workflow(
        self, client: AsyncClient, sample_workspace, sample_company, test_user
    ):
        """Test creating a workflow."""
        workflow_data = {
            "name": "Test Workflow",
            "description": "Test workflow description",
            "triggerType": "manual",
            "workspaceId": sample_workspace.id,
            "outputType": "excel",
        }

        response = await client.post("/api/v1/workflows", json=workflow_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["workspaceId"] == sample_workspace.id
        assert data["companyId"] == sample_company.id

    async def test_get_workflow(
        self, client: AsyncClient, sample_workflow, sample_company, test_user
    ):
        """Test getting a workflow by ID."""
        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_workflow.id
        assert data["name"] == sample_workflow.name

    async def test_get_workflow_not_found(self, client: AsyncClient, test_user):
        """Test getting a nonexistent workflow."""
        response = await client.get("/api/v1/workflows/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Workflow not found"

    async def test_get_workflow_wrong_company(
        self, client: AsyncClient, sample_workflow, second_user, test_db
    ):
        """Test getting a workflow from different company returns 404."""

        # Override both dependencies - router uses get_subscribed_user, endpoint uses get_current_active_user
        def override_user():
            return second_user

        app.dependency_overrides[get_subscribed_user] = override_user
        app.dependency_overrides[get_current_active_user] = override_user

        response = await client.get(f"/api/v1/workflows/{sample_workflow.id}")

        assert response.status_code == 404

        app.dependency_overrides.clear()

    async def test_list_workflows(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workspace,
        sample_company,
        test_user,
    ):
        """Test listing workflows."""
        response = await client.get(
            f"/api/v1/workspaces/{sample_workspace.id}/workflows"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(w["id"] == sample_workflow.id for w in data)

    async def test_list_workflows_excludes_deleted(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workspace,
        sample_company,
        test_user,
        test_db,
    ):
        """Test listing workflows excludes soft deleted ones."""

        # Create and delete a workflow
        deleted_workflow = WorkflowEntity(
            name="Deleted Workflow",
            company_id=sample_company.id,
            workspace_id=sample_workflow.workspace_id,
            trigger_type="manual",
            output_type="pdf",
            deleted=True,
        )
        test_db.add(deleted_workflow)
        await test_db.commit()

        response = await client.get(
            f"/api/v1/workspaces/{sample_workspace.id}/workflows"
        )

        assert response.status_code == 200
        data = response.json()
        assert all(w["name"] != "Deleted Workflow" for w in data)

    async def test_update_workflow(
        self, client: AsyncClient, sample_workflow, sample_company, test_user
    ):
        """Test updating a workflow."""
        update_data = {
            "name": "Updated Workflow Name",
            "description": "Updated description",
        }

        response = await client.patch(
            f"/api/v1/workflows/{sample_workflow.id}", json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Workflow Name"
        assert data["description"] == "Updated description"

    async def test_update_workflow_wrong_company(
        self, client: AsyncClient, sample_workflow, second_user, test_db
    ):
        """Test updating a workflow from different company returns 404."""

        # Override both dependencies - router uses get_subscribed_user, endpoint uses get_current_active_user
        def override_user():
            return second_user

        app.dependency_overrides[get_subscribed_user] = override_user
        app.dependency_overrides[get_current_active_user] = override_user

        update_data = {"name": "Updated Name"}

        response = await client.patch(
            f"/api/v1/workflows/{sample_workflow.id}",
            json=update_data,
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    async def test_delete_workflow(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workspace,
        sample_company,
        test_user,
    ):
        """Test deleting a workflow (soft delete)."""
        response = await client.delete(f"/api/v1/workflows/{sample_workflow.id}")

        assert response.status_code == 204

        # Verify it's not returned by list
        list_response = await client.get(
            f"/api/v1/workspaces/{sample_workspace.id}/workflows"
        )
        workflows = list_response.json()
        assert not any(w["id"] == sample_workflow.id for w in workflows)

    async def test_delete_workflow_wrong_company(
        self, client: AsyncClient, sample_workflow, second_user, test_db
    ):
        """Test deleting a workflow from different company returns 404."""

        # Override both dependencies - router uses get_subscribed_user, endpoint uses get_current_active_user
        def override_user():
            return second_user

        app.dependency_overrides[get_subscribed_user] = override_user
        app.dependency_overrides[get_current_active_user] = override_user

        response = await client.delete(f"/api/v1/workflows/{sample_workflow.id}")

        assert response.status_code == 404

        app.dependency_overrides.clear()

    @patch("packages.workflows.services.execution_service.get_temporal_client")
    async def test_execute_workflow(
        self,
        mock_temporal_connect,
        client: AsyncClient,
        sample_workflow,
        sample_company,
        test_user,
    ):
        """Test executing a workflow."""
        mock_temporal_client = AsyncMock()
        mock_temporal_client.start_workflow = AsyncMock()
        mock_temporal_connect.return_value = mock_temporal_client

        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/execute",
            json={"triggerContext": {}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflowId"] == sample_workflow.id
        assert "executionId" in data
        assert data["status"] == "pending"

    @patch("packages.workflows.services.execution_service.get_temporal_client")
    async def test_execute_deleted_workflow(
        self,
        mock_temporal_connect,
        client: AsyncClient,
        sample_workflow,
        sample_company,
        test_user,
        test_db,
    ):
        """Test executing a deleted workflow returns 404."""

        # Mark workflow as deleted
        workflow_entity = await test_db.get(WorkflowEntity, sample_workflow.id)
        workflow_entity.deleted = True
        await test_db.commit()

        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/execute",
            json={"triggerContext": {}},
        )

        assert response.status_code == 404

    async def test_list_executions(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_execution,
        sample_company,
        test_user,
    ):
        """Test listing executions for a workflow."""
        response = await client.get(
            f"/api/v1/workflows/{sample_workflow.id}/executions"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_execution(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_execution,
        sample_company,
        test_user,
    ):
        """Test getting an execution by ID."""
        response = await client.get(
            f"/api/v1/workflows/{sample_workflow.id}/executions/{sample_workflow_execution.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_workflow_execution.id

    async def test_get_execution_wrong_company(
        self,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_execution,
        second_user,
        test_db,
    ):
        """Test getting execution from different company returns 404."""

        # Override both dependencies - router uses get_subscribed_user, endpoint uses get_current_active_user
        def override_user():
            return second_user

        app.dependency_overrides[get_subscribed_user] = override_user
        app.dependency_overrides[get_current_active_user] = override_user

        response = await client.get(
            f"/api/v1/workflows/{sample_workflow.id}/executions/{sample_workflow_execution.id}"
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    @patch("packages.workflows.services.workflow_storage_service.get_storage")
    async def test_upload_input_file(
        self,
        mock_get_storage,
        client: AsyncClient,
        sample_workflow,
        sample_company,
        test_user,
    ):
        """Test uploading an input file for a workflow."""
        mock_storage = AsyncMock()
        mock_storage.upload = AsyncMock(return_value=True)
        mock_get_storage.return_value = mock_storage

        files = {
            "file": (
                "test.xlsx",
                BytesIO(b"test data"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        }
        data = {"description": "Test template file"}

        response = await client.post(
            f"/api/v1/workflows/{sample_workflow.id}/input-files",
            files=files,
            data=data,
        )

        assert response.status_code == 201
        result = response.json()
        assert result["name"] == "test.xlsx"
        assert result["workflowId"] == sample_workflow.id

    @patch("packages.workflows.services.workflow_storage_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_list_input_files(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_input_file,
        sample_company,
        test_user,
        mock_storage,
    ):
        """Test listing input files for a workflow."""
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        response = await client.get(
            f"/api/v1/workflows/{sample_workflow.id}/input-files"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @patch("packages.workflows.services.workflow_storage_service.get_storage")
    async def test_download_input_file(
        self,
        mock_get_storage,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_input_file,
        sample_company,
        test_user,
    ):
        """Test downloading an input file."""
        mock_storage = AsyncMock()
        mock_storage.download = AsyncMock(return_value=b"file data")
        mock_get_storage.return_value = mock_storage

        response = await client.get(
            f"/api/v1/workflows/{sample_workflow.id}/input-files/{sample_workflow_input_file.id}/download"
        )

        assert response.status_code == 200
        assert response.content == b"file data"

    @patch("packages.workflows.services.workflow_storage_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_delete_input_file(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        sample_workflow,
        sample_workflow_input_file,
        sample_company,
        test_user,
        mock_storage,
    ):
        """Test deleting an input file."""
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        response = await client.delete(
            f"/api/v1/workflows/{sample_workflow.id}/input-files/{sample_workflow_input_file.id}"
        )

        assert response.status_code == 204
