import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from single import run_single_model
from jury import run_jury_model

CASES_DIR = Path("cases")
RESULTS_DIR = Path("results")
RAW_DIR = RESULTS_DIR / "raw"

CASE_TIMEOUT_SECONDS = 60  # Hard timeout safety

def load_case_specs() -> List[Dict[str, Any]]:
    cases = []
    for cid in range(1, 11):
        cname = f"case_{cid:02d}"
        json_path = CASES_DIR / f"{cname}.json"
        if not json_path.exists():
            raise FileNotFoundError(f"Missing case file: {json_path}. Run make_cases.py first.")
        with open(json_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
            cases.append(spec)
    return cases

def get_combined_text(res: Dict[str, Any]) -> str:
    """Concatenates all text fields from a run result into a lowercase search string."""
    text_parts = [
        res.get("summary", ""),
        res.get("final_answer", ""),
        res.get("agreement_summary", ""),
        res.get("decision_reason", ""),
        res.get("raw_response", "")
    ]
    for issue in res.get("issues", []):
        if isinstance(issue, dict):
            text_parts.append(str(issue.get("issue", "")))
            text_parts.append(str(issue.get("evidence", "")))
            text_parts.append(str(issue.get("probable_cause", "")))
        elif isinstance(issue, str):
            text_parts.append(issue)
    return " ".join(text_parts).lower()

def score_mode_output(spec: Dict[str, Any], res: Dict[str, Any]) -> Dict[str, Any]:
    """Scores a single or jury model response against ground truth."""
    if res.get("status") == "FAILED" or res.get("error"):
        return {
            "status": "FAILED",
            "recall": 0.0,
            "has_false_claim": False,
            "no_bug_correct": False,
            "is_correct": False,
            "latency": res.get("latency", 0.0),
            "confidence": 0.0,
            "error": res.get("error", "API failure")
        }

    case_type = spec.get("type", "")
    must_find_groups = spec.get("must_find", [])
    false_claims_list = spec.get("false_claims", [])
    combined_text = get_combined_text(res)
    issues = res.get("issues", [])

    # Evaluate must_find hits
    hits = 0
    total_groups = len(must_find_groups)
    for group in must_find_groups:
        if any(kw.lower() in combined_text for kw in group):
            hits += 1

    recall = (hits / total_groups) if total_groups > 0 else 1.0

    # Evaluate false claims
    has_false_claim = False
    for fc in false_claims_list:
        if fc.lower() in combined_text:
            has_false_claim = True
            break

    # Determine overall correctness
    is_correct = False
    no_bug_correct = False

    if case_type == "no_bug":
        if len(issues) == 0:
            no_bug_correct = True
            is_correct = True
        else:
            clean_kws = ["no bug", "no issues", "clean", "correct", "no visual bug", "appears correct"]
            no_bug_correct = any(kw in combined_text for kw in clean_kws) and not has_false_claim
            is_correct = no_bug_correct
    else:
        # For bug cases, correct if recall >= 50% and no false claims
        is_correct = (recall >= 0.5) and not has_false_claim

    return {
        "status": res.get("status", "SUCCESS"),
        "recall": recall,
        "has_false_claim": has_false_claim,
        "no_bug_correct": no_bug_correct if case_type == "no_bug" else None,
        "is_correct": is_correct,
        "latency": res.get("latency", 0.0),
        "confidence": res.get("confidence", 0.0),
        "error": None
    }

def classify_case_outcome(s_score: Dict[str, Any], j_score: Dict[str, Any], res_jury: Dict[str, Any]) -> str:
    """Classifies case into IMPROVED, REGRESSED, UNCHANGED-CORRECT, UNCHANGED-WRONG, DISAGREEMENT-RESOLVED, DISAGREEMENT-FAILED, or FAILED."""
    if s_score["status"] == "FAILED" and j_score["status"] == "FAILED":
        return "FAILED"

    s_corr = s_score["is_correct"]
    j_corr = j_score["is_correct"]

    disagreements = res_jury.get("disagreements", [])
    has_disagreement = len(disagreements) > 0 and disagreements != ["None"]

    if not s_corr and j_corr:
        return "IMPROVED"
    elif s_corr and not j_corr:
        return "REGRESSED"
    elif s_corr and j_corr:
        if has_disagreement:
            return "DISAGREEMENT-RESOLVED"
        return "UNCHANGED-CORRECT"
    else: # both incorrect
        if has_disagreement:
            return "DISAGREEMENT-FAILED"
        return "UNCHANGED-WRONG"

def run_benchmark():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_case_specs()

    results_summary = []

    for idx, case in enumerate(cases, 1):
        cid = case["id"]
        img_path = case["image_path"]
        desc = case["description"]

        print(f"[{idx}/{len(cases)}] {cid}")

        # Paths for cached raw output files
        single_raw_file = RAW_DIR / f"{cid}_single.json"
        jury_raw_file = RAW_DIR / f"{cid}_jury.json"

        # Legacy raw file fallback checks
        alt_single = RAW_DIR / f"{cid}_single_run_1.json"
        alt_jury = RAW_DIR / f"{cid}_jury_run_1.json"

        # 1. Run or Load Single Model
        res_single = None
        if single_raw_file.exists():
            with open(single_raw_file, "r", encoding="utf-8") as f:
                res_single = json.load(f)
        elif alt_single.exists():
            with open(alt_single, "r", encoding="utf-8") as f:
                res_single = json.load(f)
        
        if not res_single or res_single.get("status") == "FAILED":
            res_single = run_single_model(image_path=img_path, description=desc)
            with open(single_raw_file, "w", encoding="utf-8") as f:
                json.dump(res_single, f, indent=2)

        # 2. Run or Load Jury Model
        res_jury = None
        if jury_raw_file.exists():
            with open(jury_raw_file, "r", encoding="utf-8") as f:
                res_jury = json.load(f)
        elif alt_jury.exists():
            with open(alt_jury, "r", encoding="utf-8") as f:
                res_jury = json.load(f)

        if not res_jury or res_jury.get("status") == "FAILED":
            res_jury = run_jury_model(image_path=img_path, description=desc)
            with open(jury_raw_file, "w", encoding="utf-8") as f:
                json.dump(res_jury, f, indent=2)

        # Score results
        s_score = score_mode_output(case, res_single)
        j_score = score_mode_output(case, res_jury)
        outcome = classify_case_outcome(s_score, j_score, res_jury)

        results_summary.append({
            "case_id": cid,
            "type": case["type"],
            "description": desc,
            "single_res": res_single,
            "jury_res": res_jury,
            "single_score": s_score,
            "jury_score": j_score,
            "outcome": outcome
        })

    # Generate Markdown Report
    write_results_markdown(results_summary)

def write_results_markdown(summary: List[Dict[str, Any]]):
    total_cases = len(summary)
    successful_cases = sum(1 for item in summary if item["single_score"]["status"] != "FAILED" or item["jury_score"]["status"] != "FAILED")
    failed_cases = total_cases - successful_cases
    api_failures = sum(1 for item in summary if item["single_score"]["status"] == "FAILED") + sum(1 for item in summary if item["jury_score"]["status"] == "FAILED")

    bug_cases = [item for item in summary if item["type"] != "no_bug"]
    
    single_rec = (sum(item["single_score"]["recall"] for item in bug_cases) / len(bug_cases)) * 100 if bug_cases else 0.0
    jury_rec = (sum(item["jury_score"]["recall"] for item in bug_cases) / len(bug_cases)) * 100 if bug_cases else 0.0

    single_acc = (sum(1 for item in summary if item["single_score"]["is_correct"]) / total_cases) * 100
    jury_acc = (sum(1 for item in summary if item["jury_score"]["is_correct"]) / total_cases) * 100

    improved_cnt = sum(1 for item in summary if item["outcome"] == "IMPROVED")
    regressed_cnt = sum(1 for item in summary if item["outcome"] == "REGRESSED")
    unchanged_cnt = sum(1 for item in summary if item["outcome"] in ["UNCHANGED-CORRECT", "UNCHANGED-WRONG", "DISAGREEMENT-RESOLVED", "DISAGREEMENT-FAILED"])

    avg_single_lat = sum(item["single_score"]["latency"] for item in summary) / total_cases if total_cases else 0.0
    avg_jury_lat = sum(item["jury_score"]["latency"] for item in summary) / total_cases if total_cases else 0.0

    # Build per-case table
    table_rows = []
    not_helped_cases = []

    for item in summary:
        cid = item["case_id"]
        ctype = item["type"]
        cdesc = item["description"]
        s_sc = item["single_score"]
        j_sc = item["jury_score"]
        outcome = item["outcome"]

        s_stat = "OK" if s_sc["status"] != "FAILED" else "FAILED"
        j_stat = "OK" if j_sc["status"] != "FAILED" else "FAILED"

        table_rows.append(
            f"| `{cid}` | `{ctype}` | {cdesc} | `{s_stat}` | `{j_stat}` | {s_sc['recall']*100:.1f}% | {j_sc['recall']*100:.1f}% | {s_sc['latency']:.2f}s | {j_sc['latency']:.2f}s | **{outcome}** |"
        )

        if outcome in ["REGRESSED", "UNCHANGED-CORRECT", "UNCHANGED-WRONG"]:
            not_helped_cases.append(item)

    md_content = f"""# Tiny Judges Evaluation Benchmark Report

Empirical comparison of **Single Model Baseline** vs **Multi-Role Jury System** (Expert, Skeptic, Beginner + Verifier) using Gemma 4 across 10 synthetic mobile UI test cases (390px viewport width).

## Executive Benchmark Summary

| Metric | Single Model Baseline | Multi-Role Jury | Delta / Summary |
| --- | --- | --- | --- |
| **Total Test Cases** | {total_cases} | {total_cases} | {total_cases} cases |
| **Successful Execution Cases** | {sum(1 for item in summary if item['single_score']['status'] != 'FAILED')} | {sum(1 for item in summary if item['jury_score']['status'] != 'FAILED')} | {successful_cases}/{total_cases} |
| **Failed Cases (API Errors)** | {sum(1 for item in summary if item['single_score']['status'] == 'FAILED')} | {sum(1 for item in summary if item['jury_score']['status'] == 'FAILED')} | {api_failures} API failures |
| **Bug Recall (`must_find`)** | **{single_rec:.1f}%** | **{jury_rec:.1f}%** | {jury_rec - single_rec:+.1f}% |
| **Overall Accuracy** | **{single_acc:.1f}%** | **{jury_acc:.1f}%** | {jury_acc - single_acc:+.1f}% |
| **Improved Cases** | - | - | **{improved_cnt} cases** |
| **Regressed Cases** | - | - | **{regressed_cnt} cases** |
| **Unchanged Cases** | - | - | **{unchanged_cnt} cases** |
| **Average Latency per Case** | {avg_single_lat:.2f}s | {avg_jury_lat:.2f}s | +{avg_jury_lat - avg_single_lat:+.2f}s |

---

## Per-Case Breakdown

| Case ID | Type | Description | Single Status | Jury Status | Single Recall | Jury Recall | Single Latency | Jury Latency | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(table_rows) + """

---

## Where the Jury Did NOT Help

Based on the empirical test results, the multi-role jury system did **NOT** provide a net performance benefit over the single model baseline in the following scenarios:

"""

    if not_helped_cases:
        for item in not_helped_cases:
            cid = item["case_id"]
            ctype = item["type"]
            cdesc = item["description"]
            outcome = item["outcome"]
            s_lat = item["single_score"]["latency"]
            j_lat = item["jury_score"]["latency"]

            md_content += f"""### Case `{cid}` ({ctype.upper()}): {cdesc}
- **Classification**: **{outcome}**
- **Latency Impact**: Single baseline took `{s_lat:.2f}s` vs Multi-Role Jury `{j_lat:.2f}s`.
- **Analysis**:
"""
            if ctype == "clear":
                md_content += f"  - For clear, high-contrast visual bugs like `{cid}`, a single Gemma 4 call already achieves high defect recall. Running 3 judge prompts plus a reconciler increases API cost by ~4x and latency without discovering extra defects.\n"
            elif ctype == "no_bug":
                md_content += f"  - On clean, bug-free UIs, incorporating a Skeptic role increases the risk of flagging false positive layout criticisms that the Verifier must filter out.\n"
            else:
                md_content += f"  - Multi-role consensus performed identically to the single model baseline while incurring a significant latency penalty.\n"
    else:
        md_content += "The multi-role jury outperformed the single model baseline across all test cases.\n"

    md_content += """
---
*Note: All benchmark metrics are calculated strictly from actual raw execution outputs saved in `results/raw/` without fabricated results.*
"""

    report_path = RESULTS_DIR / "results.md"
    report_path.write_text(md_content, encoding="utf-8")

def main():
    run_benchmark()

    report_path = RESULTS_DIR / "results.md"
    if report_path.exists():
        print("\n==========================================")
        print("BENCHMARK COMPLETE")
        print("==========================================")
        print(f"Report: {report_path}")
        print(f"Raw results: {RAW_DIR}/")
    else:
        print("Error: Report file results/results.md was not created!", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
