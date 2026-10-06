import os
import json
import time
import streamlit as st
from pathlib import Path
from PIL import Image

from single import run_single_model
from jury import run_jury_model

CASES_DIR = Path("cases")
RESULTS_DIR = Path("results")

st.set_page_config(
    page_title="Tiny Judges - Visual UI Bug Benchmark",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ Tiny Judges: Visual UI Bug Benchmark")
st.markdown("Comparing a **Single Model Baseline** vs a **Multi-Role Jury System** (Expert, Skeptic, Beginner + Verifier) using Gemma 4 on mobile UI screenshots.")

# Sidebar - Case Selection & Upload
st.sidebar.header("📁 Select Test Case / Input")

input_option = st.sidebar.radio("Input Source", ["Pre-generated Test Case", "Custom Upload / Prompt"])

selected_case_id = None
image_path = None
description_text = ""

if input_option == "Pre-generated Test Case":
    cases_files = sorted([f for f in CASES_DIR.glob("*.json")])
    if cases_files:
        case_options = [f.stem for f in cases_files]
        selected_case_id = st.sidebar.selectbox("Select Benchmark Case", case_options)
        
        with open(CASES_DIR / f"{selected_case_id}.json", "r", encoding="utf-8") as f:
            case_data = json.load(f)
            
        description_text = case_data.get("description", "")
        image_path = case_data.get("image_path", str(CASES_DIR / f"{selected_case_id}.png"))

        st.sidebar.markdown("---")
        st.sidebar.subheader("Ground Truth Specs")
        st.sidebar.markdown(f"**Type**: `{case_data.get('type')}`")
        st.sidebar.markdown(f"**Must Find Groups**: `{len(case_data.get('must_find', []))}`")
        with st.sidebar.expander("View Ground Truth JSON"):
            st.json(case_data)
else:
    uploaded_file = st.sidebar.file_uploader("Upload UI Screenshot", type=["png", "jpg", "jpeg", "webp"])
    description_text = st.sidebar.text_area("User Description / Context", "Audit this mobile UI screenshot for visual bugs.")
    
    if uploaded_file:
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_file_path = temp_dir / uploaded_file.name
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        image_path = str(temp_file_path)

# Main UI Layout
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("📷 Screenshot Preview")
    if image_path and Path(image_path).exists():
        img = Image.open(image_path)
        st.image(img, use_column_width=True)
    else:
        st.info("No screenshot image selected or provided.")
        
    st.markdown("### Context Description")
    st.write(description_text or "No context provided.")

with col_right:
    st.subheader("⚡ Model Comparison")
    
    btn_col1, btn_col2 = st.columns(2)
    run_single_btn = btn_col1.button("▶ Run Single Model", use_container_width=True)
    run_jury_btn = btn_col2.button("▶ Run Multi-Role Jury", use_container_width=True)
    run_both_btn = st.button("🚀 Run Both & Compare Side-by-Side", type="primary", use_container_width=True)

    if run_both_btn or run_single_btn or run_jury_btn:
        res_single = None
        res_jury = None
        
        if run_single_btn or run_both_btn:
            with st.spinner("Running Single Model Baseline..."):
                res_single = run_single_model(image_path=image_path, description=description_text)
                st.session_state["last_single"] = res_single

        if run_jury_btn or run_both_btn:
            with st.spinner("Running 3-Judge Jury + Verifier in parallel..."):
                res_jury = run_jury_model(image_path=image_path, description=description_text)
                st.session_state["last_jury"] = res_jury

    # Load from session state if available
    res_single = st.session_state.get("last_single")
    res_jury = st.session_state.get("last_jury")

    if res_single or res_jury:
        c1, c2 = st.columns(2)

        # Column 1: Single Model Results
        with c1:
            st.markdown("### 👤 Single Model Baseline")
            if res_single:
                st.metric("Latency", f"{res_single['latency']}s", delta=None)
                st.metric("Confidence", f"{res_single['confidence']}")
                
                st.markdown("**Summary:**")
                st.info(res_single.get("summary", "N/A"))

                st.markdown(f"**Issues Found ({len(res_single.get('issues', []))}):**")
                for idx, issue in enumerate(res_single.get("issues", []), 1):
                    with st.expander(f"Issue #{idx}: {issue.get('issue', 'Bug')}"):
                        st.markdown(f"**Evidence:** {issue.get('evidence')}")
                        st.markdown(f"**Probable Cause:** {issue.get('probable_cause')}")
                        st.markdown(f"**Confidence:** {issue.get('confidence')}")
            else:
                st.warning("Single Model not executed yet.")

        # Column 2: Jury Results
        with c2:
            st.markdown("### 👥 Multi-Role Jury + Verifier")
            if res_jury:
                st.metric("Latency", f"{res_jury['latency']}s", delta=f"+{round(res_jury['latency'] - (res_single['latency'] if res_single else 0), 2)}s")
                st.metric("Confidence", f"{res_jury['confidence']}")
                
                st.markdown("**Final Answer:**")
                st.success(res_jury.get("final_answer", "N/A"))

                st.markdown("**Agreement Summary:**")
                st.caption(res_jury.get("agreement_summary", "None"))

                if res_jury.get("disagreements"):
                    st.markdown("**Disagreements Resolved:**")
                    for d in res_jury.get("disagreements", []):
                        st.warning(f"• {d}")

                st.markdown("**Decision Reason:**")
                st.caption(res_jury.get("decision_reason", ""))

                st.markdown(f"**Verified Issues ({len(res_jury.get('issues', []))}):**")
                for idx, issue in enumerate(res_jury.get("issues", []), 1):
                    with st.expander(f"Verified Issue #{idx}: {issue.get('issue', 'Bug')}"):
                        st.markdown(f"**Evidence:** {issue.get('evidence')}")
                        st.markdown(f"**Probable Cause:** {issue.get('probable_cause')}")

                with st.expander("🔍 Inspect Individual Judge Outputs"):
                    for judge_res in res_jury.get("judge_outputs", []):
                        st.markdown(f"#### Role: {judge_res.get('role', 'Judge').upper()}")
                        st.json(judge_res)
            else:
                st.warning("Multi-Role Jury not executed yet.")

# Bottom Section: Overall Evaluation Dashboard
st.markdown("---")
st.header("📊 Benchmark Evaluation Dashboard")

results_md_path = RESULTS_DIR / "results.md"
summary_json_path = RESULTS_DIR / "eval_metrics_summary.json"

if summary_json_path.exists():
    with open(summary_json_path, "r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    single_m = [m for m in metrics_data if m["mode"] == "single"]
    jury_m = [m for m in metrics_data if m["mode"] == "jury"]

    if single_m and jury_m:
        s_rec = (sum(m["recall"] for m in single_m if m["case_type"] != "no_bug") / len([m for m in single_m if m["case_type"] != "no_bug"])) * 100
        j_rec = (sum(m["recall"] for m in jury_m if m["case_type"] != "no_bug") / len([m for m in jury_m if m["case_type"] != "no_bug"])) * 100

        s_fc = (sum(1 for m in single_m if m["has_false_claim"]) / len(single_m)) * 100
        j_fc = (sum(1 for m in jury_m if m["has_false_claim"]) / len(jury_m)) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Single Recall", f"{s_rec:.1f}%")
        m2.metric("Jury Recall", f"{j_rec:.1f}%", delta=f"{j_rec - s_rec:+.1f}%")
        m3.metric("Single False Claim Rate", f"{s_fc:.1f}%")
        m4.metric("Jury False Claim Rate", f"{j_fc:.1f}%", delta=f"{j_fc - s_fc:+.1f}%")

if results_md_path.exists():
    with st.expander("📄 View Full Benchmark Report (results/results.md)"):
        st.markdown(results_md_path.read_text(encoding="utf-8"))
else:
    st.info("Run `python eval.py` to generate the complete benchmark evaluation report.")
