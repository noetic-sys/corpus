"""
Request/response schemas for agent QA answer uploads.

Agents running in isolated containers POST their answers directly to the API.
These schemas reuse existing domain models.
"""

from typing import List
from pydantic import BaseModel, Field

from packages.qa.models.domain.answer_data import AnswerData


class AgentQAAnswerSetRequest(BaseModel):
    """
    Request body for agent QA answer upload.

    This schema reuses the existing domain models (TextAnswerData, DateAnswerData, etc.)
    defined in packages.qa.models.domain.answer_data.

    The agent container receives these parameters from the workflow and includes them
    in the upload request.
    """

    matrix_cell_id: int = Field(..., description="Matrix cell ID being answered")
    question_type_id: int = Field(..., description="Question type ID")
    answer_found: bool = Field(
        ..., description="Whether any answer was found in the documents"
    )
    answers: List[AnswerData] = Field(
        default_factory=list,
        description="List of answers found (TextAnswerData, DateAnswerData, CurrencyAnswerData, or SelectAnswerData)",
    )


class AgentQAAnswerUploadResponse(BaseModel):
    """Response after successfully uploading agent QA answer."""

    qa_job_id: int
    matrix_cell_id: int
    answer_count: int
    message: str = "Answer uploaded successfully"
