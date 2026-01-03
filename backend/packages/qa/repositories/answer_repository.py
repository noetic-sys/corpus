from typing import List, Optional
from sqlalchemy.future import select
from common.core.otel_axiom_exporter import trace_span
from common.repositories.base import BaseRepository
from common.providers.caching import cache
from packages.qa.models.database.answer import AnswerEntity
from packages.qa.models.domain.answer import AnswerModel
from packages.qa.cache_keys import answers_by_answer_set_key


class AnswerRepository(BaseRepository[AnswerEntity, AnswerModel]):
    def __init__(self):
        super().__init__(AnswerEntity, AnswerModel)

    @trace_span
    @cache(AnswerModel, ttl=7200, key_generator=answers_by_answer_set_key)
    async def get_by_answer_set_id(
        self, answer_set_id: int, company_id: Optional[int] = None
    ) -> List[AnswerModel]:
        """Get all answers for an answer set."""
        async with self._get_session() as session:
            query = select(AnswerEntity).where(
                AnswerEntity.answer_set_id == answer_set_id
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_answer_set_ids(
        self, answer_set_ids: List[int], company_id: Optional[int] = None
    ) -> List[AnswerModel]:
        """Batch fetch all answers for multiple answer sets."""
        if not answer_set_ids:
            return []

        async with self._get_session() as session:
            query = select(AnswerEntity).where(
                AnswerEntity.answer_set_id.in_(answer_set_ids)
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
