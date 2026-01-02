"""AI configuration for question types and matrix types."""

from typing import Dict, NamedTuple

from matrices.matrix_enums import MatrixType
from questions.question_type import QuestionTypeName


class AIParams(NamedTuple):
    """AI parameters for a question type."""

    temperature: float
    max_tokens: int


class PromptFiles(NamedTuple):
    """Prompt file configuration for question types."""

    file_name: str


# AI parameters by question type
AI_PARAMS_BY_TYPE: Dict[QuestionTypeName, AIParams] = {
    QuestionTypeName.DATE: AIParams(temperature=0.0, max_tokens=3000),
    QuestionTypeName.CURRENCY: AIParams(temperature=0.0, max_tokens=3000),
    QuestionTypeName.SHORT_ANSWER: AIParams(temperature=0.1, max_tokens=3000),
    QuestionTypeName.SELECT: AIParams(temperature=0.0, max_tokens=3000),
    QuestionTypeName.LONG_ANSWER: AIParams(temperature=0.2, max_tokens=6000),
}

# Default parameters for unknown types
DEFAULT_AI_PARAMS = AIParams(temperature=0.1, max_tokens=3000)

# Answer format prompt files by question type (in answers/ subdirectory)
PROMPT_FILES_BY_TYPE: Dict[QuestionTypeName, PromptFiles] = {
    QuestionTypeName.DATE: PromptFiles("answers/answer_question_date.txt"),
    QuestionTypeName.CURRENCY: PromptFiles("answers/answer_question_currency.txt"),
    QuestionTypeName.SHORT_ANSWER: PromptFiles("answers/answer_question_short.txt"),
    QuestionTypeName.SELECT: PromptFiles("answers/answer_question_select.txt"),
    QuestionTypeName.LONG_ANSWER: PromptFiles("answers/answer_question.txt"),
}

# Default answer format prompt file
DEFAULT_PROMPT_FILE = "answers/answer_question.txt"

# Analysis prompt files by matrix type (in analysis/ subdirectory)
ANALYSIS_PROMPTS_BY_MATRIX_TYPE: Dict[MatrixType, str] = {
    MatrixType.STANDARD: "analysis/standard_analysis.txt",
    MatrixType.CROSS_CORRELATION: "analysis/correlation_analysis.txt",
    MatrixType.GENERIC_CORRELATION: "analysis/correlation_analysis.txt",
}

# Default analysis prompt (for standard matrices)
DEFAULT_ANALYSIS_PROMPT = "analysis/standard_analysis.txt"

# Type-specific instructions for user messages
TYPE_INSTRUCTIONS: Dict[QuestionTypeName, str] = {
    QuestionTypeName.DATE: "\n\nPlease extract the date and format it as YYYY-MM-DD. If no date is found, respond with 'No date found'.",
    QuestionTypeName.CURRENCY: "\n\nPlease extract the monetary amount. Include currency symbol or code if present. If no amount is found, respond with 'No amount found'.",
    QuestionTypeName.SHORT_ANSWER: "\n\nPlease provide a brief, concise answer (under 200 characters). Focus on the key information only.",
    QuestionTypeName.LONG_ANSWER: "\n\nPlease provide a detailed, comprehensive answer based on the document content.",
    QuestionTypeName.SELECT: "\n\nPlease select all relevant options from the provided list that match the document content.",
}

# Default instruction
DEFAULT_INSTRUCTION = (
    "\n\nPlease answer the question based on the document content above."
)


def get_ai_params(question_type: QuestionTypeName) -> AIParams:
    """Get AI parameters for a question type."""
    return AI_PARAMS_BY_TYPE.get(question_type, DEFAULT_AI_PARAMS)


def get_prompt_file(question_type: QuestionTypeName) -> str:
    """Get prompt file for a question type."""
    prompt_config = PROMPT_FILES_BY_TYPE.get(question_type)
    return prompt_config.file_name if prompt_config else DEFAULT_PROMPT_FILE


def get_type_instruction(question_type: QuestionTypeName) -> str:
    """Get type-specific instruction for a question type."""
    return TYPE_INSTRUCTIONS.get(question_type, DEFAULT_INSTRUCTION)


def get_analysis_prompt_file(matrix_type: MatrixType) -> str:
    """Get analysis prompt file based on matrix type.

    Args:
        matrix_type: Type of matrix (STANDARD, CROSS_CORRELATION, GENERIC_CORRELATION)

    Returns:
        Path to analysis prompt file (standard_analysis.txt or correlation_analysis.txt)
    """
    return ANALYSIS_PROMPTS_BY_MATRIX_TYPE.get(matrix_type, DEFAULT_ANALYSIS_PROMPT)
