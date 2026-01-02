"""
Orchestration helpers for workflow execution patterns.

Provides reusable patterns for the launch→poll→extract→cleanup workflow orchestration.
"""

from typing import Any, Dict
from datetime import timedelta
from temporalio import workflow
from temporalio.exceptions import ApplicationError

from common.execution.workflow_framework.orchestration_models import (
    PollingConfig,
    OrchestrationConfig,
)


async def poll_until_complete(
    workflow_instance: Any,
    execution_info: Dict[str, Any],
    config: PollingConfig,
) -> Dict[str, Any]:
    """
    Poll job status until completion or timeout.

    Args:
        workflow_instance: The workflow instance (to access workflow.sleep and workflow.execute_activity)
        execution_info: Execution info from launch activity
        config: Polling configuration

    Returns:
        Final status result dict

    Raises:
        ApplicationError: If job fails or times out
    """
    elapsed_minutes = 0

    while elapsed_minutes < config.max_wait_minutes:
        # Sleep using Temporal timer
        await workflow.sleep(config.poll_interval_seconds)
        elapsed_minutes += config.poll_interval_seconds / 60

        # Check status
        status_result = await workflow.execute_activity(
            config.check_status_activity,
            args=[execution_info],
            start_to_close_timeout=timedelta(seconds=config.status_timeout_seconds),
        )

        workflow.logger.info(f"Status check: {status_result}")

        if status_result["status"] == "completed":
            return status_result
        elif status_result["status"] == "failed":
            raise ApplicationError(
                f"Job failed with exit code {status_result.get('exit_code')}",
                type="JobExecutionFailed",
            )

    # Timed out
    raise ApplicationError(
        f"Job timed out after {config.max_wait_minutes} minutes",
        type="JobExecutionTimeout",
    )


async def orchestrate_agent_job(
    workflow_instance: Any,
    config: OrchestrationConfig,
) -> Dict[str, Any]:
    """
    Orchestrate complete agent job lifecycle: launch→poll→extract→cleanup.

    Args:
        workflow_instance: The workflow instance
        config: Orchestration configuration

    Returns:
        Results from extract activity

    Raises:
        ApplicationError: If any step fails
    """
    # Step 1: Launch job
    execution_info = await workflow.execute_activity(
        config.launch_activity,
        args=config.launch_args,
        start_to_close_timeout=timedelta(minutes=config.launch_timeout_minutes),
    )

    workflow.logger.info(f"Launched job: {execution_info}")

    # Step 2: Poll until complete
    await poll_until_complete(workflow_instance, execution_info, config.polling)

    # Step 3: Extract results
    extract_args = (
        config.extract_args_builder(execution_info)
        if config.extract_args_builder
        else [execution_info]
    )

    result = await workflow.execute_activity(
        config.extract_activity,
        args=extract_args,
        start_to_close_timeout=timedelta(minutes=config.extract_timeout_minutes),
    )

    # Step 4: Cleanup
    cleanup_args = (
        config.cleanup_args_builder(execution_info)
        if config.cleanup_args_builder
        else [execution_info]
    )

    await workflow.execute_activity(
        config.cleanup_activity,
        args=cleanup_args,
        start_to_close_timeout=timedelta(minutes=config.cleanup_timeout_minutes),
    )

    return result
