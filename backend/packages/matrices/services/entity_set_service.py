"""
Service for managing matrix entity sets and their members.

Provides business logic layer on top of entity set repositories.
Handles entity set creation, member management, and validation.
"""

from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.matrices.repositories.entity_set_repository import EntitySetRepository
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetModel,
    MatrixEntitySetCreateModel,
    MatrixEntitySetMemberModel,
    MatrixEntitySetMemberCreateModel,
    MatrixCellEntityReferenceModel,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class EntitySetService:
    """Service for handling entity set operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.entity_set_repo = EntitySetRepository()
        self.member_repo = EntitySetMemberRepository()
        self.reference_repo = CellEntityReferenceRepository()
        self.matrix_repo = MatrixRepository()

    @trace_span
    async def create_entity_set(
        self, create_model: MatrixEntitySetCreateModel
    ) -> MatrixEntitySetModel:
        """Create a new entity set for a matrix.

        Args:
            create_model: Entity set creation data

        Returns:
            Created entity set

        Raises:
            HTTPException: If matrix not found or entity set type already exists
        """
        logger.info(
            f"Creating entity set '{create_model.name}' for matrix {create_model.matrix_id}"
        )

        # Verify matrix exists and belongs to company
        matrix = await self.matrix_repo.get(
            create_model.matrix_id, create_model.company_id
        )
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

        # Note: We allow multiple entity sets with the same entity_type for correlation matrices
        # (e.g., LEFT and RIGHT document sets). Uniqueness is enforced by the set name if needed.

        # Create entity set
        entity_set = await self.entity_set_repo.create_entity_set(create_model)

        logger.info(f"Created entity set with ID: {entity_set.id}")
        return entity_set

    @trace_span
    async def get_entity_set(
        self, entity_set_id: int, company_id: Optional[int] = None
    ) -> Optional[MatrixEntitySetModel]:
        """Get an entity set by ID."""
        return await self.entity_set_repo.get(entity_set_id, company_id)

    @trace_span
    async def get_matrix_entity_sets(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixEntitySetModel]:
        """Get all entity sets for a matrix."""
        return await self.entity_set_repo.get_by_matrix_id(matrix_id, company_id)

    @trace_span
    async def get_entity_set_by_type(
        self, matrix_id: int, entity_type: EntityType, company_id: Optional[int] = None
    ) -> Optional[MatrixEntitySetModel]:
        """Get entity set for a matrix by entity type."""
        return await self.entity_set_repo.get_by_matrix_and_type(
            matrix_id, entity_type, company_id
        )

    @trace_span
    async def add_member_to_set(
        self, create_model: MatrixEntitySetMemberCreateModel
    ) -> MatrixEntitySetMemberModel:
        """Add a single member to an entity set.

        Args:
            create_model: Member creation data

        Returns:
            Created member

        Raises:
            HTTPException: If entity set not found or member already exists
        """
        logger.info(
            f"Adding entity {create_model.entity_id} to set {create_model.entity_set_id}"
        )

        # Verify entity set exists
        entity_set = await self.entity_set_repo.get(
            create_model.entity_set_id, create_model.company_id
        )
        if not entity_set:
            raise HTTPException(status_code=404, detail="Entity set not found")

        # Check if member already exists
        existing = await self.member_repo.get_member_by_entity_id(
            create_model.entity_set_id,
            create_model.entity_id,
            create_model.entity_type,
            create_model.company_id,
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Entity {create_model.entity_id} is already a member of this set",
            )

        # Add member
        member = await self.member_repo.add_member(create_model)

        logger.info(f"Added member with ID: {member.id}")
        return member

    @trace_span
    async def add_members_batch(
        self,
        entity_set_id: int,
        entity_ids: List[int],
        entity_type: EntityType,
        company_id: int,
    ) -> List[MatrixEntitySetMemberModel]:
        """Add multiple members to an entity set in a batch.

        Args:
            entity_set_id: Entity set to add members to
            entity_ids: List of entity IDs to add
            entity_type: Type of entities (DOCUMENT or QUESTION)
            company_id: Company ID for multi-tenancy

        Returns:
            List of created members

        Raises:
            HTTPException: If entity set not found
        """
        logger.info(f"Batch adding {len(entity_ids)} entities to set {entity_set_id}")

        # Verify entity set exists
        entity_set = await self.entity_set_repo.get(entity_set_id, company_id)
        if not entity_set:
            raise HTTPException(status_code=404, detail="Entity set not found")

        # Get existing members to determine order and avoid duplicates
        existing_members = await self.member_repo.get_by_entity_set_id(
            entity_set_id, company_id
        )
        existing_entity_ids = {m.entity_id for m in existing_members}
        next_order = len(existing_members)

        # Filter out duplicates
        new_entity_ids = [eid for eid in entity_ids if eid not in existing_entity_ids]

        if not new_entity_ids:
            logger.info("No new entities to add (all already exist)")
            return []

        # Create member models
        create_models = [
            MatrixEntitySetMemberCreateModel(
                entity_set_id=entity_set_id,
                company_id=company_id,
                entity_type=entity_type,
                entity_id=entity_id,
                member_order=next_order + i,
            )
            for i, entity_id in enumerate(new_entity_ids)
        ]

        # Add members
        members = await self.member_repo.add_members_batch(create_models)

        logger.info(f"Batch added {len(members)} members")
        return members

    @trace_span
    async def get_cell_entity_references_by_cell_id(
        self, cell_id
    ) -> [MatrixCellEntityReferenceModel]:
        return await self.reference_repo.get_by_cell_id(cell_id)

    @trace_span
    async def get_entity_set_members_by_ids(
        self, member_ids: [int]
    ) -> [MatrixEntitySetMemberModel]:
        return await self.member_repo.get_by_member_ids(member_ids)

    @trace_span
    async def get_entity_set_members(
        self, entity_set_id: int, company_id: Optional[int] = None
    ) -> List[MatrixEntitySetMemberModel]:
        """Get all members of an entity set, ordered by member_order."""
        return await self.member_repo.get_by_entity_set_id(entity_set_id, company_id)

    @trace_span
    async def get_entity_sets_with_members(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[tuple[MatrixEntitySetModel, List[MatrixEntitySetMemberModel]]]:
        """Get all entity sets for a matrix with their members populated.

        This is used by the frontend to get complete entity set information
        for constructing tile queries and understanding matrix dimensionality.

        Returns:
            List of tuples (entity_set, members)
        """
        # Get all entity sets for the matrix
        entity_sets = await self.get_matrix_entity_sets(matrix_id, company_id)

        # Fetch members for each entity set
        result = []
        for entity_set in entity_sets:
            members = await self.get_entity_set_members(entity_set.id, company_id)
            result.append((entity_set, members))

        return result

    @trace_span
    async def get_member_id_mappings(
        self, entity_set_id: int, company_id: Optional[int] = None
    ) -> Dict[int, int]:
        """Get mapping of entity_id -> member_id for an entity set.

        Used by strategies when creating cells.

        Returns:
            Dictionary mapping entity_id to member_id
        """
        return await self.member_repo.get_member_id_mappings(entity_set_id, company_id)

    @trace_span
    async def remove_member_from_set(
        self, entity_set_id: int, member_id: int, company_id: int
    ) -> bool:
        """Remove a member from an entity set (soft delete).

        Note: This will also affect all cells that reference this member.
        Consider whether cells should be deleted or marked invalid.

        Args:
            entity_set_id: Entity set ID
            member_id: Member ID to remove
            company_id: Company ID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If entity set not found
        """
        logger.info(f"Removing member {member_id} from set {entity_set_id}")

        # Verify entity set exists
        entity_set = await self.entity_set_repo.get(entity_set_id, company_id)
        if not entity_set:
            raise HTTPException(status_code=404, detail="Entity set not found")

        # Soft delete the member
        result = await self.member_repo.soft_delete(member_id)

        if result:
            logger.info(f"Removed member {member_id}")
            # Note: In a full implementation, you might want to handle
            # cells that reference this member (delete them, mark invalid, etc.)
        else:
            logger.warning(f"Member {member_id} not found")

        return result

    @trace_span
    async def update_member_label(
        self, entity_set_id: int, member_id: int, label: Optional[str], company_id: int
    ) -> MatrixEntitySetMemberModel:
        """Update the label of an entity set member.

        Args:
            entity_set_id: Entity set ID
            member_id: Member ID to update
            label: New label value (can be None to clear)
            company_id: Company ID

        Returns:
            Updated member

        Raises:
            HTTPException: If entity set or member not found
        """
        logger.info(f"Updating label for member {member_id} in set {entity_set_id}")

        # Verify entity set exists
        entity_set = await self.entity_set_repo.get(entity_set_id, company_id)
        if not entity_set:
            raise HTTPException(status_code=404, detail="Entity set not found")

        # Update label
        updated_member = await self.member_repo.update_label(
            member_id, label, company_id
        )

        if not updated_member:
            raise HTTPException(status_code=404, detail="Entity set member not found")

        logger.info(f"Updated label for member {member_id} to: {label}")
        return updated_member

    @trace_span
    async def get_all_members_by_type(
        self, matrix_id: int, entity_type: EntityType, company_id: int
    ) -> List[MatrixEntitySetMemberModel]:
        """Get all members of a specific entity type across all entity sets in a matrix.

        This is useful for getting all documents or all questions in a matrix,
        regardless of which entity set they belong to (important for correlation matrices
        which may have multiple entity sets of the same type, e.g., LEFT and RIGHT documents).

        Args:
            matrix_id: Matrix ID
            entity_type: Type of entities to retrieve (DOCUMENT or QUESTION)
            company_id: Company ID

        Returns:
            List of all members matching the entity type, ordered by entity set and member order
        """
        logger.info(f"Getting all {entity_type} members for matrix {matrix_id}")

        # Get all entity sets for the matrix
        entity_sets_with_members = await self.get_entity_sets_with_members(
            matrix_id, company_id
        )

        # Filter to entity sets of the requested type
        matching_entity_sets = [
            (es, members)
            for es, members in entity_sets_with_members
            if es.entity_type == entity_type
        ]

        if not matching_entity_sets:
            logger.info(f"No {entity_type} entity sets found for matrix {matrix_id}")
            return []

        # Collect all members from all matching entity sets
        all_members = []
        for entity_set, _ in matching_entity_sets:
            members = await self.member_repo.get_by_entity_set_id(
                entity_set.id, company_id
            )
            all_members.extend(members)

        logger.info(
            f"Found {len(all_members)} {entity_type} members for matrix {matrix_id}"
        )
        return all_members

    @trace_span
    async def load_entity_refs_for_cells(
        self, cell_ids: List[int], company_id: Optional[int] = None
    ) -> tuple[
        Dict[int, List[MatrixCellEntityReferenceModel]],
        Dict[int, MatrixEntitySetMemberModel],
    ]:
        """Load entity references for a list of cell IDs with member data.

        Args:
            cell_ids: List of cell IDs to load entity refs for
            company_id: Optional company ID for filtering

        Returns:
            Tuple of (entity_refs_by_cell, members_by_id) where:
            - entity_refs_by_cell: Dictionary mapping cell_id to list of entity references
            - members_by_id: Dictionary mapping member_id to entity set member
        """
        if not cell_ids:
            return {}, {}

        # Load all entity refs for these cells
        entity_refs = await self.reference_repo.get_by_cell_ids_bulk(
            cell_ids, company_id
        )

        # Collect unique member IDs
        member_ids = list(set(ref.entity_set_member_id for ref in entity_refs))

        # Load all members
        members_by_id: Dict[int, MatrixEntitySetMemberModel] = {}
        if member_ids:
            for member_id in member_ids:
                member = await self.member_repo.get(member_id, company_id)
                if member:
                    members_by_id[member_id] = member

        # Group entity refs by cell_id
        entity_refs_by_cell: Dict[int, List[MatrixCellEntityReferenceModel]] = {}
        for ref in entity_refs:
            if ref.matrix_cell_id not in entity_refs_by_cell:
                entity_refs_by_cell[ref.matrix_cell_id] = []
            entity_refs_by_cell[ref.matrix_cell_id].append(ref)

        return entity_refs_by_cell, members_by_id

    @trace_span
    async def duplicate_entity_set_members(
        self,
        source_entity_set_id: int,
        target_entity_set_id: int,
        company_id: int,
        entity_id_mapping: Optional[Dict[int, int]] = None,
    ) -> int:
        """Duplicate members from source entity set to target entity set.

        Args:
            source_entity_set_id: Source entity set to copy from
            target_entity_set_id: Target entity set to copy to
            company_id: Company ID for multi-tenancy
            entity_id_mapping: Optional mapping of old entity ID -> new entity ID (for questions)

        Returns:
            Number of members copied
        """
        logger.info(
            f"Duplicating members from entity set {source_entity_set_id} to {target_entity_set_id}"
        )

        # Get source entity set to determine type
        source_entity_set = await self.entity_set_repo.get(
            source_entity_set_id, company_id
        )
        if not source_entity_set:
            logger.warning(f"Source entity set {source_entity_set_id} not found")
            return 0

        # Get all members from source
        source_members = await self.member_repo.get_by_entity_set_id(
            source_entity_set_id, company_id
        )

        if not source_members:
            logger.info(
                f"No members to duplicate from entity set {source_entity_set_id}"
            )
            return 0

        # Map entity IDs (use mapping if provided, otherwise use original IDs)
        new_entity_ids = []
        for member in source_members:
            if entity_id_mapping and member.entity_id in entity_id_mapping:
                new_entity_ids.append(entity_id_mapping[member.entity_id])
            else:
                new_entity_ids.append(member.entity_id)

        # Add members to target entity set
        new_members = await self.add_members_batch(
            target_entity_set_id,
            new_entity_ids,
            source_entity_set.entity_type,
            company_id,
        )

        logger.info(f"Copied {len(new_members)} members to target entity set")
        return len(new_members)


def get_entity_set_service(db_session: AsyncSession) -> EntitySetService:
    """Get entity set service instance."""
    return EntitySetService(db_session)
