from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import update

from common.repositories.base import BaseRepository
from packages.agents.models.database.conversation import ConversationEntity
from packages.agents.models.domain.conversation import ConversationModel
from common.core.otel_axiom_exporter import trace_span


class ConversationRepository(BaseRepository[ConversationEntity, ConversationModel]):
    def __init__(self):
        super().__init__(ConversationEntity, ConversationModel)

    @trace_span
    async def get_active_conversations(
        self, company_id: Optional[int] = None
    ) -> List[ConversationModel]:
        query = (
            select(self.entity_class)
            .where(
                self.entity_class.is_active == True, self.entity_class.deleted == False
            )
            .order_by(self.entity_class.id.desc())
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def deactivate_conversation(
        self, conversation_id: int, company_id: Optional[int] = None
    ) -> Optional[ConversationModel]:
        query = update(self.entity_class).where(self.entity_class.id == conversation_id)

        if company_id is not None:
            query = query.where(self.entity_class.company_id == company_id)

        async with self._get_session() as session:
            result = await session.execute(
                query.values(is_active=False).returning(self.entity_class)
            )
            entity = result.scalar_one_or_none()
            if entity:
                await session.flush()
                return self._entity_to_domain(entity)
            return None

    @trace_span
    async def get_by_ai_model_id(
        self, ai_model_id: int, company_id: Optional[int] = None
    ) -> List[ConversationModel]:
        query = (
            select(self.entity_class)
            .where(
                self.entity_class.ai_model_id == ai_model_id,
                self.entity_class.is_active == True,
                self.entity_class.deleted == False,
            )
            .order_by(self.entity_class.id.desc())
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_all(
        self, skip: int = 0, limit: int = 100, company_id: Optional[int] = None
    ) -> List[ConversationModel]:
        """Get all active, non-deleted conversations with pagination."""
        query = (
            select(self.entity_class)
            .where(
                self.entity_class.is_active == True, self.entity_class.deleted == False
            )
            .order_by(self.entity_class.id.desc())
            .offset(skip)
            .limit(limit)
        )

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        async with self._get_session() as session:
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
