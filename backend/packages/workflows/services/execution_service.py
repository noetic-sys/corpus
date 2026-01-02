from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from packages.workflows.models.domain.execution import (
    WorkflowExecutionModel,
    WorkflowExecutionCreateModel,
    WorkflowExecutionUpdateModel,
)
from packages.workflows.repositories.execution_repository import (
    WorkflowExecutionRepository,
)
from packages.workflows.repositories.workflow_repository import WorkflowRepository
from packages.workflows.temporal.workflow_execution_workflow import (
    WorkflowExecutionWorkflow,
)
from common.db.transaction_utils import transactional
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.core.config import settings

logger = get_logger(__name__)


class WorkflowExecutionService:
    """Service for managing workflow executions.

    This service handles:
    - Creating execution records
    - Triggering Temporal workflows
    - Querying execution history

    Actual execution happens in Temporal workflows/activities.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.execution_repo = WorkflowExecutionRepository(db_session)
        self.workflow_repo = WorkflowRepository(db_session)

    @trace_span
    @transactional
    async def trigger_execution(
        self,
        workflow_id: int,
        user_id: int,
        company_id: int,
        trigger_context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecutionModel:
        """Trigger a workflow execution.

        Creates an execution record and starts the Temporal workflow.
        Returns immediately with the execution record.
        """
        logger.info(f"Triggering execution for workflow {workflow_id}")

        # Get workflow with company filtering
        workflow = await self.workflow_repo.get(workflow_id, company_id=company_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Create execution record
        execution_create = WorkflowExecutionCreateModel(
            workflow_id=workflow.id,
            company_id=company_id,
            trigger_type=workflow.trigger_type.value,
            started_at=datetime.utcnow(),
            status="pending",
        )

        execution = await self.execution_repo.create(execution_create)
        logger.info(f"Created execution record {execution.id}")

        # Start Temporal workflow
        temporal_host = getattr(settings, "temporal_host", "localhost:7233")
        client = await Client.connect(temporal_host)

        await client.start_workflow(
            WorkflowExecutionWorkflow.run,
            args=[
                execution.id,
                workflow_id,
                workflow.workspace_id,
                user_id,
                company_id,
            ],
            id=f"workflow-execution-{execution.id}",
            task_queue="workflow-execution-queue",
        )

        logger.info(f"Started Temporal workflow for execution {execution.id}")
        return execution

    @trace_span
    async def get_execution(
        self, execution_id: int, company_id: int
    ) -> Optional[WorkflowExecutionModel]:
        """Get execution by ID with company filtering."""
        execution = await self.execution_repo.get(execution_id)
        if execution and execution.company_id != company_id:
            return None
        return execution

    @trace_span
    async def list_executions(
        self, workflow_id: int, company_id: int, skip: int = 0, limit: int = 100
    ) -> List[WorkflowExecutionModel]:
        """List executions for a workflow with company filtering."""
        executions = await self.execution_repo.list_by_workflow(
            workflow_id, skip, limit
        )
        # Filter by company_id for security
        return [e for e in executions if e.company_id == company_id]

    @trace_span
    async def get_last_execution(
        self, workflow_id: int, company_id: int
    ) -> Optional[WorkflowExecutionModel]:
        """Get the most recent execution for a workflow with company filtering."""
        execution = await self.execution_repo.get_last_execution(workflow_id)
        if execution and execution.company_id != company_id:
            return None
        return execution

    @trace_span
    async def get_last_successful_execution(
        self, workflow_id: int, company_id: int
    ) -> Optional[WorkflowExecutionModel]:
        """Get the most recent successful execution for a workflow with company filtering."""
        execution = await self.execution_repo.get_last_successful_execution(workflow_id)
        if execution and execution.company_id != company_id:
            return None
        return execution

    @trace_span
    async def update_execution(
        self,
        execution_id: int,
        company_id: int,
        update_data: WorkflowExecutionUpdateModel,
    ) -> Optional[WorkflowExecutionModel]:
        """Update an execution with company validation."""
        execution = await self.execution_repo.get(execution_id)
        if not execution or execution.company_id != company_id:
            return None
        return await self.execution_repo.update(execution_id, update_data)


def get_execution_service(db_session: AsyncSession) -> WorkflowExecutionService:
    """Get execution service instance."""
    return WorkflowExecutionService(db_session)
