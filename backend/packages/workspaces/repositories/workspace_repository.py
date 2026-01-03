from typing import List, Optional
from sqlalchemy.future import select
from packages.workspaces.models.database.workspace import WorkspaceEntity
from packages.workspaces.models.domain.workspace import Workspace
from common.repositories.base import BaseRepository
from common.core.otel_axiom_exporter import trace_span


class WorkspaceRepository(BaseRepository[WorkspaceEntity, Workspace]):
    def __init__(self):
        super().__init__(WorkspaceEntity, Workspace)

    def _add_company_filter(self, query, company_id: int):
        """Add company filtering to any query."""
        return query.where(self.entity_class.company_id == company_id)

    @trace_span
    async def get(
        self, entity_id: int, company_id: Optional[int] = None
    ) -> Optional[Workspace]:
        """Get workspace by ID with company filtering."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id == entity_id,
                self.entity_class.deleted == False,  # noqa
            )
            if company_id:
                query = self._add_company_filter(query, company_id)
            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_multi(
        self, company_id: int, skip: int = 0, limit: int = 100
    ) -> List[Workspace]:
        """Get multiple workspaces with company filtering."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.deleted == False,  # noqa
            )
            query = self._add_company_filter(query, company_id)
            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def delete(self, entity_id: int, company_id: int) -> bool:
        """Soft delete workspace with company access control."""
        # First verify the workspace belongs to the company
        workspace = await self.get(entity_id, company_id)
        if not workspace:
            return False

        # Use the base class soft_delete method
        return await super().soft_delete(entity_id)
