import pytest
from httpx import AsyncClient

from tests.fixtures import SAMPLE_WORKSPACE_DATA, SAMPLE_MATRIX_DATA


@pytest.fixture(autouse=True)
def require_subscription(sample_subscription):
    """Ensure all route tests have an active subscription."""
    pass


class TestMatrixTemplateVariableOperations:
    """Unit tests for matrix template variable CRUD operations."""

    async def test_create_template_variable(self, client: AsyncClient):
        """Test creating a template variable for a matrix."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix with workspace_id
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        assert matrix_response.status_code == 200
        matrix = matrix_response.json()

        # Create template variable
        template_variable_data = {
            "templateString": "company_name",
            "value": "Acme Corporation",
        }
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json=template_variable_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["templateString"] == "company_name"
        assert data["value"] == "Acme Corporation"
        assert data["matrixId"] == matrix["id"]
        assert "id" in data
        assert "createdAt" in data
        assert "updatedAt" in data

    async def test_get_matrix_template_variables(self, client: AsyncClient):
        """Test getting all template variables for a matrix."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create multiple template variables
        template_vars = [
            {"templateString": "company_name", "value": "Acme Corp"},
            {"templateString": "product_name", "value": "Widget Pro"},
            {"templateString": "year", "value": "2025"},
        ]

        for var in template_vars:
            await client.post(
                f"/api/v1/matrices/{matrix['id']}/template-variables/", json=var
            )

        # Get all template variables
        response = await client.get(
            f"/api/v1/matrices/{matrix['id']}/template-variables/"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        # Verify all variables are present
        template_strings = {var["templateString"] for var in data}
        assert template_strings == {"company_name", "product_name", "year"}

    async def test_get_template_variable_by_id(self, client: AsyncClient):
        """Test getting a specific template variable by ID."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create template variable
        create_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "test_var", "value": "test_value"},
        )
        created_var = create_response.json()

        # Get by ID
        response = await client.get(f"/api/v1/template-variables/{created_var['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_var["id"]
        assert data["templateString"] == "test_var"
        assert data["value"] == "test_value"

    async def test_update_template_variable(self, client: AsyncClient):
        """Test updating a template variable."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create template variable
        create_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "company_name", "value": "Old Name"},
        )
        created_var = create_response.json()

        # Update the variable
        update_data = {"value": "New Name"}
        response = await client.patch(
            f"/api/v1/template-variables/{created_var['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "New Name"
        assert data["templateString"] == "company_name"  # Should not change

    async def test_delete_template_variable(self, client: AsyncClient):
        """Test deleting a template variable that is not in use."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create template variable
        create_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "temp_var", "value": "temp_value"},
        )
        created_var = create_response.json()

        # Delete the variable
        response = await client.delete(
            f"/api/v1/template-variables/{created_var['id']}"
        )
        assert response.status_code == 200
        assert "message" in response.json()

        # Verify it's deleted
        get_response = await client.get(
            f"/api/v1/template-variables/{created_var['id']}"
        )
        assert get_response.status_code == 404

    async def test_create_duplicate_template_variable(self, client: AsyncClient):
        """Test that creating a duplicate template variable fails."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create first variable
        template_data = {"templateString": "duplicate_var", "value": "value1"}
        await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/", json=template_data
        )

        # Try to create duplicate
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/", json=template_data
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    async def test_get_affected_questions(self, client: AsyncClient):
        """Test getting questions affected by a template variable."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create template variable
        create_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "test_var", "value": "test_value"},
        )
        created_var = create_response.json()

        # Get affected questions (should be empty initially)
        response = await client.get(
            f"/api/v1/template-variables/{created_var['id']}/affected-questions"
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_update_template_string_conflict(self, client: AsyncClient):
        """Test that updating a template variable to a duplicate string fails."""
        # Create workspace and matrix
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Create first template variable
        create_response1 = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "var1", "value": "value1"},
        )
        var1 = create_response1.json()

        # Create second template variable
        create_response2 = await client.post(
            f"/api/v1/matrices/{matrix['id']}/template-variables/",
            json={"templateString": "var2", "value": "value2"},
        )
        var2 = create_response2.json()

        # Try to update var2's template_string to conflict with var1
        update_data = {"templateString": "var1"}
        response = await client.patch(
            f"/api/v1/template-variables/{var2['id']}", json=update_data
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
