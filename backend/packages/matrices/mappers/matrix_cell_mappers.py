from __future__ import annotations
from typing import Optional, List, Dict

from packages.qa.models.domain.answer_set import AnswerSetModel
from packages.qa.models.domain.answer import AnswerModel
from packages.qa.models.domain.citation import CitationModel
from packages.matrices.models.domain.matrix import MatrixCellModel
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixCellEntityReferenceModel,
    MatrixEntitySetMemberModel,
)
from packages.matrices.models.schemas.matrix_cell_answer import (
    MatrixCellAnswerResponse,
    AnswerWithCitations,
)
from packages.matrices.models.schemas.matrix import (
    MatrixCellWithAnswerResponse,
    EntityRefResponse,
)
from packages.qa.models.schemas.citation import CitationMinimalResponse
from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)


def _convert_entity_refs_to_response(
    entity_refs: List[MatrixCellEntityReferenceModel],
    members_by_id: Dict[int, MatrixEntitySetMemberModel],
) -> List[EntityRefResponse]:
    """Convert domain entity refs to response schema, enriching with member data."""
    result = []
    for ref in entity_refs:
        member = members_by_id.get(ref.entity_set_member_id)
        if member:
            result.append(
                EntityRefResponse(
                    id=ref.id,
                    entity_set_id=ref.entity_set_id,
                    entity_set_member_id=ref.entity_set_member_id,
                    entity_type=member.entity_type,
                    entity_id=member.entity_id,
                    role=ref.role,
                    entity_order=ref.entity_order,
                )
            )
    return result


async def build_matrix_cell_answer_response(
    answer_set: AnswerSetModel, matrix_service: "MatrixService"
) -> MatrixCellAnswerResponse:
    """Helper function to build MatrixCellAnswerResponse from answer set."""
    answer_service = matrix_service.answer_service
    answers = await answer_service.get_answers_for_answer_set(answer_set.id)

    if answers:
        # Convert all answers to response format with their citations
        answers_with_citations = []
        for answer in answers:
            if answer.answer_data:
                # Get citations for this specific answer
                answer_citations = []
                if answer.current_citation_set_id:
                    citation_set = await matrix_service.citation_service.get_citation_set_with_citations(
                        answer.current_citation_set_id
                    )
                    if citation_set and citation_set.citations:
                        answer_citations = [
                            CitationMinimalResponse(
                                id=citation.id,
                                citation_order=citation.citation_order,
                                document_id=citation.document_id,
                                quote_text=citation.quote_text,
                            )
                            for citation in citation_set.citations
                        ]

                # Create answer with citations wrapper
                answers_with_citations.append(
                    AnswerWithCitations(
                        answer_data=answer.answer_data.model_dump(),
                        citations=answer_citations,
                    )
                )

        return MatrixCellAnswerResponse(
            id=answer_set.id,  # Answer set ID
            matrix_cell_id=answer_set.matrix_cell_id,
            question_type_id=answer_set.question_type_id,
            answers=answers_with_citations,  # List of answers with citations
            answer_found=answer_set.answer_found,
            confidence=answer_set.confidence,
            processing_metadata=None,  # Not stored in new system
            created_at=answer_set.created_at,
            updated_at=answer_set.updated_at,
        )
    else:
        # Handle case where answer set exists but has no answers (not found case)
        return MatrixCellAnswerResponse(
            id=answer_set.id,  # Answer set ID
            matrix_cell_id=answer_set.matrix_cell_id,
            question_type_id=answer_set.question_type_id,
            answers=[],  # Empty list for not found
            answer_found=answer_set.answer_found,  # Should be False
            confidence=answer_set.confidence,
            processing_metadata=None,
            created_at=answer_set.created_at,
            updated_at=answer_set.updated_at,
        )


async def build_matrix_cell_with_answer_response(
    cell: MatrixCellModel,
    current_answer_set: Optional[AnswerSetModel],
    matrix_service: "MatrixService",
    entity_refs: Optional[List[MatrixCellEntityReferenceModel]] = None,
) -> MatrixCellWithAnswerResponse:
    """Helper function to build MatrixCellWithAnswerResponse from cell and answer set.

    Args:
        cell: The matrix cell model
        current_answer_set: Optional answer set for the cell
        matrix_service: Matrix service for loading data
        entity_refs: Optional pre-loaded entity references. If not provided, will be loaded.
    """
    current_answer_response = None
    if current_answer_set:
        current_answer_response = await build_matrix_cell_answer_response(
            current_answer_set, matrix_service
        )

    # Load entity refs if not provided
    if entity_refs is None:
        ref_repo = CellEntityReferenceRepository()
        entity_refs = await ref_repo.get_by_cell_id(cell.id)

    return MatrixCellWithAnswerResponse(
        id=cell.id,
        matrix_id=cell.matrix_id,
        entity_refs=_convert_entity_refs_to_response(entity_refs),
        current_answer_set_id=cell.current_answer_set_id,
        status=cell.status,
        created_at=cell.created_at,
        updated_at=cell.updated_at,
        current_answer=current_answer_response,
    )


