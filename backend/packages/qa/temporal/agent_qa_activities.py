"""
Temporal activities for agent-based QA execution.

Activities for managing agent QA lifecycle:
- Launch K8s job/Docker container with agent
- Monitor execution status
- Extract results (agent POSTs directly to API)
- Cleanup resources
"""

import json
from typing import Dict, Any
from temporalio import activity

from common.core.config import settings
from common.core.constants import WorkflowExecutionMode
from common.db.scoped import transaction
from common.execution.executors.docker import DockerExecutor
from common.execution.executors.k8s import K8sExecutor
from common.execution.job_spec import JobSpec
from common.execution.workflow_framework.service_accounts import (
    create_execution_service_account,
    cleanup_execution_service_account,
)
from packages.questions.services.question_option_service import QuestionOptionService
from packages.qa.services.qa_job_service import get_qa_job_service
from packages.matrices.services.matrix_service import get_matrix_service
from questions.question_type import QuestionTypeName


def _get_executor():
    """Get appropriate executor based on execution mode."""
    execution_mode = WorkflowExecutionMode(settings.workflow_execution_mode)
    if execution_mode == WorkflowExecutionMode.DOCKER:
        return DockerExecutor()
    else:
        return K8sExecutor()


@activity.defn
async def launch_agent_qa_activity(
    qa_job_id: int,
    matrix_cell_id: int,
    document_ids: list[int],
    question: str,
    matrix_type: str,
    question_type_id: int,
    question_id: int,
    company_id: int,
    min_answers: int,
    max_answers: int,
) -> Dict[str, Any]:
    """
    Launch agent QA job (returns immediately).

    Creates service account, launches container/job with agent QA parameters.

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
        Dictionary with execution info for status polling
    """
    execution_mode = WorkflowExecutionMode(settings.workflow_execution_mode)
    activity.logger.info(
        f"Launching agent QA for job {qa_job_id} in {execution_mode.value} mode"
    )

    container_name = f"agent-qa-{qa_job_id}"

    # Create service account for API access
    service_account_id, api_key = await create_execution_service_account(
        qa_job_id, company_id
    )
    activity.logger.info(f"Created service account {service_account_id}")

    # Load options for SELECT questions
    options = []
    question_type = QuestionTypeName.from_id(question_type_id)
    if question_type == QuestionTypeName.SELECT:
        activity.logger.info(f"Loading options for SELECT question {question_id}")
        async with transaction():
            option_service = QuestionOptionService()
            option_models = await option_service.get_options_for_question(question_id)
            options = [opt.value for opt in option_models]
            activity.logger.info(f"Loaded {len(options)} options")

    # Build job spec for agent QA
    job_spec = JobSpec(
        container_name=container_name,
        template_name="agent_qa_job.yaml.j2",
        image_name="corpus/agent-qa",
        image_tag=(
            settings.agent_qa_image_tag
            if hasattr(settings, "agent_qa_image_tag")
            else "latest"
        ),
        env_vars={
            "QA_JOB_ID": str(qa_job_id),
            "MATRIX_CELL_ID": str(matrix_cell_id),
            "DOCUMENT_IDS": json.dumps(document_ids),
            "QUESTION": question,
            "MATRIX_TYPE": matrix_type,
            "QUESTION_TYPE_ID": str(question_type_id),
            "QUESTION_ID": str(question_id),
            "COMPANY_ID": str(company_id),
            "MIN_ANSWERS": str(min_answers),
            "MAX_ANSWERS": str(max_answers),
            "QUESTION_OPTIONS": json.dumps(options),  # Serialized options list
            "API_ENDPOINT": settings.api_endpoint,
            "API_KEY": api_key,
        },
        template_vars={
            "qa_job_id": qa_job_id,
        },
    )

    # Launch using executor
    executor = _get_executor()
    execution_info = executor.launch(job_spec)

    # Add service account ID to execution info for cleanup
    execution_info["service_account_id"] = service_account_id

    activity.logger.info(f"Launched {execution_info['mode']} agent QA job {qa_job_id}")

    return execution_info


@activity.defn
async def check_agent_qa_status_activity(
    execution_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check status of running agent QA job.

    Returns:
        {"status": "running|completed|failed", "exit_code": int}
    """
    executor = _get_executor()
    return executor.check_status(execution_info)


@activity.defn
async def extract_agent_qa_results_activity(
    execution_info: Dict[str, Any], qa_job_id: int, company_id: int
) -> Dict[str, Any]:
    """
    Validate agent QA results were uploaded.

    For agent QA, the agent POSTs the answer directly to the API endpoint.
    This activity validates that the answer set was actually created in the database.

    Args:
        execution_info: Execution info from launch
        qa_job_id: QA job ID
        company_id: Company ID

    Returns:
        Result summary with answer count

    Raises:
        Exception if answer set not found
    """
    activity.logger.info(f"Validating agent QA results for job {qa_job_id}")

    async with scoped_session():
        # Get QA job to find matrix cell
        qa_job_service = get_qa_job_service()
        qa_job = await qa_job_service.get_qa_job(qa_job_id)

        if not qa_job:
            raise Exception(f"QA job {qa_job_id} not found")

        # Check that answer set exists for the matrix cell
        matrix_service = get_matrix_service()
        cell = await matrix_service.get_matrix_cell(qa_job.matrix_cell_id)

        if not cell:
            raise Exception(f"Matrix cell {qa_job.matrix_cell_id} not found")

        if not cell.current_answer_set_id:
            raise Exception(
                f"No answer set found for matrix cell {qa_job.matrix_cell_id}. "
                "Agent may have failed to upload answer."
            )

        # Get answer set to count answers
        answer_set = await matrix_service.answer_set_service.get_answer_set(
            cell.current_answer_set_id, company_id
        )

        if not answer_set:
            raise Exception(f"Answer set {cell.current_answer_set_id} not found")

        # Get answers for the set
        answers = await matrix_service.answer_service.get_answers_for_answer_set(
            cell.current_answer_set_id, company_id
        )

        activity.logger.info(
            f"Validated agent QA results for job {qa_job_id}: "
            f"answer_found={answer_set.answer_found}, "
            f"answer_count={len(answers)}"
        )

        return {
            "qa_job_id": qa_job_id,
            "matrix_cell_id": qa_job.matrix_cell_id,
            "answer_set_id": cell.current_answer_set_id,
            "answer_found": answer_set.answer_found,
            "answer_count": len(answers),
        }


@activity.defn
async def cleanup_agent_qa_activity(
    execution_info: Dict[str, Any], company_id: int
) -> None:
    """
    Cleanup agent QA resources.

    Removes container/job and deletes service account.

    Args:
        execution_info: Execution info from launch
        company_id: Company ID
    """
    service_account_id = execution_info.get("service_account_id")
    activity.logger.info(
        f"Cleaning up agent QA resources, service_account_id={service_account_id}"
    )

    # Cleanup container/job
    try:
        executor = _get_executor()
        executor.cleanup(execution_info)
        activity.logger.info("Cleaned up container/job")
    except Exception as e:
        activity.logger.error(f"Failed to cleanup container/job: {e}")

    # Cleanup service account
    if service_account_id:
        try:
            await cleanup_execution_service_account(service_account_id, company_id)
            activity.logger.info(f"Cleaned up service account {service_account_id}")
        except Exception as e:
            activity.logger.error(f"Failed to cleanup service account: {e}")
