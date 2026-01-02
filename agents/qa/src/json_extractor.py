"""
JSON extraction utilities for agent responses.

Separated from agent_executor to allow testing without heavy dependencies.
"""

import json
import re
from typing import Optional


def extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract JSON object or <<ANSWER_NOT_FOUND>> from text.

    Looks for:
    1. <<ANSWER_NOT_FOUND>> marker (valid "not found" response)
    2. ```json ... ``` blocks
    3. { ... } JSON objects

    Args:
        text: Text containing JSON or ANSWER_NOT_FOUND marker

    Returns:
        JSON string or "<<ANSWER_NOT_FOUND>>" if found, None otherwise
    """
    # Check for ANSWER_NOT_FOUND marker first (valid response, not an error)
    if "<<ANSWER_NOT_FOUND>>" in text:
        return "<<ANSWER_NOT_FOUND>>"

    # Try to find JSON in code block first
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)

    # Try to find raw JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        potential_json = json_match.group(0)
        # Validate it's actually JSON
        try:
            json.loads(potential_json)
            return potential_json
        except json.JSONDecodeError:
            pass

    return None


def adjust_confidence_in_json(answer_json: str, multiplier: float) -> str:
    """
    Adjust confidence scores in answer JSON.

    Args:
        answer_json: JSON string with answers
        multiplier: Confidence multiplier (0.0-1.0)

    Returns:
        Updated JSON string
    """
    try:
        data = json.loads(answer_json)

        for answer in data.get("answers", []):
            original = answer.get("confidence", 1.0)
            answer["confidence"] = original * multiplier

        return json.dumps(data)
    except Exception:
        return answer_json
