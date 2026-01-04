from __future__ import annotations
from typing import List, Optional, Dict

from packages.matrices.models.domain.matrix_enums import EntityRole, EntityType
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.matrices.services.matrix_template_variable_service import (
    MatrixTemplateVariableService,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
)
from packages.questions.services.question_service import QuestionService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.matrices.repositories.matrix_repository import (
    MatrixRepository,
)
from packages.matrices.repositories.matrix_cell_repository import MatrixCellRepository
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixCellEntityReferenceModel,
)
from packages.matrices.models.domain.matrix import (
    MatrixModel,
    MatrixCreateModel,
    MatrixUpdateModel,
    MatrixCellModel,
    MatrixCellUpdateModel,
    MatrixCellStatus,
    MatrixCellStatsModel,
)
from packages.matrices.models.schemas.matrix import MatrixCellWithAnswerResponse
from packages.qa.models.domain.answer_set import AnswerSetCreateModel, AnswerSetModel
from packages.qa.models.domain.answer import (
    AnswerCreateModel,
    AnswerUpdateModel,
    AnswerModel,
)
from packages.qa.models.domain.citation import (
    CitationSetCreateModel,
    CitationCreateWithoutSetIdModel,
    CitationModel,
)
from packages.matrices.models.schemas.matrix import (
    MatrixDuplicateRequest,
    MatrixDuplicateResponse,
)
from packages.qa.services.answer_set_service import AnswerSetService
from packages.qa.services.citation_service import CitationService
from packages.qa.services.answer_service import AnswerService
from packages.documents.services.document_service import DocumentService
from common.db.transaction_utils import transactional
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.matrices.services.batch_processing_service import BatchProcessingService
from packages.matrices.services.entity_set_service import EntitySetService
from packages.billing.services.quota_service import QuotaService
from packages.matrices.models.domain.matrix_entity_set import MatrixEntitySetCreateModel
from packages.matrices.strategies.factory import CellStrategyFactory
from packages.matrices.mappers.matrix_cell_mappers import (
    build_matrix_cells_with_answer_responses,
)

logger = get_logger(__name__)


