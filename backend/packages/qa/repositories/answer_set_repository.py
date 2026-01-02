from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from common.core.otel_axiom_exporter import trace_span
from common.repositories.base import BaseRepository
from common.providers.caching import cache
from packages.qa.models.database.answer_set import AnswerSetEntity
from packages.qa.models.domain.answer_set import AnswerSetModel
from packages.qa.cache_keys import (
    answer_set_by_matrix_cell_key,
    answer_set_current_by_matrix_cell_key,
)


class AnswerSetRepository(BaseRepository[AnswerSetEntity, AnswerSetModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(AnswerSetEntity, AnswerSetModel, db_session)

    @trace_span
    @cache(AnswerSetModel, ttl=7200, key_generator=answer_set_by_matrix_cell_key)
    async def get_by_matrix_cell_id(
        self, matrix_cell_id: int, company_id: Optional[int] = None
    ) -> List[AnswerSetModel]:
        """Get all answer sets for a matrix cell."""
        query = select(AnswerSetEntity).where(
            AnswerSetEntity.matrix_cell_id == matrix_cell_id
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    @cache(
        AnswerSetModel, ttl=7200, key_generator=answer_set_current_by_matrix_cell_key
    )
    async def get_current_for_matrix_cell(
        self, matrix_cell_id: int, company_id: Optional[int] = None
    ) -> Optional[AnswerSetModel]:
        """Get the current answer set for a matrix cell (most recent one)."""
        query = (
            select(AnswerSetEntity)
            .where(AnswerSetEntity.matrix_cell_id == matrix_cell_id)
            .order_by(AnswerSetEntity.created_at.desc())
            .limit(1)
        )
        if company_id is not None:
            query = query.where(AnswerSetEntity.company_id == company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None
