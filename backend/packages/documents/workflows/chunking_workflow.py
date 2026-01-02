"""
Temporal workflow for document chunking.

Orchestrates chunking execution with tiered strategy:
1. Determine chunking strategy based on subscription tier and quota
2. For agentic: Launch K8s job/Docker container with chunking agent
3. For naive: Run in-process chunking
4. Verify chunks were uploaded
5. Clean up resources (agentic only)
"""

from temporalio import workflow
from temporalio.exceptions import ApplicationError
from datetime import timedelta

from packages.documents.models.domain.chunking_strategy import ChunkingStrategy

# Use string-based activity names to avoid sandbox import restrictions
GET_CHUNKING_STRATEGY_ACTIVITY = "get_chunking_strategy_activity"
LAUNCH_CHUNKING_ACTIVITY = "launch_chunking_activity"
CHECK_CHUNKING_STATUS_ACTIVITY = "check_chunking_status_activity"
EXTRACT_CHUNKING_RESULTS_ACTIVITY = "extract_chunking_results_activity"
CLEANUP_CHUNKING_ACTIVITY = "cleanup_chunking_activity"
NAIVE_CHUNKING_ACTIVITY = "naive_chunking_activity"
REFUND_AGENTIC_CHUNKING_CREDIT_ACTIVITY = "refund_agentic_chunking_credit_activity"
UPDATE_AGENTIC_CHUNKING_METADATA_ACTIVITY = "update_agentic_chunking_metadata_activity"


@workflow.defn
class DocumentChunkingWorkflow:
    @workflow.run
    async def run(
        self,
        document_id: int,
        company_id: int,
    ) -> dict:
        """
        Execute document chunking with tier-based strategy selection.

        Args:
            document_id: Document ID to chunk
            company_id: Company ID

        Returns:
            Dict with document_id, chunk_count, s3_prefix, and strategy
        """
        workflow.logger.info(f"Starting document chunking for document {document_id}")

        try:
            # Step 1: Determine chunking strategy and atomically reserve credit if agentic
            strategy_result = await workflow.execute_activity(
                GET_CHUNKING_STRATEGY_ACTIVITY,
                args=[company_id, document_id],
                start_to_close_timeout=timedelta(seconds=30),
            )

            strategy = strategy_result["strategy"]
            tier = strategy_result["tier"]
            usage_event_id = strategy_result.get("usage_event_id")

            workflow.logger.info(
                f"Chunking strategy for document {document_id}: "
                f"strategy={strategy}, tier={tier}, usage_event_id={usage_event_id}"
            )

            # Step 2: Branch based on strategy
            if strategy == ChunkingStrategy.AGENTIC.value:
                result = await self._run_agentic_chunking(
                    document_id, company_id, usage_event_id
                )
            else:
                result = await self._run_naive_chunking(
                    document_id, company_id, strategy
                )

            workflow.logger.info(f"Chunking completed: {result}")
            return result

        except Exception as e:
            workflow.logger.error(f"Document chunking workflow failed: {e}")
            raise

    async def _run_agentic_chunking(
        self, document_id: int, company_id: int, usage_event_id: int
    ) -> dict:
        """Run agentic chunking via K8s job.

        Credit was already reserved atomically in get_chunking_strategy_activity.
        """
        workflow.logger.info(
            f"Running agentic chunking for document {document_id} "
            f"(usage_event_id={usage_event_id})"
        )

        try:
            # Launch chunking job
            execution_info = await workflow.execute_activity(
                LAUNCH_CHUNKING_ACTIVITY,
                args=[document_id, company_id],
                start_to_close_timeout=timedelta(minutes=2),
            )

            workflow.logger.info(f"Launched chunking job: {execution_info}")

            # Poll for completion
            max_wait_minutes = 15
            poll_interval_seconds = 5
            elapsed_minutes = 0

            while elapsed_minutes < max_wait_minutes:
                await workflow.sleep(poll_interval_seconds)
                elapsed_minutes += poll_interval_seconds / 60

                status_result = await workflow.execute_activity(
                    CHECK_CHUNKING_STATUS_ACTIVITY,
                    args=[execution_info],
                    start_to_close_timeout=timedelta(seconds=30),
                )

                if status_result["status"] == "completed":
                    workflow.logger.info(f"Chunking completed: {status_result}")
                    break
                elif status_result["status"] == "failed":
                    raise ApplicationError(
                        f"Chunking failed: {status_result.get('error')}"
                    )

            if elapsed_minutes >= max_wait_minutes:
                raise ApplicationError(
                    f"Chunking timed out after {max_wait_minutes} minutes"
                )

            # Extract and validate chunk results
            extract_result = await workflow.execute_activity(
                EXTRACT_CHUNKING_RESULTS_ACTIVITY,
                args=[execution_info, document_id, company_id],
                start_to_close_timeout=timedelta(minutes=2),
            )

            # Cleanup container/job
            await workflow.execute_activity(
                CLEANUP_CHUNKING_ACTIVITY,
                args=[execution_info, company_id],
                start_to_close_timeout=timedelta(minutes=1),
            )

            # Update usage event with chunk count metadata
            await workflow.execute_activity(
                UPDATE_AGENTIC_CHUNKING_METADATA_ACTIVITY,
                args=[usage_event_id, extract_result["chunk_count"]],
                start_to_close_timeout=timedelta(seconds=30),
            )

            return {
                "document_id": document_id,
                "chunk_count": extract_result["chunk_count"],
                "s3_prefix": extract_result["s3_prefix"],
                "strategy": ChunkingStrategy.AGENTIC.value,
            }

        except Exception as e:
            # Refund credit on failure (creates -1 event to offset reservation)
            workflow.logger.warning(f"Agentic chunking failed, refunding credit: {e}")
            await workflow.execute_activity(
                REFUND_AGENTIC_CHUNKING_CREDIT_ACTIVITY,
                args=[company_id, document_id, usage_event_id],
                start_to_close_timeout=timedelta(seconds=30),
            )
            raise

    async def _run_naive_chunking(
        self, document_id: int, company_id: int, strategy: str
    ) -> dict:
        """Run naive chunking in-process."""
        workflow.logger.info(
            f"Running naive chunking for document {document_id} with strategy {strategy}"
        )

        result = await workflow.execute_activity(
            NAIVE_CHUNKING_ACTIVITY,
            args=[document_id, company_id, strategy],
            start_to_close_timeout=timedelta(minutes=5),
        )

        return result
