from typing import List, Optional
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.matrices.models.database.matrix import MatrixEntity
from packages.matrices.models.domain.matrix import (
    MatrixModel,
)
from common.core.otel_axiom_exporter import trace_span
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class MatrixRepository(BaseRepository[MatrixEntity, MatrixModel]):
    def __init__(self):
        super().__init__(MatrixEntity, MatrixModel)

    @trace_span
    async def get(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> MatrixModel:
        """Get matrices by workspace ID with pagination."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_with_relationships(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> Optional[MatrixModel]:
        # Note: This method now just returns the matrix without eager loading relationships
        # Callers should fetch related data separately if needed
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id is not None:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_valid_ids(
        self, matrix_ids: List[int], company_id: Optional[int] = None
    ) -> List[int]:
        """Get valid matrix IDs that exist and are not deleted."""
        async with self._get_session() as session:
            valid_matrices_query = select(MatrixEntity.id).where(
                MatrixEntity.id.in_(matrix_ids), MatrixEntity.deleted == False  # noqa
            )
            if company_id is not None:
                valid_matrices_query = valid_matrices_query.where(
                    MatrixEntity.company_id == company_id
                )
            result = await session.execute(valid_matrices_query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def get_by_workspace_id(
        self,
        workspace_id: int,
        skip: int = 0,
        limit: int = 100,
        company_id: Optional[int] = None,
    ) -> List[MatrixModel]:
        """Get matrices by workspace ID with pagination."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class)
                .where(
                    self.entity_class.workspace_id == workspace_id,
                    self.entity_class.deleted == False,  # noqa
                )
                .offset(skip)
                .limit(limit)
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
