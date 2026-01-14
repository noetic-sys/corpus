from typing import List, Tuple

from fastapi import HTTPException

from packages.matrices.strategies.factory import CellStrategyFactory
from packages.matrices.models.domain.matrix import (
    MatrixCellModel,
    MatrixCellCreateModel,
)
from packages.qa.models.domain.qa_job import (
    QAJobModel,
    QAJobStatus,
    QAJobCreateModel,
)
from packages.matrices.repositories.matrix_cell_repository import MatrixCellRepository
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.qa.repositories.qa_job_repository import QAJobRepository
from packages.matrices.services.entity_set_service import EntitySetService
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixCellEntityReferenceCreateModel,
)
from packages.matrices.strategies.models import CellUpdateSpec
from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.messages import QAJobMessage
from common.providers.messaging.constants import QueueName
from common.providers.locking.factory import get_lock_provider
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.scoped import transaction
from packages.matrices.lock_keys import (
    matrix_structure_lock_key,
    MATRIX_STRUCTURE_LOCK_TTL,
    MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT,
)
from packages.billing.services.usage_service import UsageService
from packages.billing.services.quota_service import QuotaService
from packages.matrices.models.domain.matrix_enums import EntityType

# Note: QuestionService imported locally in _check_quota_for_cells to avoid circular import
# question_service → reprocessing_service → batch_processing_service → question_service

logger = get_logger(__name__)


