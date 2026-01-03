from typing import List, Optional
from fastapi import HTTPException

from packages.workflows.repositories.workflow_repository import WorkflowRepository
from packages.workflows.models.domain.workflow import (
    WorkflowModel,
    WorkflowCreateModel,
    WorkflowUpdateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class WorkflowService:
    """Service for managing workflows."""

    def __init__(self):
        self.workflow_repo = WorkflowRepository()

    def _validate_workflow_create(self, workflow_data: WorkflowCreateModel):
        """Validate workflow creation data."""
        # Validate required fields
        if not workflow_data.workspace_id:
            raise HTTPException(
                status_code=400,
                detail="Workflow must have workspace_id",
            )

        if not workflow_data.name:
            raise HTTPException(
                status_code=400,
                detail="Workflow must have a name",
            )

    @trace_span
    async def create_workflow(
        self, workflow_data: WorkflowCreateModel
    ) -> WorkflowModel:
        """Create a new workflow."""
        logger.info(f"Creating workflow: {workflow_data.name}")

        # Validate workflow data
        self._validate_workflow_create(workflow_data)

        # Create workflow
        workflow = await self.workflow_repo.create(workflow_data)

        logger.info(f"Created workflow {workflow.id}: {workflow.name}")
        return workflow

    @trace_span
    async def get_workflow(
        self, workflow_id: int, company_id: int
    ) -> Optional[WorkflowModel]:
        """Get workflow by ID with company filtering."""
        return await self.workflow_repo.get(workflow_id, company_id)

    @trace_span
    async def update_workflow(
        self, workflow_id: int, workflow_data: WorkflowUpdateModel, company_id: int
    ) -> WorkflowModel:
        """Update a workflow."""
        logger.info(f"Updating workflow {workflow_id}")

        # Get existing workflow
        workflow = await self.get_workflow(workflow_id, company_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Update workflow
        updated_workflow = await self.workflow_repo.update(workflow_id, workflow_data)

        logger.info(f"Updated workflow {workflow_id}")
        return updated_workflow

    @trace_span
    async def delete_workflow(self, workflow_id: int, company_id: int) -> bool:
        """Delete a workflow (soft delete)."""
        logger.info(f"Deleting workflow {workflow_id}")

        # Get existing workflow
        workflow = await self.get_workflow(workflow_id, company_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        # Soft delete
        await self.workflow_repo.soft_delete(workflow_id)

        logger.info(f"Deleted workflow {workflow_id}")
        return True

    @trace_span
    async def list_workflows(
        self,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowModel]:
        """List workflows for a company (excludes soft deleted)."""
        return await self.workflow_repo.list_by_company(company_id, skip, limit)

    @trace_span
    async def list_workflows_by_workspace(
        self,
        workspace_id: int,
        company_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkflowModel]:
        """List workflows that use a specific workspace."""
        return await self.workflow_repo.list_by_workspace(
            workspace_id, company_id, skip, limit
        )


def get_workflow_service() -> WorkflowService:
    """Get workflow service instance."""
    return WorkflowService()
