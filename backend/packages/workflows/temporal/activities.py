"""
Temporal activities for workflow execution.

Thin layer over executor and lifecycle modules that handles:
- Activity registration
- Logging
- Error handling
"""

import json
from typing import Dict, Any, List
from temporalio import activity
from datetime import datetime

from common.db.session import get_db
from common.core.config import settings
from common.core.constants import WorkflowExecutionMode
from packages.workflows.services.execution_service import WorkflowExecutionService
from packages.workflows.services.workflow_storage_service import WorkflowStorageService
from packages.workflows.services.execution_file_service import ExecutionFileService
from packages.workflows.models.domain.execution import WorkflowExecutionUpdateModel
from packages.workflows.models.domain.execution_result import ExecutionManifest
from packages.workflows.models.domain.execution_file import ExecutionFileCreateModel
from packages.workflows.models.database.execution_file import ExecutionFileType
from common.execution.executors.docker import DockerExecutor
from common.execution.executors.k8s import K8sExecutor
from common.execution.job_spec import JobSpec
from common.execution.workflow_framework.service_accounts import (
    create_execution_service_account,
    cleanup_execution_service_account,
)


def _get_executor():
    """Get appropriate executor based on execution mode."""
    if settings.workflow_execution_mode == WorkflowExecutionMode.DOCKER:
        return DockerExecutor()
    else:
        return K8sExecutor()


@activity.defn
async def launch_workflow_agent_activity(
    execution_id: int,
    workflow_id: int,
    workspace_id: int,
    created_by_user_id: int,
    created_by_company_id: int,
) -> Dict[str, Any]:
    """
    Launch workflow agent container/job (returns immediately).

    Returns container/job identifier for status polling.
    """
    activity.logger.info(
        f"Launching agent for execution {execution_id} in {settings.workflow_execution_mode.value} mode"
    )

    container_name = f"workflow-exec-{execution_id}"

    # Create service account
    service_account_id, api_key = await create_execution_service_account(
        execution_id, created_by_company_id
    )
    activity.logger.info(f"Created service account {service_account_id}")

    # Build job spec
    job_spec = JobSpec(
        container_name=container_name,
        template_name="workflow_job.yaml.j2",
        image_name="corpus/workflow-agent",
        image_tag=settings.workflow_agent_image_tag,
        env_vars={
            "EXECUTION_ID": str(execution_id),
            "WORKFLOW_ID": str(workflow_id),
            "WORKSPACE_ID": str(workspace_id),
            "API_ENDPOINT": settings.api_endpoint,
            "API_KEY": api_key,
        },
        template_vars={
            "execution_id": execution_id,
        },
    )

    # Launch using executor
    executor = _get_executor()
    execution_info = executor.launch(job_spec)

    # Add service account ID to execution info for cleanup
    execution_info["service_account_id"] = service_account_id

    activity.logger.info(f"Launched {execution_info['mode']} execution")

    return execution_info


@activity.defn
async def check_workflow_agent_status_activity(
    execution_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check status of running workflow agent.

    Returns: {"status": "running|completed|failed", "exit_code": int}
    """
    executor = _get_executor()
    return executor.check_status(execution_info)


@activity.defn
async def extract_workflow_results_activity(
    execution_info: Dict[str, Any], execution_id: int, workflow_id: int, company_id: int
) -> Dict[str, Any]:
    """Read manifest from S3 and create DB records (files already uploaded by agent)."""
    storage_service = WorkflowStorageService()

    # Read manifest from S3 (uploaded by agent after completion)
    manifest_key = storage_service._get_execution_manifest_path(
        company_id, workflow_id, execution_id
    )
    manifest_data = await storage_service.storage.download(manifest_key)

    if not manifest_data:
        raise Exception(f"Manifest not found in S3 at {manifest_key}")

    manifest_dict = json.loads(manifest_data)
    manifest = ExecutionManifest.model_validate(manifest_dict)

    # Create DB records for files (already in S3)
    async for db_session in get_db():
        file_service = ExecutionFileService(db_session)

        # Create DB records for output files
        for file_info in manifest.output_files:
            storage_path = storage_service._get_execution_output_path(
                company_id, workflow_id, execution_id, file_info.name
            )

            await file_service.create_file_record(
                ExecutionFileCreateModel(
                    execution_id=execution_id,
                    company_id=company_id,
                    file_type=ExecutionFileType.OUTPUT,
                    name=file_info.name,
                    storage_path=storage_path,
                    file_size=file_info.size,
                )
            )

    output_files = manifest.output_files
    all_files = [f.model_dump() for f in output_files]

    return {
        "generated_files": all_files,
        "total_size_bytes": sum(f.size for f in output_files),
        "metadata": manifest.metadata.model_dump(),
    }


@activity.defn
async def cleanup_workflow_agent_activity(
    execution_info: Dict[str, Any], created_by_company_id: int
) -> None:
    """Cleanup workflow agent resources."""
    service_account_id = execution_info.get("service_account_id")
    activity.logger.info(f"has service account id: {service_account_id}")

    # Cleanup container/job
    try:
        executor = _get_executor()
        executor.cleanup(execution_info)
    except Exception as e:
        activity.logger.error(f"Failed to cleanup container/job: {e}")

    # Cleanup service account
    if service_account_id:
        activity.logger.info("did have a service acccount!!!")
        try:
            await cleanup_execution_service_account(
                service_account_id, created_by_company_id
            )
        except Exception as e:
            activity.logger.error(f"Failed to cleanup service account: {e}")


@activity.defn
async def update_execution_status_activity(
    execution_id: int,
    status: str,
    generated_files: List[Dict[str, Any]] | None,
    total_size_bytes: int | None,
    metadata: Dict[str, Any] | None,
) -> None:
    """Update workflow execution status in database."""

    async for db_session in get_db():
        execution_service = WorkflowExecutionService(db_session)

        activity.logger.info(f"Updating execution {execution_id} to status {status}")

        # Get execution to find company_id
        execution = await execution_service.execution_repo.get(execution_id)
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")

        # Build update model
        update_data = WorkflowExecutionUpdateModel(
            status=status,
            completed_at=datetime.now() if status in ["completed", "failed"] else None,
            output_size_bytes=total_size_bytes,
            error_message=(
                metadata.get("error") if metadata and status == "failed" else None
            ),
            execution_log=metadata,
        )

        await execution_service.update_execution(
            execution_id, execution.company_id, update_data
        )

        activity.logger.info(f"Updated execution {execution_id} to {status}")
