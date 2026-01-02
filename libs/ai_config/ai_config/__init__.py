"""Shared AI configuration for question types and matrix types."""

from ai_config.config import (
    AI_PARAMS_BY_TYPE,
    ANALYSIS_PROMPTS_BY_MATRIX_TYPE,
    DEFAULT_AI_PARAMS,
    DEFAULT_ANALYSIS_PROMPT,
    DEFAULT_INSTRUCTION,
    DEFAULT_PROMPT_FILE,
    PROMPT_FILES_BY_TYPE,
    TYPE_INSTRUCTIONS,
    AIParams,
    PromptFiles,
    get_ai_params,
    get_analysis_prompt_file,
    get_prompt_file,
    get_type_instruction,
)

__all__ = [
    "AIParams",
    "PromptFiles",
    "AI_PARAMS_BY_TYPE",
    "DEFAULT_AI_PARAMS",
    "PROMPT_FILES_BY_TYPE",
    "DEFAULT_PROMPT_FILE",
    "ANALYSIS_PROMPTS_BY_MATRIX_TYPE",
    "DEFAULT_ANALYSIS_PROMPT",
    "TYPE_INSTRUCTIONS",
    "DEFAULT_INSTRUCTION",
    "get_ai_params",
    "get_prompt_file",
    "get_type_instruction",
    "get_analysis_prompt_file",
]
