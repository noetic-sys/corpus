from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.repositories.matrix_cell_repository import MatrixCellRepository
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.models.schemas.matrix import MatrixSoftDeleteRequest
from common.db.transaction_utils import TransactionMixin, transactional
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class SoftDeleteService(TransactionMixin):
    """Service for performing soft delete operations on matrix entities."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.matrix_repo = MatrixRepository(db_session)
        self.matrix_cell_repo = MatrixCellRepository(db_session)
        self.member_repo = EntitySetMemberRepository(db_session)
        self.cell_ref_repo = CellEntityReferenceRepository(db_session)

    @trace_span
    @transactional
    async def soft_delete_entities(
        self, matrix_id: int, request: MatrixSoftDeleteRequest
    ) -> Tuple[int, int]:
        """
        Soft delete entities and their related matrix cells.
        Returns (entities_deleted, cells_deleted).
        """
        logger.info(
            f"Starting soft delete for matrix {matrix_id} with request: {request}"
        )

        entities_deleted = 0
        cells_deleted = 0

        # Soft delete cells and entity set members by entity set filters
        if request.entity_set_filters:
            member_count, cell_count = await self._soft_delete_cells_by_entity_filters(
                matrix_id, request.entity_set_filters
            )
            entities_deleted += member_count
            cells_deleted += cell_count

        # Soft delete matrices and all their cells
        if request.matrix_ids:
            m_count, m_cell_count = await self._soft_delete_matrices(request.matrix_ids)
            entities_deleted += m_count
            cells_deleted += m_cell_count

        logger.info(
            f"Soft delete completed: {entities_deleted} entities, {cells_deleted} cells"
        )
        return entities_deleted, cells_deleted

    async def _soft_delete_cells_by_entity_filters(
        self, matrix_id: int, entity_set_filters: List
    ) -> Tuple[int, int]:
        """Soft delete cells and entity set members that reference specified entities (role-agnostic).

        IMPORTANT: Entity set members are ALWAYS deleted, even if no cells are found.
        This ensures entities are removed from the UI even if all their cells were already deleted.

        Process:
        1. entity_ids → member_ids (via entity_set_members table)
        2. Soft delete the entity set members (ALWAYS)
        3. member_ids → cell_ids (via cell_entity_refs table)
        4. Soft delete cells (if any found)

        Returns:
            Tuple of (entities_deleted, cells_deleted)
        """
        cell_ids_set: set[int] = set()
        member_ids_to_delete: set[int] = set()

        for filter in entity_set_filters:
            # Step 1: Get member IDs for these entity IDs
            # NOTE: This uses the version that includes deleted=False filter,
            # so we only find non-deleted members to delete
            member_ids = await self.member_repo.get_member_ids_by_entity_ids(
                filter.entity_set_id, filter.entity_ids
            )

            if not member_ids:
                logger.warning(
                    f"No members found for entity_set_id={filter.entity_set_id}, "
                    f"entity_ids={filter.entity_ids} - may already be deleted"
                )
                continue

            # Track member IDs to delete
            member_ids_to_delete.update(member_ids)

            # Step 2: Get cells that reference these members (any role)
            found_cell_ids = await self.cell_ref_repo.get_cells_by_member_ids(
                matrix_id, filter.entity_set_id, member_ids
            )

            cell_ids_set.update(found_cell_ids)
            logger.info(
                f"Entity set filter (set_id={filter.entity_set_id}, "
                f"entity_ids={filter.entity_ids}): found {len(member_ids)} members and {len(found_cell_ids)} cells"
            )

        if not member_ids_to_delete:
            logger.info(
                "No members matched the entity filters for deletion (may already be deleted)"
            )
            return 0, 0

        logger.info(
            f"Preparing to soft delete: {len(member_ids_to_delete)} members and {len(cell_ids_set)} cells"
        )
        logger.info(f"Member IDs to delete: {list(member_ids_to_delete)}")
        logger.info(f"Cell IDs to delete: {list(cell_ids_set)}")

        # CRITICAL: Soft delete the entity set members FIRST and ALWAYS
        # This ensures they disappear from the UI even if cells are already deleted
        member_count = 0
        if member_ids_to_delete:
            for member_id in member_ids_to_delete:
                deleted = await self.member_repo.soft_delete(member_id)
                if deleted:
                    member_count += 1
            logger.info(
                f"Soft deleted {member_count} entity set members (attempted {len(member_ids_to_delete)})"
            )

        # Soft delete the cells (if any found)
        cell_count = 0
        if cell_ids_set:
            cell_count = await self.matrix_cell_repo.bulk_soft_delete_by_cell_ids(
                list(cell_ids_set)
            )
            logger.info(
                f"Soft deleted {cell_count} cells (attempted {len(cell_ids_set)})"
            )

        return member_count, cell_count

    async def _soft_delete_matrices(self, matrix_ids: List[int]) -> Tuple[int, int]:
        """Soft delete matrices and all their related cells.

        Entity set members are preserved as they may be shared across matrices.
        """
        # Get valid matrix IDs that exist and are not deleted
        valid_matrix_ids = await self.matrix_repo.get_valid_ids(matrix_ids)

        if not valid_matrix_ids:
            logger.warning("No valid matrices found for deletion")
            return 0, 0

        # Soft delete matrices
        matrix_count = await self.matrix_repo.bulk_soft_delete(valid_matrix_ids)

        # Soft delete all matrix cells in these matrices
        cell_count = await self.matrix_cell_repo.bulk_soft_delete_by_matrix_ids(
            valid_matrix_ids
        )

        logger.info(
            f"Soft deleted {matrix_count} matrices and {cell_count} related cells"
        )
        return matrix_count, cell_count


def get_soft_delete_service(db_session: AsyncSession) -> SoftDeleteService:
    """Get soft delete service instance."""
    return SoftDeleteService(db_session)
