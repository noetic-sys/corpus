import pytest

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.list_questions import (
    ListQuestionsTool,
    ListQuestionsParameters,
)
from packages.questions.models.schemas.question import QuestionResponse
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.questions.models.database.question import QuestionEntity


class TestListQuestionsTool:
    """Test ListQuestionsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListQuestionsTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = ListQuestionsTool.definition()

        assert definition.name == "list_questions"
        assert definition.description == "List questions for a given matrix"
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = ListQuestionsTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = ListQuestionsTool.parameter_class()
        assert param_class == ListQuestionsParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = ListQuestionsParameters(matrix_id=1)
        assert params.matrix_id == 1

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            ListQuestionsParameters()  # Missing required matrix_id

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = ListQuestionsTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param
        assert matrix_id_param["description"] == "the matrix id to list questions for"


class TestListQuestionsToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListQuestionsTool()

    async def test_execute_with_matrix_questions(
        self, tool, test_db, test_user, sample_matrix, sample_company
    ):
        """Test successful tool execution with questions in matrix."""
        question1 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract date?",
            question_type_id=1,
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="What is the contract amount?",
            question_type_id=1,
            label="Amount Question",
            company_id=sample_company.id,
        )
        test_db.add_all([question1, question2])
        await test_db.commit()

        params = ListQuestionsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.questions) == 2

        for question in result.result.questions:
            assert isinstance(question, QuestionResponse)
            assert question.matrix_id == sample_matrix.id

        question_texts = {q.question_text for q in result.result.questions}
        expected_texts = {"What is the contract date?", "What is the contract amount?"}
        assert question_texts == expected_texts

    async def test_execute_empty_matrix(self, tool, test_db, test_user, sample_matrix):
        """Test successful tool execution with empty matrix."""
        params = ListQuestionsParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.questions) == 0

    async def test_execute_nonexistent_matrix(
        self, tool, test_db, test_user, sample_company
    ):
        """Test tool execution with nonexistent matrix returns empty result."""
        params = ListQuestionsParameters(matrix_id=99999)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.questions) == 0
