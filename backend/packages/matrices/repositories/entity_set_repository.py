"""
Repository for matrix entity sets.

Manages the matrix_entity_sets table, which contains named collections
of entities (documents or questions) used in matrix dimensions.
"""

from typing import List, Optional
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.matrices.models.database.matrix_entity_set import MatrixEntitySetEntity
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetModel,
    MatrixEntitySetCreateModel,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class EntitySetRepository(BaseRepository[MatrixEntitySetEntity, MatrixEntitySetModel]):
    """Repository for managing matrix entity sets."""

    def __init__(self):
        super().__init__(MatrixEntitySetEntity, MatrixEntitySetModel)

    @trace_span
    async def get_by_matrix_id(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixEntitySetModel]:
        """Get all entity sets for a given matrix."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_matrix_and_type(
        self, matrix_id: int, entity_type: EntityType, company_id: Optional[int] = None
    ) -> Optional[MatrixEntitySetModel]:
        """Get entity set for a matrix by entity type (typically one of each type per matrix)."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.entity_type == entity_type.value,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def create_entity_set(
        self, create_model: MatrixEntitySetCreateModel
    ) -> MatrixEntitySetModel:
        """Create a new entity set."""
        return await self.create(create_model)

    @trace_span
    async def get_by_ids(
        self, entity_set_ids: List[int], company_id: Optional[int] = None
    ) -> List[MatrixEntitySetModel]:
        """Get multiple entity sets by their IDs."""
        if not entity_set_ids:
            return []

        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id.in_(entity_set_ids),
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
