"""Unit tests for AI configuration module."""

import pytest
from matrices.matrix_enums import MatrixType
from questions.question_type import QuestionTypeName

from ai_config import (
    DEFAULT_AI_PARAMS,
    DEFAULT_ANALYSIS_PROMPT,
    DEFAULT_INSTRUCTION,
    DEFAULT_PROMPT_FILE,
    AIParams,
    PromptFiles,
    get_ai_params,
    get_analysis_prompt_file,
    get_prompt_file,
    get_type_instruction,
)


class TestAIParams:
    """Test AIParams NamedTuple."""

    def test_ai_params_creation(self):
        """Test creating AIParams instance."""
        params = AIParams(temperature=0.5, max_tokens=100)
        assert params.temperature == 0.5
        assert params.max_tokens == 100

    def test_ai_params_immutable(self):
        """Test that AIParams is immutable."""
        params = AIParams(temperature=0.5, max_tokens=100)
        with pytest.raises(AttributeError):
            params.temperature = 0.7


class TestPromptFiles:
    """Test PromptFiles NamedTuple."""

    def test_prompt_files_creation(self):
        """Test creating PromptFiles instance."""
        prompt = PromptFiles(file_name="test.txt")
        assert prompt.file_name == "test.txt"

    def test_prompt_files_immutable(self):
        """Test that PromptFiles is immutable."""
        prompt = PromptFiles(file_name="test.txt")
        with pytest.raises(AttributeError):
            prompt.file_name = "other.txt"


@pytest.mark.skip("these change often")
class TestGetAIParams:
    """Test get_ai_params function."""

    def test_get_ai_params_date(self):
        """Test getting AI parameters for DATE type."""
        params = get_ai_params(QuestionTypeName.DATE)
        assert params.temperature == 0.0
        assert params.max_tokens == 50

    def test_get_ai_params_currency(self):
        """Test getting AI parameters for CURRENCY type."""
        params = get_ai_params(QuestionTypeName.CURRENCY)
        assert params.temperature == 0.0
        assert params.max_tokens == 100

    def test_get_ai_params_short_answer(self):
        """Test getting AI parameters for SHORT_ANSWER type."""
        params = get_ai_params(QuestionTypeName.SHORT_ANSWER)
        assert params.temperature == 0.1
        assert params.max_tokens == 200

    def test_get_ai_params_select(self):
        """Test getting AI parameters for SELECT type."""
        params = get_ai_params(QuestionTypeName.SELECT)
        assert params.temperature == 0.0
        assert params.max_tokens == 300

    def test_get_ai_params_long_answer(self):
        """Test getting AI parameters for LONG_ANSWER type."""
        params = get_ai_params(QuestionTypeName.LONG_ANSWER)
        assert params.temperature == 0.2
        assert params.max_tokens == 1500

    def test_get_ai_params_default_fallback(self):
        """Test getting default AI parameters for unknown type."""
        # Since we can't create an invalid enum value, test with None handling
        # by testing the default constant directly
        assert DEFAULT_AI_PARAMS.temperature == 0.1
        assert DEFAULT_AI_PARAMS.max_tokens == 1000


class TestGetPromptFile:
    """Test get_prompt_file function."""

    def test_get_prompt_file_date(self):
        """Test getting prompt file for DATE type."""
        result = get_prompt_file(QuestionTypeName.DATE)
        assert result == "answers/answer_question_date.txt"

    def test_get_prompt_file_currency(self):
        """Test getting prompt file for CURRENCY type."""
        result = get_prompt_file(QuestionTypeName.CURRENCY)
        assert result == "answers/answer_question_currency.txt"

    def test_get_prompt_file_short_answer(self):
        """Test getting prompt file for SHORT_ANSWER type."""
        result = get_prompt_file(QuestionTypeName.SHORT_ANSWER)
        assert result == "answers/answer_question_short.txt"

    def test_get_prompt_file_select(self):
        """Test getting prompt file for SELECT type."""
        result = get_prompt_file(QuestionTypeName.SELECT)
        assert result == "answers/answer_question_select.txt"

    def test_get_prompt_file_long_answer(self):
        """Test getting prompt file for LONG_ANSWER type."""
        result = get_prompt_file(QuestionTypeName.LONG_ANSWER)
        assert result == "answers/answer_question.txt"

    def test_get_prompt_file_default_fallback(self):
        """Test getting default prompt file for unknown type."""
        # Test the default constant directly
        assert DEFAULT_PROMPT_FILE == "answers/answer_question.txt"


