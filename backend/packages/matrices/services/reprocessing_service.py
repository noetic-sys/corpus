from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from packages.matrices.repositories.matrix_cell_repository import MatrixCellRepository
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.models.domain.matrix import MatrixCellModel
from packages.matrices.models.domain.matrix_enums import EntityRole
from packages.matrices.models.schemas.matrix import MatrixReprocessRequest
from packages.matrices.services.batch_processing_service import BatchProcessingService
from packages.billing.services.quota_service import QuotaService
from packages.billing.services.usage_service import UsageService
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.transaction_utils import TransactionMixin, transactional

logger = get_logger(__name__)


class ReprocessingService(TransactionMixin):
    """Service for reprocessing matrix cells."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.matrix_cell_repo = MatrixCellRepository(db_session)
        self.member_repo = EntitySetMemberRepository(db_session)
        self.cell_ref_repo = CellEntityReferenceRepository(db_session)
        self.batch_processing_service = BatchProcessingService(db_session)

    @trace_span
    @transactional
    async def reprocess_matrix_cells(
        self, matrix_id: int, request: MatrixReprocessRequest
    ) -> int:
        """Reprocess multiple matrix cells based on the request criteria."""
        logger.info(
            f"Starting bulk reprocessing for matrix {matrix_id} with request: {request}"
        )

        # Resolve which cells to reprocess
        cells_to_reprocess = await self._resolve_cells_to_reprocess(matrix_id, request)

        if not cells_to_reprocess:
            logger.warning(f"No cells found to reprocess for matrix {matrix_id}")
            return 0

        cell_ids = [cell.id for cell in cells_to_reprocess]
        logger.info(f"Found {len(cell_ids)} cells to reprocess: {cell_ids}")

        # Get company_id from the first cell (all cells in a matrix have same company)
        company_id = cells_to_reprocess[0].company_id

        # Check quotas before reprocessing (raises 429 if exceeded)
        agentic_count = await self._check_quota_for_reprocess(
            cells_to_reprocess, company_id
        )

        # Bulk update cells to pending status
        updated_count = await self.matrix_cell_repo.bulk_update_cells_to_pending(
            cell_ids
        )
        logger.info(f"Updated {updated_count} cells to pending status")

        # Commit transaction before publishing messages
        await self.db_session.flush()
        logger.info("Committed bulk reprocessing changes to database")

        # Use batch processing service to create jobs and queue them
        jobs_created = (
            await self.batch_processing_service.create_jobs_and_queue_for_cells(
                cells_to_reprocess
            )
        )

        logger.info(
            f"Successfully created and queued {jobs_created} reprocessing jobs for matrix {matrix_id}"
        )

        # Track usage after reprocessing
        await self._track_usage_for_reprocess(
            cells_to_reprocess, company_id, matrix_id, agentic_count
        )

        return len(cells_to_reprocess)

    async def _resolve_cells_to_reprocess(
        self, matrix_id: int, request: MatrixReprocessRequest
    ) -> List[MatrixCellModel]:
        """Resolve which cells to reprocess based on the request criteria."""
        cell_ids_set: set[int] = set()

        # If whole_matrix is True, get all cells for the matrix
        if request.whole_matrix:
            cells = await self.matrix_cell_repo.get_cells_by_matrix_id(matrix_id)
            for cell in cells:
                cell_ids_set.add(cell.id)
            logger.info(f"Whole matrix requested: found {len(cells)} cells")

        # Add cells by entity set filters (role-agnostic)
        if request.entity_set_filters:
            for filter in request.entity_set_filters:
                # Step 1: Get member IDs for these entity IDs
                member_ids = await self.member_repo.get_member_ids_by_entity_ids(
                    filter.entity_set_id, filter.entity_ids
                )

                if not member_ids:
                    logger.warning(
                        f"No members found for entity_set_id={filter.entity_set_id}, "
                        f"entity_ids={filter.entity_ids}"
                    )
                    continue

                # Step 2: Get cells that reference these members (any role)
                found_cell_ids = await self.cell_ref_repo.get_cells_by_member_ids(
                    matrix_id, filter.entity_set_id, member_ids
                )

                cell_ids_set.update(found_cell_ids)
                logger.info(
                    f"Entity set filter (set_id={filter.entity_set_id}, "
                    f"entity_ids={filter.entity_ids}): found {len(found_cell_ids)} cells"
                )

        # Add cells by explicit cell IDs
        if request.cell_ids:
            cells = await self.matrix_cell_repo.get_cells_by_ids(request.cell_ids)
            # Filter to only cells in the specified matrix
            for cell in cells:
                if cell.matrix_id == matrix_id:
                    cell_ids_set.add(cell.id)
            matrix_cells = [cell for cell in cells if cell.matrix_id == matrix_id]
            logger.info(
                f"Cell IDs {request.cell_ids}: found {len(matrix_cells)} valid cells in matrix"
            )

        # Load full cell models
        if not cell_ids_set:
            logger.info("No cells matched the criteria")
            return []

        result = await self.matrix_cell_repo.get_cells_by_ids(list(cell_ids_set))
        logger.info(f"Total unique cells to reprocess: {len(result)}")
        return result

    async def _check_quota_for_reprocess(
        self, cells: List[MatrixCellModel], company_id: int
    ) -> int:
        """Check quotas before reprocessing. Returns agentic count for later tracking."""
        if not cells:
            return 0

        quota_service = QuotaService(self.db_session)

        # Check cell operation quota (raises 429 if exceeded)
        await quota_service.check_cell_operation_quota(company_id)

        # Get question IDs for these cells to check agentic quota
        question_ids = await self._get_question_ids_for_cells(cells)

        agentic_count = 0
        if question_ids:
            # Local import to avoid circular dependency
            from packages.questions.services.question_service import (  # noqa: PLC0415
                QuestionService,
            )

            question_service = QuestionService(self.db_session)
            agentic_count = await question_service.count_agentic_questions(
                question_ids, company_id
            )
            if agentic_count > 0:
                # Check agentic QA quota (raises 429 if exceeded)
                await quota_service.check_agentic_qa_quota(company_id)
                logger.info(f"Checked agentic quota for {agentic_count} agentic cells")

        return agentic_count

    async def _get_question_ids_for_cells(
        self, cells: List[MatrixCellModel]
    ) -> List[int]:
        """Get question IDs for cells from their entity references."""
        cell_ids = [cell.id for cell in cells]

        # Get entity refs for all cells in bulk
        entity_refs = await self.cell_ref_repo.get_by_cell_ids_bulk(cell_ids)

        # Get member IDs for QUESTION role refs
        question_member_ids = list(
            set(
                ref.entity_set_member_id
                for ref in entity_refs
                if ref.role == EntityRole.QUESTION
            )
        )

        if not question_member_ids:
            return []

        # Get entity IDs (question IDs) from members
        members = await self.member_repo.get_by_member_ids(question_member_ids)
        return [member.entity_id for member in members]

    async def _track_usage_for_reprocess(
        self,
        cells: List[MatrixCellModel],
        company_id: int,
        matrix_id: int,
        agentic_count: int,
    ) -> None:
        """Track usage after reprocessing cells."""
        if not cells:
            return

        usage_service = UsageService()

        # Track all cell operations
        await usage_service.track_cell_operation(
            company_id=company_id,
            quantity=len(cells),
            matrix_id=matrix_id,
        )
        logger.info(
            f"Tracked cell operation usage for {len(cells)} reprocessed cells in matrix {matrix_id}"
        )

        # Track agentic QA if applicable
        if agentic_count > 0:
            await usage_service.track_agentic_qa(
                company_id=company_id,
                quantity=agentic_count,
                matrix_id=matrix_id,
            )
            logger.info(
                f"Tracked agentic QA usage for {agentic_count} cells in matrix {matrix_id}"
            )


def get_reprocessing_service(db_session: AsyncSession) -> ReprocessingService:
    """Get reprocessing service instance."""
    return ReprocessingService(db_session)