class MatrixService:
    """Service for handling matrix operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.matrix_repo = MatrixRepository()
        self.matrix_cell_repo = MatrixCellRepository()
        self.cell_entity_ref_repo = CellEntityReferenceRepository()
        self.member_repo = EntitySetMemberRepository()
        self.answer_set_service = AnswerSetService()
        self.answer_service = AnswerService()
        self.citation_service = CitationService()

    @trace_span
    async def create_matrix(self, matrix_data: MatrixCreateModel) -> MatrixModel:
        """Create a new matrix with entity sets defined by strategy."""
        # Local imports to avoid circular dependencies

        logger.info(f"Creating matrix: {matrix_data.name}")

        matrix = await self.matrix_repo.create(matrix_data)

        # Get strategy for this matrix type
        strategy = CellStrategyFactory.get_strategy(matrix.matrix_type, self.db_session)

        # Get entity set definitions from strategy
        entity_set_definitions = strategy.get_entity_set_definitions()

        # Create entity sets based on strategy definitions
        entity_set_service = EntitySetService(self.db_session)

        for definition in entity_set_definitions:
            entity_set = MatrixEntitySetCreateModel(
                matrix_id=matrix.id,
                name=definition.name,
                entity_type=definition.entity_type,
                company_id=matrix_data.company_id,
            )
            await entity_set_service.create_entity_set(entity_set)
            logger.info(
                f"Created entity set '{definition.name}' ({definition.entity_type.value}) "
                f"for {matrix.matrix_type.value} matrix {matrix.id}"
            )

        logger.info(f"Created matrix with ID: {matrix.id}")
        return matrix

    @trace_span
    async def get_matrix(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> Optional[MatrixModel]:
        """Get a matrix by ID."""
        return await self.matrix_repo.get(matrix_id, company_id)

    @trace_span
    async def list_matrices(
        self, skip: int = 0, limit: int = 100, company_id: Optional[int] = None
    ) -> List[MatrixModel]:
        """List matrices with pagination."""
        return await self.matrix_repo.get_multi(skip, limit, company_id)

    @trace_span
    async def get_matrices_by_workspace(
        self,
        workspace_id: int,
        skip: int = 0,
        limit: int = 100,
        company_id: Optional[int] = None,
    ) -> List[MatrixModel]:
        """Get matrices by workspace ID with pagination."""
        logger.info(f"Getting matrices for workspace {workspace_id}")
        return await self.matrix_repo.get_by_workspace_id(
            workspace_id, skip, limit, company_id
        )

    @trace_span
    async def get_matrix_cell_stats(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> MatrixCellStatsModel:
        """Get cell statistics for a matrix, including document extraction stats."""
        logger.info(f"Getting cell stats for matrix {matrix_id}")

        # Get QA cell stats
        cell_stats = await self.matrix_cell_repo.get_cell_stats_by_matrix(matrix_id)

        # Get document extraction stats
        entity_set_service = EntitySetService(self.db_session)
        entity_sets = await entity_set_service.get_matrix_entity_sets(
            matrix_id, company_id
        )

        # Get all document entity sets (handles both standard and correlation matrices)
        document_ids = []
        for entity_set in entity_sets:
            if entity_set.entity_type == EntityType.DOCUMENT:
                members = await self.member_repo.get_by_entity_set_id(
                    entity_set.id, company_id
                )
                document_ids.extend([member.entity_id for member in members])

        # Get document extraction stats if there are documents
        if document_ids:
            document_service = DocumentService(self.db_session)
            doc_stats = await document_service.get_extraction_stats_for_document_ids(
                document_ids, company_id
            )

            cell_stats.documents_pending_extraction = doc_stats.pending
            cell_stats.documents_failed_extraction = doc_stats.failed

        return cell_stats

    @trace_span
    async def update_matrix(
        self,
        matrix_id: int,
        matrix_update: MatrixUpdateModel,
        company_id: Optional[int] = None,
    ) -> Optional[MatrixModel]:
        """Update a matrix."""
        # Check if matrix exists first with company filtering
        existing_matrix = await self.matrix_repo.get(matrix_id, company_id)
        if not existing_matrix:
            return None

        matrix = await self.matrix_repo.update(matrix_id, matrix_update)
        if matrix:
            logger.info(f"Updated matrix {matrix_id}")
        return matrix

    @trace_span
    async def delete_matrix(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> bool:
        """Delete a matrix."""
        # Check if matrix exists first with company filtering
        existing_matrix = await self.matrix_repo.get(matrix_id, company_id)
        if not existing_matrix:
            return False

        success = await self.matrix_repo.delete(matrix_id)
        if success:
            logger.info(f"Deleted matrix {matrix_id}")
        return success

    @trace_span
    async def get_matrix_cell(
        self, cell_id: int, company_id: Optional[int] = None
    ) -> Optional[MatrixCellModel]:
        """Get a matrix cell by ID."""
        return await self.matrix_cell_repo.get(cell_id, company_id)

    @trace_span
    async def update_matrix_cell_status(
        self, cell_id: int, status: MatrixCellStatus
    ) -> bool:
        """Update matrix cell status."""
        update_model = MatrixCellUpdateModel(status=status)
        cell = await self.matrix_cell_repo.update(cell_id, update_model)
        if cell:
            logger.info(
                f"Updated cell {cell_id} status to {status.value if isinstance(status, MatrixCellStatus) else status}"
            )
            return True
        return False

    @trace_span
    async def create_matrix_cell_answer_set_from_ai(
        self,
        cell_id: int,
        question_type_id: int,
        ai_answer_set: AIAnswerSet,
        set_as_current: bool = True,
    ) -> bool:
        """Create a new answer set from AI response for a matrix cell, including citations."""
        # Create the answer set with the AI-provided answer_found status
        cell = await self.matrix_cell_repo.get(cell_id)

        # Calculate average confidence from individual answers
        avg_confidence = 1.0
        if ai_answer_set.answers:
            confidence_sum = sum(answer.confidence for answer in ai_answer_set.answers)
            avg_confidence = confidence_sum / len(ai_answer_set.answers)

        answer_set_create = AnswerSetCreateModel(
            matrix_cell_id=cell_id,
            question_type_id=question_type_id,
            answer_found=ai_answer_set.answer_found,
            confidence=avg_confidence,
            company_id=cell.company_id,
        )

        logger.info(
            f"Creating answer set for cell {cell_id} from AI response with {ai_answer_set.answer_count} answers, "
            f"answer_found: {ai_answer_set.answer_found}, confidence: {avg_confidence:.2f}"
        )

        # Flag low-confidence answers for review
        CONFIDENCE_THRESHOLD = 0.7
        if avg_confidence < CONFIDENCE_THRESHOLD:
            logger.warning(
                f"LOW CONFIDENCE ALERT: Cell {cell_id} has answer confidence {avg_confidence:.2f} "
                f"(below threshold {CONFIDENCE_THRESHOLD}). Answer may need human review."
            )

        answer_set = await self.answer_set_service.create_answer_set(
            answer_set_create, company_id=cell.company_id
        )

        # Create individual answers within the answer set (if any)
        created_answers = []
        for answer_data in ai_answer_set.answers:
            answer_create = AnswerCreateModel(
                answer_set_id=answer_set.id,
                answer_data=answer_data,
                company_id=cell.company_id,
            )
            answer = await self.answer_service.create_answer(
                answer_create, company_id=cell.company_id
            )
            created_answers.append(answer)

            # Create citations for this answer - all answer types now have citations field
            if answer_data.citations:
                logger.info(
                    f"Creating {len(answer_data.citations)} citations for answer {answer.id}"
                )

                # Build citation create models from the answer data citations
                citation_creates = []
                for citation_ref in answer_data.citations:
                    citation_creates.append(
                        CitationCreateWithoutSetIdModel(
                            document_id=citation_ref.document_id,
                            company_id=cell.company_id,
                            quote_text=citation_ref.quote_text,
                            citation_order=citation_ref.citation_number,
                        )
                    )

                # Create citation set with all citations
                if citation_creates:
                    citation_set_create = CitationSetCreateModel(
                        answer_id=answer.id,
                        company_id=cell.company_id,
                        citations=citation_creates,
                    )
                    citation_set = (
                        await self.citation_service.create_citation_set_with_citations(
                            citation_set_create, cell.company_id
                        )
                    )

                    # Update answer to point to current citation set
                    answer_update = AnswerUpdateModel(
                        current_citation_set_id=citation_set.id
                    )
                    await self.answer_service.update_answer(answer.id, answer_update)
                    logger.info(
                        f"Created citation set {citation_set.id} with {len(citation_creates)} citations for answer {answer.id}"
                    )

        if set_as_current:
            # Update matrix cell to point to this answer set as current
            updated_cell = await self.matrix_cell_repo.update_current_answer_set(
                cell_id, answer_set.id
            )
            if not updated_cell:
                logger.error(
                    f"Failed to set answer set {answer_set.id} as current for cell {cell_id}"
                )
                return False

        logger.info(
            f"Created answer set {answer_set.id} from AI with {len(created_answers)} answers for cell {cell_id}, answer_found: {answer_set.answer_found}"
        )
        return True

    @trace_span
    async def get_pending_matrix_cells(self) -> List[MatrixCellModel]:
        """Get all matrix cells in PENDING state."""
        return await self.matrix_cell_repo.get_by_status(MatrixCellStatus.PENDING.value)

    @trace_span
    async def update_matrix_cell(
        self, cell_id: int, **updates
    ) -> Optional[MatrixCellModel]:
        """Update a matrix cell with arbitrary fields."""
        update_model = MatrixCellUpdateModel(**updates)
        cell = await self.matrix_cell_repo.update(cell_id, update_model)
        if cell:
            logger.info(f"Updated matrix cell {cell_id}")
        return cell

    @trace_span
    async def get_matrix_cells(self, matrix_id: int) -> List[MatrixCellModel]:
        """Get all matrix cells for a given matrix."""
        return await self.matrix_cell_repo.get_cells_by_matrix_id(matrix_id)

    @trace_span
    async def get_matrix_cells_by_document(
        self, matrix_id: int, document_id: int, entity_set_id: int
    ) -> List[MatrixCellModel]:
        """Get all matrix cells for a given matrix and document (via entity refs).

        Handles both standard (DOCUMENT role) and cross-correlation (LEFT/RIGHT roles) matrices.

        2-step query:
        1. entity_id → member_id
        2. member_id + applicable roles → cell_ids
        3. Load cells
        """

        # Step 1: Get member ID for this document
        member_ids = await self.member_repo.get_member_ids_by_entity_ids(
            entity_set_id, [document_id]
        )
        logger.info(
            f"get_matrix_cells_by_document: document_id={document_id}, "
            f"entity_set_id={entity_set_id}, member_ids={member_ids}"
        )
        if not member_ids:
            logger.info(
                f"No member_ids found for document {document_id} in entity_set {entity_set_id}"
            )
            return []

        member_id = member_ids[0]

        # Step 2: Get matrix type to determine which roles to query
        matrix = await self.matrix_repo.get(matrix_id)
        if not matrix:
            logger.warning(f"Matrix {matrix_id} not found")
            return []

        # Determine roles based on matrix type
        if matrix.matrix_type.value in ("cross_correlation", "generic_correlation"):
            # For correlation matrices, query for both LEFT and RIGHT roles
            roles = [EntityRole.LEFT, EntityRole.RIGHT]
        else:
            # For standard and other matrix types, use DOCUMENT role
            roles = [EntityRole.DOCUMENT]

        logger.info(
            f"Matrix {matrix_id} type={matrix.matrix_type.value}, using roles={[r.value for r in roles]}"
        )

        # Get cells for all applicable roles
        all_cell_ids = set()
        for role in roles:
            cell_ids = await self.cell_entity_ref_repo.get_cells_by_entity_member(
                matrix_id, entity_set_id, member_id, role
            )
            logger.info(
                f"Role {role.value}: found {len(cell_ids)} cell_ids for "
                f"matrix={matrix_id}, entity_set={entity_set_id}, member={member_id}"
            )
            all_cell_ids.update(cell_ids)

        if not all_cell_ids:
            logger.info(
                f"No cell_ids found across all roles for document {document_id}"
            )
            return []

        # Step 3: Load full cell models
        cells = await self.matrix_cell_repo.get_cells_by_ids(list(all_cell_ids))
        logger.info(f"Loaded {len(cells)} cells for document {document_id}")
        return cells

    @trace_span
    async def get_matrix_cells_by_question(
        self, matrix_id: int, question_id: int, entity_set_id: int
    ) -> List[MatrixCellModel]:
        """Get all matrix cells for a given matrix and question (via entity refs).

        2-step query:
        1. entity_id → member_id
        2. member_id + role=QUESTION → cell_ids
        3. Load cells
        """

        # Step 1: Get member ID for this question
        member_ids = await self.member_repo.get_member_ids_by_entity_ids(
            entity_set_id, [question_id]
        )
        if not member_ids:
            return []

        # Step 2: Get cells that reference this member with role=QUESTION
        cell_ids = await self.cell_entity_ref_repo.get_cells_by_entity_member(
            matrix_id, entity_set_id, member_ids[0], EntityRole.QUESTION
        )
        if not cell_ids:
            return []

        # Step 3: Load full cell models
        return await self.matrix_cell_repo.get_cells_by_ids(cell_ids)

    @trace_span
    async def get_matrix_cell_with_current_answer_set(
        self, matrix_id: int, document_id: int, question_id: int
    ) -> tuple[Optional[MatrixCellModel], Optional[AnswerSetModel]]:
        """Get a matrix cell with its current answer set by coordinates."""
        cell = await self.get_matrix_cell_by_coordinates(
            matrix_id, document_id, question_id
        )
        if not cell:
            return None, None

        current_answer_set = None
        if cell.current_answer_set_id:
            current_answer_set = await self.answer_set_service.get_answer_set(
                cell.current_answer_set_id
            )

        return cell, current_answer_set

    @trace_span
    async def _batch_fetch_cell_data(self, cells: List[MatrixCellModel]) -> tuple[
        List[AnswerSetModel],
        List[AnswerModel],
        List[CitationModel],
        Dict[int, List[MatrixCellEntityReferenceModel]],
    ]:
        """Helper: Batch fetch answer sets, answers, citations, and entity refs for given cells.

        Returns: (answer_sets, answers, citations, entity_refs_by_cell)
        """
        # Step 1: Batch fetch answer sets
        answer_set_ids = [
            cell.current_answer_set_id for cell in cells if cell.current_answer_set_id
        ]
        answer_sets = []
        if answer_set_ids:
            answer_sets = await self.answer_set_service.get_by_ids(answer_set_ids)

        # Step 2: Batch fetch all answers
        answers = []
        if answer_set_ids:
            answers = await self.answer_service.get_by_answer_set_ids(answer_set_ids)

        # Step 3: Batch fetch all citations
        citation_set_ids = [
            answer.current_citation_set_id
            for answer in answers
            if answer.current_citation_set_id
        ]
        citations = []
        if citation_set_ids:
            citations = await self.citation_service.get_citations_by_citation_set_ids(
                citation_set_ids
            )

        # Step 4: Batch fetch entity refs
        cell_ids = [cell.id for cell in cells]
        entity_refs = await self.cell_entity_ref_repo.get_by_cell_ids_bulk(cell_ids)

        # Group by cell_id
        entity_refs_by_cell: Dict[int, List[MatrixCellEntityReferenceModel]] = {}
        for ref in entity_refs:
            if ref.matrix_cell_id not in entity_refs_by_cell:
                entity_refs_by_cell[ref.matrix_cell_id] = []
            entity_refs_by_cell[ref.matrix_cell_id].append(ref)

        return answer_sets, answers, citations, entity_refs_by_cell

    @trace_span
    async def get_matrix_cells_with_current_answer_sets_by_document(
        self, matrix_id: int, document_id: int, entity_set_id: int
    ) -> List[MatrixCellWithAnswerResponse]:
        """Get matrix cells with answers for a document - returns mapped response objects."""
        cells = await self.get_matrix_cells_by_document(
            matrix_id, document_id, entity_set_id
        )
        answer_sets, answers, citations, entity_refs_by_cell = (
            await self._batch_fetch_cell_data(cells)
        )

        # Fetch members for entity refs
        all_entity_refs = [ref for refs in entity_refs_by_cell.values() for ref in refs]
        member_ids = list(set(ref.entity_set_member_id for ref in all_entity_refs))
        members = await self.member_repo.get_by_ids(member_ids) if member_ids else []
        members_by_id = {member.id: member for member in members}

        return build_matrix_cells_with_answer_responses(
            cells, answer_sets, answers, citations, entity_refs_by_cell, members_by_id
        )

    @trace_span
    async def get_matrix_cells_with_current_answer_sets_by_question(
        self, matrix_id: int, question_id: int, entity_set_id: int
    ) -> List[MatrixCellWithAnswerResponse]:
        """Get matrix cells with answers for a question - returns mapped response objects."""
        cells = await self.get_matrix_cells_by_question(
            matrix_id, question_id, entity_set_id
        )
        answer_sets, answers, citations, entity_refs_by_cell = (
            await self._batch_fetch_cell_data(cells)
        )

        # Fetch members for entity refs
        all_entity_refs = [ref for refs in entity_refs_by_cell.values() for ref in refs]
        member_ids = list(set(ref.entity_set_member_id for ref in all_entity_refs))
        members = await self.member_repo.get_by_ids(member_ids) if member_ids else []
        members_by_id = {member.id: member for member in members}

        return build_matrix_cells_with_answer_responses(
            cells, answer_sets, answers, citations, entity_refs_by_cell, members_by_id
        )

    @trace_span
    async def get_matrix_cells_with_current_answer_sets_by_batch(
        self, matrix_id: int, entity_set_filters: List
    ) -> List[MatrixCellWithAnswerResponse]:
        """Batch fetch cells by entity_set_filters - returns mapped response objects.

        Uses role-aware intersection to find cells at the Cartesian product of filters.
        Each filter specifies entities for a specific role/axis, and we return cells
        that match ALL filters simultaneously.

        Example: Documents (LEFT): [6,7,8] AND Questions (QUESTION): [1,2,3]
        Returns exactly 9 cells (3×3 intersection).
        """
        if not entity_set_filters:
            return []

        # Get cell IDs for each filter (role-aware)
        filter_cell_ids: List[set[int]] = []

        for filter in entity_set_filters:
            # Step 1: Get member IDs for these entity IDs
            member_ids = await self.member_repo.get_member_ids_by_entity_ids(
                filter.entity_set_id, filter.entity_ids
            )

            if not member_ids:
                # If any filter has no members, intersection is empty
                return []

            # Step 2: Get cells that reference these members WITH the specified role
            found_cell_ids = (
                await self.cell_entity_ref_repo.get_cells_by_member_ids_with_role(
                    matrix_id, filter.entity_set_id, member_ids, filter.role
                )
            )

            filter_cell_ids.append(set(found_cell_ids))

        # Step 3: Find intersection of all filter results (cells matching ALL filters)
        if not filter_cell_ids:
            return []

        cell_ids_set = filter_cell_ids[0]
        for filter_result in filter_cell_ids[1:]:
            cell_ids_set = cell_ids_set.intersection(filter_result)

        if not cell_ids_set:
            return []

        # Load full cell models
        cells = await self.matrix_cell_repo.get_cells_by_ids(list(cell_ids_set))
        answer_sets, answers, citations, entity_refs_by_cell = (
            await self._batch_fetch_cell_data(cells)
        )

        # Fetch all referenced entity set members to enrich entity refs
        all_entity_refs = [ref for refs in entity_refs_by_cell.values() for ref in refs]
        member_ids = list(set(ref.entity_set_member_id for ref in all_entity_refs))
        members = await self.member_repo.get_by_ids(member_ids) if member_ids else []
        members_by_id = {member.id: member for member in members}

        return build_matrix_cells_with_answer_responses(
            cells, answer_sets, answers, citations, entity_refs_by_cell, members_by_id
        )

    # TODO: should this take company id?
    @trace_span
    @transactional
    async def duplicate_matrix(
        self, matrix_id: int, duplicate_request: MatrixDuplicateRequest
    ) -> MatrixDuplicateResponse:
        """Duplicate a matrix with specified entity sets.

        Entity-set based duplication: creates a new matrix with the same structure,
        then copies members from specified entity sets and creates cells.
        """

        logger.info(
            f"Duplicating matrix {matrix_id} with entity sets {duplicate_request.entity_set_ids}"
        )

        # Verify source matrix exists
        source_matrix = await self.get_matrix(matrix_id)
        if not source_matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")
        company_id = source_matrix.company_id

        # Check quotas BEFORE creating anything (prevents bypass via large matrix duplication)
        quota_service = QuotaService(self.db_session)
        await quota_service.check_cell_operation_quota(company_id)

        # Check agentic quota if we're duplicating question entity sets
        entity_set_service = EntitySetService(self.db_session)
        source_entity_sets = await entity_set_service.get_matrix_entity_sets(
            matrix_id, company_id
        )
        has_question_set = any(
            es.id in duplicate_request.entity_set_ids
            and es.entity_type == EntityType.QUESTION
            for es in source_entity_sets
        )
        if has_question_set:
            # Get questions and check if any are agentic
            question_service = QuestionService(self.db_session)
            questions = await question_service.get_questions_for_matrix(matrix_id)
            question_ids = [q.id for q in questions]
            if question_ids:
                agentic_count = await question_service.count_agentic_questions(
                    question_ids, company_id
                )
                if agentic_count > 0:
                    await quota_service.check_agentic_qa_quota(company_id)
                    logger.info(
                        f"Checked agentic quota for matrix duplication with {agentic_count} agentic questions"
                    )

        # Create the new matrix (this creates empty entity sets based on matrix type)
        matrix_create = MatrixCreateModel(
            name=duplicate_request.name,
            description=duplicate_request.description,
            workspace_id=source_matrix.workspace_id,
            company_id=company_id,
            matrix_type=source_matrix.matrix_type,
        )
        duplicate_matrix = await self.create_matrix(matrix_create)

        # Get target entity sets (source_entity_sets already fetched during quota check)
        target_entity_sets = await entity_set_service.get_matrix_entity_sets(
            duplicate_matrix.id, company_id
        )

        # Duplicate template variables if any question entity sets are being duplicated
        template_variable_id_mapping = {}
        if has_question_set:
            template_variable_id_mapping = await self._duplicate_template_variables(
                matrix_id,
                duplicate_matrix.id,
                duplicate_request.template_variable_overrides,
            )

        # Duplicate questions if any question entity sets are being duplicated
        question_id_mapping = {}
        if has_question_set:
            question_service = QuestionService(self.db_session)

            # Use existing duplicate_questions_to_matrix_with_template_mapping method
            duplicated_questions = await question_service.duplicate_questions_to_matrix_with_template_mapping(
                matrix_id,
                duplicate_matrix.id,
                template_variable_id_mapping,
            )

            # Build mapping of old question ID -> new question ID
            # We need to get the source questions to match them up
            source_questions = await question_service.get_questions_for_matrix(
                matrix_id
            )

            # Match by label to create the ID mapping
            for i, source_q in enumerate(source_questions):
                if i < len(duplicated_questions):
                    question_id_mapping[source_q.id] = duplicated_questions[i].id

            logger.info(
                f"Duplicated {len(question_id_mapping)} questions with template variable remapping"
            )

        # Track duplication stats
        entity_sets_duplicated = {}
        target_entity_set_ids = []

        # For each requested entity set, copy members to corresponding target entity set
        for source_entity_set_id in duplicate_request.entity_set_ids:
            # Find source entity set
            source_entity_set = next(
                (es for es in source_entity_sets if es.id == source_entity_set_id), None
            )
            if not source_entity_set:
                logger.warning(
                    f"Source entity set {source_entity_set_id} not found, skipping"
                )
                continue

            # Find corresponding target entity set (match by entity_type and name)
            target_entity_set = next(
                (
                    es
                    for es in target_entity_sets
                    if es.entity_type == source_entity_set.entity_type
                    and es.name == source_entity_set.name
                ),
                None,
            )
            if not target_entity_set:
                logger.warning(
                    f"Target entity set for {source_entity_set.name} not found, skipping"
                )
                continue

            # Copy members from source to target
            # For questions, use the question_id_mapping; for documents, no mapping needed
            entity_id_mapping = (
                question_id_mapping
                if source_entity_set.entity_type == EntityType.QUESTION
                else None
            )
            members_copied = await entity_set_service.duplicate_entity_set_members(
                source_entity_set.id,
                target_entity_set.id,
                company_id,
                entity_id_mapping,
            )

            entity_sets_duplicated[source_entity_set_id] = members_copied
            target_entity_set_ids.append(target_entity_set.id)
            logger.info(
                f"Copied {members_copied} members from entity set {source_entity_set.name}"
            )

        # Create cells for all populated entity sets
        cells_created = 0
        if len(target_entity_set_ids) > 0:
            batch_service = BatchProcessingService(self.db_session)
            created_cells, created_jobs = (
                await batch_service.batch_create_matrix_cells_and_jobs(
                    duplicate_matrix.id,
                    target_entity_set_ids,
                    create_qa_jobs=True,
                )
            )
            cells_created = len(created_cells)
            logger.info(
                f"Created {cells_created} matrix cells and {len(created_jobs)} QA jobs"
            )

        # Build response message
        total_members = sum(entity_sets_duplicated.values())
        message = f"Successfully duplicated matrix '{source_matrix.name}' as '{duplicate_matrix.name}' "
        message += f"with {len(entity_sets_duplicated)} entity sets ({total_members} total members) and {cells_created} cells"

        logger.info(f"Completed matrix duplication: {message}")

        return MatrixDuplicateResponse(
            original_matrix_id=matrix_id,
            duplicate_matrix_id=duplicate_matrix.id,
            entity_sets_duplicated=entity_sets_duplicated,
            cells_created=cells_created,
            message=message,
        )

    @trace_span
    async def _duplicate_template_variables(
        self,
        source_matrix_id: int,
        target_matrix_id: int,
        template_variable_overrides: Optional[List] = None,
    ) -> dict[int, int]:
        """Duplicate template variables from source to target matrix with optional value overrides.

        Returns mapping of old_template_variable_id -> new_template_variable_id
        """

        template_service = MatrixTemplateVariableService()

        # Get all template variables from source matrix
        source_variables = await template_service.get_matrix_template_variables(
            source_matrix_id
        )

        if not source_variables:
            logger.info(
                f"No template variables found in source matrix {source_matrix_id}"
            )
            return {}

        # Create mapping of template variable ID -> override value
        override_mapping = {}
        if template_variable_overrides:
            override_mapping = {
                override.template_variable_id: override.new_value
                for override in template_variable_overrides
            }
            logger.info(f"Template variable overrides provided: {override_mapping}")

        # Create mapping of old ID -> new ID
        id_mapping = {}

        for source_var in source_variables:
            # Use override value if provided, otherwise use original value
            value_to_use = override_mapping.get(source_var.id, source_var.value)

            # Create new template variable in target matrix
            new_var_data = MatrixTemplateVariableCreateModel(
                template_string=source_var.template_string,
                value=value_to_use,
                matrix_id=target_matrix_id,
                company_id=source_var.company_id,
            )

            new_var = await template_service.create_template_variable(
                target_matrix_id, new_var_data, source_var.company_id
            )

            id_mapping[source_var.id] = new_var.id

            if source_var.id in override_mapping:
                logger.info(
                    f"Duplicated template variable {source_var.id} -> {new_var.id}: '{source_var.template_string}' with override value '{value_to_use}'"
                )
            else:
                logger.info(
                    f"Duplicated template variable {source_var.id} -> {new_var.id}: '{source_var.template_string}' with original value '{value_to_use}'"
                )

        logger.info(
            f"Duplicated {len(id_mapping)} template variables with ID mapping: {id_mapping}"
        )
        return id_mapping


def get_matrix_service(db_session: AsyncSession) -> MatrixService:
    """Get matrix service instance."""
    return MatrixService(db_session)
