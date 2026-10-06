import json
import re
from typing import Dict, Any, Tuple

def extract_json_block(text: str) -> str:
    """Strips markdown backticks and isolates the outermost JSON object/array."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Locate outermost { } or [ ]
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace:last_brace + 1]

    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        return text[first_bracket:last_bracket + 1]

    return text

def parse_json_response(text: str) -> Tuple[Dict[str, Any], bool]:
    """
    Parses LLM string output to a dictionary.
    Returns (parsed_dict, success_boolean).
    """
    cleaned = extract_json_block(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data, True
        elif isinstance(data, list):
            return {"items": data}, True
    except Exception:
        pass
    
    # Fallback structure if JSON decoding fails
    return {
        "raw_text": text,
        "parse_error": True,
        "issues": [],
        "confidence": 0.0,
        "summary": text
    }, False
