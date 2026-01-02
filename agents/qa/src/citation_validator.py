"""
Citation validation logic for agent QA pipeline.
"""

import logging
from typing import Dict

from qa.citation_validation import CitationValidationResult
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

EXACT_MATCH_SCORE = 1.0
FUZZY_MATCH_THRESHOLD = 90
PARTIAL_MATCH_THRESHOLD = 70


def validate_citation_grounding(
    citation_index: int,
    document_id: int,
    quote_text: str,
    document_contents: Dict[int, str],
) -> CitationValidationResult:
    """
    Validate that a citation's quote exists in the document content.

    Args:
        citation_index: Index of citation for logging
        document_id: Document ID to validate against
        quote_text: Quote text from citation
        document_contents: Dict mapping document_id -> full_document_content

    Returns:
        CitationValidationResult with grounding status
    """
    if not document_id:
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=False,
            grounding_score=0.0,
            error_message="Missing document_id",
        )

    if not quote_text:
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=False,
            grounding_score=0.0,
            error_message="Missing quote_text",
        )

    document_content = document_contents.get(document_id)
    if not document_content:
        logger.error(f"Citation {citation_index}: Document {document_id} not found")
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=False,
            grounding_score=0.0,
            error_message=f"Document {document_id} not found",
        )

    quote_text = quote_text.strip()
    document_content = document_content.strip()

    # Exact match
    if quote_text in document_content:
        logger.info(f"Citation {citation_index}: Exact match in document {document_id}")
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=True,
            grounding_score=EXACT_MATCH_SCORE,
        )

    # Normalized match
    import re

    normalized_quote = re.sub(r"\s+", " ", quote_text.lower()).strip()
    normalized_document = re.sub(r"\s+", " ", document_content.lower()).strip()

    if normalized_quote in normalized_document:
        logger.info(
            f"Citation {citation_index}: Normalized match in document {document_id}"
        )
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=True,
            grounding_score=0.95,
        )

    # Fuzzy match
    partial_score = fuzz.partial_ratio(normalized_quote, normalized_document)
    grounding_score = partial_score / 100.0

    if partial_score >= FUZZY_MATCH_THRESHOLD:
        logger.info(
            f"Citation {citation_index}: Fuzzy match (score={partial_score}) in document {document_id}"
        )
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=True,
            grounding_score=grounding_score,
        )

    if partial_score >= PARTIAL_MATCH_THRESHOLD:
        logger.warning(
            f"Citation {citation_index}: Partial match (score={partial_score}) in document {document_id}"
        )
        return CitationValidationResult(
            citation_id=citation_index,
            is_grounded=True,
            grounding_score=grounding_score,
        )

    # Not grounded - log full content (truncate for readability)
    logger.error(
        f"Citation {citation_index}: Quote not grounded in document {document_id} (score={partial_score})"
    )
    logger.error(f"QUOTE TEXT:\n{quote_text}")
    logger.error(f"DOCUMENT CONTENT (first 500 chars):\n{document_content[:500]}...")

    return CitationValidationResult(
        citation_id=citation_index,
        is_grounded=False,
        grounding_score=grounding_score,
        error_message=f"Quote not found (similarity={partial_score}%)",
    )