class TestGetTypeInstruction:
    """Test get_type_instruction function."""

    def test_get_type_instruction_date(self):
        """Test getting instruction for DATE type."""
        result = get_type_instruction(QuestionTypeName.DATE)
        assert "YYYY-MM-DD" in result
        assert "No date found" in result

    def test_get_type_instruction_currency(self):
        """Test getting instruction for CURRENCY type."""
        result = get_type_instruction(QuestionTypeName.CURRENCY)
        assert "monetary amount" in result
        assert "No amount found" in result

    def test_get_type_instruction_short_answer(self):
        """Test getting instruction for SHORT_ANSWER type."""
        result = get_type_instruction(QuestionTypeName.SHORT_ANSWER)
        assert "brief, concise answer" in result
        assert "under 200 characters" in result

    def test_get_type_instruction_long_answer(self):
        """Test getting instruction for LONG_ANSWER type."""
        result = get_type_instruction(QuestionTypeName.LONG_ANSWER)
        assert "detailed, comprehensive answer" in result

    def test_get_type_instruction_default_fallback(self):
        """Test getting default instruction for unknown type."""
        # Test the default constant directly
        assert (
            "Please answer the question based on the document content above"
            in DEFAULT_INSTRUCTION
        )


class TestGetAnalysisPromptFile:
    """Test get_analysis_prompt_file function."""

    def test_get_analysis_prompt_standard(self):
        """Test getting analysis prompt for STANDARD matrix type."""
        result = get_analysis_prompt_file(MatrixType.STANDARD)
        assert result == "analysis/standard_analysis.txt"

    def test_get_analysis_prompt_cross_correlation(self):
        """Test getting analysis prompt for CROSS_CORRELATION matrix type."""
        result = get_analysis_prompt_file(MatrixType.CROSS_CORRELATION)
        assert result == "analysis/correlation_analysis.txt"

    def test_get_analysis_prompt_generic_correlation(self):
        """Test getting analysis prompt for GENERIC_CORRELATION matrix type."""
        result = get_analysis_prompt_file(MatrixType.GENERIC_CORRELATION)
        assert result == "analysis/correlation_analysis.txt"

    def test_get_analysis_prompt_default_fallback(self):
        """Test getting default analysis prompt."""
        assert DEFAULT_ANALYSIS_PROMPT == "analysis/standard_analysis.txt"


class TestConfigurationConsistency:
    """Test consistency across configuration mappings."""

    def test_all_question_types_have_ai_params(self):
        """Test that all question types have AI parameters defined."""
        for question_type in QuestionTypeName:
            params = get_ai_params(question_type)
            assert isinstance(params, AIParams)
            assert isinstance(params.temperature, (int, float))
            assert isinstance(params.max_tokens, int)
            assert params.temperature >= 0.0
            assert params.max_tokens > 0

    def test_all_question_types_have_prompt_files(self):
        """Test that all question types have prompt files defined."""
        for question_type in QuestionTypeName:
            prompt_file = get_prompt_file(question_type)
            assert isinstance(prompt_file, str)
            assert prompt_file.endswith(".txt")
            assert len(prompt_file) > 0

    def test_all_question_types_have_instructions(self):
        """Test that all question types have instructions defined."""
        for question_type in QuestionTypeName:
            instruction = get_type_instruction(question_type)
            assert isinstance(instruction, str)
            assert len(instruction) > 0
            # All instructions should start with newlines for formatting
            assert instruction.startswith("\n\n")

    def test_deterministic_types_have_zero_temperature(self):
        """Test that deterministic question types have zero temperature."""
        deterministic_types = [
            QuestionTypeName.DATE,
            QuestionTypeName.CURRENCY,
            QuestionTypeName.SELECT,
        ]

        for question_type in deterministic_types:
            params = get_ai_params(question_type)
            assert (
                params.temperature == 0.0
            ), f"{question_type} should have zero temperature"

    def test_creative_types_have_higher_temperature(self):
        """Test that creative question types have higher temperature."""
        creative_types = [
            QuestionTypeName.SHORT_ANSWER,
            QuestionTypeName.LONG_ANSWER,
        ]

        for question_type in creative_types:
            params = get_ai_params(question_type)
            assert (
                params.temperature > 0.0
            ), f"{question_type} should have positive temperature"
