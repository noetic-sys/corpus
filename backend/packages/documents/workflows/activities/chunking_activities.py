"""
Temporal activities for document chunking workflow.

Activities handle:
1. Determining chunking strategy based on tier/quota
2. Launching chunking container (agentic)
3. In-process naive chunking
4. Checking execution status
5. Validating chunks were uploaded
6. Cleanup
7. Credit reservation and refunds
"""

import json
from typing import Dict, Any
from temporalio import activity
from sqlalchemy import update as sql_update

from common.core.config import settings
from common.core.constants import WorkflowExecutionMode
from common.db.session import get_db
from common.providers.storage.factory import get_storage
from common.providers.storage.paths import (
    get_document_chunks_prefix,
    get_document_chunk_manifest_path,
)
from common.execution.executors.docker import DockerExecutor
from common.execution.executors.k8s import K8sExecutor
from common.execution.job_spec import JobSpec
from common.execution.workflow_framework.service_accounts import (
    create_execution_service_account,
    cleanup_execution_service_account,
)
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy
from packages.documents.services.naive_chunking_service import (
    get_naive_chunking_service,
)
from packages.documents.services.chunk_upload_service import get_chunk_upload_service
from packages.documents.services.document_service import get_document_service
from packages.billing.services.quota_service import QuotaService
from packages.billing.services.usage_service import UsageService
from packages.billing.models.database.usage import UsageEventEntity


def _get_executor():
    """Get appropriate executor based on execution mode."""
    execution_mode = WorkflowExecutionMode(settings.workflow_execution_mode)
    if execution_mode == WorkflowExecutionMode.DOCKER:
        return DockerExecutor()
    else:
        return K8sExecutor()


# ============================================================================
# Strategy Selection Activity
# ============================================================================


@activity.defn
async def get_chunking_strategy_activity(
    company_id: int, document_id: int
) -> Dict[str, Any]:
    """
    Determine chunking strategy and atomically reserve credit if agentic.

    Uses QuotaService.reserve_agentic_chunking_if_available which:
    1. Acquires advisory lock for this company (serializes concurrent requests)
    2. Checks quota
    3. If available: reserves credit and returns agentic
    4. If exceeded: returns sentence (no reservation)

    Args:
        company_id: Company ID
        document_id: Document ID (for reservation tracking)

    Returns:
        Dict with strategy, tier, usage_event_id (if agentic), quota_exceeded
    """
    activity.logger.info(
        f"Determining chunking strategy for company {company_id}, document {document_id}"
    )

    async for db_session in get_db():
        quota_service = QuotaService(db_session)
        result = await quota_service.reserve_agentic_chunking_if_available(
            company_id=company_id,
            document_id=document_id,
        )
        await db_session.commit()

        if result.reserved:
            activity.logger.info(
                f"Agentic chunking reserved for company {company_id}, "
                f"document {document_id}, event_id={result.usage_event_id} "
                f"({result.current_usage}/{result.limit})"
            )
            return {
                "strategy": ChunkingStrategy.AGENTIC.value,
                "tier": result.tier.value,
                "usage_event_id": result.usage_event_id,
                "quota_exceeded": False,
            }
        else:
            activity.logger.info(
                f"Agentic quota exceeded for company {company_id}, "
                f"falling back to sentence ({result.current_usage}/{result.limit})"
            )
            return {
                "strategy": ChunkingStrategy.SENTENCE.value,
                "tier": result.tier.value,
                "usage_event_id": None,
                "quota_exceeded": True,
            }


# ============================================================================
# Agentic Chunking Activities
# ============================================================================


