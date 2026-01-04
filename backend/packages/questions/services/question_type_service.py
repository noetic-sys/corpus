from typing import List, Optional

from packages.questions.repositories.question_type_repository import (
    QuestionTypeRepository,
)
from questions.question_type import QuestionTypeModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QuestionTypeService:
    """Service for handling question type operations."""

    def __init__(self):
        self.question_type_repo = QuestionTypeRepository()

    @trace_span
    async def get_all_question_types(self) -> List[QuestionTypeModel]:
        """Get all available question types."""
        return await self.question_type_repo.get_all_question_types()

    @trace_span
    async def get_question_type(
        self, question_type_id: int
    ) -> Optional[QuestionTypeModel]:
        """Get a question type by ID."""
        return await self.question_type_repo.get(question_type_id)

    @trace_span
    async def get_question_type_by_name(self, name: str) -> Optional[QuestionTypeModel]:
        """Get a question type by name."""
        return await self.question_type_repo.get_question_type_by_name(name)


def get_question_type_service() -> QuestionTypeService:
    """Get question type service instance."""
    return QuestionTypeService()
