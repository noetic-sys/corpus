"""
Temporal workflow for executing agent-based QA.

Orchestrates the lifecycle of agent QA execution:
1. Launch K8s job/Docker container with agent
2. Monitor execution
3. Extract answer from output file
4. Clean up resources
"""

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from datetime import timedelta
from typing import Dict, Any

# Use string-based activity names to avoid sandbox import restrictions
LAUNCH_AGENT_QA_ACTIVITY = "launch_agent_qa_activity"
CHECK_AGENT_QA_STATUS_ACTIVITY = "check_agent_qa_status_activity"
EXTRACT_AGENT_QA_RESULTS_ACTIVITY = "extract_agent_qa_results_activity"
CLEANUP_AGENT_QA_ACTIVITY = "cleanup_agent_qa_activity"


@workflow.defn
class AgentQAWorkflow:
    @workflow.run
    async def run(
        self,
        qa_job_id: int,
        matrix_cell_id: int,
        document_ids: list[int],
        question: str,
        matrix_type: str,
        question_type_id: int,
        question_id: int,
        company_id: int,
        min_answers: int = 1,
        max_answers: int = 1,
    ) -> Dict[str, Any]:
        """
        Execute agent-based QA in a sandboxed K8s pod.

        Args:
            qa_job_id: ID of the QA job
            matrix_cell_id: Matrix cell being processed
            document_ids: List of document IDs to query
            question: Question text
            matrix_type: Matrix type (STANDARD, CROSS_CORRELATION, etc.)
            question_type_id: Question type ID
            question_id: Question ID (for loading options)
            company_id: Company ID for scoping
            min_answers: Minimum number of answers
            max_answers: Maximum number of answers

        Returns:
            Dictionary with answer set data
        """
        workflow.logger.info(
            f"Starting agent QA for job {qa_job_id}, cell {matrix_cell_id}"
        )

        try:
            # Step 1: Launch agent QA job (returns immediately)
            execution_info = await workflow.execute_activity(
                LAUNCH_AGENT_QA_ACTIVITY,
                args=[
                    qa_job_id,
                    matrix_cell_id,
                    document_ids,
                    question,
                    matrix_type,
                    question_type_id,
                    question_id,
                    company_id,
                    min_answers,
                    max_answers,
                ],
                start_to_close_timeout=timedelta(minutes=2),
            )

            workflow.logger.info(f"Launched agent QA: {execution_info}")

            # Step 2: Poll for completion using Temporal timers
            max_wait_minutes = 15  # Agent QA should be faster than full workflows
            poll_interval_seconds = 5
            elapsed_minutes = 0

            while elapsed_minutes < max_wait_minutes:
                # Sleep using Temporal timer
                await workflow.sleep(poll_interval_seconds)
                elapsed_minutes += poll_interval_seconds / 60

                # Check status
                status_result = await workflow.execute_activity(
                    CHECK_AGENT_QA_STATUS_ACTIVITY,
                    args=[execution_info],
                    start_to_close_timeout=timedelta(seconds=30),
                )

                workflow.logger.info(f"Status check: {status_result}")

                if status_result["status"] == "completed":
                    break
                elif status_result["status"] == "failed":
                    raise ApplicationError(
                        f"Agent QA failed with exit code {status_result.get('exit_code')}",
                        type="AgentQAExecutionFailed",
                    )

            if status_result["status"] == "running":
                raise ApplicationError(
                    f"Agent QA timed out after {max_wait_minutes} minutes",
                    type="AgentQAExecutionTimeout",
                )

            # Step 3: Extract answer results
            result = await workflow.execute_activity(
                EXTRACT_AGENT_QA_RESULTS_ACTIVITY,
                args=[execution_info, qa_job_id, company_id],
                start_to_close_timeout=timedelta(minutes=1),
            )

            # Step 4: Cleanup
            await workflow.execute_activity(
                CLEANUP_AGENT_QA_ACTIVITY,
                args=[execution_info, company_id],
                start_to_close_timeout=timedelta(minutes=1),
            )

            workflow.logger.info(f"Agent QA for job {qa_job_id} completed successfully")

            return result

        except Exception as e:
            workflow.logger.error(f"Agent QA for job {qa_job_id} failed: {e}")

            # Raise ApplicationError to properly fail the workflow
            raise ApplicationError(
                f"Agent QA execution failed: {str(e)}", type="AgentQAExecutionFailed"
            )
