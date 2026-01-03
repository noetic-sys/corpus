from typing import List
from fastapi import APIRouter, HTTPException, Path

from packages.questions.models.schemas.question_type import QuestionTypeResponse
from packages.questions.services.question_type_service import get_question_type_service
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.context import readonly

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/question-types/",
    response_model=List[QuestionTypeResponse],
    tags=["workflow_agent"],
    operation_id="get_question_types",
)
@readonly
@trace_span
async def get_question_types():
    """Get all available question types."""
    question_type_service = get_question_type_service()
    question_types = await question_type_service.get_all_question_types()
    return question_types


@router.get("/question-types/{questionTypeId}", response_model=QuestionTypeResponse)
@readonly
@trace_span
async def get_question_type(
    question_type_id: int = Path(alias="questionTypeId"),
):
    """Get a specific question type by ID."""
    question_type_service = get_question_type_service()
    question_type = await question_type_service.get_question_type(question_type_id)
    if question_type is None:
        raise HTTPException(status_code=404, detail="Question type not found")
    return question_type
