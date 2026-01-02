"""
Cross-correlation strategy: document pairs × questions (3D).

Creates one cell for each non-diagonal pair of documents × each question.
For N documents, generates N×(N-1) pairs (all pairs except self-comparisons).
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


class CrossCorrelationStrategy(BaseCellCreationStrategy):
    """Strategy for cross-correlation: document pairs × questions.

    Entity sets:
    - Documents (used for both LEFT and RIGHT roles)
    - Questions (QUESTION role)

    Cell structure:
    - Two documents (LEFT, RIGHT) from same set + one question = CORRELATION cell type
    - Excludes diagonal (self-comparisons)
    """

    def get_entity_set_definitions(self) -> List[EntitySetDefinition]:
        """Define entity sets for cross-correlation matrix."""
        return [
            EntitySetDefinition(
                name="Documents",
                entity_type=EntityType.DOCUMENT,
                description="Documents to compare (used as both LEFT and RIGHT)",
            ),
            EntitySetDefinition(
                name="Questions",
                entity_type=EntityType.QUESTION,
                description="Questions to answer about document pairs",
            ),
        ]

    def get_matrix_type(self) -> MatrixType:
        """Return CROSS_CORRELATION matrix type."""
        return MatrixType.CROSS_CORRELATION

    def get_cell_type(self) -> CellType:
        """Return CORRELATION cell type."""
        return CellType.CORRELATION

    def get_structure_metadata(self) -> MatrixStructureMetadata:
        """Return structure metadata for cross-correlation matrices."""
        return MatrixStructureMetadata(
            explanation=(
                "Cross-correlation matrix: document pairs × questions (3D). "
                "One entity set contains documents (used as both LEFT and RIGHT), another contains questions. "
                "Creates cells for all non-diagonal pairs (excludes self-comparisons). "
                "For N documents, generates N×(N-1) comparison pairs."
            ),
            roles_explanation={
                "LEFT": "First document in the comparison pair (from Documents entity set)",
                "RIGHT": "Second document in the comparison pair (from same Documents entity set)",
                "QUESTION": "Comparison question asking about the relationship between the two documents",
            },
            system_placeholders={
                "@{{LEFT}}": "System placeholder in questions that references the LEFT document during AI processing",
                "@{{RIGHT}}": "System placeholder in questions that references the RIGHT document during AI processing",
            },
            cell_structure=(
                "Each cell contains: 1 LEFT document, 1 RIGHT document (both from same entity set), "
                "1 comparison question, and an AI-generated answer comparing the two documents."
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
        """Create cells for a new entity in a cross-correlation matrix.

        Cross-correlation: document pairs × questions (same doc set used as LEFT and RIGHT)
        - New document: pair with ALL documents (including itself on opposite axis) × ALL questions
        - New question: pair with ALL document pairs × this question
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

        # Find document and question entity sets
        document_entity_set = next(
            (es for es in all_entity_sets if es.entity_type == EntityType.DOCUMENT),
            None,
        )
        question_entity_set = next(
            (es for es in all_entity_sets if es.entity_type == EntityType.QUESTION),
            None,
        )

        if not document_entity_set or not question_entity_set:
            raise ValueError(
                f"Cross-correlation matrix {matrix_id} requires DOCUMENT and QUESTION entity sets"
            )

        # Get ALL documents and questions
        document_members = await self.entity_set_service.get_entity_set_members(
            document_entity_set.id, company_id
        )
        document_ids = [m.entity_id for m in document_members]

        question_members = await self.entity_set_service.get_entity_set_members(
            question_entity_set.id, company_id
        )
        question_ids = [m.entity_id for m in question_members]

        # Get member mappings
        document_members_map = await self.entity_set_service.get_member_id_mappings(
            document_entity_set.id
        )
        question_members_map = await self.entity_set_service.get_member_id_mappings(
            question_entity_set.id
        )

        # Create cells based on what was added
        if new_entity_set.entity_type == EntityType.QUESTION:
            # New question: create cells for ALL document pairs × this question
            question_ids = [new_entity_id]
        elif new_entity_set.entity_type == EntityType.DOCUMENT:
            # New document: only create cells for pairs involving this document
            # We'll filter in the loop below
            pass

        # Generate all non-diagonal document pairs (all pairs except left == right)
        cell_models = []
        pair_count = 0

        for left_doc_id in document_ids:
            if left_doc_id not in document_members_map:
                logger.warning(
                    f"Document {left_doc_id} not found in entity set {document_entity_set.id}, skipping"
                )
                continue

            left_member_id = document_members_map[left_doc_id]

            for right_doc_id in document_ids:
                # Skip diagonal (self-comparisons)
                if left_doc_id == right_doc_id:
                    continue

                # NEW DOCUMENT OPTIMIZATION: If adding a document, only create pairs involving that document
                if new_entity_set.entity_type == EntityType.DOCUMENT:
                    if new_entity_id != left_doc_id and new_entity_id != right_doc_id:
                        continue

                if right_doc_id not in document_members_map:
                    logger.warning(
                        f"Document {right_doc_id} not found in entity set {document_entity_set.id}, skipping"
                    )
                    continue

                right_member_id = document_members_map[right_doc_id]
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
                            entity_set_id=document_entity_set.id,
                            entity_set_member_id=left_member_id,
                            entity_type=EntityType.DOCUMENT,
                            entity_id=left_doc_id,
                            role=EntityRole.LEFT,
                            entity_order=0,
                        ),
                        EntityReference(
                            entity_set_id=document_entity_set.id,
                            entity_set_member_id=right_member_id,
                            entity_type=EntityType.DOCUMENT,
                            entity_id=right_doc_id,
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
            f"Created {len(cell_models)} cross-correlation cell models "
            f"({pair_count} pairs × {len(question_ids)} questions)"
        )

        # SANITY CHECK: Validate cell count doesn't exceed theoretical maximum
        # Upper bound = product of OTHER entity sets
        if new_entity_set.entity_type == EntityType.DOCUMENT:
            # New doc appears as LEFT or RIGHT, pairs with all other docs × all questions
            # Conservative upper bound: 2×N×Q (N docs × Q questions, doc appears in 2 roles)
            max_cells = 2 * len(document_ids) * len(question_ids)
        else:
            # New question pairs with all document pairs
            # Conservative upper bound: N² (N docs used for both LEFT and RIGHT)
            max_cells = len(document_ids) * len(document_ids)

        if len(cell_models) > max_cells:
            raise ValueError(
                f"STRATEGY BUG: Cross-correlation generated {len(cell_models)} cells but maximum expected is {max_cells}. "
                f"Matrix has {len(document_ids)} docs, {len(question_ids)} questions. "
                f"New entity: {new_entity_set.entity_type.value} (id={new_entity_id})"
            )

        return cell_models

    @trace_span
    async def load_cell_data(self, cell_id: int, company_id: int) -> CellDataContext:
        """Load cell data for cross-correlation matrix.

        Cross-correlation cell has:
        - 1 document (LEFT role)
        - 1 document (RIGHT role) from same entity set
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
            matrix_type=MatrixType.CROSS_CORRELATION,
            documents=[left_doc, right_doc],
            question=question,
            entity_refs=entity_refs,
        )
