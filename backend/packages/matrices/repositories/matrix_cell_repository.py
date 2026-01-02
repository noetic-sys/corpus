from typing import Optional, List

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from common.core.otel_axiom_exporter import trace_span, get_logger
from common.repositories.base import BaseRepository
from sqlalchemy import exists
from packages.matrices.models.database import (
    MatrixCellEntity,
)
from packages.matrices.models.domain.matrix import (
    MatrixCellModel,
    MatrixCellCreateModel,
    MatrixCellUpdateModel,
    MatrixCellStatus,
    MatrixCellStatsModel,
)

logger = get_logger(__name__)


class MatrixCellRepository(BaseRepository[MatrixCellEntity, MatrixCellModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(MatrixCellEntity, MatrixCellModel, db_session)

    async def bulk_create_from_models(
        self, create_models: List[MatrixCellCreateModel]
    ) -> List[MatrixCellModel]:
        """Bulk create from domain create models, excluding entity_refs which are stored separately."""
        if not create_models:
            return []

        # Convert create models to entities, excluding entity_refs
        entities = []
        for create_model in create_models:
            # Exclude entity_refs as they're stored in a separate table
            model_data = create_model.model_dump(
                exclude_none=True, exclude={"entity_refs"}, mode="json"
            )
            entity = self.entity_class(**model_data)
            entities.append(entity)

        return await self.bulk_create(entities)

    @trace_span
    async def get_by_matrix_id(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixCellModel]:
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
    async def get_by_status(self, status: MatrixCellStatus) -> List[MatrixCellModel]:
        result = await self.db_session.execute(
            select(self.entity_class).where(
                self.entity_class.status == status.value,
                self.entity_class.deleted == False,  # noqa
            )
        )
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_cells_by_matrix_id(self, matrix_id: int) -> List[MatrixCellModel]:
        """Get all matrix cells for a given matrix."""
        result = await self.db_session.execute(
            select(self.entity_class).where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )
        )
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def update_current_answer_set(
        self, matrix_cell_id: int, answer_set_id: int
    ) -> Optional[MatrixCellModel]:
        """Update the current_answer_set_id for a matrix cell."""
        update_model = MatrixCellUpdateModel(current_answer_set_id=answer_set_id)
        return await self.update(matrix_cell_id, update_model)

    @trace_span
    async def get_cells_by_ids(self, cell_ids: List[int]) -> List[MatrixCellModel]:
        """Get matrix cells by a list of cell IDs."""
        if not cell_ids:
            return []

        result = await self.db_session.execute(
            select(self.entity_class).where(
                self.entity_class.id.in_(cell_ids),
                self.entity_class.deleted == False,  # noqa
            )
        )
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def matrix_has_cells(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> bool:
        """Fast check if a matrix has any cells.

        Used for fast-path deduplication: empty matrices don't need deduplication.
        Returns True if matrix has at least one non-deleted cell.
        """

        query = select(
            exists().where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )
        )

        if company_id is not None:
            query = query.where(self.entity_class.company_id == company_id)

        result = await self.db_session.execute(query)
        return result.scalar()

    @trace_span
    async def bulk_update_cells_to_pending(self, cell_ids: List[int]) -> int:
        """Bulk update matrix cells to pending status and clear current_answer_set_id."""
        if not cell_ids:
            return 0

        result = await self.db_session.execute(
            update(self.entity_class)
            .where(self.entity_class.id.in_(cell_ids))
            .values(status=MatrixCellStatus.PENDING.value, current_answer_set_id=None)
        )
        await self.db_session.flush()
        return result.rowcount

    @trace_span
    async def bulk_soft_delete_by_cell_ids(self, cell_ids: List[int]) -> int:
        """Bulk soft delete matrix cells by cell IDs."""
        if not cell_ids:
            return 0

        result = await self.db_session.execute(
            update(self.entity_class)
            .where(
                self.entity_class.id.in_(cell_ids),
                self.entity_class.deleted == False,  # noqa
            )
            .values(deleted=True)
        )
        await self.db_session.flush()
        return result.rowcount

    @trace_span
    async def bulk_soft_delete_by_matrix_ids(self, matrix_ids: List[int]) -> int:
        """Bulk soft delete matrix cells by matrix IDs."""
        if not matrix_ids:
            return 0

        result = await self.db_session.execute(
            update(self.entity_class)
            .where(
                self.entity_class.matrix_id.in_(matrix_ids),
                self.entity_class.deleted == False,  # noqa
            )
            .values(deleted=True)
        )
        await self.db_session.flush()
        return result.rowcount

    @trace_span
    async def get_cell_stats_by_matrix(self, matrix_id: int) -> MatrixCellStatsModel:
        """Get cell statistics by status for a matrix."""
        result = await self.db_session.execute(
            select(
                self.entity_class.status,
                func.count(self.entity_class.id).label("count"),
            )
            .where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )
            .group_by(self.entity_class.status)
        )

        # Build counts for each status
        counts = {
            MatrixCellStatus.COMPLETED.value: 0,
            MatrixCellStatus.PROCESSING.value: 0,
            MatrixCellStatus.PENDING.value: 0,
            MatrixCellStatus.FAILED.value: 0,
        }

        for row in result:
            status_value, count = row
            counts[status_value] = count

        total = sum(counts.values())

        return MatrixCellStatsModel(
            total_cells=total,
            completed=counts[MatrixCellStatus.COMPLETED.value],
            processing=counts[MatrixCellStatus.PROCESSING.value],
            pending=counts[MatrixCellStatus.PENDING.value],
            failed=counts[MatrixCellStatus.FAILED.value],
        )
