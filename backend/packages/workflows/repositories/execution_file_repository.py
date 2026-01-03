"""
Repository for workflow execution files.
"""

from typing import List
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.workflows.models.database.execution_file import (
    WorkflowExecutionFile,
    ExecutionFileType,
)
from packages.workflows.models.domain.execution_file import ExecutionFileModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ExecutionFileRepository(
    BaseRepository[WorkflowExecutionFile, ExecutionFileModel]
):
    def __init__(self):
        super().__init__(WorkflowExecutionFile, ExecutionFileModel)

    @trace_span
    async def list_by_execution(
        self, execution_id: int, file_type: ExecutionFileType | None = None
    ) -> List[ExecutionFileModel]:
        """List files for an execution, optionally filtered by type."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.execution_id == execution_id
            )

            if file_type:
                query = query.where(self.entity_class.file_type == file_type.value)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
