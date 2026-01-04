from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import desc, func

from common.repositories.base import BaseRepository
from packages.agents.models.database.message import MessageEntity
from packages.agents.models.domain.message import MessageModel
from common.core.otel_axiom_exporter import trace_span


class MessageRepository(BaseRepository[MessageEntity, MessageModel]):
    def __init__(self):
        super().__init__(MessageEntity, MessageModel)

    @trace_span
    async def get_by_conversation_id(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> List[MessageModel]:
        query = (
            select(self.entity_class)
            .where(self.entity_class.conversation_id == conversation_id)
            .order_by(self.entity_class.sequence_number.asc())
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        if limit:
            query = query.limit(limit)

        async with self._get_session() as session:
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_latest_by_conversation_id(
        self, conversation_id: int, count: int = 10, company_id: Optional[int] = None
    ) -> List[MessageModel]:
        query = (
            select(self.entity_class)
            .where(self.entity_class.conversation_id == conversation_id)
            .order_by(desc(self.entity_class.sequence_number))
            .limit(count)
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            entities = result.scalars().all()
            # Reverse to get chronological order
            return self._entities_to_domain(list(reversed(entities)))

    @trace_span
    async def get_next_sequence_number(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> int:
        query = select(func.max(self.entity_class.sequence_number)).where(
            self.entity_class.conversation_id == conversation_id
        )

        if company_id is not None:
            query = query.where(self.entity_class.company_id == company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            max_seq = result.scalar() or 0
            return max_seq + 1

    @trace_span
    async def get_by_tool_call_id(
        self, tool_call_id: str, company_id: Optional[int] = None
    ) -> Optional[MessageModel]:
        query = select(self.entity_class).where(
            self.entity_class.tool_call_id == tool_call_id
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def count_by_conversation_id(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> int:
        query = select(func.count(self.entity_class.id)).where(
            self.entity_class.conversation_id == conversation_id
        )

        if company_id is not None:
            query = query.where(self.entity_class.company_id == company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            return result.scalar() or 0
