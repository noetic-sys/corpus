from typing import Optional, List
from sqlalchemy.future import select
from sqlalchemy import delete

from common.repositories.base import BaseRepository
from packages.questions.models.database.question_option import (
    QuestionOptionSetEntity,
    QuestionOptionEntity,
)
from packages.questions.models.domain.question_option import (
    QuestionOptionSetModel,
    QuestionOptionModel,
    QuestionOptionCreateModel,
    QuestionOptionSetRepositoryCreateModel,
    QuestionOptionRepositoryCreateModel,
)
from common.core.otel_axiom_exporter import trace_span


class QuestionOptionSetRepository(
    BaseRepository[QuestionOptionSetEntity, QuestionOptionSetModel]
):
    def __init__(self):
        super().__init__(QuestionOptionSetEntity, QuestionOptionSetModel)

    def _entity_to_domain(
        self, entity: QuestionOptionSetEntity
    ) -> QuestionOptionSetModel:
        """Convert entity to domain model without accessing relationships."""
        return QuestionOptionSetModel(
            id=entity.id,
            question_id=entity.question_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @trace_span
    async def get_by_question_id(
        self, question_id: int
    ) -> Optional[QuestionOptionSetModel]:
        """Get option set for a question using separate queries."""
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class).where(
                    self.entity_class.question_id == question_id
                )
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return None

            return QuestionOptionSetModel(
                id=entity.id,
                question_id=entity.question_id,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )

    @trace_span
    async def create_for_question(self, question_id: int) -> QuestionOptionSetModel:
        """Create option set for a question."""
        create_model = QuestionOptionSetRepositoryCreateModel(question_id=question_id)
        return await self.create(create_model)

    @trace_span
    async def delete_by_question_id(self, question_id: int) -> bool:
        """Delete option set and all its options for a question."""
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class).where(
                    self.entity_class.question_id == question_id
                )
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return False

            await session.delete(entity)
            await session.commit()
            return True


class QuestionOptionRepository(
    BaseRepository[QuestionOptionEntity, QuestionOptionModel]
):
    def __init__(self):
        super().__init__(QuestionOptionEntity, QuestionOptionModel)

    @trace_span
    async def get_by_option_set_id(
        self, option_set_id: int
    ) -> List[QuestionOptionModel]:
        """Get all options for an option set."""
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class).where(
                    self.entity_class.option_set_id == option_set_id
                )
            )
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def create_for_set(
        self, option_set_id: int, create_model: QuestionOptionCreateModel
    ) -> QuestionOptionModel:
        """Create a single option for an option set."""
        repository_create_model = QuestionOptionRepositoryCreateModel(
            option_set_id=option_set_id, value=create_model.value
        )
        return await self.create(repository_create_model)

    @trace_span
    async def bulk_create_for_set(
        self, option_set_id: int, create_models: List[QuestionOptionCreateModel]
    ) -> List[QuestionOptionModel]:
        """Create multiple options for an option set."""
        entities = []
        for i, create_model in enumerate(create_models):
            option_data = create_model.model_dump(exclude_none=True)

            entity = self.entity_class(
                option_set_id=option_set_id, value=option_data["value"]
            )
            entities.append(entity)

        return await self.bulk_create(entities)

    @trace_span
    async def replace_all_for_set(
        self, option_set_id: int, create_models: List[QuestionOptionCreateModel]
    ) -> List[QuestionOptionModel]:
        """Replace all options for an option set."""
        async with self._get_session() as session:
            # Delete existing options
            await session.execute(
                delete(self.entity_class).where(
                    self.entity_class.option_set_id == option_set_id
                )
            )
            await session.commit()

        # Create new options
        return await self.bulk_create_for_set(option_set_id, create_models)

    @trace_span
    async def delete_by_option_set_id(self, option_set_id: int) -> int:
        """Delete all options for an option set."""
        async with self._get_session() as session:
            result = await session.execute(
                delete(self.entity_class).where(
                    self.entity_class.option_set_id == option_set_id
                )
            )
            await session.commit()
            return result.rowcount
