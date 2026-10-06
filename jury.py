import sys
import time
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

from llm import ask, PRIMARY_MODEL
from utils import parse_json_response

EXPERT_PROMPT = """You are a DOMAIN EXPERT in UI/UX Engineering and Visual Design Systems.
Examine the provided UI screenshot and user description. Use your technical domain knowledge (CSS layout models, flexbox/grid, WCAG accessibility standards, typography, 390px mobile viewport rules) to detect visual bugs.

User Context: {description}

Output ONLY valid JSON with this exact structure:
{{
  "role": "expert",
  "summary": "Technical evaluation of the UI.",
  "issues": [
    {{
      "issue": "Clear technical description of the UI bug.",
      "evidence": "Specific visual evidence in the image.",
      "probable_cause": "Technical CSS/HTML/layout cause."
    }}
  ],
  "confidence": 0.85
}}
"""

SKEPTIC_PROMPT = """You are a SKEPTICAL QA AUDITOR searching for hidden, subtle, or overlooked visual flaws.
Examine the provided UI screenshot and user description. Actively question design intent vs unintended bugs, look for subtle alignment drift, text truncation, awkward padding, contrast issues, or clipped content that others might miss.

User Context: {description}

Output ONLY valid JSON with this exact structure:
{{
  "role": "skeptic",
  "summary": "Skeptical audit of potential UI flaws.",
  "issues": [
    {{
      "issue": "Description of subtle flaw or bug.",
      "evidence": "Visual evidence or subtle anomaly observed.",
      "probable_cause": "Potential design/implementation flaw."
    }}
  ],
  "confidence": 0.85
}}
"""

BEGINNER_PROMPT = """You are a COMMON-SENSE USER/BEGINNER evaluating a mobile screen.
Examine the provided UI screenshot and user description with fresh eyes. Do not use complex jargon. Look for obvious things that look wrong, broken, ugly, overlapping, unreadable, cut off, or out of place for a smartphone screen.

User Context: {description}

Output ONLY valid JSON with this exact structure:
{{
  "role": "beginner",
  "summary": "Common-sense user feedback on the UI.",
  "issues": [
    {{
      "issue": "Simple, straightforward description of what looks wrong.",
      "evidence": "What is visually wrong on the screen.",
      "probable_cause": "Common-sense explanation."
    }}
  ],
  "confidence": 0.85
}}
"""

VERIFIER_PROMPT = """You are the CHIEF VERIFIER & RECONCILER for a panel of UI auditors.
You have been provided with:
1. The original UI screenshot (and context description).
2. The independent reports from the available judge(s):

User Context: {description}

Judges' Reports:
{judges_json}

INSTRUCTIONS FOR RECONCILIATION:
1. Independently inspect the image to verify each judge's claims against screenshot evidence.
2. Compare the available analyses: identify consensus (agreements) and conflicts (disagreements).
3. Do NOT simply rely on majority vote. Reject hallucinated bugs or false claims unsupported by the image. Accept valid subtle findings if visually backed by evidence.
4. Consolidate a final, authoritative list of verified UI issues.

Output ONLY valid JSON with this exact structure:
{{
  "final_answer": "Comprehensive synthesis of verified UI issues.",
  "agreement_summary": "Summary of points where judges agreed.",
  "disagreements": ["Specific point of disagreement 1", "Specific point of disagreement 2"],
  "decision_reason": "Explanation of how evidence resolved disagreements or filtered false claims.",
  "issues": [
    {{
      "issue": "Verified description of the UI bug.",
      "evidence": "Confirmed visual evidence from the screenshot.",
      "probable_cause": "Most likely root cause.",
      "confidence": 0.9
    }}
  ],
  "confidence": 0.90
}}
"""

def _run_single_role(role_name: str, prompt_template: str, image_path: Optional[str], description: str) -> Dict[str, Any]:
    prompt = prompt_template.format(description=description)
    raw = ask(prompt=prompt, image_path=image_path, temperature=0.8, max_retries=1)
    parsed, success = parse_json_response(raw)
    parsed["role"] = role_name
    parsed["parse_error"] = not success
    parsed["raw_response"] = raw
    return parsed

