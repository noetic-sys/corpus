"""
Common helper utilities for temporal activities.

Provides shared logic that all execution activities use.
NOT activities themselves - just helper functions to reduce duplication.
"""

from typing import Dict, Any, Callable
from temporalio import activity

from common.core.constants import WorkflowExecutionMode
from common.execution.executors.docker import DockerExecutor
from common.execution.executors.k8s import K8sExecutor


def get_executor():
    """
    Get appropriate executor based on execution mode.

    Returns:
        DockerExecutor or K8sExecutor based on settings
    """
    # Import settings here to avoid workflow sandbox issues
    from common.core.config import settings  # noqa: PLC0415

    execution_mode = WorkflowExecutionMode(settings.workflow_execution_mode)
    if execution_mode == WorkflowExecutionMode.DOCKER:
        return DockerExecutor()
    else:
        return K8sExecutor()


async def check_execution_status(execution_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check status of running container/job.

    Args:
        execution_info: Execution info from launch activity

    Returns:
        Status dict with "status" key ("running", "completed", "failed")
    """
    executor = get_executor()
    return executor.check_status(execution_info)


async def cleanup_execution_resources(
    execution_info: Dict[str, Any],
    company_id: int,
    cleanup_service_account_fn: Callable,
) -> None:
    """
    Common cleanup logic for execution activities.

    Cleans up container/job and service account.

    Args:
        execution_info: Execution info from launch
        company_id: Company ID
        cleanup_service_account_fn: Async function to cleanup service account
    """
    service_account_id = execution_info.get("service_account_id")
    activity.logger.info(
        f"Cleaning up resources, service_account_id={service_account_id}"
    )

    # Cleanup container/job
    try:
        executor = get_executor()
        executor.cleanup(execution_info)
        activity.logger.info("Cleaned up container/job")
    except Exception as e:
        activity.logger.error(f"Failed to cleanup container/job: {e}")

    # Cleanup service account
    if service_account_id:
        try:
            await cleanup_service_account_fn(service_account_id, company_id)
            activity.logger.info(f"Cleaned up service account {service_account_id}")
        except Exception as e:
            activity.logger.error(f"Failed to cleanup service account: {e}")
