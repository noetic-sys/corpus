"""Unit tests for AI response models using pydantic."""

import json
import pytest
from pydantic import ValidationError
from packages.qa.models.domain.ai_responses import (
    CurrencyResponse,
    DateResponse,
    SelectResponse,
    TextResponse,
    CitationItem,
)
from tests.conftest import AI_RESPONSE_SAMPLES, SAMPLE_OPTIONS


class TestCurrencyResponse:
    """Unit tests for CurrencyResponse JSON model."""

    def test_valid_currency_response(self):
        """Test parsing valid currency JSON response with single item."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["valid"]
        data = json.loads(json_str)

        response = CurrencyResponse(**data)
        assert len(response.items) == 1
        assert response.items[0].amount == 1250.50
        assert response.items[0].code == "USD"

    def test_multiple_currency_items(self):
        """Test parsing currency response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["multiple"]
        data = json.loads(json_str)

        response = CurrencyResponse(**data)
        assert len(response.items) == 2
        assert response.items[0].amount == 1250.50
        assert response.items[0].code == "USD"
        assert response.items[1].amount == 1100.00
        assert response.items[1].code == "EUR"

    def test_empty_currency_response(self):
        """Test parsing empty currency response."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["empty"]
        data = json.loads(json_str)

        response = CurrencyResponse(**data)
        assert len(response.items) == 0
        assert response.items == []

    def test_currency_code_normalization(self):
        """Test that currency codes are normalized to uppercase."""
        data = {"items": [{"amount": 100, "code": "eur", "citations": []}]}

        response = CurrencyResponse(**data)
        assert response.items[0].code == "EUR"

    def test_invalid_currency_code(self):
        """Test validation error for invalid currency code."""
        data = {"items": [{"amount": 100, "code": "US", "citations": []}]}

        with pytest.raises(ValidationError) as exc_info:
            CurrencyResponse(**data)
        assert "Invalid currency code" in str(exc_info.value)

    def test_currency_with_decimals(self):
        """Test currency with decimal places."""
        data = {"items": [{"amount": 1234567.89, "code": "JPY", "citations": []}]}

        response = CurrencyResponse(**data)
        assert response.items[0].amount == 1234567.89
        assert response.items[0].code == "JPY"

    def test_currency_with_citations(self):
        """Test currency with citations."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["with_citations"]
        data = json.loads(json_str)

        response = CurrencyResponse(**data)
        assert len(response.items) == 1
        assert response.items[0].amount == 1250.50
        assert response.items[0].code == "USD"
        assert len(response.items[0].citations) == 1
        assert response.items[0].citations[0].order == 1
        assert (
            response.items[0].citations[0].quote_text
            == "The contract value is $1,250.50"
        )
        assert response.items[0].citations[0].document_id == 1


