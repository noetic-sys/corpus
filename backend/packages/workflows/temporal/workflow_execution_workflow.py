"""
Temporal workflow for executing workflow agents.

Orchestrates the lifecycle of a workflow execution:
1. Create service account
2. Launch K8s job with agent
3. Monitor execution
4. Extract generated files
5. Clean up resources
"""

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from datetime import timedelta
from typing import Dict, Any

# Use string-based activity names to avoid sandbox import restrictions
LAUNCH_WORKFLOW_AGENT_ACTIVITY = "launch_workflow_agent_activity"
CHECK_WORKFLOW_AGENT_STATUS_ACTIVITY = "check_workflow_agent_status_activity"
EXTRACT_WORKFLOW_RESULTS_ACTIVITY = "extract_workflow_results_activity"
CLEANUP_WORKFLOW_AGENT_ACTIVITY = "cleanup_workflow_agent_activity"
UPDATE_EXECUTION_STATUS_ACTIVITY = "update_execution_status_activity"


@workflow.defn
class WorkflowExecutionWorkflow:
    @workflow.run
    async def run(
        self,
        execution_id: int,
        workflow_id: int,
        workspace_id: int,
        created_by_user_id: int,
        created_by_company_id: int,
    ) -> Dict[str, Any]:
        """
        Execute a workflow using Claude Agent in a sandboxed K8s pod.

        Args:
            execution_id: ID of the workflow execution record
            workflow_id: ID of the workflow to execute
            workspace_id: ID of the workspace to scope execution to
            created_by_user_id: User who initiated the execution
            created_by_company_id: Company ID for scoping

        Returns:
            Dictionary with execution results and generated files
        """
        workflow.logger.info(f"Starting workflow execution {execution_id}")

        try:
            # Step 1: Update status to running
            await workflow.execute_activity(
                UPDATE_EXECUTION_STATUS_ACTIVITY,
                args=[execution_id, "running", None, None, None],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 2: Launch workflow agent (returns immediately)
            execution_info = await workflow.execute_activity(
                LAUNCH_WORKFLOW_AGENT_ACTIVITY,
                args=[
                    execution_id,
                    workflow_id,
                    workspace_id,
                    created_by_user_id,
                    created_by_company_id,
                ],
                start_to_close_timeout=timedelta(minutes=2),
            )

            workflow.logger.info(f"Launched agent: {execution_info}")

            # Step 3: Poll for completion using Temporal timers (doesn't block worker)
            max_wait_minutes = 30
            poll_interval_seconds = 10
            elapsed_minutes = 0

            while elapsed_minutes < max_wait_minutes:
                # Sleep using Temporal timer (allows workflow to be paused/resumed)
                await workflow.sleep(poll_interval_seconds)
                elapsed_minutes += poll_interval_seconds / 60

                # Check status
                status_result = await workflow.execute_activity(
                    CHECK_WORKFLOW_AGENT_STATUS_ACTIVITY,
                    args=[execution_info],
                    start_to_close_timeout=timedelta(seconds=30),
                )

                workflow.logger.info(f"Status check: {status_result}")

                if status_result["status"] == "completed":
                    break
                elif status_result["status"] == "failed":
                    raise ApplicationError(
                        f"Agent failed with exit code {status_result.get('exit_code')}",
                        type="AgentExecutionFailed",
                    )

            if status_result["status"] == "running":
                raise ApplicationError(
                    f"Agent timed out after {max_wait_minutes} minutes",
                    type="AgentExecutionTimeout",
                )

            # Step 4: Extract results
            result = await workflow.execute_activity(
                EXTRACT_WORKFLOW_RESULTS_ACTIVITY,
                args=[execution_info, execution_id, workflow_id, created_by_company_id],
                start_to_close_timeout=timedelta(minutes=2),
            )

            # Step 5: Cleanup
            await workflow.execute_activity(
                CLEANUP_WORKFLOW_AGENT_ACTIVITY,
                args=[execution_info, created_by_company_id],
                start_to_close_timeout=timedelta(minutes=2),
            )

            # Step 6: Update status to completed
            await workflow.execute_activity(
                UPDATE_EXECUTION_STATUS_ACTIVITY,
                args=[
                    execution_id,
                    "completed",
                    result.get("generated_files"),
                    result.get("total_size_bytes"),
                    {},
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )

            workflow.logger.info(
                f"Workflow execution {execution_id} completed with {len(result.get('generated_files', []))} files"
            )

            return result

        except Exception as e:
            workflow.logger.error(f"Workflow execution {execution_id} failed: {e}")

            # Update status to failed
            try:
                await workflow.execute_activity(
                    UPDATE_EXECUTION_STATUS_ACTIVITY,
                    args=[execution_id, "failed", None, None, {"error": str(e)}],
                    start_to_close_timeout=timedelta(seconds=30),
                )
            except Exception as update_error:
                workflow.logger.error(f"Failed to update status: {update_error}")

            # Raise ApplicationError to properly fail the workflow
            raise ApplicationError(
                f"Workflow execution failed: {str(e)}", type="WorkflowExecutionFailed"
            )
