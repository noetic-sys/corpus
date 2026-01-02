import pytest
from httpx import AsyncClient
from unittest.mock import patch

from tests.fixtures import (
    SAMPLE_WORKSPACE_DATA,
    SAMPLE_MATRIX_DATA,
    SAMPLE_QUESTION_DATA,
)


@pytest.fixture(autouse=True)
def require_subscription(sample_subscription):
    """Ensure all route tests have an active subscription."""
    pass


class TestQuestionEndpoints:
    """Unit tests for question API endpoints."""

    async def _get_question_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get question entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        question_entity_set = next(
            es for es in entity_sets if es["entityType"] == "question"
        )
        return question_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    async def test_create_question(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test creating a question."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix first
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        # Create a question
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == SAMPLE_QUESTION_DATA["question_text"]
        assert data["matrixId"] == matrix["id"]
        assert "id" in data
        assert "createdAt" in data

    @patch("packages.documents.services.document_service.get_storage")
    async def test_get_question(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test getting a single question."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix and question
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Get the question
        response = await client.get(f"/api/v1/questions/{question['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == question["id"]
        assert data["questionText"] == SAMPLE_QUESTION_DATA["question_text"]

    async def test_get_nonexistent_question(self, client: AsyncClient):
        """Test getting a non-existent question."""
        response = await client.get("/api/v1/questions/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Question not found"

    @patch("packages.documents.services.document_service.get_storage")
    async def test_update_question(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test updating a question."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix and question
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Update the question
        update_data = {"questionText": "Updated question text?"}
        response = await client.patch(
            f"/api/v1/questions/{question['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == update_data["questionText"]

    @patch("packages.documents.services.document_service.get_storage")
    async def test_delete_question(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test deleting a question."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix and question
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Delete the question
        response = await client.delete(f"/api/v1/questions/{question['id']}")
        assert response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/api/v1/questions/{question['id']}")
        assert get_response.status_code == 404

    @patch("packages.documents.services.document_service.get_storage")
    @patch(
        "packages.matrices.services.batch_processing_service.BatchProcessingService.process_entity_added_to_set"
    )
    async def test_create_question_rollback_on_cell_processing_failure(
        self,
        mock_process_entity_added_to_set,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
    ):
        """Test that question creation rolls back when cell processing fails."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Mock cell processing to fail
        mock_process_entity_added_to_set.side_effect = Exception(
            "Cell processing failed"
        )

        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix first
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        # Attempt to create a question (should fail due to cell processing error)
        with pytest.raises(Exception) as exc_info:
            _ = await client.post(
                f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
                json=SAMPLE_QUESTION_DATA,
            )
        assert "Cell processing failed" in str(exc_info.value)

        # Verify no question was persisted (transaction rolled back)
        questions_response = await client.get(
            f"/api/v1/matrices/{matrix['id']}/questions/"
        )
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert len(questions) == 0


class TestQuestionStreamingEndpoints:
    """Unit tests for new question streaming endpoints."""

    async def _get_question_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get question entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        question_entity_set = next(
            es for es in entity_sets if es["entityType"] == "question"
        )
        return question_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    async def test_get_questions_by_matrix(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test getting all questions for a specific matrix."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix_id)

        # Create multiple questions for the matrix
        question_texts = [
            "What is the main topic?",
            "Who are the key stakeholders?",
            "What are the risks?",
        ]
        for question_text in question_texts:
            question_data = {"questionText": question_text}
            response = await client.post(
                f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={entity_set_id}",
                json=question_data,
            )
            assert response.status_code == 200

        # Create another matrix with a question (should not be included)
        other_matrix_data = {
            "name": "Other Matrix",
            "description": "Other",
            "workspaceId": workspace["id"],
        }
        other_matrix_response = await client.post(
            "/api/v1/matrices/", json=other_matrix_data
        )
        other_matrix = other_matrix_response.json()

        # Get question entity set ID for other matrix
        other_entity_set_id = await self._get_question_entity_set_id(
            client, other_matrix["id"]
        )

        other_question_data = {"questionText": "Other question?"}
        await client.post(
            f"/api/v1/matrices/{other_matrix['id']}/questions/?entitySetId={other_entity_set_id}",
            json=other_question_data,
        )

        # Call the streaming endpoint
        response = await client.get(f"/api/v1/matrices/{matrix_id}/questions/")

        # Assertions
        assert response.status_code == 200
        questions = response.json()
        assert isinstance(questions, list)
        assert len(questions) == 3

        # Verify all questions belong to the correct matrix
        returned_texts = [q["questionText"] for q in questions]
        for question in questions:
            assert question["matrixId"] == matrix_id
            assert question["questionText"] in question_texts
            assert "id" in question
            assert "createdAt" in question

        # Verify we got all expected questions
        for expected_text in question_texts:
            assert expected_text in returned_texts

    @patch("packages.documents.services.document_service.get_storage")
    async def test_get_questions_by_matrix_empty(
        self, mock_get_storage, client: AsyncClient, mock_storage
    ):
        """Test getting questions for a matrix with no questions."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix without questions
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Call the streaming endpoint
        response = await client.get(f"/api/v1/matrices/{matrix_id}/questions/")

        # Assertions
        assert response.status_code == 200
        questions = response.json()
        assert isinstance(questions, list)
        assert len(questions) == 0

    async def test_get_questions_by_nonexistent_matrix(self, client: AsyncClient):
        """Test getting questions for a non-existent matrix."""
        # Call the streaming endpoint with non-existent matrix ID
        response = await client.get("/api/v1/matrices/99999/questions/")

        # Should return empty list since service returns empty for non-existent matrix
        assert response.status_code == 200
        questions = response.json()
        assert isinstance(questions, list)
        assert len(questions) == 0

    @patch("packages.documents.services.document_service.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_questions_vs_full_matrix_consistency(
        self,
        mock_get_message_queue,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
    ):
        """Test that streaming questions endpoint returns same data as full matrix."""
        # Use common fixtures
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix with questions
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix_id)

        # Create questions
        question_texts = ["Question 1?", "Question 2?", "Question 3?"]
        for question_text in question_texts:
            question_data = {"questionText": question_text}
            await client.post(
                f"/api/v1/matrices/{matrix_id}/questions/?entitySetId={entity_set_id}",
                json=question_data,
            )

        # Get questions via streaming endpoint
        streaming_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/questions/"
        )
        streaming_questions = streaming_response.json()

        # Assertions
        assert len(streaming_questions) == 3

        # Sort both lists by ID for comparison
        streaming_questions.sort(key=lambda x: x["id"])

        for i, stream_q in enumerate(streaming_questions):
            assert stream_q["id"] == i + 1
            assert stream_q["questionText"] == question_texts[i]
            assert stream_q["matrixId"] == matrix_id


class TestQuestionWithOptionsEndpoints:
    """Unit tests for question-with-options API endpoints."""

    async def _get_question_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get question entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        question_entity_set = next(
            es for es in entity_sets if es["entityType"] == "question"
        )
        return question_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch(
        "packages.matrices.services.batch_processing_service.BatchProcessingService.process_entity_added_to_set"
    )
    async def test_create_question_with_options_rollback_on_cell_processing_failure(
        self,
        mock_process_entity_added_to_set,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
    ):
        """Test that question-with-options creation rolls back when cell processing fails."""
        # Use common fixture
        mock_get_storage.return_value = mock_storage

        # Mock cell processing to fail
        mock_process_entity_added_to_set.side_effect = Exception(
            "Cell processing failed"
        )

        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix first
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        # Create question data with options
        question_with_options_data = {
            "questionText": "What is the status?",
            "questionTypeId": 2,  # Assuming 2 is SINGLE_SELECT
            "options": [
                {"value": "active"},
                {"value": "inactive"},
            ],
        }

        # Attempt to create a question with options (should fail due to cell processing error)
        with pytest.raises(Exception) as exc_info:
            _ = await client.post(
                f"/api/v1/matrices/{matrix['id']}/questions-with-options/?entitySetId={entity_set_id}",
                json=question_with_options_data,
            )
        assert "Cell processing failed" in str(exc_info.value)

        # Verify no question was persisted (transaction rolled back)
        questions_response = await client.get(
            f"/api/v1/matrices/{matrix['id']}/questions/"
        )
        assert questions_response.status_code == 200
        questions = questions_response.json()
        assert len(questions) == 0


class TestQuestionUpdateWithOptionsEndpoints:
    """Unit tests for the comprehensive question update endpoint."""

    async def _get_question_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get question entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        question_entity_set = next(
            es for es in entity_sets if es["entityType"] == "question"
        )
        return question_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_success(
        self,
        mock_get_message_queue,
        mock_tracer,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
    ):
        """Test successful comprehensive question update."""
        # Setup mocks
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix and question
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Update the question with options
        update_data = {
            "questionText": "Updated question with options?",
            "questionTypeId": 5,  # SINGLE_SELECT
            "options": [
                {"value": "Option A"},
                {"value": "Option B"},
            ],
        }
        response = await client.patch(
            f"/api/v1/matrices/{matrix['id']}/questions/{question['id']}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == update_data["questionText"]
        assert data["questionTypeId"] == update_data["questionTypeId"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_partial_update(
        self,
        mock_get_message_queue,
        mock_tracer,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
    ):
        """Test partial question update (only text)."""
        # Setup mocks
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix and question
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get question entity set ID
        entity_set_id = await self._get_question_entity_set_id(client, matrix["id"])

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Update only the question text
        update_data = {"questionText": "Only text updated?"}
        response = await client.patch(
            f"/api/v1/matrices/{matrix['id']}/questions/{question['id']}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == update_data["questionText"]
        # Type should remain unchanged (default is 1)
        assert data["questionTypeId"] == 1  # Default SHORT_ANSWER type

    async def test_update_question_with_options_question_not_found(
        self, client: AsyncClient
    ):
        """Test updating non-existent question."""
        update_data = {"questionText": "Updated text?"}
        response = await client.patch(
            "/api/v1/matrices/1/questions/99999", json=update_data
        )
        assert response.status_code == 404

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_wrong_matrix(
        self,
        mock_get_message_queue,
        mock_tracer,
        mock_get_storage,
        client: AsyncClient,
        mock_storage,
    ):
        """Test updating question with wrong matrix ID."""
        # Setup mocks
        mock_get_storage.return_value = mock_storage
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create two matrices
        matrix1_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix1_response = await client.post("/api/v1/matrices/", json=matrix1_data)
        matrix1 = matrix1_response.json()

        matrix2_data = {
            "name": "Matrix 2",
            "description": "Second matrix",
            "workspaceId": workspace["id"],
        }
        matrix2_response = await client.post(
            "/api/v1/matrices/",
            json=matrix2_data,
        )
        matrix2 = matrix2_response.json()

        # Get question entity set ID for matrix1
        entity_set_id = await self._get_question_entity_set_id(client, matrix1["id"])

        # Create question in matrix1
        question_response = await client.post(
            f"/api/v1/matrices/{matrix1['id']}/questions/?entitySetId={entity_set_id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Try to update the question using matrix2's ID
        update_data = {"questionText": "Updated text?"}
        response = await client.patch(
            f"/api/v1/matrices/{matrix2['id']}/questions/{question['id']}",
            json=update_data,
        )

        assert response.status_code == 400
        assert "Question does not belong to this matrix" in response.json()["detail"]