class TestDateResponse:
    """Unit tests for DateResponse JSON model."""

    def test_valid_date_response(self):
        """Test parsing valid date JSON response with single item."""
        json_str = AI_RESPONSE_SAMPLES["date"]["valid"]
        data = json.loads(json_str)

        response = DateResponse(**data)
        assert len(response.items) == 1
        assert response.items[0].value == "2024-03-15"

    def test_multiple_date_items(self):
        """Test parsing date response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["date"]["multiple"]
        data = json.loads(json_str)

        response = DateResponse(**data)
        assert len(response.items) == 2
        assert response.items[0].value == "2024-03-15"
        assert response.items[1].value == "2024-03-16"

    def test_empty_date_response(self):
        """Test parsing empty date response."""
        json_str = AI_RESPONSE_SAMPLES["date"]["empty"]
        data = json.loads(json_str)

        response = DateResponse(**data)
        assert len(response.items) == 0
        assert response.items == []

    def test_invalid_date_format(self):
        """Test validation error for invalid date format."""
        data = {"items": [{"value": "03/15/2024", "citations": []}]}

        with pytest.raises(ValidationError) as exc_info:
            DateResponse(**data)
        assert "Invalid date format" in str(exc_info.value)

    def test_date_edge_cases(self):
        """Test date with edge case values."""
        # Leap year date
        data = {"items": [{"value": "2024-02-29", "citations": []}]}

        response = DateResponse(**data)
        assert response.items[0].value == "2024-02-29"

        # First day of year
        data = {"items": [{"value": "2024-01-01", "citations": []}]}

        response = DateResponse(**data)
        assert response.items[0].value == "2024-01-01"


class TestSelectResponse:
    """Unit tests for unified SelectResponse JSON model."""

    def test_single_select_response(self):
        """Test parsing select response with single option."""
        json_str = AI_RESPONSE_SAMPLES["select"]["single"]
        data = json.loads(json_str)

        response = SelectResponse(**data)
        assert len(response.options) == 1
        assert response.options[0].value == "Option A"
        assert response.options[0].citations == []

    def test_multiple_select_response(self):
        """Test parsing select response with multiple options."""
        json_str = AI_RESPONSE_SAMPLES["select"]["multiple"]
        data = json.loads(json_str)

        response = SelectResponse(**data)
        assert len(response.options) == 3
        assert [opt.value for opt in response.options] == [
            "Option A",
            "Option B",
            "Option C",
        ]
        assert all(opt.citations == [] for opt in response.options)

    def test_empty_select_response(self):
        """Test parsing empty select response."""
        json_str = AI_RESPONSE_SAMPLES["select"]["empty"]
        data = json.loads(json_str)

        response = SelectResponse(**data)
        assert len(response.options) == 0
        assert response.options == []

    def test_select_with_special_chars(self):
        """Test select with special characters."""
        data = {"options": [{"value": "Yes - With & Special Chars", "citations": []}]}

        response = SelectResponse(**data)
        assert response.options[0].value == "Yes - With & Special Chars"

    def test_select_with_duplicates(self):
        """Test select with duplicate options."""
        data = {
            "options": [
                {"value": SAMPLE_OPTIONS[0], "citations": []},
                {"value": SAMPLE_OPTIONS[0], "citations": []},
                {"value": SAMPLE_OPTIONS[1], "citations": []},
            ]
        }

        response = SelectResponse(**data)
        # Should preserve duplicates as-is
        assert [opt.value for opt in response.options] == [
            SAMPLE_OPTIONS[0],
            SAMPLE_OPTIONS[0],
            SAMPLE_OPTIONS[1],
        ]


class TestTextResponse:
    """Unit tests for TextResponse JSON model."""

    def test_valid_text_response(self):
        """Test parsing valid text JSON response with single item."""
        json_str = AI_RESPONSE_SAMPLES["text"]["valid"]
        data = json.loads(json_str)

        response = TextResponse(**data)
        assert len(response.items) == 1
        assert response.items[0].value == "This is the answer text"

    def test_multiple_text_items(self):
        """Test parsing text response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["text"]["multiple"]
        data = json.loads(json_str)

        response = TextResponse(**data)
        assert len(response.items) == 2
        assert response.items[0].value == "First answer"
        assert response.items[1].value == "Second answer"

    def test_empty_text_response(self):
        """Test parsing empty text response."""
        json_str = AI_RESPONSE_SAMPLES["text"]["empty"]
        data = json.loads(json_str)

        response = TextResponse(**data)
        assert len(response.items) == 0
        assert response.items == []

    def test_text_with_newlines(self):
        """Test text with newlines and formatting."""
        data = {"items": [{"value": "Line 1\nLine 2\nLine 3", "citations": []}]}

        response = TextResponse(**data)
        assert response.items[0].value == "Line 1\nLine 2\nLine 3"

    def test_text_with_special_characters(self):
        """Test text with special characters."""
        data = {"items": [{"value": 'Q&A: <important> "quoted"', "citations": []}]}

        response = TextResponse(**data)
        assert response.items[0].value == 'Q&A: <important> "quoted"'

    def test_text_with_citations(self):
        """Test text with citations."""
        json_str = AI_RESPONSE_SAMPLES["text"]["with_citations"]
        data = json.loads(json_str)

        response = TextResponse(**data)
        assert len(response.items) == 1
        assert response.items[0].value == "This answer has citations [[cite:1]]"
        assert len(response.items[0].citations) == 1
        assert response.items[0].citations[0].order == 1
        assert response.items[0].citations[0].quote_text == "This is the source text"
        assert response.items[0].citations[0].document_id == 1


class TestJSONEdgeCases:
    """Test edge cases in JSON parsing."""

    def test_whitespace_handling(self):
        """Test that whitespace is preserved in JSON strings."""
        data = {"items": [{"value": "  Trimmed text  ", "citations": []}]}

        response = TextResponse(**data)
        # JSON preserves whitespace in strings
        assert response.items[0].value == "  Trimmed text  "

    def test_empty_string_values(self):
        """Test parsing empty string values."""
        data = {"items": [{"value": "", "citations": []}]}

        response = TextResponse(**data)
        assert response.items[0].value == ""

    def test_unicode_characters(self):
        """Test parsing unicode characters."""
        data = {
            "items": [
                {"value": "Unicode: 🚀 émojis and spëcial chârs", "citations": []}
            ]
        }

        response = TextResponse(**data)
        assert response.items[0].value == "Unicode: 🚀 émojis and spëcial chârs"

    def test_malformed_json(self):
        """Test that malformed JSON raises appropriate errors."""
        malformed = '{"items": [{"value": "Unclosed'

        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed)


class TestCitationModels:
    """Test citation JSON models."""

    def test_citation_item_creation(self):
        """Test creating a single citation item."""
        citation_data = {
            "order": 1,
            "quote_text": "This is a test quote",
            "document_id": 1,
        }

        citation = CitationItem(**citation_data)
        assert citation.order == 1
        assert citation.quote_text == "This is a test quote"
        assert citation.document_id == 1

    def test_multiple_citations(self):
        """Test creating multiple citations."""
        citations_data = [
            {"order": 1, "quote_text": "First quote", "document_id": 1},
            {"order": 2, "quote_text": "Second quote", "document_id": 1},
        ]

        citations = [CitationItem(**item) for item in citations_data]
        assert len(citations) == 2
        assert citations[0].order == 1
        assert citations[0].quote_text == "First quote"
        assert citations[0].document_id == 1
        assert citations[1].order == 2
        assert citations[1].quote_text == "Second quote"
        assert citations[1].document_id == 1

    def test_citation_with_special_characters(self):
        """Test citation with special characters in quote text."""
        citation_data = {
            "order": 1,
            "quote_text": 'Quote with & special <chars> "quoted"',
            "document_id": 1,
        }

        citation = CitationItem(**citation_data)
        assert citation.order == 1
        assert citation.quote_text == 'Quote with & special <chars> "quoted"'
        assert citation.document_id == 1


# Note: Not found responses are now handled by AIResponseParser returning AIAnswerSet.not_found()
# when it sees <<ANSWER_NOT_FOUND>>, not by the JSON models