def run_jury_model(image_path: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs 3 independent judges sequentially with a slight pause to avoid rate limits.
    If a judge fails, it records the failure and continues with remaining judges.
    The verifier reconciles output from all successful judges.
    """
    start_time = time.perf_counter()
    desc_text = description if description else "Perform a visual bug audit on this UI screenshot."

    roles_config = [
        ("expert", EXPERT_PROMPT),
        ("skeptic", SKEPTIC_PROMPT),
        ("beginner", BEGINNER_PROMPT)
    ]

    judge_results = []
    # 1. Run judges sequentially
    for role_name, template in roles_config:
        try:
            res = _run_single_role(role_name, template, image_path, desc_text)
            judge_results.append(res)
        except Exception as e:
            judge_results.append({
                "role": role_name,
                "status": "FAILED",
                "summary": f"Judge failed due to API error: {e}",
                "issues": [],
                "confidence": 0.0,
                "parse_error": True,
                "error": str(e)
            })
        time.sleep(0.5)

    successful_judges = [j for j in judge_results if not j.get("error") and not j.get("parse_error")]

    # If ALL judges failed, return a structured FAILED result
    if not successful_judges:
        total_latency = time.perf_counter() - start_time
        return {
            "mode": "jury",
            "status": "FAILED",
            "image_path": str(image_path) if image_path else None,
            "description": desc_text,
            "final_answer": "Case failed due to API errors across all judges.",
            "agreement_summary": "",
            "disagreements": [],
            "decision_reason": "",
            "issues": [],
            "confidence": 0.0,
            "latency": round(total_latency, 3),
            "judge_outputs": judge_results,
            "model": PRIMARY_MODEL,
            "parse_error": True,
            "raw_response": ""
        }

    # 2. Run Reconciler/Verifier on successful judges
    judges_summary_str = json.dumps(successful_judges, indent=2)
    verifier_prompt = VERIFIER_PROMPT.format(
        description=desc_text,
        judges_json=judges_summary_str
    )

    try:
        verifier_raw = ask(prompt=verifier_prompt, image_path=image_path, temperature=0.7, max_retries=1)
        total_latency = time.perf_counter() - start_time
        verifier_parsed, success = parse_json_response(verifier_raw)

        issues = verifier_parsed.get("issues", [])
        if not isinstance(issues, list):
            issues = []

        try:
            conf = float(verifier_parsed.get("confidence", 0.5))
        except (ValueError, TypeError):
            conf = 0.5

        return {
            "mode": "jury",
            "status": "SUCCESS" if success else "PARSE_ERROR",
            "image_path": str(image_path) if image_path else None,
            "description": desc_text,
            "final_answer": verifier_parsed.get("final_answer", verifier_raw if not success else ""),
            "agreement_summary": verifier_parsed.get("agreement_summary", ""),
            "disagreements": verifier_parsed.get("disagreements", []),
            "decision_reason": verifier_parsed.get("decision_reason", ""),
            "issues": issues,
            "confidence": round(conf, 2),
            "latency": round(total_latency, 3),
            "judge_outputs": judge_results,
            "model": PRIMARY_MODEL,
            "parse_error": not success,
            "raw_response": verifier_raw
        }
    except Exception as e:
        # Fallback if reconciliation call itself fails: construct composite from successful judges
        total_latency = time.perf_counter() - start_time
        combined_issues = []
        for j in successful_judges:
            combined_issues.extend(j.get("issues", []))

        return {
            "mode": "jury",
            "status": "PARTIAL_SUCCESS",
            "image_path": str(image_path) if image_path else None,
            "description": desc_text,
            "final_answer": f"Reconciler API failed ({e}). Consolidated findings from {len(successful_judges)} judges.",
            "agreement_summary": f"{len(successful_judges)} judges completed successfully.",
            "disagreements": [f"Reconciliation step API error: {e}"],
            "decision_reason": "Direct union of successful judge issues.",
            "issues": combined_issues,
            "confidence": 0.5,
            "latency": round(total_latency, 3),
            "judge_outputs": judge_results,
            "model": PRIMARY_MODEL,
            "parse_error": True,
            "error": str(e),
            "raw_response": ""
        }

def main():
    parser = argparse.ArgumentParser(description="Run 3-Judge Gemma 4 Jury + Verifier on a UI image/description.")
    parser.add_argument("image_path", nargs="?", default=None, help="Path to UI screenshot image.")
    parser.add_argument("--description", "-d", type=str, default="", help="Optional user context or description.")
    args = parser.parse_args()

    if not args.image_path and not args.description:
        print("Error: Must provide an image_path or a --description.")
        sys.exit(1)

    print(f"--- Running 3-Judge Jury + Verifier on {args.image_path or 'Text Prompt'} ---")
    res = run_jury_model(image_path=args.image_path, description=args.description)
    print("\n--- Jury Result ---")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
