"""
Generic correlation strategy: left axis × right axis × questions (3D).

Creates one cell for each pair combination from two different document axes.
For N left documents and M right documents, generates N×M pairs × questions.
"""

from typing import List
from packages.matrices.models.domain.matrix import MatrixCellCreateModel
from packages.matrices.models.domain.matrix_enums import (
    MatrixCellStatus,
    CellType,
    MatrixType,
    EntityType,
    EntityRole,
)
from packages.matrices.models.domain.matrix_entity_set import EntityReference
from .base_strategy import BaseCellCreationStrategy
from .models import EntitySetDefinition, CellDataContext, MatrixStructureMetadata
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class GenericCorrelationStrategy(BaseCellCreationStrategy):
    """Strategy for generic correlation: left documents × right documents × questions.

    Entity sets:
    - Left Documents (LEFT role)
    - Right Documents (RIGHT role)
    - Questions (QUESTION role)

    Cell structure:
    - One LEFT document + one RIGHT document + one question = CORRELATION cell type
    """

    def get_entity_set_definitions(self) -> List[EntitySetDefinition]:
        """Define entity sets for generic correlation matrix."""
        return [
            EntitySetDefinition(
                name="Left Documents",
                entity_type=EntityType.DOCUMENT,
                description="Documents for the left axis",
            ),
            EntitySetDefinition(
                name="Right Documents",
                entity_type=EntityType.DOCUMENT,
                description="Documents for the right axis",
            ),
            EntitySetDefinition(
                name="Questions",
                entity_type=EntityType.QUESTION,
                description="Questions to answer about document pairs",
            ),
        ]

    def get_matrix_type(self) -> MatrixType:
        """Return GENERIC_CORRELATION matrix type."""
        return MatrixType.GENERIC_CORRELATION

    def get_cell_type(self) -> CellType:
        """Return CORRELATION cell type."""
        return CellType.CORRELATION

    def get_structure_metadata(self) -> MatrixStructureMetadata:
        """Return structure metadata for generic correlation matrices."""
        return MatrixStructureMetadata(
            explanation=(
                "Generic correlation matrix: left documents × right documents × questions (3D). "
                "Two separate entity sets: 'Left Documents' and 'Right Documents', plus Questions. "
                "Creates cells for all combinations: N left docs × M right docs × Q questions. "
                "Used when comparing documents from two different collections."
            ),
            roles_explanation={
                "LEFT": "Document from the left axis (from 'Left Documents' entity set)",
                "RIGHT": "Document from the right axis (from 'Right Documents' entity set)",
                "QUESTION": "Comparison question asking about the relationship between left and right documents",
            },
            system_placeholders={
                "@{{LEFT}}": "System placeholder in questions that references the LEFT document during AI processing",
                "@{{RIGHT}}": "System placeholder in questions that references the RIGHT document during AI processing",
            },
            cell_structure=(
                "Each cell contains: 1 LEFT document (from left entity set), 1 RIGHT document (from right entity set), "
                "1 comparison question, and an AI-generated answer comparing the two documents from different sets."
            ),
        )

    @trace_span
    async def create_cells_for_new_entity(
        self,
        matrix_id: int,
        company_id: int,
        new_entity_id: int,
        entity_set_id: int,
    ) -> List[MatrixCellCreateModel]:
        """Create cells for a new entity in a generic correlation matrix.

        Generic correlation: LEFT docs × RIGHT docs × questions (two separate doc entity sets)
        - New LEFT doc: pair with ALL RIGHT docs × ALL questions
        - New RIGHT doc: pair with ALL LEFT docs × ALL questions
        - New question: pair with ALL LEFT × ALL RIGHT × this question
        """
        # Get the entity set the new entity belongs to
        new_entity_set = await self.entity_set_service.get_entity_set(
            entity_set_id, company_id
        )
        if not new_entity_set:
            raise ValueError(f"Entity set {entity_set_id} not found")

        # Get all entity sets for this matrix
        all_entity_sets = await self.entity_set_service.get_matrix_entity_sets(
            matrix_id, company_id
        )

        # Find LEFT, RIGHT, and QUESTION entity sets by name (fickle but works for now)
        left_entity_set = next(
            (
                es
                for es in all_entity_sets
                if es.entity_type == EntityType.DOCUMENT and "left" in es.name.lower()
            ),
            None,
        )
        right_entity_set = next(
            (
                es
                for es in all_entity_sets
                if es.entity_type == EntityType.DOCUMENT and "right" in es.name.lower()
            ),
            None,
        )
        question_entity_set = next(
            (es for es in all_entity_sets if es.entity_type == EntityType.QUESTION),
            None,
        )

        if not left_entity_set or not right_entity_set or not question_entity_set:
            raise ValueError(
                f"Generic correlation matrix {matrix_id} requires LEFT, RIGHT, and QUESTION entity sets. "
                f"Found: LEFT={left_entity_set is not None}, RIGHT={right_entity_set is not None}, QUESTION={question_entity_set is not None}"
            )

        # Determine which entity IDs to use based on what was added
        if new_entity_set.id == left_entity_set.id:
            # New LEFT document: pair with ALL RIGHT docs × ALL questions
            left_ids = [new_entity_id]
            right_members = await self.entity_set_service.get_entity_set_members(
                right_entity_set.id, company_id
            )
            right_ids = [m.entity_id for m in right_members]
            question_members = await self.entity_set_service.get_entity_set_members(
                question_entity_set.id, company_id
            )
            question_ids = [m.entity_id for m in question_members]

            logger.info(
                f"New LEFT document {new_entity_id}: pairing with {len(right_ids)} RIGHT docs × {len(question_ids)} questions"
            )

        elif new_entity_set.id == right_entity_set.id:
            # New RIGHT document: pair with ALL LEFT docs × ALL questions
            left_members = await self.entity_set_service.get_entity_set_members(
                left_entity_set.id, company_id
            )
            left_ids = [m.entity_id for m in left_members]
            right_ids = [new_entity_id]
            question_members = await self.entity_set_service.get_entity_set_members(
                question_entity_set.id, company_id
            )
            question_ids = [m.entity_id for m in question_members]

            logger.info(
                f"New RIGHT document {new_entity_id}: pairing with {len(left_ids)} LEFT docs × {len(question_ids)} questions"
            )

        else:
            # New question: pair with ALL LEFT × ALL RIGHT × this question
            left_members = await self.entity_set_service.get_entity_set_members(
                left_entity_set.id, company_id
            )
            left_ids = [m.entity_id for m in left_members]
            right_members = await self.entity_set_service.get_entity_set_members(
                right_entity_set.id, company_id
            )
            right_ids = [m.entity_id for m in right_members]
            question_ids = [new_entity_id]

            logger.info(
                f"New question {new_entity_id}: pairing with {len(left_ids)} LEFT × {len(right_ids)} RIGHT docs"
            )

        # Get member mappings
        left_members_map = await self.entity_set_service.get_member_id_mappings(
            left_entity_set.id
        )
        right_members_map = await self.entity_set_service.get_member_id_mappings(
            right_entity_set.id
        )
        question_members_map = await self.entity_set_service.get_member_id_mappings(
            question_entity_set.id
        )

        # Generate all combinations of left × right × questions
        cell_models = []
        pair_count = 0

        for left_id in left_ids:
            if left_id not in left_members_map:
                logger.warning(
                    f"LEFT document {left_id} not found in entity set {left_entity_set.id}, skipping"
                )
                continue

            left_member_id = left_members_map[left_id]

            for right_id in right_ids:
                if right_id not in right_members_map:
                    logger.warning(
                        f"RIGHT document {right_id} not found in entity set {right_entity_set.id}, skipping"
                    )
                    continue

                right_member_id = right_members_map[right_id]
                pair_count += 1

                # For each pair, create cells for all questions
                for question_id in question_ids:
                    if question_id not in question_members_map:
                        logger.warning(
                            f"Question {question_id} not found in entity set {question_entity_set.id}, skipping"
                        )
                        continue

                    question_member_id = question_members_map[question_id]

                    # Create entity references for this cell (3D coordinates)
                    entity_refs = [
                        EntityReference(
                            entity_set_id=left_entity_set.id,
                            entity_set_member_id=left_member_id,
                            entity_type=EntityType.DOCUMENT,
                            entity_id=left_id,
                            role=EntityRole.LEFT,
                            entity_order=0,
                        ),
                        EntityReference(
                            entity_set_id=right_entity_set.id,
                            entity_set_member_id=right_member_id,
                            entity_type=EntityType.DOCUMENT,
                            entity_id=right_id,
                            role=EntityRole.RIGHT,
                            entity_order=1,
                        ),
                        EntityReference(
                            entity_set_id=question_entity_set.id,
                            entity_set_member_id=question_member_id,
                            entity_type=EntityType.QUESTION,
                            entity_id=question_id,
                            role=EntityRole.QUESTION,
                            entity_order=2,
                        ),
                    ]

                    cell_model = MatrixCellCreateModel(
                        matrix_id=matrix_id,
                        company_id=company_id,
                        status=MatrixCellStatus.PENDING.value,
                        cell_type=CellType.CORRELATION,
                        cell_signature=self._compute_cell_signature(entity_refs),
                        entity_refs=entity_refs,
                    )
                    cell_models.append(cell_model)

        logger.info(
            f"Created {len(cell_models)} generic correlation cell models "
            f"({len(left_ids)} left × {len(right_ids)} right = {pair_count} pairs × {len(question_ids)} questions)"
        )

        # SANITY CHECK: Validate cell count doesn't exceed theoretical maximum
        # Upper bound = product of OTHER entity sets
        if new_entity_set.id == left_entity_set.id:
            # New LEFT doc pairs with all RIGHT docs × all questions
            max_cells = len(right_ids) * len(question_ids)
        elif new_entity_set.id == right_entity_set.id:
            # New RIGHT doc pairs with all LEFT docs × all questions
            max_cells = len(left_ids) * len(question_ids)
        else:
            # New question pairs with all LEFT × all RIGHT
            max_cells = len(left_ids) * len(right_ids)

        if len(cell_models) > max_cells:
            raise ValueError(
                f"STRATEGY BUG: Generic correlation generated {len(cell_models)} cells but maximum expected is {max_cells}. "
                f"Matrix has {len(left_ids)} left docs, {len(right_ids)} right docs, {len(question_ids)} questions. "
                f"New entity: {new_entity_set.entity_type.value} in set '{new_entity_set.name}' (id={new_entity_id})"
            )

        return cell_models

    @trace_span
    async def load_cell_data(self, cell_id: int, company_id: int) -> CellDataContext:
        """Load cell data for generic correlation matrix.

        Generic correlation cell has:
        - 1 document (LEFT role) from left entity set
        - 1 document (RIGHT role) from right entity set
        - 1 question (QUESTION role)
        """
        # Load cell and entity refs
        cell, entity_refs = await self._get_cell_with_refs(cell_id, company_id)

        # Find document and question refs
        left_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.LEFT), None
        )
        right_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.RIGHT), None
        )
        question_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.QUESTION), None
        )

        if not left_ref or not right_ref or not question_ref:
            raise ValueError(
                f"Cell {cell_id} missing LEFT, RIGHT, or QUESTION reference"
            )

        # Load documents and question using shared utilities
        left_doc = await self._load_document(
            left_ref.entity_id, company_id, EntityRole.LEFT, left_ref
        )
        right_doc = await self._load_document(
            right_ref.entity_id, company_id, EntityRole.RIGHT, right_ref
        )
        question = await self._load_question(
            question_ref.entity_id, company_id, question_ref
        )

        return CellDataContext(
            cell_id=cell.id,
            matrix_id=cell.matrix_id,
            cell_type=CellType.CORRELATION,
            matrix_type=MatrixType.GENERIC_CORRELATION,
            documents=[left_doc, right_doc],
            question=question,
            entity_refs=entity_refs,
        )
