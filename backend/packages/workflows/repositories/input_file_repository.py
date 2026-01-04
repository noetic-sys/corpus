"""
Repository for workflow input files.
"""

from typing import List
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.workflows.models.database.input_file import WorkflowInputFile
from packages.workflows.models.domain.input_file import InputFileModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class InputFileRepository(BaseRepository[WorkflowInputFile, InputFileModel]):
    def __init__(self):
        super().__init__(WorkflowInputFile, InputFileModel)

    @trace_span
    async def get(
        self, entity_id: int, company_id: int | None = None
    ) -> InputFileModel | None:
        """Get input file by ID with optional company filtering."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id == entity_id, self.entity_class.deleted == False
            )
            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def list_by_workflow(
        self, workflow_id: int, company_id: int | None = None
    ) -> List[InputFileModel]:
        """List input files for a workflow with optional company filtering."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.workflow_id == workflow_id,
                self.entity_class.deleted == False,
            )
            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def delete(self, entity_id: int, company_id: int | None = None) -> bool:
        """Soft delete input file with optional company access control."""
        async with self._get_session() as session:
            # Get the entity with company filtering
            file = await self.get(entity_id, company_id)
            if not file:
                return False

            # Soft delete by setting deleted flag
            query = select(self.entity_class).where(self.entity_class.id == entity_id)
            result = await session.execute(query)
            entity = result.scalar_one_or_none()

            if entity:
                entity.deleted = True
                await session.flush()
                return True

            return False
