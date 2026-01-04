"""
Repository for matrix cell entity references.

Manages the matrix_cell_entity_refs table, which stores N-dimensional
coordinates for cells using entity set members and roles.
"""

from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import and_

from common.repositories.base import BaseRepository
from packages.matrices.models.database.matrix_entity_set import (
    MatrixCellEntityReferenceEntity,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixCellEntityReferenceModel,
    MatrixCellEntityReferenceCreateModel,
)
from packages.matrices.models.domain.matrix_enums import EntityRole
from common.core.otel_axiom_exporter import trace_span, get_logger
from sqlalchemy import exists

logger = get_logger(__name__)


class CellEntityReferenceRepository(
    BaseRepository[MatrixCellEntityReferenceEntity, MatrixCellEntityReferenceModel]
):
    """Repository for managing cell entity references (N-dimensional coordinates)."""

    def __init__(self):
        super().__init__(
            MatrixCellEntityReferenceEntity,
            MatrixCellEntityReferenceModel,
        )

    @trace_span
    async def get_by_cell_id(
        self, cell_id: int, company_id: Optional[int] = None
    ) -> List[MatrixCellEntityReferenceModel]:
        """Get all entity references for a cell, ordered by entity_order.

        Returns the N-dimensional coordinates of the cell.
        """
        async with self._get_session() as session:
            query = (
                select(self.entity_class)
                .where(self.entity_class.matrix_cell_id == cell_id)
                .order_by(self.entity_class.entity_order)
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_cell_id_and_role(
        self, cell_id: int, role: EntityRole, company_id: Optional[int] = None
    ) -> Optional[MatrixCellEntityReferenceModel]:
        """Get entity reference for a cell by role (identifies the axis)."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.matrix_cell_id == cell_id,
                self.entity_class.role == role.value,
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_cells_by_entity_member(
        self,
        matrix_id: int,
        entity_set_id: int,
        entity_set_member_id: int,
        role: EntityRole,
        company_id: Optional[int] = None,
    ) -> List[int]:
        """Get all cell IDs that reference a specific entity member with a specific role.

        Used for finding all cells affected by entity changes.
        Role is REQUIRED for proper axis identification.

        Returns: List of cell IDs
        """
        async with self._get_session() as session:
            query = select(self.entity_class.matrix_cell_id).where(
                and_(
                    self.entity_class.matrix_id == matrix_id,
                    self.entity_class.entity_set_id == entity_set_id,
                    self.entity_class.entity_set_member_id == entity_set_member_id,
                    self.entity_class.role == role.value,
                )
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def create_reference(
        self, create_model: MatrixCellEntityReferenceCreateModel
    ) -> MatrixCellEntityReferenceModel:
        """Create a new cell entity reference."""
        return await self.create(create_model)

    @trace_span
    async def create_references_batch(
        self, create_models: List[MatrixCellEntityReferenceCreateModel]
    ) -> List[MatrixCellEntityReferenceModel]:
        """Create multiple cell entity references in a batch using bulk insert.

        Used by strategies when creating cells with N-dimensional coordinates.
        Uses the base repository's bulk_create_from_models which does a single insert.
        """
        return await self.bulk_create_from_models(create_models)

    @trace_span
    async def get_by_matrix_id(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixCellEntityReferenceModel]:
        """Get all entity references for a matrix."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.matrix_id == matrix_id,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_by_cell_ids_bulk(
        self, cell_ids: List[int], company_id: Optional[int] = None
    ) -> List[MatrixCellEntityReferenceModel]:
        """Bulk load entity references for multiple cells.

        Returns all entity references for the given cell IDs.
        Caller should group by cell_id if needed.
        """
        if not cell_ids:
            return []

        async with self._get_session() as session:
            query = (
                select(self.entity_class)
                .where(self.entity_class.matrix_cell_id.in_(cell_ids))
                .order_by(
                    self.entity_class.matrix_cell_id, self.entity_class.entity_order
                )
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_cells_by_member_ids(
        self,
        matrix_id: int,
        entity_set_id: int,
        member_ids: List[int],
        company_id: Optional[int] = None,
    ) -> List[int]:
        """Get all cell IDs that reference any of the given members (role-agnostic).

        Used for reprocessing/soft-delete where we don't care about roles.
        Returns cells where the member appears in ANY role.

        Returns: List of unique cell IDs
        """
        if not member_ids:
            return []

        async with self._get_session() as session:
            query = (
                select(self.entity_class.matrix_cell_id)
                .where(
                    and_(
                        self.entity_class.matrix_id == matrix_id,
                        self.entity_class.entity_set_id == entity_set_id,
                        self.entity_class.entity_set_member_id.in_(member_ids),
                        self.entity_class.deleted == False,  # noqa
                    )
                )
                .distinct()
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def get_cells_by_member_ids_with_role(
        self,
        matrix_id: int,
        entity_set_id: int,
        member_ids: List[int],
        role: EntityRole,
        company_id: Optional[int] = None,
    ) -> List[int]:
        """Get all cell IDs that reference any of the given members with a specific role.

        Role-aware version for batch queries where we need to respect axis positions.
        Returns cells where the member appears in the SPECIFIED role only.

        Returns: List of unique cell IDs
        """
        if not member_ids:
            return []

        async with self._get_session() as session:
            query = (
                select(self.entity_class.matrix_cell_id)
                .where(
                    and_(
                        self.entity_class.matrix_id == matrix_id,
                        self.entity_class.entity_set_id == entity_set_id,
                        self.entity_class.entity_set_member_id.in_(member_ids),
                        self.entity_class.role == role.value,
                    )
                )
                .distinct()
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def members_have_cells_in_matrix(
        self,
        matrix_id: int,
        member_ids: List[int],
        company_id: Optional[int] = None,
    ) -> bool:
        """Fast check if any entity set members have cells in a matrix.

        This is O(1) with proper indices and avoids loading all refs.
        Used for fast-path deduplication: new entities have no members with cells.

        Args:
            matrix_id: The matrix ID
            member_ids: List of entity set member IDs to check
            company_id: Optional company filter

        Returns:
            True if any member has at least one cell, False otherwise
        """
        if not member_ids:
            return False

        async with self._get_session() as session:
            # Check if any cells reference these members
            query = select(
                exists().where(
                    and_(
                        self.entity_class.matrix_id == matrix_id,
                        self.entity_class.entity_set_member_id.in_(member_ids),
                        self.entity_class.deleted == False,  # noqa
                    )
                )
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            return result.scalar()

    @trace_span
    async def get_cell_combinations_for_members(
        self,
        matrix_id: int,
        member_ids: List[int],
        company_id: Optional[int] = None,
    ) -> set:
        """Get existing cell combinations that reference specific entity set members.

        Only loads cells that reference these members, not all cells in the matrix.
        For a new document in a 4000-cell matrix, this loads ~0 cells.
        For an existing document, this loads only its ~50 cells (not all 4000).

        Args:
            matrix_id: The matrix ID
            member_ids: List of entity set member IDs to find cells for
            company_id: Optional company filter

        Returns:
            Set of tuples representing existing cell combinations
        """
        if not member_ids:
            return set()

        async with self._get_session() as session:
            # Get all cells that reference any of these members
            query = (
                select(self.entity_class.matrix_cell_id)
                .where(
                    self.entity_class.matrix_id == matrix_id,
                    self.entity_class.entity_set_member_id.in_(member_ids),
                    self.entity_class.deleted == False,  # noqa
                )
                .distinct()
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            cell_ids = [row[0] for row in result.fetchall()]

            if not cell_ids:
                return set()

            logger.info(
                f"Loading refs for {len(cell_ids)} cells that reference {len(member_ids)} members"
            )

            # Now load all refs for just these cells
            refs_query = (
                select(
                    self.entity_class.matrix_cell_id,
                    self.entity_class.role,
                    self.entity_class.entity_set_id,
                    self.entity_class.entity_set_member_id,
                )
                .where(
                    self.entity_class.matrix_cell_id.in_(cell_ids),
                    self.entity_class.deleted == False,  # noqa
                )
                .order_by(self.entity_class.matrix_cell_id)
            )

            result = await session.execute(refs_query)
            rows = result.fetchall()

            logger.info(f"Loaded {len(rows)} entity refs for deduplication")

            # Group by cell and build combination keys
            refs_by_cell = {}
            for cell_id, role, entity_set_id, member_id in rows:
                if cell_id not in refs_by_cell:
                    refs_by_cell[cell_id] = []
                refs_by_cell[cell_id].append((role, entity_set_id, member_id))

            existing_combos = set()
            for cell_id, refs in refs_by_cell.items():
                key = tuple(sorted(refs))
                existing_combos.add(key)

            logger.info(f"Found {len(existing_combos)} existing cell combinations")
            return existing_combos

    @trace_span
    async def delete_by_cell_id(
        self, cell_id: int, company_id: Optional[int] = None
    ) -> None:
        """Delete all entity references for a cell.

        Used when deleting or regenerating a cell.
        """
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.matrix_cell_id == cell_id
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()

            for entity in entities:
                await session.delete(entity)
