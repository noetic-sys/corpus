from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.workspaces.models.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceResponse,
)
from packages.workspaces.models.domain.workspace import (
    WorkspaceCreateModel,
    WorkspaceUpdateModel,
)
from packages.workspaces.services.workspace_service import WorkspaceService
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.context import readonly

router = APIRouter()
logger = get_logger(__name__)


def get_workspace_service() -> WorkspaceService:
    return WorkspaceService()


@router.post("/", response_model=WorkspaceResponse)
@trace_span
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Create a new workspace."""
    create_model = WorkspaceCreateModel(
        name=workspace_data.name,
        company_id=current_user.company_id,
        description=workspace_data.description,
    )
    workspace = await workspace_service.create_workspace(create_model)
    return WorkspaceResponse.model_validate(workspace)


@router.get("/", response_model=List[WorkspaceResponse])
@readonly
@trace_span
async def get_workspaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Get all workspaces."""
    workspaces = await workspace_service.get_workspaces(
        company_id=current_user.company_id, skip=skip, limit=limit
    )
    return [WorkspaceResponse.model_validate(workspace) for workspace in workspaces]


@router.get("/{workspaceId}", response_model=WorkspaceResponse)
@readonly
@trace_span
async def get_workspace(
    workspace_id: int = Path(alias="workspaceId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Get a workspace by ID."""
    workspace = await workspace_service.get_workspace_or_404(
        workspace_id, current_user.company_id
    )
    return WorkspaceResponse.model_validate(workspace)


@router.put("/{workspaceId}", response_model=WorkspaceResponse)
@trace_span
async def update_workspace(
    workspace_id: Annotated[int, Path(alias="workspaceId")],
    workspace_data: WorkspaceUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Update a workspace."""
    update_model = WorkspaceUpdateModel(
        name=workspace_data.name,
        description=workspace_data.description,
    )
    workspace = await workspace_service.update_workspace(
        workspace_id=workspace_id,
        company_id=current_user.company_id,
        workspace_update=update_model,
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace)


@router.delete("/{workspaceId}")
@trace_span
async def delete_workspace(
    workspace_id: int = Path(alias="workspaceId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
):
    """Soft delete a workspace."""
    success = await workspace_service.delete_workspace(
        workspace_id, current_user.company_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"message": "Workspace deleted successfully"}
