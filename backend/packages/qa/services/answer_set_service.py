from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.qa.repositories.answer_set_repository import AnswerSetRepository
from packages.qa.models.domain.answer_set import AnswerSetModel, AnswerSetCreateModel

logger = get_logger(__name__)


class AnswerSetService:
    """Service for handling answer set operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.answer_set_repo = AnswerSetRepository(db_session)

    @trace_span
    async def create_answer_set(
        self, answer_set_data: AnswerSetCreateModel, company_id: int
    ) -> AnswerSetModel:
        """Create a new answer set."""
        logger.info(
            f"Creating answer set for matrix cell {answer_set_data.matrix_cell_id}"
        )

        # Ensure company_id matches
        if answer_set_data.company_id != company_id:
            raise ValueError("Answer set company_id must match the provided company_id")

        answer_set = await self.answer_set_repo.create(answer_set_data)

        logger.info(f"Created answer set with ID: {answer_set.id}")
        return answer_set

    @trace_span
    async def get_answer_set(
        self, answer_set_id: int, company_id: Optional[int] = None
    ) -> Optional[AnswerSetModel]:
        """Get an answer set by ID."""
        answer_set = await self.answer_set_repo.get(answer_set_id)
        if (
            answer_set
            and company_id is not None
            and answer_set.company_id != company_id
        ):
            return None
        return answer_set

    @trace_span
    async def get_by_ids(self, answer_set_ids: List[int]) -> List[AnswerSetModel]:
        """Batch fetch answer sets by IDs."""
        return await self.answer_set_repo.get_by_ids(answer_set_ids)

    @trace_span
    async def get_answer_sets_for_matrix_cell(
        self, matrix_cell_id: int, company_id: Optional[int] = None
    ) -> List[AnswerSetModel]:
        """Get all answer sets for a matrix cell."""
        return await self.answer_set_repo.get_by_matrix_cell_id(
            matrix_cell_id, company_id
        )

    @trace_span
    async def get_current_answer_set_for_matrix_cell(
        self, matrix_cell_id: int, company_id: Optional[int] = None
    ) -> Optional[AnswerSetModel]:
        """Get the current (most recent) answer set for a matrix cell."""
        return await self.answer_set_repo.get_current_for_matrix_cell(
            matrix_cell_id, company_id
        )
