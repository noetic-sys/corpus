"""
Standard matrix strategy: documents × questions (2D).

Creates one cell for each combination of document and question.
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


class StandardMatrixStrategy(BaseCellCreationStrategy):
    """Strategy for standard matrices: documents × questions.

    Entity sets:
    - Documents (DOCUMENT role)
    - Questions (QUESTION role)

    Cell structure:
    - One document + one question = STANDARD cell type
    """

    def get_entity_set_definitions(self) -> List[EntitySetDefinition]:
        """Define entity sets for standard matrix."""
        return [
            EntitySetDefinition(
                name="Documents",
                entity_type=EntityType.DOCUMENT,
                description="Documents to analyze",
            ),
            EntitySetDefinition(
                name="Questions",
                entity_type=EntityType.QUESTION,
                description="Questions to answer",
            ),
        ]

    def get_matrix_type(self) -> MatrixType:
        """Return STANDARD matrix type."""
        return MatrixType.STANDARD

    def get_cell_type(self) -> CellType:
        """Return STANDARD cell type."""
        return CellType.STANDARD

    def get_structure_metadata(self) -> MatrixStructureMetadata:
        """Return structure metadata for standard matrices."""
        return MatrixStructureMetadata(
            explanation=(
                "Standard matrix: documents × questions (2D). "
                "One entity set contains documents, another contains questions. "
                "Each cell pairs one document with one question."
            ),
            roles_explanation={
                "DOCUMENT": "The document being analyzed (from Documents entity set)",
                "QUESTION": "The question being answered (from Questions entity set)",
            },
            system_placeholders={},  # Standard matrices don't use @{{}} placeholders
            cell_structure=(
                "Each cell contains: 1 document (DOCUMENT role), 1 question (QUESTION role), "
                "and an AI-generated answer based on analyzing the document against the question."
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
        """Create cells for a new entity in a standard matrix.

        Standard matrix: document × question
        - New document: pair with ALL questions
        - New question: pair with ALL documents
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
                f"Standard matrix {matrix_id} requires DOCUMENT and QUESTION entity sets"
            )

        # Determine which entity IDs to use based on what was added
        if new_entity_set.entity_type == EntityType.DOCUMENT:
            # New document: pair with ALL questions
            document_ids = [new_entity_id]
            question_members = await self.entity_set_service.get_entity_set_members(
                question_entity_set.id, company_id
            )
            question_ids = [m.entity_id for m in question_members]
        else:
            # New question: pair with ALL documents
            document_members = await self.entity_set_service.get_entity_set_members(
                document_entity_set.id, company_id
            )
            document_ids = [m.entity_id for m in document_members]
            question_ids = [new_entity_id]

        # Get member mappings
        document_members_map = await self.entity_set_service.get_member_id_mappings(
            document_entity_set.id
        )
        question_members_map = await self.entity_set_service.get_member_id_mappings(
            question_entity_set.id
        )

        # Create cells
        cell_models = []
        for document_id in document_ids:
            if document_id not in document_members_map:
                logger.warning(
                    f"Document {document_id} not found in entity set {document_entity_set.id}, skipping"
                )
                continue

            document_member_id = document_members_map[document_id]

            for question_id in question_ids:
                if question_id not in question_members_map:
                    logger.warning(
                        f"Question {question_id} not found in entity set {question_entity_set.id}, skipping"
                    )
                    continue

                question_member_id = question_members_map[question_id]

                entity_refs = [
                    EntityReference(
                        entity_set_id=document_entity_set.id,
                        entity_set_member_id=document_member_id,
                        entity_type=EntityType.DOCUMENT,
                        entity_id=document_id,
                        role=EntityRole.DOCUMENT,
                        entity_order=0,
                    ),
                    EntityReference(
                        entity_set_id=question_entity_set.id,
                        entity_set_member_id=question_member_id,
                        entity_type=EntityType.QUESTION,
                        entity_id=question_id,
                        role=EntityRole.QUESTION,
                        entity_order=1,
                    ),
                ]

                cell_model = MatrixCellCreateModel(
                    matrix_id=matrix_id,
                    company_id=company_id,
                    status=MatrixCellStatus.PENDING.value,
                    cell_type=CellType.STANDARD,
                    cell_signature=self._compute_cell_signature(entity_refs),
                    entity_refs=entity_refs,
                )
                cell_models.append(cell_model)

        logger.info(
            f"Created {len(cell_models)} standard cell models "
            f"({len(document_ids)} docs × {len(question_ids)} questions)"
        )

        # SANITY CHECK: Validate cell count doesn't exceed theoretical maximum
        # Upper bound = product of OTHER entity sets
        if new_entity_set.entity_type == EntityType.DOCUMENT:
            # New document pairs with all questions
            max_cells = len(question_ids)
        else:
            # New question pairs with all documents
            max_cells = len(document_ids)

        if len(cell_models) > max_cells:
            raise ValueError(
                f"STRATEGY BUG: Standard matrix generated {len(cell_models)} cells but maximum expected is {max_cells}. "
                f"Matrix has {len(document_ids)} docs, {len(question_ids)} questions. "
                f"New entity: {new_entity_set.entity_type.value} (id={new_entity_id})"
            )

        return cell_models

    @trace_span
    async def load_cell_data(self, cell_id: int, company_id: int) -> CellDataContext:
        """Load cell data for standard matrix.

        Standard cell has:
        - 1 document (DOCUMENT role)
        - 1 question (QUESTION role)
        """
        # Load cell and entity refs
        cell, entity_refs = await self._get_cell_with_refs(cell_id, company_id)

        # Find document and question refs
        document_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.DOCUMENT), None
        )
        question_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.QUESTION), None
        )

        if not document_ref or not question_ref:
            raise ValueError(f"Cell {cell_id} missing document or question reference")

        # Load document and question using shared utilities
        document = await self._load_document(
            document_ref.entity_id, company_id, EntityRole.DOCUMENT, document_ref
        )
        question = await self._load_question(
            question_ref.entity_id, company_id, question_ref
        )

        return CellDataContext(
            cell_id=cell.id,
            matrix_id=cell.matrix_id,
            cell_type=CellType.STANDARD,
            matrix_type=MatrixType.STANDARD,
            documents=[document],
            question=question,
            entity_refs=entity_refs,
        )
