"""Unit tests for AIResponseParser service."""

import pytest
from packages.qa.services.ai_response_parser import AIResponseParser
from questions.question_type import QuestionTypeName
from packages.qa.models.domain.answer_data import (
    TextAnswerData,
    DateAnswerData,
    CurrencyAnswerData,
    SelectAnswerData,
)
from packages.qa.models.domain.answer_data import AIAnswerSet
from tests.conftest import AI_RESPONSE_SAMPLES, SAMPLE_OPTIONS


class TestAIResponseParser:
    """Unit tests for AIResponseParser."""

    def test_parse_not_found_response(self):
        """Test parsing <<ANSWER_NOT_FOUND>> responses."""
        not_found_response = AI_RESPONSE_SAMPLES["not_found"]

        result = AIResponseParser.parse_response(
            not_found_response, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_not_found_response_currency(self):
        """Test parsing <<ANSWER_NOT_FOUND>> for currency questions."""
        not_found_response = AI_RESPONSE_SAMPLES["not_found"]

        result = AIResponseParser.parse_response(
            not_found_response, QuestionTypeName.CURRENCY
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_not_found_response_date(self):
        """Test parsing <<ANSWER_NOT_FOUND>> for date questions."""
        not_found_response = AI_RESPONSE_SAMPLES["not_found"]

        result = AIResponseParser.parse_response(
            not_found_response, QuestionTypeName.DATE
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_not_found_response_single_select(self):
        """Test parsing <<ANSWER_NOT_FOUND>> for single select questions."""
        not_found_response = AI_RESPONSE_SAMPLES["not_found"]

        result = AIResponseParser.parse_response(
            not_found_response, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_not_found_response_select(self):
        """Test parsing <<ANSWER_NOT_FOUND>> for multi select questions."""
        not_found_response = AI_RESPONSE_SAMPLES["not_found"]

        result = AIResponseParser.parse_response(
            not_found_response, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_currency_response(self):
        """Test parsing valid currency JSON response."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["valid"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.CURRENCY)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1

        answer = result.answers[0]
        assert isinstance(answer, CurrencyAnswerData)
        assert answer.value == "1250.5 USD"
        assert answer.amount == 1250.5
        assert answer.currency == "USD"

    def test_parse_multiple_currency_response(self):
        """Test parsing currency response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["multiple"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.CURRENCY)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 2
        assert len(result.answers) == 2

        # First currency
        assert isinstance(result.answers[0], CurrencyAnswerData)
        assert result.answers[0].amount == 1250.5
        assert result.answers[0].currency == "USD"

        # Second currency
        assert isinstance(result.answers[1], CurrencyAnswerData)
        assert result.answers[1].amount == 1100.0
        assert result.answers[1].currency == "EUR"

    def test_parse_empty_currency_response(self):
        """Test parsing empty currency response."""
        json_str = AI_RESPONSE_SAMPLES["currency"]["empty"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.CURRENCY)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_date_response(self):
        """Test parsing valid date JSON response."""
        json_str = AI_RESPONSE_SAMPLES["date"]["valid"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.DATE)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1
        assert len(result.answers) == 1

        answer = result.answers[0]
        assert isinstance(answer, DateAnswerData)
        assert answer.value == "2024-03-15"
        assert answer.parsed_date == "2024-03-15"

    def test_parse_multiple_date_response(self):
        """Test parsing date response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["date"]["multiple"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.DATE)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 2

        assert result.answers[0].value == "2024-03-15"
        assert result.answers[1].value == "2024-03-16"

    def test_parse_single_select_response(self):
        """Test parsing select response with single option."""
        json_str = AI_RESPONSE_SAMPLES["select"]["single"]

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1

        answer = result.answers[0]
        assert isinstance(answer, SelectAnswerData)
        assert answer.option_id == 1  # "Option A" is first in SAMPLE_OPTIONS
        assert answer.option_value == "Option A"

    def test_parse_single_select_response_no_match(self):
        """Test parsing single select with option not in available options."""
        json_str = """{
            "options": [
                {
                    "value": "Unknown Option",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answer_count == 0

    def test_parse_multi_select_response(self):
        """Test parsing select response with multiple options."""
        json_str = AI_RESPONSE_SAMPLES["select"]["multiple"]

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert (
            result.answer_count == 3
        )  # Multi-select returns multiple SelectAnswerData objects

        # Each selected option should be a separate SelectAnswerData
        assert len(result.answers) == 3
        option_values = [answer.option_value for answer in result.answers]
        assert "Option A" in option_values
        assert "Option B" in option_values
        assert "Option C" in option_values

    def test_parse_multi_select_response_partial_match(self):
        """Test parsing multi select where only some options match."""
        json_str = """{
            "options": [
                {
                    "value": "Option A",
                    "citations": []
                },
                {
                    "value": "Unknown Option",
                    "citations": []
                },
                {
                    "value": "Option B",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 2  # Only matched options

        # Should have separate SelectAnswerData for each matched option
        assert len(result.answers) == 2
        option_values = [answer.option_value for answer in result.answers]
        assert "Option A" in option_values
        assert "Option B" in option_values
        assert "Unknown Option" not in option_values

    def test_parse_multi_select_response_empty_options(self):
        """Test parsing select with empty options."""
        json_str = """{"options": []}"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is False
        assert result.answers == []
        assert result.answer_count == 0

    def test_parse_text_response(self):
        """Test parsing valid text JSON response."""
        json_str = AI_RESPONSE_SAMPLES["text"]["valid"]

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1

        answer = result.answers[0]
        assert isinstance(answer, TextAnswerData)
        assert answer.value == "This is the answer text"

    def test_parse_multiple_text_response(self):
        """Test parsing text response with multiple items."""
        json_str = AI_RESPONSE_SAMPLES["text"]["multiple"]

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 2

        assert result.answers[0].value == "First answer"
        assert result.answers[1].value == "Second answer"

    def test_parse_text_response_long_answer(self):
        """Test parsing text for LONG_ANSWER type."""
        json_str = AI_RESPONSE_SAMPLES["text"]["valid"]

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.LONG_ANSWER)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1

        answer = result.answers[0]
        assert isinstance(answer, TextAnswerData)
        assert answer.value == "This is the answer text"

    def test_parse_text_response_none_type(self):
        """Test parsing text with None question type defaults to text."""
        json_str = AI_RESPONSE_SAMPLES["text"]["valid"]

        result = AIResponseParser.parse_response(json_str, None)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answer_count == 1

        answer = result.answers[0]
        assert isinstance(answer, TextAnswerData)
        assert answer.value == "This is the answer text"

    def test_parse_response_invalid_json(self):
        """Test parsing malformed JSON raises exception."""
        malformed_json = '{"items": [{"amount": 100'  # Missing closing brackets

        with pytest.raises(Exception):
            AIResponseParser.parse_response(malformed_json, QuestionTypeName.CURRENCY)

    def test_parse_response_wrong_json_structure(self):
        """Test parsing JSON with wrong structure for question type."""
        # Send date JSON to currency parser
        date_json = AI_RESPONSE_SAMPLES["date"]["valid"]

        with pytest.raises(Exception):
            AIResponseParser.parse_response(date_json, QuestionTypeName.CURRENCY)

    def test_parse_currency_invalid_currency_code(self):
        """Test parsing currency with invalid currency code."""
        json_str = """{
            "items": [
                {
                    "amount": 100.00,
                    "code": "US",
                    "citations": []
                }
            ]
        }"""

        with pytest.raises(Exception):
            AIResponseParser.parse_response(json_str, QuestionTypeName.CURRENCY)

    def test_parse_date_invalid_format(self):
        """Test parsing date with invalid format."""
        json_str = """{
            "items": [
                {
                    "value": "12/25/2024",
                    "citations": []
                }
            ]
        }"""

        with pytest.raises(Exception):
            AIResponseParser.parse_response(json_str, QuestionTypeName.DATE)

    def test_parse_response_whitespace_handling(self):
        """Test that parser handles whitespace correctly."""
        json_with_whitespace = "   " + AI_RESPONSE_SAMPLES["text"]["valid"] + "   "

        result = AIResponseParser.parse_response(
            json_with_whitespace, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answers[0].value == "This is the answer text"

    def test_parse_response_quoted_not_found(self):
        """Test parsing quoted not found responses."""
        quoted_responses = [
            '"<<ANSWER_NOT_FOUND>>"',
            "'<<ANSWER_NOT_FOUND>>'",
        ]

        for quoted_response in quoted_responses:
            result = AIResponseParser.parse_response(
                quoted_response, QuestionTypeName.SHORT_ANSWER
            )

            assert isinstance(result, AIAnswerSet)
            assert result.answer_found is False
            assert result.answers == []
            assert result.answer_count == 0


class TestAIResponseParserUtils:
    """Test utility methods of AIResponseParser."""

    def test_find_option_id_exact_match(self):
        """Test finding option ID with exact match."""
        option_id = AIResponseParser._find_option_id("Option A", SAMPLE_OPTIONS)
        assert option_id == 1  # 1-based indexing

    def test_find_option_id_case_insensitive(self):
        """Test finding option ID with case insensitive match."""
        option_id = AIResponseParser._find_option_id("option a", SAMPLE_OPTIONS)
        assert option_id == 1  # Should match "Option A"

    def test_find_option_id_no_match(self):
        """Test finding option ID when no match exists."""
        option_id = AIResponseParser._find_option_id("Unknown Option", SAMPLE_OPTIONS)
        assert option_id is None

    def test_find_option_id_no_options(self):
        """Test finding option ID when options list is None."""
        option_id = AIResponseParser._find_option_id("Option A", None)
        assert option_id is None

    def test_find_option_id_empty_options(self):
        """Test finding option ID when options list is empty."""
        option_id = AIResponseParser._find_option_id("Option A", [])
        assert option_id is None

    # =========================================================================
    # _clean_response tests
    # =========================================================================

    def test_clean_response_plain_json(self):
        """Test that plain JSON passes through unchanged."""
        plain_json = '{"items": [{"value": "test", "confidence": 0.9, "citations": []}]}'
        result = AIResponseParser._clean_response(plain_json)
        assert result == plain_json

    def test_clean_response_code_block_at_start(self):
        """Test extracting JSON from code block at start of response."""
        response = '```json\n{"items": [{"value": "test"}]}\n```'
        result = AIResponseParser._clean_response(response)
        assert result == '{"items": [{"value": "test"}]}'

    def test_clean_response_code_block_without_json_label(self):
        """Test extracting JSON from code block without 'json' label."""
        response = '```\n{"items": [{"value": "test"}]}\n```'
        result = AIResponseParser._clean_response(response)
        assert result == '{"items": [{"value": "test"}]}'

    def test_clean_response_preamble_before_code_block(self):
        """Test extracting JSON when there's text before the code block."""
        response = 'Here is the answer [[cite:1]].\n```json\n{"items": [{"value": "test"}]}\n```'
        result = AIResponseParser._clean_response(response)
        assert result == '{"items": [{"value": "test"}]}'

    def test_clean_response_preamble_and_trailing_text(self):
        """Test extracting JSON with both preamble and trailing text."""
        response = 'Preamble text.\n```json\n{"items": [{"value": "test"}]}\n```\nTrailing text.'
        result = AIResponseParser._clean_response(response)
        assert result == '{"items": [{"value": "test"}]}'

    def test_clean_response_nested_braces(self):
        """Test extracting JSON with nested objects."""
        nested_json = '{"items": [{"value": "test", "nested": {"key": "value"}}]}'
        response = f'Some text\n```json\n{nested_json}\n```'
        result = AIResponseParser._clean_response(response)
        assert result == nested_json

    def test_clean_response_trailing_comma_cleanup(self):
        """Test that trailing commas are removed."""
        json_with_trailing = '{"items": [{"value": "test",}],}'
        result = AIResponseParser._clean_response(json_with_trailing)
        assert result == '{"items": [{"value": "test"}]}'

    def test_clean_response_whitespace_handling(self):
        """Test that leading/trailing whitespace is stripped."""
        response = '   \n  {"items": []}  \n   '
        result = AIResponseParser._clean_response(response)
        assert result == '{"items": []}'

    def test_clean_response_real_world_example(self):
        """Test with real-world AI response format (the actual bug case)."""
        response = '''The laws of the State of Nevada govern this Agreement [[cite:1]].
```json
{
  "items": [
    {
      "value": "The laws of the State of Nevada govern this Agreement [[cite:1]]",
      "confidence": 0.95,
      "citations": [
        {
          "order": 1,
          "document_id": 55,
          "quote_text": "shall be governed by the laws of the State of Nevada"
        }
      ]
    }
  ]
}
```'''
        result = AIResponseParser._clean_response(response)
        # Should extract just the JSON
        assert result.startswith('{')
        assert result.endswith('}')
        assert '"items"' in result
        assert 'The laws of the State of Nevada' not in result.split('{')[0]  # Preamble removed

    def test_is_iso_date_valid(self):
        """Test ISO date validation with valid dates."""
        valid_dates = [
            "2024-01-01",
            "2024-12-31",
            "2024-02-29",  # Leap year
        ]

        for date_str in valid_dates:
            assert AIResponseParser._is_iso_date(date_str) is True

    def test_is_iso_date_invalid(self):
        """Test ISO date validation with invalid dates."""
        invalid_dates = [
            "2024-1-1",  # No zero padding
            "24-01-01",  # Two digit year
            "2024/01/01",  # Wrong separator
            "01-01-2024",  # Wrong order
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "not a date",  # Not a date
            "",  # Empty string
        ]

        for date_str in invalid_dates:
            assert AIResponseParser._is_iso_date(date_str) is False


class TestAIResponseParserEdgeCases:
    """Test edge cases and error scenarios."""

    def test_parse_text_with_special_characters(self):
        """Test parsing text containing special characters."""
        json_str = """{
            "items": [
                {
                    "value": "Q&A: <important> \\"quoted\\"",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answers[0].value == 'Q&A: <important> "quoted"'

    def test_parse_text_with_newlines(self):
        """Test parsing text containing newlines."""
        json_str = """{
            "items": [
                {
                    "value": "Line 1\\nLine 2\\nLine 3",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert "Line 1\nLine 2\nLine 3" in result.answers[0].value

    def test_parse_currency_with_large_amount(self):
        """Test parsing currency with large amount."""
        json_str = """{
            "items": [
                {
                    "amount": 999999999.99,
                    "code": "USD",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(json_str, QuestionTypeName.CURRENCY)

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answers[0].amount == 999999999.99
        assert result.answers[0].currency == "USD"

    def test_parse_select_with_special_chars(self):
        """Test parsing select with special characters."""
        json_str = """{
            "options": [
                {
                    "value": "Yes - With & Special Chars",
                    "citations": []
                }
            ]
        }"""

        # Add the special option to our test options
        special_options = SAMPLE_OPTIONS + ["Yes - With & Special Chars"]

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, special_options
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answers[0].option_value == "Yes - With & Special Chars"

    def test_parse_multi_select_with_duplicates(self):
        """Test parsing multi select containing duplicate options."""
        json_str = """{
            "options": [
                {
                    "value": "Option A",
                    "citations": []
                },
                {
                    "value": "Option A",
                    "citations": []
                },
                {
                    "value": "Option B",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SELECT, SAMPLE_OPTIONS
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True

        # Should only include each matched option once
        assert result.answer_count == 2  # Duplicates removed
        assert len(result.answers) == 2
        option_values = [answer.option_value for answer in result.answers]
        assert "Option A" in option_values
        assert "Option B" in option_values

    def test_parse_response_with_unicode(self):
        """Test parsing response containing unicode characters."""
        json_str = """{
            "items": [
                {
                    "value": "Unicode: 🚀 émojis and spëcial chârs",
                    "citations": []
                }
            ]
        }"""

        result = AIResponseParser.parse_response(
            json_str, QuestionTypeName.SHORT_ANSWER
        )

        assert isinstance(result, AIAnswerSet)
        assert result.answer_found is True
        assert result.answers[0].value == "Unicode: 🚀 émojis and spëcial chârs"

    def test_answer_set_boolean_conversion(self):
        """Test that AIAnswerSet boolean conversion works correctly."""
        # Test not found
        not_found = AIResponseParser.parse_response(
            "<<ANSWER_NOT_FOUND>>", QuestionTypeName.SHORT_ANSWER
        )
        assert not not_found  # Should be False when used as boolean
        assert not_found.answer_found is False

        # Test found
        found = AIResponseParser.parse_response(
            AI_RESPONSE_SAMPLES["text"]["valid"], QuestionTypeName.SHORT_ANSWER
        )
        assert found  # Should be True when used as boolean
        assert found.answer_found is True
