"""
Synopsis strategy: all documents x questions (1D from cell perspective).

Creates one cell per question, where each cell contains ALL documents.
For N documents and Q questions, generates Q cells total.
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
from .models import EntitySetDefinition, CellDataContext, MatrixStructureMetadata, CellUpdateSpec
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class SynopsisStrategy(BaseCellCreationStrategy):
    """Strategy for synopsis matrices: all documents x questions.

    Entity sets:
    - Documents (DOCUMENT role, ALL documents per cell)
    - Questions (QUESTION role, one per cell)

    Cell structure:
    - ALL N documents + one question = SYNOPSIS cell type
    - For N documents and Q questions, generates Q cells total

    Key difference from other strategies:
    - New question: Creates 1 cell with all existing documents
    - New document: Updates ALL existing cells to include it (handled by update_cells_for_new_entity)
    """

    def get_entity_set_definitions(self) -> List[EntitySetDefinition]:
        """Define entity sets for synopsis matrix."""
        return [
            EntitySetDefinition(
                name="Documents",
                entity_type=EntityType.DOCUMENT,
                description="Documents to synthesize across",
            ),
            EntitySetDefinition(
                name="Questions",
                entity_type=EntityType.QUESTION,
                description="Questions to answer using all documents",
            ),
        ]

    def get_matrix_type(self) -> MatrixType:
        """Return SYNOPSIS matrix type."""
        return MatrixType.SYNOPSIS

    def get_cell_type(self) -> CellType:
        """Return SYNOPSIS cell type."""
        return CellType.SYNOPSIS

    def get_structure_metadata(self) -> MatrixStructureMetadata:
        """Return structure metadata for synopsis matrices."""
        return MatrixStructureMetadata(
            explanation=(
                "Synopsis matrix: all documents x questions (1D from cell perspective). "
                "One entity set contains documents, another contains questions. "
                "Each cell synthesizes ALL documents to answer ONE question. "
                "For N documents and Q questions, generates Q cells total."
            ),
            roles_explanation={
                "DOCUMENT": "Documents being synthesized (ALL documents from Documents entity set)",
                "QUESTION": "The question being answered across all documents",
            },
            system_placeholders={},  # Synopsis doesn't use @{{}} placeholders
            cell_structure=(
                "Each cell contains: ALL documents (DOCUMENT role, ordered by entity_order), "
                "1 question (QUESTION role), and an AI-generated synopsis/summary across all documents."
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
        """Create cells for a new entity in a synopsis matrix.

        Synopsis: all documents x questions
        - New question: Create 1 cell with ALL existing documents
        - New document: No new cells created (handled by update_cells_for_new_entity)
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
                f"Synopsis matrix {matrix_id} requires DOCUMENT and QUESTION entity sets"
            )

        if new_entity_set.entity_type == EntityType.DOCUMENT:
            # New document: create cells for all existing questions that don't have cells yet
            # This handles the case where questions were added before any documents
            document_id = new_entity_id

            # Get all questions
            question_members = await self.entity_set_service.get_entity_set_members(
                question_entity_set.id, company_id
            )
            question_ids = [m.entity_id for m in question_members]

            if not question_ids:
                logger.info(
                    f"No questions in matrix {matrix_id}: no cells to create for new document"
                )
                return []

            # Get member mappings to translate between entity_id and member_id
            question_members_map = await self.entity_set_service.get_member_id_mappings(
                question_entity_set.id
            )
            # Reverse mapping: member_id -> entity_id
            member_to_entity = {v: k for k, v in question_members_map.items()}

            # Get existing cells to see which questions already have cells
            existing_cells = await self.matrix_service.get_matrix_cells(matrix_id)
            existing_cell_question_ids = set()
            for cell in existing_cells:
                cell_refs = await self.entity_set_service.get_cell_entity_references_by_cell_id(cell.id)
                for ref in cell_refs:
                    if ref.role == EntityRole.QUESTION:
                        # Convert member_id back to entity_id
                        entity_id = member_to_entity.get(ref.entity_set_member_id)
                        if entity_id:
                            existing_cell_question_ids.add(entity_id)

            # Questions that need new cells (no cell exists yet)
            questions_needing_cells = [q for q in question_ids if q not in existing_cell_question_ids]

            if not questions_needing_cells:
                # All questions already have cells - update_cells_for_new_entity handles adding doc
                logger.info(
                    f"All questions already have cells: new document will be added via update"
                )
                return []

            # Get document member mappings (question_members_map already fetched above)
            document_members_map = await self.entity_set_service.get_member_id_mappings(
                document_entity_set.id
            )

            # Get ALL document IDs (including the new one)
            all_document_members = await self.entity_set_service.get_entity_set_members(
                document_entity_set.id, company_id
            )
            all_document_ids = [m.entity_id for m in all_document_members]

            cells = []
            for question_id in questions_needing_cells:
                if question_id not in question_members_map:
                    continue

                entity_refs = []
                for order, doc_id in enumerate(all_document_ids):
                    if doc_id not in document_members_map:
                        continue
                    entity_refs.append(
                        EntityReference(
                            entity_set_id=document_entity_set.id,
                            entity_set_member_id=document_members_map[doc_id],
                            entity_type=EntityType.DOCUMENT,
                            entity_id=doc_id,
                            role=EntityRole.DOCUMENT,
                            entity_order=order,
                        )
                    )

                entity_refs.append(
                    EntityReference(
                        entity_set_id=question_entity_set.id,
                        entity_set_member_id=question_members_map[question_id],
                        entity_type=EntityType.QUESTION,
                        entity_id=question_id,
                        role=EntityRole.QUESTION,
                        entity_order=len(all_document_ids),
                    )
                )

                cells.append(
                    MatrixCellCreateModel(
                        matrix_id=matrix_id,
                        company_id=company_id,
                        status=MatrixCellStatus.PENDING.value,
                        cell_type=CellType.SYNOPSIS,
                        cell_signature=self._compute_cell_signature(entity_refs),
                        entity_refs=entity_refs,
                    )
                )

            logger.info(
                f"Created {len(cells)} synopsis cells for questions without cells (new doc triggered)"
            )
            return cells

        # New question: create 1 cell with ALL documents
        question_id = new_entity_id

        # Get all documents
        document_members = await self.entity_set_service.get_entity_set_members(
            document_entity_set.id, company_id
        )
        document_ids = [m.entity_id for m in document_members]

        # Synopsis requires at least 1 document to create a cell
        if not document_ids:
            logger.info(
                f"No documents in matrix {matrix_id}: skipping cell creation for question {question_id}"
            )
            return []

        # Get member mappings
        document_members_map = await self.entity_set_service.get_member_id_mappings(
            document_entity_set.id
        )
        question_members_map = await self.entity_set_service.get_member_id_mappings(
            question_entity_set.id
        )

        if question_id not in question_members_map:
            logger.warning(
                f"Question {question_id} not found in entity set {question_entity_set.id}"
            )
            return []

        # Build entity refs for all documents
        entity_refs = []
        for order, doc_id in enumerate(document_ids):
            if doc_id not in document_members_map:
                logger.warning(
                    f"Document {doc_id} not found in entity set {document_entity_set.id}, skipping"
                )
                continue

            entity_refs.append(
                EntityReference(
                    entity_set_id=document_entity_set.id,
                    entity_set_member_id=document_members_map[doc_id],
                    entity_type=EntityType.DOCUMENT,
                    entity_id=doc_id,
                    role=EntityRole.DOCUMENT,
                    entity_order=order,
                )
            )

        # Add question ref (after all documents)
        entity_refs.append(
            EntityReference(
                entity_set_id=question_entity_set.id,
                entity_set_member_id=question_members_map[question_id],
                entity_type=EntityType.QUESTION,
                entity_id=question_id,
                role=EntityRole.QUESTION,
                entity_order=len(document_ids),
            )
        )

        cell_model = MatrixCellCreateModel(
            matrix_id=matrix_id,
            company_id=company_id,
            status=MatrixCellStatus.PENDING.value,
            cell_type=CellType.SYNOPSIS,
            cell_signature=self._compute_cell_signature(entity_refs),
            entity_refs=entity_refs,
        )

        logger.info(
            f"Created 1 synopsis cell model ({len(document_ids)} docs x 1 question)"
        )

        # SANITY CHECK: Validate cell count
        max_cells = 1  # Synopsis creates exactly 1 cell per question
        if 1 > max_cells:
            raise ValueError(
                f"STRATEGY BUG: Synopsis generated more than 1 cell for a single question"
            )

        return [cell_model]

    @trace_span
    async def update_cells_for_new_entity(
        self,
        matrix_id: int,
        company_id: int,
        new_entity_id: int,
        entity_set_id: int,
    ) -> List[CellUpdateSpec]:
        """Update existing cells when a new document is added to synopsis matrix.

        For synopsis, adding a document means ALL existing cells need to
        include this document and be re-processed.

        Args:
            matrix_id: Matrix ID
            company_id: Company ID for access control
            new_entity_id: ID of document being added
            entity_set_id: Entity set the document was added to

        Returns:
            List of CellUpdateSpec for all existing cells
        """
        # Get the entity set the new entity belongs to
        new_entity_set = await self.entity_set_service.get_entity_set(
            entity_set_id, company_id
        )
        if not new_entity_set:
            raise ValueError(f"Entity set {entity_set_id} not found")

        if new_entity_set.entity_type != EntityType.DOCUMENT:
            # Only documents trigger updates in synopsis
            # Questions create new cells instead
            return []

        # Get all entity sets for this matrix
        all_entity_sets = await self.entity_set_service.get_matrix_entity_sets(
            matrix_id, company_id
        )

        document_entity_set = next(
            (es for es in all_entity_sets if es.entity_type == EntityType.DOCUMENT),
            None,
        )

        if not document_entity_set:
            raise ValueError(f"Synopsis matrix {matrix_id} requires DOCUMENT entity set")

        # Get existing cells for this matrix
        existing_cells = await self.matrix_service.get_matrix_cells(matrix_id)

        if not existing_cells:
            logger.info(f"No existing cells in matrix {matrix_id} to update")
            return []

        # Get member mapping for the new document
        document_members_map = await self.entity_set_service.get_member_id_mappings(
            document_entity_set.id
        )

        if new_entity_id not in document_members_map:
            logger.warning(
                f"Document {new_entity_id} not found in entity set {document_entity_set.id}"
            )
            return []

        new_doc_member_id = document_members_map[new_entity_id]

        # For each existing cell, create an update spec to add this document
        updates = []
        for cell in existing_cells:
            # Get current entity refs to determine next order
            cell_refs = await self.entity_set_service.get_cell_entity_references_by_cell_id(
                cell.id
            )
            current_doc_count = sum(
                1 for ref in cell_refs if ref.role == EntityRole.DOCUMENT
            )

            new_entity_ref = EntityReference(
                entity_set_id=document_entity_set.id,
                entity_set_member_id=new_doc_member_id,
                entity_type=EntityType.DOCUMENT,
                entity_id=new_entity_id,
                role=EntityRole.DOCUMENT,
                entity_order=current_doc_count,  # Add at end of documents
            )

            updates.append(
                CellUpdateSpec(
                    cell_id=cell.id,
                    entity_refs_to_add=[new_entity_ref],
                    reset_status=True,
                )
            )

        logger.info(
            f"Created {len(updates)} cell update specs to include new document {new_entity_id}"
        )

        return updates

    @trace_span
    async def load_cell_data(self, cell_id: int, company_id: int) -> CellDataContext:
        """Load cell data for synopsis matrix.

        Synopsis cell has:
        - N documents (DOCUMENT role)
        - 1 question (QUESTION role)
        """
        # Load cell and entity refs
        cell, entity_refs = await self._get_cell_with_refs(cell_id, company_id)

        # Find all document refs and question ref
        document_refs = [
            ref for ref in entity_refs if ref.role == EntityRole.DOCUMENT
        ]
        question_ref = next(
            (ref for ref in entity_refs if ref.role == EntityRole.QUESTION), None
        )

        if not question_ref:
            raise ValueError(f"Cell {cell_id} missing QUESTION reference")

        # Sort documents by entity_order
        document_refs.sort(key=lambda r: r.entity_order)

        # Load all documents
        documents = []
        for doc_ref in document_refs:
            doc = await self._load_document(
                doc_ref.entity_id, company_id, EntityRole.DOCUMENT, doc_ref
            )
            documents.append(doc)

        question = await self._load_question(
            question_ref.entity_id, company_id, question_ref
        )

        return CellDataContext(
            cell_id=cell.id,
            matrix_id=cell.matrix_id,
            cell_type=CellType.SYNOPSIS,
            matrix_type=MatrixType.SYNOPSIS,
            documents=documents,
            question=question,
            entity_refs=entity_refs,
        )
