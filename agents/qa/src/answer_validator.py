"""
Answer validation orchestration for agent QA pipeline.
"""

import json
import logging
from typing import Any, Dict, List

from qa.citation_validation import AnswerValidationResult

from citation_validator import validate_citation_grounding

logger = logging.getLogger(__name__)

VALIDATION_RETRY_THRESHOLD = 0.7


def validate_answer(
    answer_json: str,
    document_contents: Dict[int, str],
) -> AnswerValidationResult:
    """
    Validate all citations in an answer.

    Args:
        answer_json: JSON string from agent
        document_contents: Dict mapping document_id -> full_document_content

    Returns:
        AnswerValidationResult with grounding details
    """
    try:
        answer_data = json.loads(answer_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse answer JSON: {e}")
        return AnswerValidationResult(
            answer_id=0,
            all_citations_grounded=False,
            avg_grounding_score=0.0,
            ungrounded_citations=[],
            validation_details=[],
        )

    citations = _extract_citations(answer_data)

    if not citations:
        logger.info("No citations to validate")
        return AnswerValidationResult(
            answer_id=0,
            all_citations_grounded=True,
            avg_grounding_score=1.0,
            ungrounded_citations=[],
            validation_details=[],
        )

    # Validate each citation
    validations = []
    for idx, citation in enumerate(citations):
        result = validate_citation_grounding(
            citation_index=idx,
            document_id=citation.get("document_id"),
            quote_text=citation.get("quote_text", ""),
            document_contents=document_contents,
        )
        validations.append(result)

    # Calculate metrics
    scores = [v.grounding_score for v in validations]
    avg_score = sum(scores) / len(scores)
    ungrounded = [v.citation_id for v in validations if not v.is_grounded]

    logger.info(
        f"Validation complete: avg_score={avg_score:.2f}, ungrounded={len(ungrounded)}/{len(validations)}"
    )

    return AnswerValidationResult(
        answer_id=0,
        all_citations_grounded=len(ungrounded) == 0,
        avg_grounding_score=avg_score,
        ungrounded_citations=ungrounded,
        validation_details=validations,
    )


def _extract_citations(answer_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract citations from answer JSON."""
    citations = []

    if not answer_data.get("answer_found", True):
        return citations

    # Multi-answer format (items array)
    for item in answer_data.get("items", []):
        for citation in item.get("citations", []):
            citations.append(
                {
                    "document_id": citation.get("document_id"),
                    "quote_text": citation.get("quote_text", ""),
                }
            )

    # Legacy multi-answer format
    for answer in answer_data.get("answers", []):
        for citation in answer.get("citations", []):
            citations.append(
                {
                    "document_id": citation.get("document_id"),
                    "quote_text": citation.get("quote_text", citation.get("quote", "")),
                }
            )

    # Legacy single-answer format
    for citation in answer_data.get("citations", []):
        citations.append(
            {
                "document_id": citation.get("document_id"),
                "quote_text": citation.get("quote_text", citation.get("quote", "")),
            }
        )

    return citations


def should_retry(validation: AnswerValidationResult) -> bool:
    """Determine if answer should be retried based on validation."""
    return validation.avg_grounding_score < VALIDATION_RETRY_THRESHOLD


def build_retry_feedback(validation: AnswerValidationResult) -> str:
    """Build feedback message for agent retry."""
    ungrounded = [v for v in validation.validation_details if not v.is_grounded]

    lines = [
        "CITATION VALIDATION FAILED - Please retry with accurate citations.",
        f"Average grounding score: {validation.avg_grounding_score:.2f}",
        f"Ungrounded citations: {len(ungrounded)}/{len(validation.validation_details)}",
        "\nProblems:",
    ]

    for v in ungrounded:
        lines.append(f"  - Citation {v.citation_id}: {v.error_message}")

    lines.append(
        "\nPlease re-answer with citations that use EXACT quotes from the document content (word-for-word)."
    )
    lines.append(
        "DO NOT paraphrase or add words. Copy the exact text as it appears in the document chunks you read."
    )

    return "\n".join(lines)


def adjust_confidence(answer_json: str, validation: AnswerValidationResult) -> str:
    """Adjust confidence in answer JSON based on validation score."""
    try:
        answer_data = json.loads(answer_json)

        for answer in answer_data.get("answers", []):
            original = answer.get("confidence", 1.0)
            adjusted = original * validation.avg_grounding_score
            answer["confidence"] = adjusted

        return json.dumps(answer_data)

    except Exception as e:
        logger.error(f"Failed to adjust confidence: {e}")
        return answer_json
