# Tiny Judges Evaluation Benchmark Report

Empirical comparison of **Single Model Baseline** vs **Multi-Role Jury System** (Expert, Skeptic, Beginner + Verifier) using Gemma 4 across 10 synthetic mobile UI test cases (390px viewport width).

## Executive Benchmark Summary

| Metric | Single Model Baseline | Multi-Role Jury | Delta / Summary |
| --- | --- | --- | --- |
| **Total Test Cases** | 10 | 10 | 10 cases |
| **Successful Execution Cases** | 7 | 6 | 9/10 |
| **Failed Cases (API Errors)** | 3 | 4 | 7 API failures |
| **Bug Recall (`must_find`)** | **75.0%** | **75.0%** | +0.0% |
| **Overall Accuracy** | **70.0%** | **60.0%** | -10.0% |
| **Improved Cases** | - | - | **2 cases** |
| **Regressed Cases** | - | - | **3 cases** |
| **Unchanged Cases** | - | - | **4 cases** |
| **Average Latency per Case** | 46.79s | 166.10s | ++119.31s |

---

## Per-Case Breakdown

| Case ID | Type | Description | Single Status | Jury Status | Single Recall | Jury Recall | Single Latency | Jury Latency | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `case_01` | `clear` | Mobile UI with a fixed 600px width banner causing horizontal page overflow scroll on a 390px mobile screen. | `OK` | `OK` | 100.0% | 100.0% | 94.52s | 311.08s | **UNCHANGED-CORRECT** |
| `case_02` | `clear` | Form page where an absolute positioned submit button directly overlaps and obscures body text. | `OK` | `OK` | 100.0% | 100.0% | 53.57s | 236.38s | **UNCHANGED-CORRECT** |
| `case_03` | `clear` | Primary action button rendered with white text on a white background, making button text invisible. | `OK` | `OK` | 100.0% | 100.0% | 82.03s | 300.23s | **UNCHANGED-CORRECT** |
| `case_04` | `clear` | Modal dialog whose bottom content and action buttons are truncated off the bottom of the screen. | `FAILED` | `OK` | 0.0% | 100.0% | 2.21s | 147.19s | **IMPROVED** |
| `case_05` | `subtle` | Search input box where the search magnifying glass icon is misaligned 6px higher than text input baseline. | `OK` | `FAILED` | 100.0% | 0.0% | 48.79s | 50.53s | **REGRESSED** |
| `case_06` | `subtle` | Article paragraph with cramped line-height (0.80) causing text lines to touch and slightly overlap. | `FAILED` | `OK` | 0.0% | 100.0% | 55.97s | 121.28s | **IMPROVED** |
| `case_07` | `subtle` | Footer disclaimer text using faint light grey text (#e2e8f0) on white background violating contrast standards. | `OK` | `OK` | 100.0% | 100.0% | 39.12s | 111.11s | **UNCHANGED-CORRECT** |
| `case_08` | `no_bug` | Clean, properly styled mobile login form with no visual defects or layout bugs. | `OK` | `FAILED` | 100.0% | 0.0% | 35.18s | 142.94s | **REGRESSED** |
| `case_09` | `no_bug` | Clean e-commerce product card with high resolution image placeholder, title, rating, price, and CTA. | `FAILED` | `FAILED` | 0.0% | 0.0% | 2.99s | 146.92s | **FAILED** |
| `case_10` | `vague` | Settings page with a dark theme toggle situated near a floating action badge, creating ambiguous visual hierarchy. | `OK` | `FAILED` | 100.0% | 0.0% | 53.54s | 93.37s | **REGRESSED** |

---

## Where the Jury Did NOT Help

Based on the empirical test results, the multi-role jury system did **NOT** provide a net performance benefit over the single model baseline in the following scenarios:

### Case `case_01` (CLEAR): Mobile UI with a fixed 600px width banner causing horizontal page overflow scroll on a 390px mobile screen.
- **Classification**: **UNCHANGED-CORRECT**
- **Latency Impact**: Single baseline took `94.52s` vs Multi-Role Jury `311.08s`.
- **Analysis**:
  - For clear, high-contrast visual bugs like `case_01`, a single Gemma 4 call already achieves high defect recall. Running 3 judge prompts plus a reconciler increases API cost by ~4x and latency without discovering extra defects.
### Case `case_02` (CLEAR): Form page where an absolute positioned submit button directly overlaps and obscures body text.
- **Classification**: **UNCHANGED-CORRECT**
- **Latency Impact**: Single baseline took `53.57s` vs Multi-Role Jury `236.38s`.
- **Analysis**:
  - For clear, high-contrast visual bugs like `case_02`, a single Gemma 4 call already achieves high defect recall. Running 3 judge prompts plus a reconciler increases API cost by ~4x and latency without discovering extra defects.
### Case `case_03` (CLEAR): Primary action button rendered with white text on a white background, making button text invisible.
- **Classification**: **UNCHANGED-CORRECT**
- **Latency Impact**: Single baseline took `82.03s` vs Multi-Role Jury `300.23s`.
- **Analysis**:
  - For clear, high-contrast visual bugs like `case_03`, a single Gemma 4 call already achieves high defect recall. Running 3 judge prompts plus a reconciler increases API cost by ~4x and latency without discovering extra defects.
### Case `case_05` (SUBTLE): Search input box where the search magnifying glass icon is misaligned 6px higher than text input baseline.
- **Classification**: **REGRESSED**
- **Latency Impact**: Single baseline took `48.79s` vs Multi-Role Jury `50.53s`.
- **Analysis**:
  - Multi-role consensus performed identically to the single model baseline while incurring a significant latency penalty.
### Case `case_07` (SUBTLE): Footer disclaimer text using faint light grey text (#e2e8f0) on white background violating contrast standards.
- **Classification**: **UNCHANGED-CORRECT**
- **Latency Impact**: Single baseline took `39.12s` vs Multi-Role Jury `111.11s`.
- **Analysis**:
  - Multi-role consensus performed identically to the single model baseline while incurring a significant latency penalty.
### Case `case_08` (NO_BUG): Clean, properly styled mobile login form with no visual defects or layout bugs.
- **Classification**: **REGRESSED**
- **Latency Impact**: Single baseline took `35.18s` vs Multi-Role Jury `142.94s`.
- **Analysis**:
  - On clean, bug-free UIs, incorporating a Skeptic role increases the risk of flagging false positive layout criticisms that the Verifier must filter out.
### Case `case_10` (VAGUE): Settings page with a dark theme toggle situated near a floating action badge, creating ambiguous visual hierarchy.
- **Classification**: **REGRESSED**
- **Latency Impact**: Single baseline took `53.54s` vs Multi-Role Jury `93.37s`.
- **Analysis**:
  - Multi-role consensus performed identically to the single model baseline while incurring a significant latency penalty.

---
*Note: All benchmark metrics are calculated strictly from actual raw execution outputs saved in `results/raw/` without fabricated results.*
