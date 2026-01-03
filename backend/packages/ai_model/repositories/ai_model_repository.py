from typing import List, Optional
from sqlalchemy.future import select

from packages.ai_model.models.database.ai_model import AIModelEntity
from packages.ai_model.models.database.ai_provider import AIProviderEntity
from packages.ai_model.models.domain.ai_model import AIModelModel
from packages.ai_model.models.domain.ai_provider import AIProviderModel
from common.repositories.base import BaseRepository
from common.core.otel_axiom_exporter import trace_span
from common.providers.caching import cache


class AIModelRepository(BaseRepository[AIModelEntity, AIModelModel]):
    def __init__(self):
        super().__init__(AIModelEntity, AIModelModel)

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get(self, model_id: int) -> Optional[AIModelModel]:
        """Override base get to include provider information."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(self.entity_class.id == model_id)
            )

            # Add deleted filter if the entity has a deleted column
            if hasattr(self.entity_class, "deleted"):
                query = query.where(self.entity_class.deleted == False)  # noqa

            result = await session.execute(query)
            row = result.one_or_none()

            if not row:
                return None

            model_entity, provider_entity = row
            model = self._entity_to_domain(model_entity)

            if provider_entity:
                model.provider = AIProviderModel.model_validate(provider_entity)

            return model

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[AIModelModel]:
        """Override base get_multi to include provider information."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .offset(skip)
                .limit(limit)
            )

            # Add deleted filter if the entity has a deleted column
            if hasattr(self.entity_class, "deleted"):
                query = query.where(self.entity_class.deleted == False)  # noqa

            result = await session.execute(query)
            rows = result.all()

            models = []
            for model_entity, provider_entity in rows:
                model = self._entity_to_domain(model_entity)
                if provider_entity:
                    model.provider = AIProviderModel.model_validate(provider_entity)
                models.append(model)

            return models

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_by_provider_id(self, provider_id: int) -> List[AIModelModel]:
        """Get all AI models for a specific provider."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(self.entity_class.provider_id == provider_id)
            )
            result = await session.execute(query)
            rows = result.all()

            models = []
            for model_entity, provider_entity in rows:
                model = self._entity_to_domain(model_entity)
                if provider_entity:
                    model.provider = AIProviderModel.model_validate(provider_entity)
                models.append(model)

            return models

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_enabled_by_provider_id(self, provider_id: int) -> List[AIModelModel]:
        """Get all enabled AI models for a specific provider."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(
                    self.entity_class.provider_id == provider_id,
                    self.entity_class.enabled == True,  # noqa
                )
            )
            result = await session.execute(query)
            rows = result.all()

            models = []
            for model_entity, provider_entity in rows:
                model = self._entity_to_domain(model_entity)
                if provider_entity:
                    model.provider = AIProviderModel.model_validate(provider_entity)
                models.append(model)

            return models

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_enabled(self) -> List[AIModelModel]:
        """Get all enabled AI models."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(self.entity_class.enabled == True)  # noqa
            )
            result = await session.execute(query)
            rows = result.all()

            models = []
            for model_entity, provider_entity in rows:
                model = self._entity_to_domain(model_entity)
                if provider_entity:
                    model.provider = AIProviderModel.model_validate(provider_entity)
                models.append(model)

            return models

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_by_model_name_and_provider(
        self, model_name: str, provider_id: int
    ) -> Optional[AIModelModel]:
        """Get AI model by model name and provider ID."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(
                    self.entity_class.model_name == model_name,
                    self.entity_class.provider_id == provider_id,
                )
            )
            result = await session.execute(query)
            row = result.one_or_none()

            if not row:
                return None

            model_entity, provider_entity = row
            model = self._entity_to_domain(model_entity)

            if provider_entity:
                model.provider = AIProviderModel.model_validate(provider_entity)

            return model

    @trace_span
    @cache(bool, ttl=3600)  # 1 hour cache
    async def exists_by_name_and_provider(
        self, model_name: str, provider_id: int, exclude_id: Optional[int] = None
    ) -> bool:
        """Check if AI model with name and provider exists (optionally excluding an ID)."""
        async with self._get_session() as session:
            query = select(self.entity_class.id).where(
                self.entity_class.model_name == model_name,
                self.entity_class.provider_id == provider_id,
            )

            if exclude_id is not None:
                query = query.where(self.entity_class.id != exclude_id)

            result = await session.execute(query)
            return result.scalar() is not None

    @trace_span
    @cache(AIModelModel, ttl=3600)  # 1 hour cache
    async def get_with_provider(self, model_id: int) -> Optional[AIModelModel]:
        """Get AI model with provider information using JOIN.

        TODO: Consider refactoring domain models to have simpler structures
        without nested complex objects, now that we've removed SQLAlchemy
        relationships. This would make the architecture more consistent
        with the flat database entity structure.
        """
        async with self._get_session() as session:
            query = (
                select(self.entity_class, AIProviderEntity)
                .join(
                    AIProviderEntity,
                    self.entity_class.provider_id == AIProviderEntity.id,
                )
                .where(self.entity_class.id == model_id)
            )

            result = await session.execute(query)
            row = result.one_or_none()

            if not row:
                return None

            model_entity, provider_entity = row
            model = self._entity_to_domain(model_entity)

            # Attach the provider to the model
            if provider_entity:
                model.provider = AIProviderModel.model_validate(provider_entity)

            return model

    async def create(self, create_model):
        """AI models are managed via database migrations only."""
        raise NotImplementedError("AI models must be created via database migrations")

    async def update(self, id: int, update_model):
        """AI models are managed via database migrations only."""
        raise NotImplementedError("AI models must be updated via database migrations")

    async def delete(self, id: int) -> bool:
        """AI models are managed via database migrations only."""
        raise NotImplementedError("AI models must be deleted via database migrations")
