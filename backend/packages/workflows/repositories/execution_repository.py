from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.workflows.models.database.workflow import WorkflowExecutionEntity
from packages.workflows.models.domain.execution import (
    WorkflowExecutionModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class WorkflowExecutionRepository(
    BaseRepository[WorkflowExecutionEntity, WorkflowExecutionModel]
):
    def __init__(self, db_session: AsyncSession):
        super().__init__(WorkflowExecutionEntity, WorkflowExecutionModel, db_session)

    @trace_span
    async def get(self, execution_id: int) -> Optional[WorkflowExecutionModel]:
        """Get execution by ID."""
        query = select(self.entity_class).where(
            self.entity_class.id == execution_id,
        )

        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def list_by_workflow(
        self,
        workflow_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowExecutionModel]:
        """List executions for a workflow."""
        query = (
            select(self.entity_class)
            .where(self.entity_class.workflow_id == workflow_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.entity_class.started_at.desc())
        )

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_last_execution(
        self, workflow_id: int
    ) -> Optional[WorkflowExecutionModel]:
        """Get the most recent execution for a workflow."""
        query = (
            select(self.entity_class)
            .where(self.entity_class.workflow_id == workflow_id)
            .order_by(self.entity_class.started_at.desc())
            .limit(1)
        )

        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_last_successful_execution(
        self, workflow_id: int
    ) -> Optional[WorkflowExecutionModel]:
        """Get the most recent successful execution for a workflow."""
        query = (
            select(self.entity_class)
            .where(
                self.entity_class.workflow_id == workflow_id,
                self.entity_class.status == "completed",
            )
            .order_by(self.entity_class.started_at.desc())
            .limit(1)
        )

        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None
