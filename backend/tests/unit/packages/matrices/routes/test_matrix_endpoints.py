import pytest
from uuid import uuid4
from httpx import AsyncClient
from unittest.mock import patch
from io import BytesIO

from tests.fixtures import (
    SAMPLE_WORKSPACE_DATA,
    SAMPLE_MATRIX_DATA,
)


@pytest.fixture(autouse=True)
def require_subscription(sample_subscription):
    """Ensure all route tests have an active subscription."""
    pass


class TestMatrixOperations:
    """Integration tests for matrix CRUD operations."""

    async def test_create_matrix(self, client: AsyncClient):
        """Test creating a matrix."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix with workspace_id
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        response = await client.post("/api/v1/matrices/", json=matrix_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == SAMPLE_MATRIX_DATA["name"]
        assert data["description"] == SAMPLE_MATRIX_DATA["description"]
        assert data["workspaceId"] == workspace["id"]
        assert "id" in data
        assert "createdAt" in data

    async def test_list_matrices(self, client: AsyncClient):
        """Test listing matrices."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a few matrices
        for i in range(3):
            matrix_data = {
                "name": f"Matrix {i}",
                "description": f"Description {i}",
                "workspaceId": workspace["id"],
            }
            await client.post("/api/v1/matrices/", json=matrix_data)

        # List matrices
        response = await client.get("/api/v1/matrices/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    async def test_get_matrix(self, client: AsyncClient):
        """Test getting a single matrix."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        create_response = await client.post("/api/v1/matrices/", json=matrix_data)
        created_matrix = create_response.json()

        # Get the matrix
        response = await client.get(f"/api/v1/matrices/{created_matrix['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created_matrix["id"]
        assert data["name"] == SAMPLE_MATRIX_DATA["name"]

    async def test_update_matrix(self, client: AsyncClient):
        """Test updating a matrix."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        create_response = await client.post("/api/v1/matrices/", json=matrix_data)
        created_matrix = create_response.json()

        # Update the matrix
        update_data = {
            "name": "Updated Matrix Name",
            "description": "Updated description",
        }
        response = await client.patch(
            f"/api/v1/matrices/{created_matrix['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    async def test_delete_matrix(self, client: AsyncClient):
        """Test deleting a matrix."""
        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        create_response = await client.post("/api/v1/matrices/", json=matrix_data)
        created_matrix = create_response.json()

        # Delete the matrix
        response = await client.delete(f"/api/v1/matrices/{created_matrix['id']}")
        assert response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/api/v1/matrices/{created_matrix['id']}")
        assert get_response.status_code == 404

    async def test_get_nonexistent_matrix(self, client: AsyncClient):
        """Test getting a non-existent matrix."""
        response = await client.get("/api/v1/matrices/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Matrix not found"


class TestMatrixEntitySets:
    """Integration tests for matrix entity set operations."""

    async def test_get_matrix_entity_sets_empty(self, client: AsyncClient):
        """Test getting entity sets for a newly created matrix."""
        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get entity sets (should have default entity sets created)
        response = await client.get(f"/api/v1/matrices/{matrix['id']}/entity-sets")
        assert response.status_code == 200
        data = response.json()

        assert "matrixId" in data
        assert data["matrixId"] == matrix["id"]
        assert "matrixType" in data
        assert "entitySets" in data
        assert isinstance(data["entitySets"], list)
        # Should have default document and question entity sets
        assert len(data["entitySets"]) >= 2

    async def test_get_matrix_entity_sets_nonexistent(self, client: AsyncClient):
        """Test getting entity sets for non-existent matrix."""
        response = await client.get("/api/v1/matrices/99999/entity-sets")
        assert response.status_code == 404


class TestMatrixCellBatch:
    """Integration tests for matrix cell batch operations."""

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_matrix_cells_batch_empty(
        self,
        mock_get_message_queue_qa,
        mock_get_message_queue_batch,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test batch fetching cells with empty filters."""
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue_qa.return_value = mock_message_queue
        mock_get_message_queue_batch.return_value = mock_message_queue

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Try to fetch with empty filters (should error)
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/cells/batch",
            json={"entitySetFilters": []},
        )
        assert response.status_code == 400
        assert "at least one filter" in response.json()["detail"].lower()


class TestMatrixCellStreamingEndpoints:
    """Integration tests for matrix cell streaming endpoints."""

    async def test_get_matrix_cells_empty_matrix(self, client: AsyncClient):
        """Test getting matrix cells for a matrix with no documents/questions."""
        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix without documents or questions
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Call streaming endpoint
        response = await client.get(f"/api/v1/matrices/{matrix_id}/cells")

        # Assertions
        assert response.status_code == 200
        cells = response.json()
        assert isinstance(cells, list)
        assert len(cells) == 0

    async def test_get_matrix_cells_nonexistent_matrix(self, client: AsyncClient):
        """Test getting matrix cells for a non-existent matrix."""
        # Call streaming endpoint with non-existent matrix ID
        response = await client.get("/api/v1/matrices/99999/cells")

        # Should return empty list
        assert response.status_code == 200
        cells = response.json()
        assert isinstance(cells, list)
        assert len(cells) == 0

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_cells_by_document_entity_set(
        self,
        mock_get_message_queue_qa,
        mock_get_message_queue_batch,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test getting cells filtered by document using entity set endpoint."""
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue_qa.return_value = mock_message_queue
        mock_get_message_queue_batch.return_value = mock_message_queue

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Get entity sets
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        entity_sets_data = entity_sets_response.json()
        doc_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "document"
        )
        question_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "question"
        )

        # Add question
        question_response = await client.post(
            f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={question_entity_set['id']}",
            json={"questionText": "What is the date?"},
        )
        question = question_response.json()

        # Add document
        files = {"file": ("test.pdf", BytesIO(uuid4().bytes), "application/pdf")}
        doc_response = await client.post(
            f"/api/v1/matrices/{matrix_id}/documents/?entitySetId={doc_entity_set['id']}",
            files=files,
        )
        document = doc_response.json()

        # Query cells by document using entity set endpoint
        response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets/{doc_entity_set['id']}/documents/{document['id']}/cells/with-answers"
        )

        assert response.status_code == 200
        cells = response.json()
        assert isinstance(cells, list)
        # Should have 1 cell (1 document × 1 question)
        assert len(cells) == 1
        assert cells[0]["matrixId"] == matrix_id

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_cells_by_question_entity_set(
        self,
        mock_get_message_queue_qa,
        mock_get_message_queue_batch,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test getting cells filtered by question using entity set endpoint."""
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue_qa.return_value = mock_message_queue
        mock_get_message_queue_batch.return_value = mock_message_queue

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Get entity sets
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        entity_sets_data = entity_sets_response.json()
        question_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "question"
        )

        # Add question
        question_response = await client.post(
            f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={question_entity_set['id']}",
            json={"questionText": "What is the date?"},
        )
        question = question_response.json()

        # Add document
        doc_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "document"
        )
        files = {"file": ("test.pdf", BytesIO(uuid4().bytes), "application/pdf")}
        await client.post(
            f"/api/v1/matrices/{matrix_id}/documents/?entitySetId={doc_entity_set['id']}",
            files=files,
        )

        # Query cells by question using entity set endpoint
        response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets/{question_entity_set['id']}/questions/{question['id']}/cells/with-answers"
        )

        assert response.status_code == 200
        cells = response.json()
        assert isinstance(cells, list)
        # Should have 1 cell (1 document × 1 question)
        assert len(cells) == 1
        assert cells[0]["matrixId"] == matrix_id

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_matrix_cells_batch_with_data(
        self,
        mock_get_message_queue_qa,
        mock_get_message_queue_batch,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test batch fetching cells with actual data using entity set filters."""
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue_qa.return_value = mock_message_queue
        mock_get_message_queue_batch.return_value = mock_message_queue

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Get entity sets
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        entity_sets_data = entity_sets_response.json()
        doc_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "document"
        )
        question_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "question"
        )

        # Add 2 questions
        question_ids = []
        for i in range(2):
            q_response = await client.post(
                f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={question_entity_set['id']}",
                json={"questionText": f"Question {i}?"},
            )
            question_ids.append(q_response.json()["id"])

        # Add 2 documents (creates 4 cells: 2×2)
        document_ids = []
        for i in range(2):
            files = {
                "file": (f"test{i}.pdf", BytesIO(uuid4().bytes), "application/pdf")
            }
            doc_response = await client.post(
                f"/api/v1/matrices/{matrix_id}/documents/?entitySetId={doc_entity_set['id']}",
                files=files,
            )
            document_ids.append(doc_response.json()["id"])

        # Batch fetch cells using entity set filters
        # Filter: first document × all questions
        batch_request = {
            "entitySetFilters": [
                {
                    "entitySetId": doc_entity_set["id"],
                    "entityIds": [document_ids[0]],
                    "role": "document",
                },
                {
                    "entitySetId": question_entity_set["id"],
                    "entityIds": question_ids,
                    "role": "question",
                },
            ]
        }

        response = await client.post(
            f"/api/v1/matrices/{matrix_id}/cells/batch", json=batch_request
        )

        assert response.status_code == 200
        cells = response.json()
        assert isinstance(cells, list)
        # Should return 2 cells (1 document × 2 questions)
        assert len(cells) == 2
        for cell in cells:
            assert cell["matrixId"] == matrix_id

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_matrix(
        self,
        mock_tracer,
        mock_get_message_queue_qa,
        mock_get_message_queue_batch,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test duplicating a matrix with documents and questions."""
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue_qa.return_value = mock_message_queue
        mock_get_message_queue_batch.return_value = mock_message_queue
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        workspace = workspace_response.json()

        # Create source matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        source_matrix = matrix_response.json()
        matrix_id = source_matrix["id"]

        # Get entity sets
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        entity_sets_data = entity_sets_response.json()
        doc_entity_set_id = next(
            es["id"]
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "document"
        )
        question_entity_set_id = next(
            es["id"]
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "question"
        )

        # Add question
        await client.post(
            f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={question_entity_set_id}",
            json={"questionText": "What is the date?"},
        )

        # Add document
        files = {"file": ("test.pdf", BytesIO(uuid4().bytes), "application/pdf")}
        await client.post(f"/api/v1/matrices/{matrix_id}/documents/", files=files)

        # Duplicate the matrix
        duplicate_request = {
            "name": "Duplicated Matrix",
            "description": "Copy of original",
            "entitySetIds": [doc_entity_set_id, question_entity_set_id],
        }

        response = await client.post(
            f"/api/v1/matrices/{matrix_id}/duplicate", json=duplicate_request
        )

        assert response.status_code == 200
        result = response.json()
        assert result["originalMatrixId"] == matrix_id
        assert result["duplicateMatrixId"] != matrix_id
        assert result["duplicateMatrixId"] > 0
        assert "Successfully duplicated matrix" in result["message"]
        assert doc_entity_set_id in [
            int(k) for k in result["entitySetsDuplicated"].keys()
        ]