@activity.defn
async def launch_chunking_activity(document_id: int, company_id: int) -> Dict[str, Any]:
    """
    Launch document chunking container.

    Args:
        document_id: Document ID to chunk
        company_id: Company ID

    Returns:
        Execution info dict with container/job details
    """
    activity.logger.info(f"Launching chunking job for document {document_id}")

    # Create service account for API authentication
    service_account_id, api_key = await create_execution_service_account(
        document_id, company_id
    )

    # Build job spec for chunking
    container_name = f"chunking-doc-{document_id}"
    job_spec = JobSpec(
        container_name=container_name,
        template_name="chunking_job.yaml.j2",
        image_name="corpus/document-chunker",
        env_vars={
            "DOCUMENT_ID": str(document_id),
            "COMPANY_ID": str(company_id),
            "API_ENDPOINT": settings.api_endpoint,
            "API_KEY": api_key,
            "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        },
        template_vars={"document_id": document_id},
    )

    # Launch container
    executor = _get_executor()
    execution_info = executor.launch(job_spec)

    # Add service account ID for cleanup
    execution_info["service_account_id"] = service_account_id

    activity.logger.info(
        f"Launched chunking job for document {document_id}: {execution_info}"
    )

    return execution_info


@activity.defn
async def check_chunking_status_activity(
    execution_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Check status of chunking container.

    Args:
        execution_info: Execution info from launch

    Returns:
        Status dict with "status" key ("running", "completed", "failed")
    """
    executor = _get_executor()
    return executor.check_status(execution_info)


@activity.defn
async def extract_chunking_results_activity(
    execution_info: Dict[str, Any], document_id: int, company_id: int
) -> Dict[str, Any]:
    """
    Validate chunks were uploaded to S3.

    Args:
        execution_info: Execution info from launch
        document_id: Document ID
        company_id: Company ID

    Returns:
        Result summary with chunk count and S3 prefix

    Raises:
        Exception if chunks not found
    """
    activity.logger.info(f"Validating chunks for document {document_id}")

    storage = get_storage()
    manifest_key = get_document_chunk_manifest_path(company_id, document_id)

    # Check that manifest exists
    if not await storage.exists(manifest_key):
        raise Exception(
            f"No chunk manifest found at {manifest_key}. Chunking may have failed to upload."
        )

    # Download and parse manifest to get chunk count
    manifest_bytes = await storage.download(manifest_key)
    if not manifest_bytes:
        raise Exception(f"Failed to download manifest from {manifest_key}")

    manifest_data = json.loads(manifest_bytes.decode("utf-8"))
    chunk_count = len(manifest_data.get("chunks", []))
    s3_prefix = get_document_chunks_prefix(company_id, document_id)

    activity.logger.info(
        f"Validated chunks for document {document_id}: "
        f"chunk_count={chunk_count}, s3_prefix={s3_prefix}"
    )

    return {
        "document_id": document_id,
        "chunk_count": chunk_count,
        "s3_prefix": s3_prefix,
    }


@activity.defn
async def cleanup_chunking_activity(
    execution_info: Dict[str, Any], company_id: int
) -> None:
    """
    Cleanup chunking resources.

    Removes container/job and deletes service account.

    Args:
        execution_info: Execution info from launch
        company_id: Company ID
    """
    service_account_id = execution_info.get("service_account_id")
    activity.logger.info(
        f"Cleaning up chunking resources, service_account_id={service_account_id}"
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


# ============================================================================
# Naive Chunking Activity
# ============================================================================


@activity.defn
async def naive_chunking_activity(
    document_id: int,
    company_id: int,
    strategy: str,
) -> Dict[str, Any]:
    """
    Perform in-process naive chunking and upload results.

    Args:
        document_id: Document ID to chunk
        company_id: Company ID
        strategy: Chunking strategy string value

    Returns:
        Dict with document_id, chunk_count, s3_prefix, and strategy
    """
    # Convert string to enum
    chunking_strategy = ChunkingStrategy(strategy)

    activity.logger.info(
        f"Starting naive chunking for document {document_id} with strategy {chunking_strategy}"
    )

    # Get document to find extracted content path
    async for db_session in get_db():
        document_service = get_document_service(db_session)
        document = await document_service.get_document(document_id, company_id)
        break

    if not document:
        raise Exception(f"Document {document_id} not found")

    if not document.extracted_content_path:
        raise Exception(f"Document {document_id} has no extracted content")

    # Download extracted text from S3
    activity.logger.info(
        f"Downloading extracted content from {document.extracted_content_path}"
    )
    storage = get_storage()
    content_bytes = await storage.download(document.extracted_content_path)
    if not content_bytes:
        raise Exception(
            f"Failed to download extracted content for document {document_id}"
        )

    text = content_bytes.decode("utf-8")
    activity.logger.info(f"Downloaded {len(text)} characters of text")

    # Chunk the text (no DB needed)
    naive_chunking_service = get_naive_chunking_service()
    chunks = naive_chunking_service.chunk(text, chunking_strategy, document_id)
    activity.logger.info(
        f"Created {len(chunks)} chunks using {chunking_strategy} strategy"
    )

    # Upload chunks via ChunkUploadService
    async for db_session in get_db():
        chunk_upload_service = get_chunk_upload_service(db_session)
        s3_prefix = await chunk_upload_service.process_chunk_upload(
            document_id=document_id,
            company_id=company_id,
            chunks=chunks,
            chunking_strategy=chunking_strategy,
        )
        break

    activity.logger.info(f"Uploaded {len(chunks)} chunks to {s3_prefix}")

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "s3_prefix": s3_prefix,
        "strategy": chunking_strategy.value,
    }


# ============================================================================
# Credit Refund Activities
# ============================================================================


@activity.defn
async def refund_agentic_chunking_credit_activity(
    company_id: int,
    document_id: int,
    original_event_id: int,
) -> int:
    """
    Refund an agentic chunking credit after failure.

    Creates a -1 quantity event to offset the reservation, preserving audit trail.

    Args:
        company_id: Company ID
        document_id: Document that failed chunking
        original_event_id: The original reservation event ID

    Returns:
        The refund event ID
    """
    activity.logger.info(
        f"Refunding agentic chunking credit for document {document_id} "
        f"(original_event_id={original_event_id})"
    )

    async for db_session in get_db():
        usage_service = UsageService(db_session)
        refund_event = await usage_service.refund_agentic_chunking(
            company_id=company_id,
            document_id=document_id,
            original_event_id=original_event_id,
        )
        await db_session.commit()
        break

    activity.logger.info(
        f"Created refund event {refund_event.id} for original event {original_event_id}"
    )

    return refund_event.id


@activity.defn
async def update_agentic_chunking_metadata_activity(
    usage_event_id: int,
    chunk_count: int,
) -> None:
    """
    Update the usage event with final chunk count after successful completion.

    Args:
        usage_event_id: The usage event ID to update
        chunk_count: Number of chunks that were created
    """
    activity.logger.info(
        f"Updating agentic chunking metadata (event_id={usage_event_id}, chunk_count={chunk_count})"
    )

    async for db_session in get_db():
        await db_session.execute(
            sql_update(UsageEventEntity)
            .where(UsageEventEntity.id == usage_event_id)
            .values(event_metadata={"chunk_count": chunk_count})
        )
        await db_session.commit()
        break

    activity.logger.info(
        f"Updated agentic chunking metadata for event {usage_event_id}"
    )
