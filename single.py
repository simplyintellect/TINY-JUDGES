import sys
import time
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from llm import ask, PRIMARY_MODEL
from utils import parse_json_response

SINGLE_JUDGE_PROMPT = """You are an expert UI/UX and visual QA auditor. Examine the provided screenshot and user description to identify any visual, layout, responsiveness, formatting, cut-off text, alignment, or design bugs.

User Description: {description}

Analyze the input thoroughly and output ONLY valid JSON using the following exact structure:
{{
  "summary": "Brief summary of visual bugs or confirmation that no bugs exist.",
  "issues": [
    {{
      "issue": "Specific description of the bug (e.g. Button overlaps text, horizontal overflow on 390px viewport)",
      "evidence": "Visual evidence seen in image (e.g. 'Submit' button overlaps footer text at bottom)",
      "probable_cause": "Likely underlying cause (e.g. fixed height container without overflow scroll, absolute positioning collision)",
      "confidence": 0.9
    }}
  ],
  "confidence": 0.95
}}

If no bugs are present, return an empty list for "issues" and summarize that the UI appears correct and bug-free. Output ONLY the JSON block.
"""

def run_single_model(image_path: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs the single model baseline judge on an image and/or text description.
    Measures latency and returns structured JSON output. Handles API errors gracefully.
    """
    start_time = time.perf_counter()
    desc_text = description if description else "Perform a general visual bug audit on this UI screenshot."
    prompt = SINGLE_JUDGE_PROMPT.format(description=desc_text)

    try:
        raw_response = ask(prompt=prompt, image_path=image_path, temperature=0.7, max_retries=1)
        latency = time.perf_counter() - start_time
        parsed_data, success = parse_json_response(raw_response)

        issues = parsed_data.get("issues", [])
        if not isinstance(issues, list):
            issues = []

        summary = parsed_data.get("summary", raw_response if not success else "")
        try:
            conf = float(parsed_data.get("confidence", 0.5))
        except (ValueError, TypeError):
            conf = 0.5

        return {
            "mode": "single",
            "status": "SUCCESS" if success else "PARSE_ERROR",
            "image_path": str(image_path) if image_path else None,
            "description": desc_text,
            "summary": summary,
            "issues": issues,
            "confidence": round(conf, 2),
            "latency": round(latency, 3),
            "model": PRIMARY_MODEL,
            "parse_error": not success,
            "raw_response": raw_response
        }
    except Exception as e:
        latency = time.perf_counter() - start_time
        return {
            "mode": "single",
            "status": "FAILED",
            "image_path": str(image_path) if image_path else None,
            "description": desc_text,
            "summary": f"API Call Failed: {e}",
            "issues": [],
            "confidence": 0.0,
            "latency": round(latency, 3),
            "model": PRIMARY_MODEL,
            "parse_error": True,
            "error": str(e),
            "raw_response": ""
        }

def main():
    parser = argparse.ArgumentParser(description="Run single Gemma 4 baseline judge on a UI image/description.")
    parser.add_argument("image_path", nargs="?", default=None, help="Path to UI screenshot image.")
    parser.add_argument("--description", "-d", type=str, default="", help="Optional user context or description.")
    args = parser.parse_args()

    if not args.image_path and not args.description:
        print("Error: Must provide an image_path or a --description.")
        sys.exit(1)

    print(f"--- Running Single Model Baseline on {args.image_path or 'Text Prompt'} ---")
    res = run_single_model(image_path=args.image_path, description=args.description)
    print("\n--- Baseline Result ---")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
