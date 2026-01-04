from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import delete, update

from common.repositories.base import BaseRepository
from packages.questions.models.database.question_template_variable import (
    QuestionTemplateVariableEntity,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableModel,
)
from common.core.otel_axiom_exporter import trace_span


class QuestionTemplateVariableRepository(
    BaseRepository[QuestionTemplateVariableEntity, QuestionTemplateVariableModel]
):
    def __init__(self):
        super().__init__(QuestionTemplateVariableEntity, QuestionTemplateVariableModel)

    @trace_span
    async def get_by_question_id(
        self, question_id: int, company_id: Optional[int] = None
    ) -> List[QuestionTemplateVariableModel]:
        """Get all template variable associations for a question (excluding soft deleted)."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.question_id == question_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_template_variable_id(
        self, template_variable_id: int, company_id: Optional[int] = None
    ) -> List[QuestionTemplateVariableModel]:
        """Get all questions using a specific template variable (excluding soft deleted)."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.template_variable_id == template_variable_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_questions_by_template_variable(
        self, template_variable_id: int, company_id: Optional[int] = None
    ) -> List[int]:
        """Get question IDs that use a specific template variable (excluding soft deleted)."""
        async with self._get_session() as session:
            query = select(self.entity_class.question_id).where(
                self.entity_class.template_variable_id == template_variable_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def bulk_get_questions_by_variables(
        self, template_variable_ids: List[int], company_id: Optional[int] = None
    ) -> List[int]:
        """Get all unique question IDs that use any of the specified template variables (excluding soft deleted)."""
        if not template_variable_ids:
            return []

        async with self._get_session() as session:
            query = (
                select(self.entity_class.question_id)
                .distinct()
                .where(
                    self.entity_class.template_variable_id.in_(template_variable_ids),
                    self.entity_class.deleted == False,  # noqa
                )
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def delete_by_question_id(
        self, question_id: int, company_id: Optional[int] = None
    ) -> int:
        """Soft delete all template variable associations for a question."""
        async with self._get_session() as session:
            query = update(self.entity_class).where(
                self.entity_class.question_id == question_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)
            result = await session.execute(query.values(deleted=True))
            await session.flush()
            return result.rowcount

    @trace_span
    async def exists(
        self,
        question_id: int,
        template_variable_id: int,
        company_id: Optional[int] = None,
    ) -> bool:
        """Check if a specific association exists (excluding soft deleted)."""
        async with self._get_session() as session:
            query = select(self.entity_class.id).where(
                self.entity_class.question_id == question_id,
                self.entity_class.template_variable_id == template_variable_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query.limit(1))
            return result.scalar() is not None

    @trace_span
    async def soft_delete(self, association_id: int) -> bool:
        """Soft delete a specific association by ID."""
        async with self._get_session() as session:
            result = await session.execute(
                update(self.entity_class)
                .where(
                    self.entity_class.id == association_id,
                    self.entity_class.deleted == False,  # noqa
                )
                .values(deleted=True)
            )
            await session.flush()
            return result.rowcount > 0

    @trace_span
    async def delete(self, entity_id: int) -> bool:
        """Override base delete to use soft delete instead."""
        return await self.soft_delete(entity_id)

    @trace_span
    async def hard_delete(self, entity_id: int) -> bool:
        """Permanently delete an association (use with caution)."""
        async with self._get_session() as session:
            result = await session.execute(
                delete(self.entity_class).where(self.entity_class.id == entity_id)
            )
            await session.flush()
            return result.rowcount > 0

    @trace_span
    async def find_soft_deleted_association(
        self,
        question_id: int,
        template_variable_id: int,
        company_id: Optional[int] = None,
    ) -> QuestionTemplateVariableModel | None:
        """Find a soft deleted association that can be restored."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.question_id == question_id,
                self.entity_class.template_variable_id == template_variable_id,
                self.entity_class.deleted == True,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query.limit(1))
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def restore_soft_deleted_association(self, association_id: int) -> bool:
        """Restore a soft deleted association by ID."""
        async with self._get_session() as session:
            result = await session.execute(
                update(self.entity_class)
                .where(
                    self.entity_class.id == association_id,
                    self.entity_class.deleted == True,  # noqa
                )
                .values(deleted=False)
            )
            await session.flush()
            return result.rowcount > 0
