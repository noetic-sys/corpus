from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.workspaces.repositories.workspace_repository import WorkspaceRepository
from packages.workspaces.models.domain.workspace import (
    Workspace,
    WorkspaceCreateModel,
    WorkspaceUpdateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class WorkspaceService:
    """Service for handling workspace operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.workspace_repo = WorkspaceRepository(db_session)

    @trace_span
    async def create_workspace(self, workspace_data: WorkspaceCreateModel) -> Workspace:
        """Create a new workspace."""
        logger.info(
            f"Creating workspace: {workspace_data.name} for company {workspace_data.company_id}"
        )

        workspace = await self.workspace_repo.create(workspace_data)
        logger.info(
            f"Created workspace with ID: {workspace.id} for company {workspace_data.company_id}"
        )
        return workspace

    @trace_span
    async def get_workspace(
        self, workspace_id: int, company_id: int
    ) -> Optional[Workspace]:
        """Get a workspace by ID with company access control."""
        workspace = await self.workspace_repo.get(workspace_id, company_id)
        if not workspace:
            logger.warning(
                f"Workspace not found: {workspace_id} in company {company_id}"
            )
        return workspace

    @trace_span
    async def get_workspaces(
        self, company_id: int, skip: int = 0, limit: int = 100
    ) -> List[Workspace]:
        """Get multiple workspaces with company filtering."""
        return await self.workspace_repo.get_multi(
            company_id=company_id, skip=skip, limit=limit
        )

    @trace_span
    async def update_workspace(
        self,
        workspace_id: int,
        company_id: int,
        workspace_update: WorkspaceUpdateModel,
    ) -> Optional[Workspace]:
        """Update a workspace with company access control."""
        # First verify workspace exists and belongs to company
        workspace = await self.get_workspace(workspace_id, company_id)
        if not workspace:
            return None

        logger.info(f"Updating workspace {workspace_id} in company {company_id}")
        return await self.workspace_repo.update(workspace_id, workspace_update)

    @trace_span
    async def delete_workspace(self, workspace_id: int, company_id: int) -> bool:
        """Soft delete a workspace with company access control."""
        logger.info(f"Soft deleting workspace: {workspace_id} in company {company_id}")
        return await self.workspace_repo.delete(workspace_id, company_id)

    @trace_span
    async def get_workspace_or_404(
        self, workspace_id: int, company_id: int
    ) -> Workspace:
        """Get a workspace by ID or raise 404 with company access control."""
        workspace = await self.get_workspace(workspace_id, company_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace
