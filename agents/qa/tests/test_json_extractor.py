"""
Tests for agent executor JSON extraction logic.

Verifies that extract_json_from_text correctly handles:
1. <<ANSWER_NOT_FOUND>> marker (critical fix)
2. JSON in markdown code blocks
3. Raw JSON objects
4. Various edge cases
"""

import json

import pytest

from src.json_extractor import extract_json_from_text


class TestExtractJsonFromText:
    """Tests for extract_json_from_text function."""

    def test_extract_answer_not_found_plain(self):
        """Test extracting <<ANSWER_NOT_FOUND>> from plain text response."""
        text = """
        I'll help you identify the parties mentioned in the document.

        Based on my analysis, this document does not contain information
        about specific parties.

        <<ANSWER_NOT_FOUND>>
        """

        result = extract_json_from_text(text)

        assert result == "<<ANSWER_NOT_FOUND>>"

    def test_extract_answer_not_found_with_explanation(self):
        """Test extracting <<ANSWER_NOT_FOUND>> when agent provides explanation."""
        text = """
        Let me analyze the document chunks.

        After reviewing [[document:228]], this appears to be an NDA Document Registry
        table. However, this document does not contain information about specific
        parties (company names, individual names, or entity names).

        <<ANSWER_NOT_FOUND>>
        """

        result = extract_json_from_text(text)

        assert result == "<<ANSWER_NOT_FOUND>>"

    def test_extract_answer_not_found_at_end(self):
        """Test extracting <<ANSWER_NOT_FOUND>> at end of response."""
        text = "Based on analysis: <<ANSWER_NOT_FOUND>>"

        result = extract_json_from_text(text)

        assert result == "<<ANSWER_NOT_FOUND>>"

    def test_extract_json_from_code_block(self):
        """Test extracting JSON from markdown code block."""
        text = """
        Here is the answer:

        ```json
        {
          "options": [
            {
              "value": "Python",
              "confidence": 0.95,
              "citations": [{"order": 1, "document_id": 123, "quote_text": "We use Python"}]
            }
          ]
        }
        ```
        """

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert "options" in parsed
        assert len(parsed["options"]) == 1
        assert parsed["options"][0]["value"] == "Python"

    def test_extract_json_from_code_block_no_language(self):
        """Test extracting JSON from code block without language specifier."""
        text = """
        ```
        {
          "items": [
            {"amount": 1250.00, "code": "USD", "confidence": 0.95}
          ]
        }
        ```
        """

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert "items" in parsed
        assert parsed["items"][0]["amount"] == 1250.00

    def test_extract_raw_json_object(self):
        """Test extracting raw JSON object without markdown."""
        text = """
        Based on the document, here's the answer:

        {"options": [{"value": "JavaScript", "confidence": 0.85}]}

        This represents the findings.
        """

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert "options" in parsed

    def test_extract_multiline_json(self):
        """Test extracting multiline JSON with nested structures."""
        json_obj = {
            "items": [
                {
                    "amount": 50000,
                    "code": "USD",
                    "confidence": 0.9,
                    "citations": [
                        {
                            "order": 1,
                            "document_id": 123,
                            "quote_text": "Budget: $50,000"
                        }
                    ]
                }
            ]
        }

        text = f"Here is the result:\n\n{json.dumps(json_obj, indent=2)}"

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert parsed == json_obj

    def test_no_json_found(self):
        """Test when no JSON or <<ANSWER_NOT_FOUND>> is present."""
        text = """
        I searched through the documents but couldn't extract
        a valid response format. This is just plain text.
        """

        result = extract_json_from_text(text)

        assert result is None

    def test_invalid_json_returns_none(self):
        """Test that invalid JSON is rejected."""
        text = """
        {
          "incomplete": "json",
          "missing":
        """

        result = extract_json_from_text(text)

        # Should return None because JSON is invalid
        assert result is None

    def test_answer_not_found_takes_precedence(self):
        """Test that <<ANSWER_NOT_FOUND>> is found even if JSON-like text exists."""
        text = """
        I tried to find {some: data} but couldn't.

        <<ANSWER_NOT_FOUND>>
        """

        result = extract_json_from_text(text)

        # Should prioritize <<ANSWER_NOT_FOUND>> over invalid JSON-like text
        assert result == "<<ANSWER_NOT_FOUND>>"

    def test_empty_string(self):
        """Test handling of empty string."""
        result = extract_json_from_text("")

        assert result is None

    def test_whitespace_only(self):
        """Test handling of whitespace-only string."""
        result = extract_json_from_text("   \n\n  \t  ")

        assert result is None

    def test_json_with_special_characters(self):
        """Test extracting JSON containing special characters in quotes."""
        json_obj = {
            "options": [
                {
                    "value": "Contract between \"Party A\" & Party B",
                    "confidence": 0.9,
                    "citations": [
                        {
                            "order": 1,
                            "document_id": 456,
                            "quote_text": "This agreement is between \"Party A\" & Party B"
                        }
                    ]
                }
            ]
        }

        text = f"```json\n{json.dumps(json_obj)}\n```"

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert "Party A" in parsed["options"][0]["value"]

    def test_code_block_with_extra_backticks(self):
        """Test extracting from code block with trailing text."""
        text = """
        ```json
        {"items": [{"amount": 100, "code": "EUR"}]}
        ```

        Additional explanation after the JSON.
        """

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert parsed["items"][0]["code"] == "EUR"

    def test_real_world_agent_response_not_found(self):
        """Test with actual agent response from production logs."""
        text = """I'll help you identify the parties mentioned in the document. Let me start by discovering what chunks are available.Now let me read the content of this chunk to identify the parties:Based on my analysis of [[document:228]], this appears to be an NDA Document Registry table that lists various NDA documents by their ID, type, and governing law. However, this document does not contain information about specific parties (company names, individual names, or entity names). It only contains metadata about NDA documents including their types (Bilateral/Unilateral) and governing jurisdictions.

<<ANSWER_NOT_FOUND>>"""

        result = extract_json_from_text(text)

        assert result == "<<ANSWER_NOT_FOUND>>"

    def test_real_world_json_response_currency(self):
        """Test with realistic currency JSON response."""
        text = """Based on the document analysis, I found the following monetary amounts:

```json
{
  "items": [
    {
      "amount": 1250.00,
      "code": "USD",
      "confidence": 0.95,
      "citations": [
        {
          "order": 1,
          "document_id": 123,
          "quote_text": "The total cost is $1,250.00 USD"
        }
      ]
    }
  ]
}
```"""

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert parsed["items"][0]["amount"] == 1250.00
        assert parsed["items"][0]["code"] == "USD"

    def test_real_world_json_response_select(self):
        """Test with realistic select options response."""
        text = """After analyzing the document, here are the matching options:

```json
{
  "options": [
    {
      "value": "Python",
      "confidence": 0.95,
      "citations": [
        {
          "order": 1,
          "document_id": 123,
          "quote_text": "We use Python for data analysis"
        }
      ]
    },
    {
      "value": "JavaScript",
      "confidence": 0.85,
      "citations": [
        {
          "order": 1,
          "document_id": 123,
          "quote_text": "Frontend built with JavaScript"
        }
      ]
    }
  ]
}
```"""

        result = extract_json_from_text(text)

        assert result is not None
        parsed = json.loads(result)
        assert len(parsed["options"]) == 2
        assert parsed["options"][0]["value"] == "Python"
        assert parsed["options"][1]["value"] == "JavaScript"
