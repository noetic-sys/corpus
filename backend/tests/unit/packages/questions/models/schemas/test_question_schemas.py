import pytest
from datetime import datetime
from pydantic import ValidationError

from packages.questions.models.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
)


class TestQuestionSchemas:
    """Unit tests for question schemas."""

    def test_question_create_valid(self):
        """Test creating a valid QuestionCreate."""
        question = QuestionCreate(question_text="What is this document about?")

        assert question.question_text == "What is this document about?"

    def test_question_create_validation(self):
        """Test QuestionCreate validation."""
        with pytest.raises(ValidationError):
            QuestionCreate()  # Missing required field

        # Empty string is actually valid in this schema
        question = QuestionCreate(question_text="")
        assert question.question_text == ""

    def test_question_update_valid(self):
        """Test creating a valid QuestionUpdate."""
        update = QuestionUpdate(question_text="Updated question text")

        assert update.question_text == "Updated question text"

    def test_question_update_optional(self):
        """Test QuestionUpdate with optional fields."""
        update = QuestionUpdate()

        assert update.question_text is None

    def test_question_response_creation(self):
        """Test creating a valid QuestionResponse."""
        now = datetime.now()
        response = QuestionResponse(
            id=1,
            question_text="What is this document about?",
            matrix_id=1,
            created_at=now,
            updated_at=now,
        )

        assert response.id == 1
        assert response.question_text == "What is this document about?"
        assert response.matrix_id == 1
        assert response.created_at == now
        assert response.updated_at == now

    def test_question_response_validation(self):
        """Test QuestionResponse validation."""
        with pytest.raises(ValidationError):
            QuestionResponse()  # Missing required fields
