from typing import List, Optional
from sqlalchemy.future import select

from common.repositories.base import BaseRepository
from packages.workflows.models.database.workflow import WorkflowEntity
from packages.workflows.models.domain.workflow import WorkflowModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class WorkflowRepository(BaseRepository[WorkflowEntity, WorkflowModel]):
    def __init__(self):
        super().__init__(WorkflowEntity, WorkflowModel)

    @trace_span
    async def get(
        self, workflow_id: int, company_id: Optional[int] = None
    ) -> Optional[WorkflowModel]:
        """Get workflow by ID."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id == workflow_id,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def list_by_company(
        self,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowModel]:
        """List workflows for a company."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.company_id == company_id,
                self.entity_class.deleted == False,  # noqa
            )

            query = (
                query.offset(skip)
                .limit(limit)
                .order_by(self.entity_class.created_at.desc())
            )

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def list_by_workspace(
        self,
        workspace_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowModel]:
        """List workflows that use a specific workspace."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class)
                .where(
                    self.entity_class.workspace_id == workspace_id,
                    self.entity_class.company_id == company_id,
                    self.entity_class.deleted == False,  # noqa
                )
                .offset(skip)
                .limit(limit)
                .order_by(self.entity_class.created_at.desc())
            )

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def list_by_trigger_type(
        self,
        trigger_type: str,
        company_id: int,
    ) -> List[WorkflowModel]:
        """List workflows by trigger type."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.trigger_type == trigger_type,
                self.entity_class.company_id == company_id,
                self.entity_class.deleted == False,  # noqa
            )

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)
