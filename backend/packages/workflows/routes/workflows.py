from typing import Annotated, List
from packages.workflows.models.database.execution_file import ExecutionFileType
from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    HTTPException,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.session import get_db
from common.db.transaction_utils import transaction
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.workflows.services.execution_service import WorkflowExecutionService
from packages.workflows.services.workflow_service import WorkflowService
from packages.workflows.services.execution_file_service import ExecutionFileService
from packages.workflows.services.input_file_service import InputFileService
from packages.workflows.models.schemas.execution import (
    ExecutionTriggerRequest,
    ExecutionStartedResponse,
    ExecutionResponse,
    ExecutionFileResponse,
)
from packages.workflows.models.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
)
from packages.workflows.models.schemas.input_file import InputFileResponse
from packages.workflows.models.domain.workflow import (
    WorkflowCreateModel,
    WorkflowUpdateModel,
)
from fastapi.responses import StreamingResponse
from packages.billing.services.quota_service import QuotaService
from packages.billing.services.usage_service import UsageService

router = APIRouter()
logger = get_logger(__name__)


def get_execution_service(
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecutionService:
    return WorkflowExecutionService(db)


def get_workflow_service() -> WorkflowService:
    return WorkflowService()


def get_execution_file_service(
    db: AsyncSession = Depends(get_db),
) -> ExecutionFileService:
    return ExecutionFileService(db)


def get_input_file_service(db: AsyncSession = Depends(get_db)) -> InputFileService:
    return InputFileService(db)


@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
@trace_span
async def create_workflow(
    request: WorkflowCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Create a new workflow."""
    workflow_data = WorkflowCreateModel(
        company_id=current_user.company_id, **request.model_dump()
    )

    workflow = await workflow_service.create_workflow(workflow_data)
    return WorkflowResponse.model_validate(workflow)


@router.get(
    "/workspaces/{workspaceId}/workflows", response_model=List[WorkflowResponse]
)
@trace_span
async def list_workflows(
    workspace_id: Annotated[int, Path(alias="workspaceId")],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """List all workflows for a workspace."""
    workflows = await workflow_service.list_workflows_by_workspace(
        workspace_id=workspace_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
    )
    return [WorkflowResponse.model_validate(w) for w in workflows]


@router.get("/workflows/{workflowId}", response_model=WorkflowResponse)
@trace_span
async def get_workflow(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Get a workflow by ID."""
    workflow = await workflow_service.get_workflow(workflow_id, current_user.company_id)

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowResponse.model_validate(workflow)


@router.patch("/workflows/{workflowId}", response_model=WorkflowResponse)
@trace_span
async def update_workflow(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    request: WorkflowUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Update a workflow."""
    workflow_data = WorkflowUpdateModel(**request.model_dump(exclude_unset=True))

    workflow = await workflow_service.update_workflow(
        workflow_id, workflow_data, current_user.company_id
    )

    return WorkflowResponse.model_validate(workflow)


@router.delete("/workflows/{workflowId}", status_code=204)
@trace_span
async def delete_workflow(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a workflow (soft delete)."""
    await workflow_service.delete_workflow(workflow_id, current_user.company_id)


@router.post("/workflows/{workflowId}/execute", response_model=ExecutionStartedResponse)
@trace_span
async def execute_workflow(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    request: ExecutionTriggerRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    execution_service: WorkflowExecutionService = Depends(get_execution_service),
):
    """
    Execute a workflow.

    Creates an execution record and starts a Temporal workflow that will:
    1. Create a service account
    2. Launch a gVisor-sandboxed K8s pod with Claude Agent
    3. Monitor execution
    4. Extract generated files
    5. Clean up resources
    """
    try:
        async with transaction(execution_service.db_session):
            # Check workflow quota before execution (raises 429 if exceeded)
            quota_service = QuotaService(execution_service.db_session)
            await quota_service.check_workflow_quota(current_user.company_id)

            execution = await execution_service.trigger_execution(
                workflow_id=workflow_id,
                user_id=current_user.user_id,
                company_id=current_user.company_id,
                trigger_context=request.trigger_context,
            )

            # Track workflow usage
            usage_service = UsageService()
            await usage_service.track_workflow(
                company_id=current_user.company_id,
                user_id=current_user.user_id,
                workflow_id=workflow_id,
            )

        return ExecutionStartedResponse(
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            status=execution.status,
            started_at=execution.started_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to start workflow execution"
        )


@router.get(
    "/workflows/{workflowId}/executions", response_model=List[ExecutionResponse]
)
@trace_span
async def list_executions(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    execution_service: WorkflowExecutionService = Depends(get_execution_service),
):
    """List all executions for a workflow."""
    executions = await execution_service.list_executions(
        workflow_id=workflow_id,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
    )
    return [ExecutionResponse.model_validate(e) for e in executions]


@router.get(
    "/workflows/{workflowId}/executions/{executionId}", response_model=ExecutionResponse
)
@trace_span
async def get_execution(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    execution_service: WorkflowExecutionService = Depends(get_execution_service),
):
    """Get workflow execution status and results."""
    execution = await execution_service.get_execution(
        execution_id, current_user.company_id
    )

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse.model_validate(execution)


@router.get(
    "/workflows/{workflowId}/executions/{executionId}/files",
    response_model=List[ExecutionFileResponse],
)
@trace_span
async def list_execution_files(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    file_type: Annotated[str | None, Query()] = None,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    file_service: ExecutionFileService = Depends(get_execution_file_service),
):
    """List files generated by an execution."""

    file_type_enum = None
    if file_type:
        try:
            file_type_enum = ExecutionFileType(file_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid file_type: {file_type}"
            )

    files = await file_service.list_execution_files(
        execution_id, current_user.company_id, file_type_enum
    )
    return [ExecutionFileResponse.model_validate(f) for f in files]


@router.get("/workflows/{workflowId}/executions/{executionId}/files/{fileId}/download")
@trace_span
async def download_execution_file(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    execution_id: Annotated[int, Path(alias="executionId")],
    file_id: Annotated[int, Path(alias="fileId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    file_service: ExecutionFileService = Depends(get_execution_file_service),
):
    """Download an execution file."""

    try:
        file_data, file = await file_service.download_file(
            file_id, execution_id, current_user.company_id
        )

        return StreamingResponse(
            iter([file_data]),
            media_type=file.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file.name}"',
                "Content-Length": str(file.file_size),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to download file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.post(
    "/workflows/{workflowId}/input-files",
    response_model=InputFileResponse,
    status_code=201,
)
@trace_span
async def upload_input_file(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    file: UploadFile = File(...),
    description: str | None = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    input_file_service: InputFileService = Depends(get_input_file_service),
):
    """Upload an input file (template, data file) for a workflow."""
    try:
        input_file = await input_file_service.upload_file(
            workflow_id=workflow_id,
            company_id=current_user.company_id,
            filename=file.filename,
            file_data=file.file,
            file_size=file.size,
            description=description,
            content_type=file.content_type,
        )

        return InputFileResponse.model_validate(input_file)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to upload input file for workflow {workflow_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to upload input file")


@router.get(
    "/workflows/{workflowId}/input-files", response_model=List[InputFileResponse]
)
@trace_span
async def list_input_files(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    input_file_service: InputFileService = Depends(get_input_file_service),
):
    """List all input files for a workflow."""
    try:
        files = await input_file_service.list_files(
            workflow_id=workflow_id,
            company_id=current_user.company_id,
        )
        return [InputFileResponse.model_validate(f) for f in files]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list input files for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list input files")


@router.get("/workflows/{workflowId}/input-files/{fileId}/download")
@trace_span
async def download_input_file(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    file_id: Annotated[int, Path(alias="fileId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    input_file_service: InputFileService = Depends(get_input_file_service),
):
    """Download an input file."""

    try:
        file_data, file = await input_file_service.download_file(
            file_id=file_id,
            company_id=current_user.company_id,
        )

        return StreamingResponse(
            iter([file_data]),
            media_type=file.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{file.name}"',
                "Content-Length": str(file.file_size),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to download input file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download input file")


@router.delete("/workflows/{workflowId}/input-files/{fileId}", status_code=204)
@trace_span
async def delete_input_file(
    workflow_id: Annotated[int, Path(alias="workflowId")],
    file_id: Annotated[int, Path(alias="fileId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    input_file_service: InputFileService = Depends(get_input_file_service),
):
    """Delete an input file."""
    try:
        async with transaction(input_file_service.db_session):
            await input_file_service.delete_file(
                file_id=file_id,
                company_id=current_user.company_id,
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete input file {file_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete input file")
