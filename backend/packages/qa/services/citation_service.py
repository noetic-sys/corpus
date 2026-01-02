from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.qa.repositories.citation_repository import (
    CitationSetRepository,
    CitationRepository,
)
from packages.qa.models.domain.citation import (
    CitationSetModel,
    CitationSetWithCitationsModel,
    CitationSetCreateModel,
    CitationSetCreateOnlyModel,
    CitationModel,
    CitationCreateModel,
)

logger = get_logger(__name__)


class CitationService:
    """Service for handling citation and citation set operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.citation_set_repo = CitationSetRepository(db_session)
        self.citation_repo = CitationRepository(db_session)

    @trace_span
    async def create_citation_set_with_citations(
        self, citation_set_data: CitationSetCreateModel, company_id: int
    ) -> CitationSetModel:
        """Create a citation set with its citations in a single transaction."""
        logger.info(
            f"Creating citation set for answer {citation_set_data.answer_id} with {len(citation_set_data.citations)} citations"
        )

        # Ensure company_id matches
        if citation_set_data.company_id != company_id:
            raise ValueError(
                "Citation set company_id must match the provided company_id"
            )

        # Create the citation set first
        citation_set_create = CitationSetCreateOnlyModel(
            answer_id=citation_set_data.answer_id,
            company_id=citation_set_data.company_id,
        )
        citation_set = await self.citation_set_repo.create(citation_set_create)
        logger.info(f"Created citation set with ID: {citation_set.id}")

        # Create all citations for this set
        if citation_set_data.citations:
            citation_models = []
            for citation_data in citation_set_data.citations:
                # Validate citation company_id matches
                if citation_data.company_id != company_id:
                    raise ValueError(
                        "All citation company_ids must match the provided company_id"
                    )

                # Create a new citation model with the citation_set_id
                citation_create = CitationCreateModel(
                    citation_set_id=citation_set.id,
                    document_id=citation_data.document_id,
                    company_id=citation_data.company_id,
                    quote_text=citation_data.quote_text,
                    citation_order=citation_data.citation_order,
                )
                citation = await self.citation_repo.create(citation_create)
                citation_models.append(citation)
                logger.debug(
                    f"Created citation {citation.id} with order {citation.citation_order}"
                )

            logger.info(
                f"Created {len(citation_models)} citations for citation set {citation_set.id}"
            )

        # Return citation set with citations loaded
        return await self.get_citation_set_with_citations(citation_set.id, company_id)

    @trace_span
    async def get_citation_set(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> Optional[CitationSetModel]:
        """Get citation set by ID without loading citations."""
        return await self.citation_set_repo.get_by_id(citation_set_id, company_id)

    @trace_span
    async def get_citation_set_with_citations(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> Optional[CitationSetWithCitationsModel]:
        """Get citation set with all citations loaded."""
        return await self.citation_set_repo.get_with_citations(
            citation_set_id, company_id
        )

    @trace_span
    async def get_citation_sets_for_answer(
        self, answer_id: int, company_id: Optional[int] = None
    ) -> List[CitationSetModel]:
        """Get all citation sets for an answer."""
        return await self.citation_set_repo.get_by_answer_id(answer_id, company_id)

    @trace_span
    async def get_citations_for_set(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations for a citation set, ordered by citation_order."""
        return await self.citation_repo.get_by_citation_set_id(
            citation_set_id, company_id
        )

    @trace_span
    async def get_citations_by_citation_set_ids(
        self, citation_set_ids: List[int], company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Batch fetch all citations for multiple citation sets."""
        return await self.citation_repo.get_by_citation_set_ids(
            citation_set_ids, company_id
        )

    @trace_span
    async def get_citations_for_document(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations that reference a specific document."""
        return await self.citation_repo.get_by_document_id(document_id, company_id)

    @trace_span
    async def create_citation(
        self, citation_data: CitationCreateModel, citation_set_id: int, company_id: int
    ) -> CitationModel:
        """Create a single citation within an existing citation set."""
        logger.info(
            f"Creating citation for citation set {citation_set_id}, document {citation_data.document_id}"
        )

        # Ensure company_id matches
        if citation_data.company_id != company_id:
            raise ValueError("Citation company_id must match the provided company_id")

        citation = await self.citation_repo.create(citation_data)
        logger.info(f"Created citation with ID: {citation.id}")
        return citation

    @trace_span
    async def get_citations_for_answer_set(
        self, answer_service, answer_set_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations for all answers in an answer set."""
        logger.debug(f"Getting citations for answer set {answer_set_id}")

        citations = []

        # Get all answers for the answer set
        answers = await answer_service.get_answers_for_answer_set(
            answer_set_id, company_id
        )

        for answer in answers:
            if answer.current_citation_set_id:
                # Get citations for this answer's citation set
                citation_set = await self.get_citation_set_with_citations(
                    answer.current_citation_set_id, company_id
                )
                if citation_set and citation_set.citations:
                    citations.extend(citation_set.citations)

        # Sort by citation order
        citations.sort(key=lambda x: x.citation_order)
        logger.debug(f"Found {len(citations)} citations for answer set {answer_set_id}")
        return citations
