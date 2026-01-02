from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.matrices.models.database.matrix_template_variable import (
    MatrixTemplateVariableEntity,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableModel,
)
from common.core.otel_axiom_exporter import trace_span


class MatrixTemplateVariableRepository(
    BaseRepository[MatrixTemplateVariableEntity, MatrixTemplateVariableModel]
):
    def __init__(self, db_session: AsyncSession):
        super().__init__(
            MatrixTemplateVariableEntity, MatrixTemplateVariableModel, db_session
        )

    @trace_span
    async def get_by_matrix_id(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixTemplateVariableModel]:
        """Get all template variables for a matrix."""
        query = select(self.entity_class).where(
            self.entity_class.matrix_id == matrix_id,
            self.entity_class.deleted == False,  # noqa
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_by_template_string(
        self, matrix_id: int, template_string: str, company_id: Optional[int] = None
    ) -> Optional[MatrixTemplateVariableModel]:
        """Get a specific template variable by matrix ID and template string."""
        query = select(self.entity_class).where(
            self.entity_class.matrix_id == matrix_id,
            self.entity_class.template_string == template_string,
            self.entity_class.deleted == False,  # noqa
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_template_mappings(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Get template string to value mappings for a matrix."""
        variables = await self.get_by_matrix_id(matrix_id, company_id)
        return {var.template_string: var.value for var in variables}
