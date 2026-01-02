"""
Temporal workflow for executing agent-based QA.

Orchestrates the lifecycle of agent QA execution:
1. Launch K8s job/Docker container with agent
2. Monitor execution
3. Extract answer from output file
4. Clean up resources
"""

from temporalio import workflow
from typing import Dict, Any

from common.execution.workflow_framework.orchestration_models import (
    PollingConfig,
    OrchestrationConfig,
)
from common.execution.workflow_framework.orchestration_helpers import (
    orchestrate_agent_job,
)

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
            # Configure orchestration
            config = OrchestrationConfig(
                launch_activity=LAUNCH_AGENT_QA_ACTIVITY,
                launch_args=[
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
                launch_timeout_minutes=2,
                polling=PollingConfig(
                    max_wait_minutes=15,
                    poll_interval_seconds=5,
                    check_status_activity=CHECK_AGENT_QA_STATUS_ACTIVITY,
                    status_timeout_seconds=30,
                ),
                extract_activity=EXTRACT_AGENT_QA_RESULTS_ACTIVITY,
                extract_args_builder=lambda execution_info: [
                    execution_info,
                    qa_job_id,
                    company_id,
                ],
                extract_timeout_minutes=1,
                cleanup_activity=CLEANUP_AGENT_QA_ACTIVITY,
                cleanup_args_builder=lambda execution_info: [
                    execution_info,
                    company_id,
                ],
                cleanup_timeout_minutes=1,
            )

            # Execute orchestration
            result = await orchestrate_agent_job(self, config)

            workflow.logger.info(
                f"Agent QA for job {qa_job_id} completed successfully: {result}"
            )

            return result

        except Exception as e:
            workflow.logger.error(f"Agent QA for job {qa_job_id} failed: {e}")
            raise
