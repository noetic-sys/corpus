from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, func

from common.repositories.base import BaseRepository
from packages.questions.models.database.question import QuestionEntity
from packages.questions.models.domain.question import QuestionModel
from common.core.otel_axiom_exporter import trace_span
from common.core.otel_axiom_exporter import get_logger


logger = get_logger(__name__)


class QuestionRepository(BaseRepository[QuestionEntity, QuestionModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(QuestionEntity, QuestionModel, db_session)

    @trace_span
    async def get(
        self, entity_id: int, company_id: Optional[int] = None
    ) -> Optional[QuestionModel]:
        """Get question by ID with optional company filtering."""
        query = select(self.entity_class).where(
            self.entity_class.id == entity_id,
            self.entity_class.deleted == False,  # noqa
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_by_matrix_id(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[QuestionModel]:
        query = (
            select(self.entity_class)
            .where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )
            .order_by(self.entity_class.id.asc())
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def search_by_text(
        self,
        search_text: str,
        matrix_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> List[QuestionModel]:
        query = select(self.entity_class).where(
            self.entity_class.question_text.ilike(f"%{search_text}%"),
            self.entity_class.deleted == False,  # noqa
        )
        if matrix_id is not None:
            query = query.where(self.entity_class.matrix_id == matrix_id)

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        logger.error(query)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_valid_ids_for_matrix(
        self, matrix_id: int, question_ids: List[int], company_id: Optional[int] = None
    ) -> List[int]:
        """Get valid question IDs that belong to the matrix and are not deleted."""
        valid_questions_query = select(QuestionEntity.id).where(
            QuestionEntity.id.in_(question_ids),
            QuestionEntity.matrix_id == matrix_id,
            QuestionEntity.deleted == False,  # noqa
        )
        if company_id is not None:
            valid_questions_query = valid_questions_query.where(
                QuestionEntity.company_id == company_id
            )
        result = await self.db_session.execute(valid_questions_query)
        return [row[0] for row in result.fetchall()]

    @trace_span
    async def bulk_soft_delete_by_matrix_ids(
        self, matrix_ids: List[int], company_id: Optional[int] = None
    ) -> int:
        """Bulk soft delete questions by matrix IDs."""
        if not matrix_ids:
            return 0

        query = update(self.entity_class).where(
            self.entity_class.matrix_id.in_(matrix_ids),
            self.entity_class.deleted == False,  # noqa
        )

        if company_id is not None:
            query = query.where(self.entity_class.company_id == company_id)

        result = await self.db_session.execute(query.values(deleted=True))
        await self.db_session.flush()
        return result.rowcount

    @trace_span
    async def delete(self, entity_id: int, company_id: Optional[int] = None) -> bool:
        """Delete question with optional company access control."""
        if company_id is not None:
            # First verify the question belongs to the company
            question = await self.get(entity_id, company_id)
            if not question:
                return False

        # Use the base class delete method
        return await super().delete(entity_id)

    @trace_span
    async def count_agentic_questions(
        self, question_ids: List[int], company_id: Optional[int] = None
    ) -> int:
        """Count how many of the given question IDs have use_agent_qa=True."""
        if not question_ids:
            return 0

        query = select(func.count(QuestionEntity.id)).where(
            QuestionEntity.id.in_(question_ids),
            QuestionEntity.use_agent_qa == True,  # noqa
            QuestionEntity.deleted == False,  # noqa
        )
        if company_id is not None:
            query = query.where(QuestionEntity.company_id == company_id)

        result = await self.db_session.execute(query)
        return result.scalar_one() or 0