def _build_lookups(
    answer_sets: List[AnswerSetModel],
    answers: List[AnswerModel],
    citations: List[CitationModel],
) -> tuple[dict, dict, dict]:
    """Build lookup dictionaries for fast access."""
    answer_sets_by_id = {a.id: a for a in answer_sets}

    answers_by_set_id = {}
    for answer in answers:
        if answer.answer_set_id not in answers_by_set_id:
            answers_by_set_id[answer.answer_set_id] = []
        answers_by_set_id[answer.answer_set_id].append(answer)

    citations_by_set_id = {}
    for citation in citations:
        if citation.citation_set_id not in citations_by_set_id:
            citations_by_set_id[citation.citation_set_id] = []
        citations_by_set_id[citation.citation_set_id].append(citation)

    return answer_sets_by_id, answers_by_set_id, citations_by_set_id


def _build_citations_for_answer(
    answer: AnswerModel, citations_by_set_id: dict
) -> List[CitationMinimalResponse]:
    """Build citation responses for a single answer."""
    if not answer.current_citation_set_id:
        return []

    answer_citations = citations_by_set_id.get(answer.current_citation_set_id, [])
    return [
        CitationMinimalResponse(
            id=citation.id,
            citation_order=citation.citation_order,
            document_id=citation.document_id,
            quote_text=citation.quote_text,
        )
        for citation in answer_citations
    ]


def _build_answers_with_citations(
    answers: List[AnswerModel], citations_by_set_id: dict
) -> List[AnswerWithCitations]:
    """Build answers with their citations."""
    answers_with_citations = []
    for answer in answers:
        if answer.answer_data:
            citations = _build_citations_for_answer(answer, citations_by_set_id)
            answers_with_citations.append(
                AnswerWithCitations(
                    answer_data=answer.answer_data.model_dump(),
                    citations=citations,
                )
            )
    return answers_with_citations


def _build_answer_response(
    answer_set: AnswerSetModel,
    answers_by_set_id: dict,
    citations_by_set_id: dict,
) -> MatrixCellAnswerResponse:
    """Build answer response for a single answer set."""
    cell_answers = answers_by_set_id.get(answer_set.id, [])

    answers_with_citations = []
    if cell_answers:
        answers_with_citations = _build_answers_with_citations(
            cell_answers, citations_by_set_id
        )

    return MatrixCellAnswerResponse(
        id=answer_set.id,
        matrix_cell_id=answer_set.matrix_cell_id,
        question_type_id=answer_set.question_type_id,
        answers=answers_with_citations,
        answer_found=answer_set.answer_found,
        confidence=answer_set.confidence,
        processing_metadata=None,
        created_at=answer_set.created_at,
        updated_at=answer_set.updated_at,
    )


def build_matrix_cells_with_answer_responses(
    cells: List[MatrixCellModel],
    answer_sets: List[AnswerSetModel],
    answers: List[AnswerModel],
    citations: List[CitationModel],
    entity_refs_by_cell: Dict[int, List[MatrixCellEntityReferenceModel]],
    members_by_id: Dict[int, MatrixEntitySetMemberModel],
) -> List[MatrixCellWithAnswerResponse]:
    """Pure transformation: build responses from flat lists.

    Args:
        cells: List of matrix cell models
        answer_sets: List of answer sets
        answers: List of answers
        citations: List of citations
        entity_refs_by_cell: Dict mapping cell_id to list of entity references
        members_by_id: Dict mapping member_id to entity set member
    """
    answer_sets_by_id, answers_by_set_id, citations_by_set_id = _build_lookups(
        answer_sets, answers, citations
    )

    result = []
    for cell in cells:
        current_answer_response = None

        if cell.current_answer_set_id:
            answer_set = answer_sets_by_id.get(cell.current_answer_set_id)
            if answer_set:
                current_answer_response = _build_answer_response(
                    answer_set, answers_by_set_id, citations_by_set_id
                )

        # Get entity refs for this cell
        entity_refs = entity_refs_by_cell.get(cell.id, [])

        cell_response = MatrixCellWithAnswerResponse(
            id=cell.id,
            matrix_id=cell.matrix_id,
            entity_refs=_convert_entity_refs_to_response(entity_refs, members_by_id),
            current_answer_set_id=cell.current_answer_set_id,
            status=cell.status,
            created_at=cell.created_at,
            updated_at=cell.updated_at,
            current_answer=current_answer_response,
        )
        result.append(cell_response)

    return result
