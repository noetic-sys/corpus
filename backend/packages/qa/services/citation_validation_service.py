"""
Citation Validation Service

Validates that citations:
1. Are grounded in actual document text (quotes match chunk content)
2. Support the answer claims (relevance checking, future)
"""

from typing import List
import re
from rapidfuzz import fuzz

from packages.documents.repositories.document_chunk_repository import (
    DocumentChunkRepository,
)
from packages.qa.models.domain.citation import CitationModel
from packages.qa.models.domain.answer import AnswerModel
from packages.qa.models.domain.citation_validation import (
    CitationValidationResult,
    AnswerValidationResult,
)
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)

# Thresholds for fuzzy matching
EXACT_MATCH_SCORE = 1.0
FUZZY_MATCH_THRESHOLD = 90  # rapidfuzz score 0-100
PARTIAL_MATCH_THRESHOLD = 70  # Minimum score to consider grounded


class CitationValidationService:
    """Service for validating citation grounding and relevance."""

    def __init__(self):
        self.chunk_repo = DocumentChunkRepository()

    async def validate_answer_citations(
        self,
        answer: AnswerModel,
        citations: List[CitationModel],
        check_relevance: bool = False,
    ) -> AnswerValidationResult:
        """
        Validate all citations for an answer.

        Args:
            answer: The answer to validate
            citations: List of citations for the answer
            check_relevance: Whether to perform LLM-based relevance checking (future)

        Returns:
            AnswerValidationResult with validation details
        """
        if not citations:
            logger.warning(f"Answer {answer.id} has no citations to validate")
            return AnswerValidationResult(
                answer_id=answer.id,
                all_citations_grounded=True,  # No citations = vacuously true
                avg_grounding_score=1.0,
                ungrounded_citations=[],
                validation_details=[],
            )

        validation_results = []
        for citation in citations:
            result = await self.validate_citation_grounding(citation)
            validation_results.append(result)

        # Calculate aggregate metrics
        grounding_scores = [r.grounding_score for r in validation_results]
        avg_grounding_score = sum(grounding_scores) / len(grounding_scores)
        ungrounded_citations = [
            r.citation_id for r in validation_results if not r.is_grounded
        ]
        all_citations_grounded = len(ungrounded_citations) == 0

        if not all_citations_grounded:
            logger.warning(
                f"Answer {answer.id} has {len(ungrounded_citations)} ungrounded citations: {ungrounded_citations}"
            )

        return AnswerValidationResult(
            answer_id=answer.id,
            all_citations_grounded=all_citations_grounded,
            avg_grounding_score=avg_grounding_score,
            ungrounded_citations=ungrounded_citations,
            validation_details=validation_results,
        )

    async def validate_citation_grounding(
        self, citation: CitationModel
    ) -> CitationValidationResult:
        """
        Validate that a citation's quote actually exists in the document chunk.

        Uses rapidfuzz for fuzzy string matching to handle minor variations.

        Args:
            citation: Citation to validate

        Returns:
            CitationValidationResult with grounding status and score
        """
        try:
            # Get the document chunk
            chunk = await self.chunk_repo.get_chunk_by_id(
                citation.document_id, str(citation.chunk_id)
            )

            if not chunk:
                logger.error(
                    f"Citation {citation.id}: Chunk {citation.chunk_id} not found for document {citation.document_id}"
                )
                return CitationValidationResult(
                    citation_id=citation.id,
                    is_grounded=False,
                    grounding_score=0.0,
                    error_message=f"Chunk {citation.chunk_id} not found",
                )

            quote_text = citation.quote_text.strip()
            chunk_content = chunk.content.strip()

            # 1. Exact match check (fast path)
            if quote_text in chunk_content:
                logger.info(
                    f"Citation {citation.id}: Exact match found in chunk {citation.chunk_id}"
                )
                return CitationValidationResult(
                    citation_id=citation.id,
                    is_grounded=True,
                    grounding_score=EXACT_MATCH_SCORE,
                )

            # 2. Normalize text (lowercase, collapse whitespace)
            normalized_quote = self._normalize_text(quote_text)
            normalized_chunk = self._normalize_text(chunk_content)

            # Check exact match on normalized text
            if normalized_quote in normalized_chunk:
                logger.info(
                    f"Citation {citation.id}: Normalized match found in chunk {citation.chunk_id}"
                )
                return CitationValidationResult(
                    citation_id=citation.id,
                    is_grounded=True,
                    grounding_score=0.95,  # Slightly lower for normalization differences
                )

            # 3. Fuzzy matching with rapidfuzz
            # Use partial_ratio to find best matching substring
            partial_score = fuzz.partial_ratio(normalized_quote, normalized_chunk)

            # Convert rapidfuzz score (0-100) to our score (0.0-1.0)
            grounding_score = partial_score / 100.0

            if partial_score >= FUZZY_MATCH_THRESHOLD:
                logger.info(
                    f"Citation {citation.id}: Fuzzy match found (score={partial_score}) in chunk {citation.chunk_id}"
                )
                return CitationValidationResult(
                    citation_id=citation.id,
                    is_grounded=True,
                    grounding_score=grounding_score,
                )

            if partial_score >= PARTIAL_MATCH_THRESHOLD:
                logger.warning(
                    f"Citation {citation.id}: Partial match (score={partial_score}) in chunk {citation.chunk_id}"
                )
                return CitationValidationResult(
                    citation_id=citation.id,
                    is_grounded=True,
                    grounding_score=grounding_score,
                )

            # No sufficient match found - log FULL content for debugging
            logger.error(
                f"Citation {citation.id}: Quote not grounded in chunk {citation.chunk_id} (score={partial_score})"
            )
            logger.error(f"FULL QUOTE TEXT:\n{quote_text}")
            logger.error(f"FULL CHUNK CONTENT:\n{chunk_content}")

            return CitationValidationResult(
                citation_id=citation.id,
                is_grounded=False,
                grounding_score=grounding_score,
                error_message=f"Quote not found in chunk content (similarity={partial_score}%)",
            )

        except Exception as e:
            logger.error(f"Error validating citation {citation.id}: {e}")
            return CitationValidationResult(
                citation_id=citation.id,
                is_grounded=False,
                grounding_score=0.0,
                error_message=str(e),
            )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, collapse whitespace)."""
        # Convert to lowercase
        text = text.lower()
        # Collapse multiple whitespace to single space
        text = re.sub(r"\s+", " ", text)
        # Strip leading/trailing whitespace
        return text.strip()
