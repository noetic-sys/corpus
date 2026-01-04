from typing import List, Optional
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.qa.models.database.qa_job import QAJobEntity
from packages.matrices.models.database.matrix import MatrixCellEntity
from packages.qa.models.domain.qa_job import QAJobModel, QAJobStatus
from packages.matrices.models.domain.matrix import MatrixCellModel, MatrixCellStatus
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QAJobRepository(BaseRepository[QAJobEntity, QAJobModel]):
    def __init__(self):
        super().__init__(QAJobEntity, QAJobModel)

    @trace_span
    async def get_by_matrix_cell_id(self, matrix_cell_id: int) -> List[QAJobModel]:
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class).where(
                    self.entity_class.matrix_cell_id == matrix_cell_id
                )
            )
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_pending_matrix_cells(
        self, matrix_id: Optional[int] = None
    ) -> List[MatrixCellModel]:
        async with self._get_session() as session:
            query = select(MatrixCellEntity).where(
                MatrixCellEntity.status == MatrixCellStatus.PENDING.value
            )

            # Filter by matrix_id if provided
            if matrix_id is not None:
                query = query.where(MatrixCellEntity.matrix_id == matrix_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return [MatrixCellModel.model_validate(entity) for entity in entities]

    @trace_span
    async def get_by_status(self, status: QAJobStatus) -> List[QAJobModel]:
        async with self._get_session() as session:
            result = await session.execute(
                select(self.entity_class).where(
                    self.entity_class.status == status.value
                )
            )
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
