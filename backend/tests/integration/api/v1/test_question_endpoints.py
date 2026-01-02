from httpx import AsyncClient

from tests.fixtures import SAMPLE_MATRIX_DATA, SAMPLE_QUESTION_DATA


class TestQuestionEndpoints:
    """Integration tests for question API endpoints."""

    async def test_create_question(
        self, client: AsyncClient, sample_question_entity_set
    ):
        """Test creating a question in a matrix."""
        # Create a matrix first
        matrix_response = await client.post(
            "/api/v1/matrices/", json=SAMPLE_MATRIX_DATA
        )
        matrix = matrix_response.json()

        # Create a question with entitySetId query parameter
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={sample_question_entity_set.id}",
            json=SAMPLE_QUESTION_DATA,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == SAMPLE_QUESTION_DATA["question_text"]
        assert data["matrixId"] == matrix["id"]
        assert "id" in data

    async def test_get_question(self, client: AsyncClient, sample_question_entity_set):
        """Test getting a single question."""
        # Create a matrix and question
        matrix_response = await client.post(
            "/api/v1/matrices/", json=SAMPLE_MATRIX_DATA
        )
        matrix = matrix_response.json()

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={sample_question_entity_set.id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Get the question
        response = await client.get(f"/api/v1/questions/{question['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == question["id"]
        assert data["questionText"] == SAMPLE_QUESTION_DATA["question_text"]

    async def test_update_question(
        self, client: AsyncClient, sample_question_entity_set
    ):
        """Test updating a question."""
        # Create a matrix and question
        matrix_response = await client.post(
            "/api/v1/matrices/", json=SAMPLE_MATRIX_DATA
        )
        matrix = matrix_response.json()

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={sample_question_entity_set.id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Update the question
        update_data = {"questionText": "What are the key findings in this document?"}
        response = await client.patch(
            f"/api/v1/questions/{question['id']}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["questionText"] == update_data["questionText"]

    async def test_delete_question(
        self, client: AsyncClient, sample_question_entity_set
    ):
        """Test deleting a question."""
        # Create a matrix and question
        matrix_response = await client.post(
            "/api/v1/matrices/", json=SAMPLE_MATRIX_DATA
        )
        matrix = matrix_response.json()

        question_response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/questions/?entitySetId={sample_question_entity_set.id}",
            json=SAMPLE_QUESTION_DATA,
        )
        question = question_response.json()

        # Delete the question
        response = await client.delete(f"/api/v1/questions/{question['id']}")
        assert response.status_code == 200

        # Verify it's deleted
        get_response = await client.get(f"/api/v1/questions/{question['id']}")
        assert get_response.status_code == 404

    async def test_get_nonexistent_question(self, client: AsyncClient):
        """Test getting a non-existent question."""
        response = await client.get("/api/v1/questions/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Question not found"

    async def test_create_question_in_nonexistent_matrix(self, client: AsyncClient):
        """Test creating a question in a non-existent matrix."""
        response = await client.post(
            "/api/v1/matrices/99999/questions/?entitySetId=1", json=SAMPLE_QUESTION_DATA
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Matrix not found"
