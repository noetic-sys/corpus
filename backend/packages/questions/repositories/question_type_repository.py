from typing import List, Optional
from sqlalchemy import select

from packages.questions.models.database.question_type import QuestionTypeEntity
from questions.question_type import QuestionTypeModel
from common.repositories.base import BaseRepository
from common.providers.caching import cache


class QuestionTypeRepository(BaseRepository[QuestionTypeEntity, QuestionTypeModel]):
    def __init__(self):
        super().__init__(QuestionTypeEntity, QuestionTypeModel)

    @cache(QuestionTypeModel, ttl=3600)  # 1 hour cache
    async def get_all_question_types(self) -> List[QuestionTypeModel]:
        """Get all available question types."""
        async with self._get_session() as session:
            stmt = select(QuestionTypeEntity).order_by(QuestionTypeEntity.id)
            result = await session.execute(stmt)
            entities = result.scalars().all()
            return [QuestionTypeModel.model_validate(entity) for entity in entities]

    @cache(QuestionTypeModel, ttl=3600)  # 1 hour cache
    async def get_question_type_by_name(self, name: str) -> Optional[QuestionTypeModel]:
        """Get a question type by its name."""
        async with self._get_session() as session:
            stmt = select(QuestionTypeEntity).where(QuestionTypeEntity.name == name)
            result = await session.execute(stmt)
            entity = result.scalar_one_or_none()
            return QuestionTypeModel.model_validate(entity) if entity else None
