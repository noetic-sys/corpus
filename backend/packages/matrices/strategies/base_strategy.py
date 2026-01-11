"""
Base strategy class with shared utilities for all matrix types.

Provides:
- Lazy-loaded services (no circular imports)
- Shared data loading utilities (documents, questions, entity refs)
- Shared template resolution
- Template method for QA processing (process_cell_to_completion)
- Abstract interface that all strategies must implement
"""

from abc import ABC, abstractmethod
from typing import List
import hashlib

from packages.matrices.models.domain.matrix_enums import (
    MatrixType,
    CellType,
    EntityRole,
    EntityType,
)
from packages.matrices.models.domain.matrix import MatrixCellCreateModel
from packages.matrices.models.domain.matrix_entity_set import (
    DocumentContext,
    QuestionContext,
    EntityReference,
)
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.qa.utils.document_reference import DocumentReference
from .models import EntitySetDefinition, CellDataContext, MatrixStructureMetadata, CellUpdateSpec

from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class BaseCellCreationStrategy(ABC):
    """Base strategy - provides shared utilities, enforces interface.

    All matrix type strategies extend this class. It provides:
    1. Lazy-loaded services (AI, template, entity set, document, question)
    2. Shared utilities for loading documents, questions, entity refs
    3. Shared template resolution (ID-based + document placeholders)
    4. Template method for QA processing (cannot override)
    5. Abstract interface (must implement)

    Strategies are ~100 lines each, mostly orchestrating these shared utilities.
    """

    def __init__(self):
        # Local imports to avoid circular dependencies
        # TODO: need to architect better...
        from packages.questions.services.template_processing_service import (  # noqa: PLC0415
            TemplateProcessingService,
        )
        from packages.matrices.services.entity_set_service import (  # noqa: PLC0415
            EntitySetService,
        )
        from packages.documents.services.document_service import (  # noqa: PLC0415
            get_document_service,
        )
        from packages.questions.services.question_service import (  # noqa: PLC0415
            QuestionService,
        )
        from packages.matrices.services.matrix_service import (  # noqa: PLC0415
            MatrixService,
        )

        # Initialize services (compose, don't duplicate)
        self.template_service = TemplateProcessingService()
        self.entity_set_service = EntitySetService()
        self.document_service = get_document_service()
        self.question_service = QuestionService()
        self.matrix_service = MatrixService()

    # =========================================================================
    # SHARED UTILITIES (DRY - used by all strategies)
    # =========================================================================

    def _compute_cell_signature(self, entity_refs: List[EntityReference]) -> str:
        """Compute cell signature from entity refs for database deduplication.

        IMPORTANT: Includes role in the signature because roles define distinct axes.
        For correlation matrices, (LEFT=A, RIGHT=B) is different from (LEFT=B, RIGHT=A).

        This signature must be included when creating cells to satisfy DB constraint.

        Args:
            entity_refs: List of EntityReference objects defining the cell's coordinates

        Returns:
            MD5 hash string of sorted entity refs
        """
        if not entity_refs:
            return ""

        # Sort by role (axis), then entity_set_id, then entity_set_member_id
        # Role MUST be included because it defines the axis/dimension
        sorted_refs = sorted(
            [
                f"{ref.role.value}|{ref.entity_set_id}|{ref.entity_set_member_id}"
                for ref in entity_refs
            ]
        )
        signature_str = ",".join(sorted_refs)
        return hashlib.md5(signature_str.encode()).hexdigest()

    @trace_span
    async def _get_cell_with_refs(self, cell_id: int, company_id: int) -> tuple:
        """Load cell and entity refs - shared across all strategies.

        Returns:
            Tuple of (MatrixCellModel, List[EntityReference])
        """
        # Load cell
        cell = await self.matrix_service.get_matrix_cell(cell_id, company_id)
        if not cell:
            raise ValueError(f"Cell {cell_id} not found")

        # Load entity references
        cell_refs = await self.entity_set_service.get_cell_entity_references_by_cell_id(
            cell_id
        )
        if not cell_refs:
            raise ValueError(f"No entity references found for cell {cell_id}")

        # Load members to get entity IDs
        member_ids = [ref.entity_set_member_id for ref in cell_refs]
        members = await self.entity_set_service.get_entity_set_members_by_ids(
            member_ids
        )
        member_map = {m.id: m for m in members}

        # Build EntityReference objects with full info
        entity_refs = []
        for ref in cell_refs:
            member = member_map.get(ref.entity_set_member_id)
            if not member:
                raise ValueError(f"Member {ref.entity_set_member_id} not found")

            entity_refs.append(
                EntityReference(
                    entity_set_id=ref.entity_set_id,
                    entity_set_member_id=ref.entity_set_member_id,
                    entity_type=member.entity_type,
                    entity_id=member.entity_id,
                    role=ref.role,
                    entity_order=ref.entity_order,
                )
            )

        return cell, entity_refs

    @trace_span
    async def _load_document(
        self,
        document_id: int,
        company_id: int,
        role: EntityRole,
        entity_ref: EntityReference,
    ) -> DocumentContext:
        """Load document with content - shared across all strategies.

        Args:
            document_id: Document ID to load
            company_id: Company ID for access control
            role: Role of this document (DOCUMENT, LEFT, RIGHT)
            entity_ref: Full entity reference for this document

        Returns:
            DocumentContext with all document data and role
        """
        doc = await self.document_service.get_document(document_id, company_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        content = await self.document_service.get_extracted_content(doc)
        if not content:
            raise ValueError(f"No extracted content for document {document_id}")

        return DocumentContext(
            document_id=doc.id,
            filename=doc.filename,
            content=content,
            role=role,
            entity_ref=entity_ref,
        )

    @trace_span
    async def _load_question(
        self, question_id: int, company_id: int, entity_ref: EntityReference
    ) -> QuestionContext:
        """Load question - shared across all strategies.

        Args:
            question_id: Question ID to load
            company_id: Company ID for access control
            entity_ref: Full entity reference for this question

        Returns:
            QuestionContext with all question data
        """
        question = await self.question_service.get_question(question_id, company_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")

        return QuestionContext(
            question_id=question.id,
            question_text=question.question_text,
            question_type_id=question.question_type_id,
            min_answers=question.min_answers,
            max_answers=question.max_answers,
            entity_ref=entity_ref,
        )

    @trace_span
    async def _resolve_question_templates(
        self,
        question_text: str,
        matrix_id: int,
        entity_refs: List[EntityReference],
    ) -> str:
        """Resolve all templates - shared across all strategies.

        Handles both:
        1. ID-based templates: #{{123}}
        2. Document placeholders: @{{LEFT}}, @{{RIGHT}}

        Args:
            question_text: Question text with template variables
            matrix_id: Matrix ID for resolving ID-based templates
            entity_refs: List of entity references for resolving document placeholders

        Returns:
            Fully resolved question text
        """
        # Step 1: Resolve ID-based templates (#{{123}})
        resolved = await self.template_service.resolve_template_variables(
            question_text, matrix_id
        )

        # Step 2: Resolve document placeholders (@{{LEFT}}, @{{RIGHT}})
        # Convert EntityReference to DocumentReference format for template service

        doc_refs = [
            DocumentReference(document_id=ref.entity_id, role=ref.role)
            for ref in entity_refs
            if ref.entity_type == EntityType.DOCUMENT
        ]

        if doc_refs:
            resolved = self.template_service.resolve_document_placeholders(
                resolved, doc_refs
            )

        logger.info(f"Resolved question template: '{question_text}' -> '{resolved}'")

        return resolved

    # =========================================================================
    # TEMPLATE METHOD (FINAL - shared implementation, cannot override)
    # =========================================================================

    @trace_span
    async def process_cell_to_completion(
        self,
        cell_id: int,
        company_id: int,
    ) -> tuple[AIAnswerSet, int]:
        """Complete QA processing pipeline - SHARED implementation.

        All strategies use the same flow:
        1. Load cell data (strategy-specific via load_cell_data)
        2. Resolve templates (shared utility)
        3. Call AI (shared utility via composed service)
        4. Return answer set

        This is a FINAL method (template method pattern) - strategies
        cannot override it. They customize behavior via load_cell_data().

        Args:
            cell_id: Cell ID to process
            company_id: Company ID for access control

        Returns:
            AIAnswerSet with parsed answers
        """
        logger.info(f"Processing cell {cell_id} to completion")

        # Step 1: Load cell data (strategy-specific implementation)
        cell_data = await self.load_cell_data(cell_id, company_id)

        # Step 2: Resolve question templates (shared utility)
        resolved_question = await self._resolve_question_templates(
            cell_data.question.question_text,
            cell_data.matrix_id,
            cell_data.entity_refs,
        )

        # Step 3: Get AI service and call it
        from packages.qa.services.ai_service import (  # noqa: PLC0415
            get_ai_service_for_question,
        )
        from packages.qa.utils.message_builders import (  # noqa: PLC0415
            DocumentContext as MessageDocumentContext,
        )

        # Load full question model for AI service
        question_model = await self.question_service.get_question(
            cell_data.question.question_id, company_id
        )
        if not question_model:
            raise ValueError(f"Question {cell_data.question.question_id} not found")

        # Get AI service configured for this question
        ai_service = await get_ai_service_for_question(question_model)

        # Convert our DocumentContext to MessageBuilder's DocumentContext
        # (they have different purposes - ours has role, theirs is for AI messages)
        documents = [
            MessageDocumentContext(
                document_id=doc.document_id,
                content=doc.content,
            )
            for doc in cell_data.documents
        ]

        answer_set = await ai_service.answer_question(
            documents=documents,
            question=resolved_question,
            matrix_type=cell_data.matrix_type,
            company_id=company_id,
            question_id=cell_data.question.question_id,
            question_type_id=cell_data.question.question_type_id,
            min_answers=cell_data.question.min_answers,
            max_answers=cell_data.question.max_answers,
        )

        logger.info(
            f"Completed cell {cell_id} with {answer_set.answer_count} answer(s), "
            f"found={answer_set.answer_found}"
        )

        return answer_set, cell_data.question.question_type_id

    # =========================================================================
    # ABSTRACT INTERFACE (must implement in concrete strategies)
    # =========================================================================

    @abstractmethod
    def get_entity_set_definitions(self) -> List[EntitySetDefinition]:
        """Define entity sets for this matrix type.

        Called during matrix creation to set up the schema.

        Returns:
            List of EntitySetDefinition describing required entity sets

        Example for StandardMatrixStrategy:
            [
                EntitySetDefinition(name="Documents", entity_type=EntityType.DOCUMENT),
                EntitySetDefinition(name="Questions", entity_type=EntityType.QUESTION),
            ]
        """
        pass

    @abstractmethod
    def get_matrix_type(self) -> MatrixType:
        """Return the matrix type this strategy handles.

        Used by factory for registration and type checking.
        """
        pass

    @abstractmethod
    def get_cell_type(self) -> CellType:
        """Return the cell type this strategy creates.

        Determines which AI prompts to use (STANDARD vs CORRELATION analysis).
        """
        pass

    @abstractmethod
    def get_structure_metadata(self) -> MatrixStructureMetadata:
        """Return metadata about matrix structure for document generation.

        Provides information about:
        - How the matrix is structured (explanation)
        - What roles entities play (roles_explanation)
        - Template variable guidance for document generation

        Returns:
            MatrixStructureMetadata with structure information

        Example for StandardMatrixStrategy:
            return MatrixStructureMetadata(
                explanation="Standard matrix: documents × questions (2D)...",
                roles_explanation={
                    "DOCUMENT": "The document being analyzed",
                    "QUESTION": "The question being answered"
                },
                template_variables=["document", "question", "answer"],
                template_guidance="Use {{document}} to reference the document..."
            )
        """
        pass

    @abstractmethod
    async def create_cells_for_new_entity(
        self,
        matrix_id: int,
        company_id: int,
        new_entity_id: int,
        entity_set_id: int,
    ) -> List[MatrixCellCreateModel]:
        """Create cells when new entity added to set.

        Strategy knows the matrix structure and determines which cells
        to create. Fetches entity sets and members as needed.

        Args:
            matrix_id: Matrix ID
            company_id: Company ID for access control
            new_entity_id: ID of entity being added (document or question)
            entity_set_id: Entity set the entity was added to

        Returns:
            List of MatrixCellCreateModel with entity_refs populated
        """
        pass

    async def update_cells_for_new_entity(
        self,
        matrix_id: int,
        company_id: int,
        new_entity_id: int,
        entity_set_id: int,
    ) -> List[CellUpdateSpec]:
        """Update existing cells when a new entity is added.

        Override in strategies that need to modify existing cells when
        new entities are added (e.g., synopsis adds new documents to all
        existing cells).

        Most strategies return empty list (default behavior).

        Args:
            matrix_id: Matrix ID
            company_id: Company ID for access control
            new_entity_id: ID of entity being added
            entity_set_id: Entity set the entity was added to

        Returns:
            List of CellUpdateSpec for cells to update
        """
        return []

    @abstractmethod
    async def load_cell_data(self, cell_id: int, company_id: int) -> CellDataContext:
        """Load all data needed for QA processing.

        Strategy knows which entity refs to load based on matrix structure.
        Uses shared utilities (_load_document, _load_question) to load entities.

        Args:
            cell_id: Cell ID to load data for
            company_id: Company ID for access control

        Returns:
            CellDataContext with documents, question, and entity refs

        Example for StandardMatrixStrategy:
            cell_data = CellDataContext(
                cell_id=cell.id,
                matrix_id=cell.matrix_id,
                cell_type=CellType.STANDARD,
                matrix_type=MatrixType.STANDARD,
                documents=[document],  # Single document
                question=question,
                entity_refs=[doc_ref, question_ref]
            )

        Example for GenericCorrelationStrategy:
            cell_data = CellDataContext(
                cell_id=cell.id,
                matrix_id=cell.matrix_id,
                cell_type=CellType.CORRELATION,
                matrix_type=MatrixType.GENERIC_CORRELATION,
                documents=[left_doc, right_doc],  # Two documents
                question=question,
                entity_refs=[left_ref, right_ref, question_ref]
            )
        """
        pass
