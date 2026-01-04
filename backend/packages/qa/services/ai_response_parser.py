"""Parser for AI JSON responses to domain models."""

import json
import re
from datetime import datetime
from typing import Optional, List

from common.core.otel_axiom_exporter import get_logger
from packages.qa.models.domain.ai_responses import (
    CurrencyResponse,
    DateResponse,
    SelectResponse,
    TextResponse,
    CitationItem,
)
from packages.qa.models.domain.answer_data import AIAnswerSet
from questions.question_type import QuestionTypeName
from packages.qa.models.domain.answer_data import (
    TextAnswerData,
    DateAnswerData,
    CurrencyAnswerData,
    SelectAnswerData,
)
from packages.qa.models.domain.citation import CitationReference

logger = get_logger(__name__)


class AIResponseParser:
    """Parses AI JSON responses into domain answer models - always returns lists."""

    @staticmethod
    def parse_response(
        json_response: str,
        question_type: Optional[QuestionTypeName],
        options: Optional[List[str]] = None,
    ) -> AIAnswerSet:
        """Parse JSON response from AI into structured answer set.

        Args:
            json_response: Raw JSON string from AI
            question_type: Type of question being answered
            options: Available options for select questions

        Returns:
            AIAnswerSet with answer_found status and list of answers
        """
        try:
            logger.info(
                f"RAW AI RESPONSE (len={len(json_response) if json_response else 0}): {repr(json_response)}"
            )

            # Clean up the response
            json_response = AIResponseParser._clean_response(json_response)
            logger.info(
                f"Parsing AI response for type {question_type.name if question_type else 'DEFAULT'}"
            )
            logger.info(
                f"After cleaning (len={len(json_response)}): {repr(json_response)}"
            )

            # Check for not found format - now returns empty answer set
            if json_response in [
                "<<ANSWER_NOT_FOUND>>",
                '"<<ANSWER_NOT_FOUND>>"',
                "'<<ANSWER_NOT_FOUND>>'",
            ]:
                logger.info("Response indicates no answer found")
                return AIAnswerSet.not_found()

            # Parse based on question type - all return AIAnswerSet now
            if question_type == QuestionTypeName.CURRENCY:
                logger.info("Parsing as CURRENCY type")
                answers = AIResponseParser._parse_currency(json_response)
            elif question_type == QuestionTypeName.DATE:
                logger.info("Parsing as DATE type")
                answers = AIResponseParser._parse_date(json_response)
            elif question_type == QuestionTypeName.SELECT:
                logger.info(f"Parsing as SELECT type with {len(options or [])} options")
                # Unified select parser
                answers = AIResponseParser._parse_select(json_response, options)
            else:
                logger.info(
                    f"Parsing as TEXT type (default for {question_type.name if question_type else 'unknown'})"
                )
                # Default to text for SHORT_ANSWER, LONG_ANSWER, or unknown
                answers = AIResponseParser._parse_text(json_response)

            # Return structured response with found answers
            if answers:
                logger.info(f"Successfully parsed {len(answers)} answer(s)")
                return AIAnswerSet.found(answers)
            else:
                logger.info("No answers extracted from response")
                return AIAnswerSet.not_found()

        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            raise e

    @staticmethod
    def _parse_currency(json_response: str) -> List[CurrencyAnswerData]:
        """Parse currency JSON response - returns list."""
        try:
            data = json.loads(json_response)
            currency_resp = CurrencyResponse(**data)
            currency_answers = []
            logger.info(f"Found {len(currency_resp.items)} currency items in response")
            for item in currency_resp.items:
                # Parse citations from JSON
                citations = AIResponseParser._parse_citations_from_json(item.citations)

                currency_answers.append(
                    CurrencyAnswerData(
                        value=f"{item.amount} {item.code}",
                        amount=item.amount,
                        currency=item.code,
                        confidence=item.confidence,
                        citations=citations,
                    )
                )
                logger.debug(
                    f"Parsed currency with {len(citations)} citations: {item.amount} {item.code}"
                )
            return currency_answers
        except Exception as e:
            logger.warning(f"Failed to parse currency JSON: {e}")
            raise e

    @staticmethod
    def _parse_date(json_response: str) -> List[DateAnswerData]:
        """Parse date JSON response - returns list."""
        try:
            data = json.loads(json_response)
            date_resp = DateResponse(**data)
            date_answers = []
            logger.info(f"Found {len(date_resp.items)} date items in response")
            for item in date_resp.items:
                # Parse citations from JSON
                citations = AIResponseParser._parse_citations_from_json(item.citations)

                date_answers.append(
                    DateAnswerData(
                        value=item.value,
                        parsed_date=item.value,
                        confidence=item.confidence,
                        citations=citations,
                    )
                )
                logger.debug(
                    f"Parsed date with {len(citations)} citations: {item.value}"
                )
            return date_answers
        except Exception as e:
            logger.warning(f"Failed to parse date JSON: {e}")
            raise e

    @staticmethod
    def _parse_select(
        json_response: str, options: Optional[List[str]]
    ) -> List[SelectAnswerData]:
        """Parse select JSON response - returns multiple SelectAnswerData objects, one per selected option."""
        try:
            data = json.loads(json_response)
            select_resp = SelectResponse(**data)
            if not select_resp.options:
                logger.info("No options found in SELECT response")
                # Return empty list for no options
                return []

            option_values = [opt.value for opt in select_resp.options]
            logger.info(
                f"Found {len(select_resp.options)} selected options in response: {option_values}"
            )

            # Return one SelectAnswerData per selected option
            select_answers = []
            seen_options = set()

            for opt_obj in select_resp.options:
                opt_value = opt_obj.value
                if opt_value not in seen_options:
                    option_id = AIResponseParser._find_option_id(opt_value, options)
                    if option_id:
                        # Parse citations from JSON
                        citations = AIResponseParser._parse_citations_from_json(
                            opt_obj.citations
                        )

                        select_answers.append(
                            SelectAnswerData(
                                option_id=option_id,
                                option_value=opt_value,
                                confidence=opt_obj.confidence,
                                citations=citations,
                            )
                        )
                        seen_options.add(opt_value)
                        logger.debug(
                            f"Mapped option '{opt_value}' to ID {option_id} with {len(citations)} citations"
                        )
                    else:
                        logger.warning(
                            f"Could not find option ID for '{opt_value}' in provided options"
                        )

            logger.info(
                f"Successfully parsed {len(select_answers)} valid SELECT answers"
            )
            return select_answers
        except Exception as e:
            logger.warning(f"Failed to parse select JSON: {e}")
            raise e

    @staticmethod
    def _parse_text(json_response: str) -> List[TextAnswerData]:
        """Parse text JSON response - returns list."""
        try:
            data = json.loads(json_response)
            text_resp = TextResponse(**data)
            text_answers = []
            logger.info(f"Found {len(text_resp.items)} text items in response")
            for item in text_resp.items:
                # Parse citations from JSON
                citations = AIResponseParser._parse_citations_from_json(item.citations)

                # Validate inline citations against citation list
                validated_text = AIResponseParser._extract_inline_citations(
                    item.value, citations
                )

                text_answers.append(
                    TextAnswerData(
                        value=validated_text,
                        confidence=item.confidence,
                        citations=citations,
                    )
                )
                logger.debug(
                    f"Parsed text answer with {len(citations)} citations: {item.value[:50]}{'...' if len(item.value) > 50 else ''}"
                )
            return text_answers
        except Exception as e:
            logger.error(f"Failed to parse text JSON: {e}")
            raise

    @staticmethod
    def _find_option_id(
        option_text: str, options: Optional[List[str]]
    ) -> Optional[int]:
        """Find the option ID (1-based index) for the given option text."""
        if not options:
            return None
        for i, option in enumerate(options):
            if option.lower() == option_text.lower():
                return i + 1  # Option IDs are 1-based
        return None

    @staticmethod
    def _is_iso_date(date_str: str) -> bool:
        """Check if string is in valid ISO date format and represents a valid date."""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return False

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _parse_citations_from_json(
        citations: List[CitationItem], document_id: int = 1
    ) -> List[CitationReference]:
        """Parse citations from JSON CitationItem list into CitationReference objects.

        Args:
            citations: List of citation items from AI response
            document_id: Default document ID (used as fallback if not in citation)
        """
        citation_refs = []
        for citation_item in citations:
            # Use document_id from citation, fall back to default parameter
            doc_id = (
                citation_item.document_id if citation_item.document_id else document_id
            )
            citation_refs.append(
                CitationReference(
                    citation_number=citation_item.order,
                    quote_text=citation_item.quote_text,
                    document_id=doc_id,
                )
            )
            logger.debug(
                f"Parsed citation {citation_item.order} for document {doc_id}: {citation_item.quote_text[:50]}..."
            )
        return citation_refs

    @staticmethod
    def _extract_inline_citations(text: str, citations: List[CitationReference]) -> str:
        """Extract inline citations from text and validate they match citation list."""
        # Find all inline citation references [[cite:1]], [[cite:2]], etc.
        inline_pattern = r"\[\[cite:(\d+)\]\]"
        matches = re.findall(inline_pattern, text)

        if matches:
            logger.info(f"Found inline citations: {matches}")
            # Validate that all inline citations have corresponding citation data
            citation_numbers = {c.citation_number for c in citations}
            for match in matches:
                cite_num = int(match)
                if cite_num not in citation_numbers:
                    logger.warning(
                        f"Inline citation [[cite:{cite_num}]] has no matching citation data"
                    )

        return text

    @staticmethod
    def _clean_response(json_response: str) -> str:
        """Clean up AI response removing markdown code blocks, trailing commas, and extra whitespace."""
        # Strip whitespace
        json_response = json_response.strip()

        # Remove markdown code blocks like ```json ... ``` or ``` ... ```
        if json_response.startswith("```"):
            lines = json_response.split("\n")
            # Remove first line (```json or ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            # Remove last line if it's ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            json_response = "\n".join(lines).strip()

        # Remove trailing commas before closing braces/brackets (common LLM mistake)
        json_response = re.sub(r",(\s*[}\]])", r"\1", json_response)

        return json_response
