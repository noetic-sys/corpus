from datetime import datetime

from packages.questions.models.domain.question import QuestionModel


class TestQuestionModel:
    """Unit tests for QuestionModel."""

    def test_question_model_creation(self):
        """Test creating a valid QuestionModel."""
        now = datetime.now()
        question = QuestionModel(
            id=1,
            question_text="What is this document about?",
            matrix_id=1,
            company_id=1,
            question_type_id=1,  # SHORT_ANSWER
            min_answers=1,
            created_at=now,
            updated_at=now,
        )

        assert question.id == 1
        assert question.question_text == "What is this document about?"
        assert question.matrix_id == 1
        assert question.question_type_id == 1
        assert question.created_at == now
        assert question.updated_at == now