class BatchProcessingService:
    """Service for batch processing matrix cells and QA jobs."""

    def __init__(self):
        self.matrix_repo = MatrixRepository()
        self.matrix_cell_repo = MatrixCellRepository()
        self.cell_entity_ref_repo = CellEntityReferenceRepository()
        self.entity_set_member_repo = EntitySetMemberRepository()
        self.entity_set_service = EntitySetService()
        # TODO: i think this actually needs to be a service call here
        self.qa_job_repo = QAJobRepository()
        self.message_queue = get_message_queue()
        self.lock_provider = get_lock_provider()
        self._queue_declared = False

    async def _check_quota_for_cells(
        self,
        cell_models: List[MatrixCellCreateModel],
        company_id: int,
    ) -> int:
        """Check quotas before creating cells. Raises HTTPException if quota exceeded.

        Returns the count of agentic questions (for later tracking).
        """
        if not cell_models:
            return 0

        quota_service = QuotaService()

        # Check cell operation quota (raises 429 if exceeded)
        await quota_service.check_cell_operation_quota(company_id)

        # Count agentic questions for quota check
        question_ids = []
        for cell_model in cell_models:
            if cell_model.entity_refs:
                for ref in cell_model.entity_refs:
                    if ref.entity_type == EntityType.QUESTION:
                        question_ids.append(ref.entity_id)

        agentic_count = 0
        if question_ids:
            # Local import to avoid circular dependency
            from packages.questions.services.question_service import (  # noqa: PLC0415
                QuestionService,
            )

            question_service = QuestionService()
            agentic_count = await question_service.count_agentic_questions(
                question_ids, company_id
            )
            if agentic_count > 0:
                # Check agentic QA quota (raises 429 if exceeded)
                await quota_service.check_agentic_qa_quota(company_id)

        return agentic_count

    async def _track_usage_for_cells(
        self,
        cell_models: List[MatrixCellCreateModel],
        company_id: int,
        matrix_id: int,
        agentic_count: int = 0,
    ) -> None:
        """Track cell operations and agentic QA usage after cells are created."""
        if not cell_models:
            return

        usage_service = UsageService()

        # Track all cell operations
        await usage_service.track_cell_operation(
            company_id=company_id, quantity=len(cell_models), matrix_id=matrix_id
        )

        # Track agentic QA if applicable
        if agentic_count > 0:
            await usage_service.track_agentic_qa(
                company_id=company_id,
                quantity=agentic_count,
                event_metadata={"matrix_id": matrix_id},
            )
            logger.info(
                f"Tracked agentic QA usage for {agentic_count} cells in matrix {matrix_id}"
            )

    async def ensure_queue_declared(self):
        if not self._queue_declared:
            await self.message_queue.declare_queue(QueueName.QA_WORKER)
            self._queue_declared = True

    @trace_span
    async def _batch_insert_matrix_cells(
        self, cell_models: List[MatrixCellCreateModel]
    ) -> List[MatrixCellModel]:
        """Batch insert matrix cells and entity references, return domain models."""
        if not cell_models:
            return []

        logger.info(f"Batch inserting {len(cell_models)} matrix cells")
        created_cells = await self.matrix_cell_repo.bulk_create_from_models(cell_models)
        logger.info(
            f"Created {len(created_cells)} cells with IDs: {[cell.id for cell in created_cells]}"
        )

        # Create entity references for each cell
        entity_ref_creates = []
        for i, cell in enumerate(created_cells):
            if cell_models[i].entity_refs:
                for entity_ref in cell_models[i].entity_refs:
                    ref_create = MatrixCellEntityReferenceCreateModel(
                        matrix_id=cell.matrix_id,
                        matrix_cell_id=cell.id,
                        entity_set_id=entity_ref.entity_set_id,
                        entity_set_member_id=entity_ref.entity_set_member_id,
                        company_id=cell.company_id,
                        role=entity_ref.role,
                        entity_order=entity_ref.entity_order,
                    )
                    entity_ref_creates.append(ref_create)

        if entity_ref_creates:
            logger.info(
                f"Creating {len(entity_ref_creates)} entity references for cells"
            )
            await self.cell_entity_ref_repo.create_references_batch(entity_ref_creates)
            logger.info(f"Created {len(entity_ref_creates)} entity references")

        return created_cells

    @trace_span
    def _create_qa_job_models(
        self, created_cells: List[MatrixCellModel]
    ) -> List[QAJobCreateModel]:
        """Create QA job create models for all matrix cells."""
        logger.info(f"Creating QA jobs for {len(created_cells)} cells")
        job_models = []
        for i, cell in enumerate(created_cells):
            logger.debug(f"Creating job for cell[{i}]={cell.id}")
            job_models.append(
                QAJobCreateModel(matrix_cell_id=cell.id, status=QAJobStatus.QUEUED)
            )
        return job_models

    @trace_span
    async def _batch_insert_qa_jobs(
        self, job_models: List[QAJobCreateModel]
    ) -> List[QAJobModel]:
        """Batch insert QA jobs and return domain models."""
        if not job_models:
            return []

        logger.info(f"Batch inserting {len(job_models)} QA jobs")
        created_jobs = await self.qa_job_repo.bulk_create_from_models(job_models)
        logger.info(
            f"Created {len(created_jobs)} jobs with IDs: {[job.id for job in created_jobs]}"
        )
        logger.info(
            f"Jobs are for cells: {[job.matrix_cell_id for job in created_jobs]}"
        )
        return created_jobs

    def _get_entity_ref_key(self, entity_refs):
        """Create a hashable key from entity refs for application-level deduplication.

        IMPORTANT: Includes role in the key because roles define distinct axes.
        For correlation matrices, (LEFT=A, RIGHT=B) is different from (LEFT=B, RIGHT=A).
        """
        if not entity_refs:
            return ()
        # Sort by role (axis), then entity_set_id, then entity_set_member_id
        # Role MUST be included because it defines the axis/dimension
        sorted_refs = sorted(
            [
                (ref.role.value, ref.entity_set_id, ref.entity_set_member_id)
                for ref in entity_refs
            ]
        )
        return tuple(sorted_refs)

    @trace_span
    async def batch_create_matrix_cells_and_jobs(
        self,
        matrix_id: int,
        entity_set_ids: List[int],
        create_qa_jobs: bool = True,
    ) -> Tuple[List[MatrixCellModel], List[QAJobModel]]:
        """Batch create matrix cells and optionally QA jobs for all entity combinations.

        This is used for operations like matrix duplication where we want to create
        cells for the Cartesian product of ALL members in the given entity sets.

        Args:
            matrix_id: The matrix ID
            entity_set_ids: List of entity set IDs to create cells from
            create_qa_jobs: Whether to create and queue QA jobs immediately

        Returns:
            Tuple of (created cells, created jobs)
        """
        if not entity_set_ids:
            return [], []

        # Get matrix
        matrix = await self.matrix_repo.get(matrix_id)
        if not matrix:
            raise ValueError(f"Matrix {matrix_id} not found")

        # Get all members from each entity set
        entity_ids_by_set = {}
        for entity_set_id in entity_set_ids:
            members = await self.entity_set_service.get_entity_set_members(
                entity_set_id, matrix.company_id
            )
            entity_ids_by_set[entity_set_id] = [m.entity_id for m in members]
            logger.info(f"Entity set {entity_set_id} has {len(members)} members")

        # Check if any entity set is empty
        if any(len(ids) == 0 for ids in entity_ids_by_set.values()):
            logger.warning("One or more entity sets are empty, no cells to create")
            return [], []

        # Get strategy and use it to create cell models
        # We'll call the strategy for each entity in the first entity set
        # This is a bit hacky but maintains the deduplication logic

        all_cell_models = []
        strategy = CellStrategyFactory.get_strategy(matrix.matrix_type)

        # Get first entity set to iterate over
        first_entity_set_id = entity_set_ids[0]
        first_entity_ids = entity_ids_by_set[first_entity_set_id]

        logger.info(
            f"Creating cells by processing {len(first_entity_ids)} entities from first entity set"
        )

        # Process each entity in the first set
        for entity_id in first_entity_ids:
            cell_models = await strategy.create_cells_for_new_entity(
                matrix_id,
                matrix.company_id,
                entity_id,
                first_entity_set_id,
            )
            all_cell_models.extend(cell_models)

        logger.info(f"Strategy generated {len(all_cell_models)} total cell models")

        # FAST PATH DEDUPLICATION: Check if matrix has any cells
        matrix_has_cells = await self.matrix_cell_repo.matrix_has_cells(
            matrix_id, matrix.company_id
        )

        if matrix_has_cells:
            logger.info("Matrix has existing cells, loading refs for deduplication")
            # SLOW PATH: Load all refs for deduplication
            all_existing_refs = await self.cell_entity_ref_repo.get_by_matrix_id(
                matrix_id
            )
            refs_by_cell = {}
            for ref in all_existing_refs:
                if ref.matrix_cell_id not in refs_by_cell:
                    refs_by_cell[ref.matrix_cell_id] = []
                refs_by_cell[ref.matrix_cell_id].append(ref)

            existing_combos = set()
            for cell_id, refs in refs_by_cell.items():
                key = self._get_entity_ref_key(refs)
                existing_combos.add(key)
            logger.info(f"Found {len(existing_combos)} existing cell combinations")
        else:
            logger.info("Matrix is empty, skipping deduplication")
            existing_combos = set()

        # Filter out duplicates
        new_cell_models = []
        for cell_model in all_cell_models:
            cell_key = self._get_entity_ref_key(cell_model.entity_refs)
            if cell_key not in existing_combos:
                new_cell_models.append(cell_model)

        logger.info(
            f"Creating {len(new_cell_models)} new cells (filtered {len(all_cell_models) - len(new_cell_models)} duplicates)"
        )

        # Check quota before creating cells (raises 429 if exceeded)
        agentic_count = await self._check_quota_for_cells(
            new_cell_models, matrix.company_id
        )

        # All DB operations in transaction - commits when exiting context
        created_cells = []
        created_jobs = []
        async with transaction():
            # Insert cells
            created_cells = await self._batch_insert_matrix_cells(new_cell_models)

            # Track usage for billing
            await self._track_usage_for_cells(
                new_cell_models, matrix.company_id, matrix_id, agentic_count
            )

            # Optionally create QA jobs
            if create_qa_jobs and created_cells:
                job_models = self._create_qa_job_models(created_cells)
                created_jobs = await self._batch_insert_qa_jobs(job_models)

        # Transaction committed - now safe to publish messages
        logger.info("Committed cells and jobs to database")

        if created_jobs:
            await self._batch_queue_jobs(created_jobs, created_cells)
            logger.info(f"Created and queued {len(created_jobs)} QA jobs")

        logger.info(
            f"Successfully created {len(created_cells)} matrix cells and {len(created_jobs)} QA jobs"
        )
        return created_cells, created_jobs

    @trace_span
    def _prepare_job_messages(
        self, qa_jobs: List[QAJobModel], cell_map: dict
    ) -> List[QAJobMessage]:
        """Prepare messages for queueing."""
        messages = []

        logger.info(f"Preparing messages for {len(qa_jobs)} jobs")

        for i, job in enumerate(qa_jobs):
            cell = cell_map.get(job.matrix_cell_id)
            if not cell:
                logger.error(
                    f"Matrix cell {job.matrix_cell_id} not found for job {job.id}"
                )
                continue

            logger.debug(f"Preparing message for job[{i}]={job.id}, cell={cell.id}")
            message = QAJobMessage(
                job_id=job.id,
                matrix_cell_id=cell.id,
            )
            messages.append(message)

        logger.info(f"Prepared {len(messages)} messages for queueing")
        return messages

    @trace_span
    async def _publish_messages(self, messages: List[QAJobMessage]) -> None:
        """Publish all messages to the queue in batch."""
        logger.info(f"Publishing {len(messages)} messages to qa_worker queue")

        # Convert to dict format for batch publish
        message_dicts = [message.model_dump() for message in messages]

        # Use batch publish for better performance
        published_count = await self.message_queue.publish_batch(
            QueueName.QA_WORKER, message_dicts
        )

        if published_count != len(messages):
            logger.error(f"Only published {published_count}/{len(messages)} messages")

    @trace_span
    async def _batch_queue_jobs(
        self,
        qa_jobs: List[QAJobModel],
        matrix_cells: List[MatrixCellModel],
    ) -> None:
        """Batch queue jobs for processing."""
        await self.ensure_queue_declared()

        cell_map = {cell.id: cell for cell in matrix_cells}
        logger.info(
            f"Cell map has {len(cell_map)} entries for {len(matrix_cells)} cells"
        )
        logger.info(f"Cell IDs in map: {sorted(cell_map.keys())}")

        messages = self._prepare_job_messages(qa_jobs, cell_map)

        await self._publish_messages(messages)

    @trace_span
    async def create_jobs_and_queue_for_cells(
        self, matrix_cells: List[MatrixCellModel]
    ) -> int:
        """Create QA jobs for existing matrix cells and queue them. Returns count of successfully queued jobs."""
        if not matrix_cells:
            return 0

        # Create QA jobs in transaction - commits when exiting context
        async with transaction():
            job_models = self._create_qa_job_models(matrix_cells)
            created_jobs = await self._batch_insert_qa_jobs(job_models)

        # Transaction committed - now safe to publish messages
        logger.info("Committed QA jobs to database before publishing messages")

        await self._batch_queue_jobs(created_jobs, matrix_cells)

        logger.info(f"Created {len(created_jobs)} QA jobs for reprocessing")

        return len(created_jobs)

    @trace_span
    async def _process_cell_updates(
        self,
        matrix_id: int,
        company_id: int,
        update_specs: List[CellUpdateSpec],
    ) -> List[MatrixCellModel]:
        """Process cell updates by adding entity refs and resetting status.

        Used by synopsis strategy when documents are added to a matrix.
        Existing cells need to include the new document and be re-processed.

        Args:
            matrix_id: The matrix ID
            company_id: Company ID for access control
            update_specs: List of CellUpdateSpec describing updates

        Returns:
            List of updated cell models
        """
        if not update_specs:
            return []

        logger.info(f"Processing {len(update_specs)} cell updates")

        # Process each update - add entity refs to cells
        updated_cell_ids = []
        for spec in update_specs:
            # Convert EntityReference to MatrixCellEntityReferenceCreateModel
            ref_creates = []
            for entity_ref in spec.entity_refs_to_add:
                ref_create = MatrixCellEntityReferenceCreateModel(
                    matrix_id=matrix_id,
                    matrix_cell_id=spec.cell_id,
                    entity_set_id=entity_ref.entity_set_id,
                    entity_set_member_id=entity_ref.entity_set_member_id,
                    company_id=company_id,
                    role=entity_ref.role,
                    entity_order=entity_ref.entity_order,
                )
                ref_creates.append(ref_create)

            # Add entity refs to cell
            if ref_creates:
                await self.cell_entity_ref_repo.create_references_batch(ref_creates)
            updated_cell_ids.append(spec.cell_id)

        # Reset status to PENDING for all updated cells if requested
        reset_cell_ids = [spec.cell_id for spec in update_specs if spec.reset_status]
        if reset_cell_ids:
            await self.matrix_cell_repo.bulk_update_cells_to_pending(reset_cell_ids)
            logger.info(f"Reset {len(reset_cell_ids)} cells to PENDING status")

        # Load and return updated cells
        updated_cells = await self.matrix_cell_repo.get_cells_by_ids(updated_cell_ids)
        logger.info(f"Successfully updated {len(updated_cells)} cells")
        return updated_cells

    @trace_span
    async def process_entity_added_to_set(
        self,
        matrix_id: int,
        entity_id: int,
        entity_set_id: int,
        create_qa_jobs: bool = False,
    ) -> Tuple[List[MatrixCellModel], List[QAJobModel]]:
        """Process a new entity added to an entity set by creating/updating matrix cells.

        This is the core method for entity-set-aware batch processing. It:
        1. Determines which entity set the new entity belongs to
        2. Finds complementary entity sets to pair with based on matrix type
        3. Creates cells using the appropriate strategy
        4. Updates existing cells if strategy requires (e.g., synopsis)
        5. Optionally creates and queues QA jobs

        Args:
            matrix_id: The matrix ID
            entity_id: The ID of the newly added entity
            entity_set_id: The entity set the entity was added to
            create_qa_jobs: Whether to create QA jobs immediately (True for questions, False for documents)

        Returns:
            Tuple of (created/updated cells, created jobs)
        """
        # Acquire structural lock to prevent race conditions with concurrent modifications
        lock_key = matrix_structure_lock_key(matrix_id)
        lock_token = await self.lock_provider.acquire_lock_with_retry(
            lock_key,
            lock_ttl_seconds=MATRIX_STRUCTURE_LOCK_TTL,
            acquire_timeout_seconds=MATRIX_STRUCTURE_LOCK_ACQUIRE_TIMEOUT,
        )
        if not lock_token:
            logger.warning(
                f"Failed to acquire structure lock for matrix {matrix_id} - concurrent modification"
            )
            raise HTTPException(
                status_code=409,
                detail="Matrix is being modified by another request. Please try again.",
            )

        try:
            # Get matrix to determine type
            matrix = await self.matrix_repo.get(matrix_id)
            if not matrix:
                raise ValueError(f"Matrix {matrix_id} not found")

            logger.info(
                f"Processing entity {entity_id} added to entity set {entity_set_id} "
                f"in matrix {matrix_id} ({matrix.matrix_type.value})"
            )

            # Get strategy and let it handle everything
            strategy = CellStrategyFactory.get_strategy(matrix.matrix_type)
            cell_models = await strategy.create_cells_for_new_entity(
                matrix_id,
                matrix.company_id,
                entity_id,
                entity_set_id,
            )

            logger.info(f"Strategy generated {len(cell_models)} cell models")

            # Get cell updates (used by synopsis strategy for document additions)
            update_specs = await strategy.update_cells_for_new_entity(
                matrix_id,
                matrix.company_id,
                entity_id,
                entity_set_id,
            )
            logger.info(f"Strategy generated {len(update_specs)} cell update specs")

            # SANITY CHECK: Validate that all cell models actually reference the new entity
            # This prevents bugs where strategies generate cells unrelated to the new entity
            invalid_cells = []
            for i, cell_model in enumerate(cell_models):
                entity_ids_in_cell = [ref.entity_id for ref in cell_model.entity_refs]
                if entity_id not in entity_ids_in_cell:
                    invalid_cells.append(i)

            if invalid_cells:
                raise ValueError(
                    f"Strategy bug: Generated {len(invalid_cells)}/{len(cell_models)} cells that don't reference new entity {entity_id}. "
                    f"This indicates the strategy is creating too many cells. "
                    f"First invalid cell refs: {[cell_models[invalid_cells[0]].entity_refs if invalid_cells else None]}"
                )

            # FAST PATH DEDUPLICATION: Check if entity already has cells
            entity_set = await self.entity_set_service.get_entity_set(
                entity_set_id, matrix.company_id
            )
            if not entity_set:
                raise ValueError(f"Entity set {entity_set_id} not found")

            # Get entity set members for this entity (service layer orchestrates repositories)
            members = await self.entity_set_member_repo.get_members_by_entity_id(
                entity_id, entity_set.entity_type, matrix.company_id
            )

            if not members:
                logger.info(f"Entity {entity_id} has no members, skipping deduplication")
                existing_combos = set()
            else:
                member_ids = [m.id for m in members]

                # Check if any of these members have cells in the matrix
                members_have_cells = (
                    await self.cell_entity_ref_repo.members_have_cells_in_matrix(
                        matrix_id, member_ids, matrix.company_id
                    )
                )

                if members_have_cells:
                    logger.info(
                        f"Entity {entity_id} already has cells, using targeted deduplication"
                    )
                    existing_combos = (
                        await self.cell_entity_ref_repo.get_cell_combinations_for_members(
                            matrix_id, member_ids, matrix.company_id
                        )
                    )
                else:
                    logger.info(
                        f"Entity {entity_id} is new to matrix, skipping deduplication"
                    )
                    existing_combos = set()

            # Filter out cells that already exist
            new_cell_models = []
            skipped_count = 0
            for cell_model in cell_models:
                cell_key = self._get_entity_ref_key(cell_model.entity_refs)
                if cell_key not in existing_combos:
                    new_cell_models.append(cell_model)
                else:
                    skipped_count += 1

            logger.info(
                f"Creating {len(new_cell_models)} new cells, skipped {skipped_count} duplicates"
            )

            # Check quota before creating cells (raises 429 if exceeded)
            agentic_count = await self._check_quota_for_cells(
                new_cell_models, matrix.company_id
            )

            # All DB operations in transaction - commits when exiting context
            created_cells = []
            updated_cells = []
            created_jobs = []
            async with transaction():
                # Insert the new cells
                created_cells = await self._batch_insert_matrix_cells(new_cell_models)
                logger.info(
                    f"Successfully created {len(created_cells)} matrix cells for entity {entity_id}"
                )

                # Process cell updates (synopsis strategy uses this)
                updated_cells = await self._process_cell_updates(
                    matrix_id, matrix.company_id, update_specs
                )

                # Track usage for billing - both new cells and updated cells
                await self._track_usage_for_cells(
                    new_cell_models, matrix.company_id, matrix_id, agentic_count
                )

                # Track updated cells too (they will be re-processed)
                if updated_cells:
                    usage_service = UsageService()
                    await usage_service.track_cell_operation(
                        company_id=matrix.company_id,
                        quantity=len(updated_cells),
                        matrix_id=matrix_id,
                    )
                    logger.info(
                        f"Tracked cell operation usage for {len(updated_cells)} updated cells"
                    )

                # Combine created and updated cells for job processing
                all_affected_cells = created_cells + updated_cells

                # Optionally create QA jobs for all affected cells
                if create_qa_jobs and all_affected_cells:
                    logger.info(f"Creating QA jobs for {len(all_affected_cells)} cells")
                    job_models = self._create_qa_job_models(all_affected_cells)
                    created_jobs = await self._batch_insert_qa_jobs(job_models)

            # Transaction committed - now safe to publish messages
            logger.info("Committed cells and jobs to database")

            if created_jobs:
                all_affected_cells = created_cells + updated_cells
                await self._batch_queue_jobs(created_jobs, all_affected_cells)
                logger.info(f"Queued {len(created_jobs)} QA jobs")
            elif not create_qa_jobs:
                logger.info("QA jobs will be created later (create_qa_jobs=False)")

            return created_cells + updated_cells, created_jobs
        finally:
            await self.lock_provider.release_lock(lock_key, lock_token)


def get_batch_processing_service() -> BatchProcessingService:
    """Get batch processing service instance."""
    return BatchProcessingService()
