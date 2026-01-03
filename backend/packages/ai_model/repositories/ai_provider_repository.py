from typing import List, Optional
from sqlalchemy.future import select

from packages.ai_model.models.database.ai_provider import AIProviderEntity
from packages.ai_model.models.domain.ai_provider import AIProviderModel
from common.repositories.base import BaseRepository
from common.core.otel_axiom_exporter import trace_span
from common.providers.caching import cache


class AIProviderRepository(BaseRepository[AIProviderEntity, AIProviderModel]):
    def __init__(self):
        super().__init__(AIProviderEntity, AIProviderModel)

    @trace_span
    @cache(AIProviderModel, ttl=3600)  # 1 hour cache
    async def get_by_name(self, name: str) -> Optional[AIProviderModel]:
        """Get AI provider by name."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(self.entity_class.name == name)
            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    @cache(AIProviderModel, ttl=3600)  # 1 hour cache
    async def get_enabled(self) -> List[AIProviderModel]:
        """Get all enabled AI providers."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.enabled == True  # noqa
            )
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    @cache(bool, ttl=3600)  # 1 hour cache
    async def exists_by_name(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if AI provider with name exists (optionally excluding an ID)."""
        async with self._get_session() as session:
            query = select(self.entity_class.id).where(self.entity_class.name == name)

            if exclude_id is not None:
                query = query.where(self.entity_class.id != exclude_id)

            result = await session.execute(query)
            return result.scalar() is not None

    async def create(self, create_model):
        """AI providers are managed via database migrations only."""
        raise NotImplementedError(
            "AI providers must be created via database migrations"
        )

    async def update(self, id: int, update_model):
        """AI providers are managed via database migrations only."""
        raise NotImplementedError(
            "AI providers must be updated via database migrations"
        )

    async def delete(self, id: int) -> bool:
        """AI providers are managed via database migrations only."""
        raise NotImplementedError(
            "AI providers must be deleted via database migrations"
        )
