import os
import json
import csv
import io
import tempfile
import base64
import matplotlib.pyplot as plt
import streamlit as st
from PIL import Image
import pandas as pd
import streamlit.components.v1 as components
from src.pipeline import process_resume
import time
import plotly.graph_objects as go
# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="ParsePal", layout="wide")
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 350px;
        }
    </style>
""", unsafe_allow_html=True)

# ─── Header ────────────────────────────────────────────────────────────────────
logo = Image.open("assets/logo.png")
st.image(logo, width=350, )
st.markdown("Upload PDF resumes and press **Process Resumes** to begin.")

# ─── Centered Uploader & Process Button ────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("### Company Inputs")

    required_skills = st.text_input(
        "Enter required skills (comma-separated)",
        placeholder="e.g. communication, logistics, python, inventory"
    )

    jd_file = st.file_uploader("Upload Job Description (.txt)", type="txt", key="jd_uploader")

    uploaded_files = st.file_uploader(
        "Drop PDF resumes here",
        type="pdf",
        accept_multiple_files=True,
        key="center_uploader"
    )
    process = st.button("▶ Process Resumes")



# ─── Process & Store Results ───────────────────────────────────────────────────
company_skills = [s.strip().lower() for s in required_skills.split(",") if s.strip()]
if process and uploaded_files:
    with st.spinner("Parsing resumes, please wait…"):
        results = []
        for pdf in uploaded_files:
            # write to temp file for pipeline
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf.getbuffer())
                tmp_path = tmp.name
            jd_path = None
            if jd_file:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as jd_tmp:
                    jd_tmp.write(jd_file.getbuffer())
                    jd_path = jd_tmp.name
            res = process_resume(tmp_path, jd_path=jd_path, company_skills=company_skills)
            res["_pdf_buffer"] = pdf.getbuffer()  # keep in memory
            res["file_name"] = pdf.name  # ✅ Store original filename
            results.append(res)
            os.unlink(tmp_path)
    st.success("✅ Parsing complete!")
    st.session_state["results"] = results
    st.session_state["idx"] = 0  # start at first




# ─── Sidebar Controls ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    results = st.session_state["results"]
    idx     = st.session_state.get("idx", 0)
    total   = len(results)
    current = idx + 1  # human‑friendly count

    # 1) Show textual progress
    st.sidebar.markdown(f"#### Resume Progress: {current} / {total}")

    # 2) Show a full bar
    progress = current / total
    st.sidebar.progress(progress)
    count = len(st.session_state["results"])
    st.sidebar.markdown(f"###  Parsed Resumes ({count})")

    current_idx = st.session_state.get("idx", 0)

    for i, r in enumerate(st.session_state["results"]):
        label = r["file_name"]
        
        # Show badge and bold for active resume
        if i == current_idx:
            display_label = f" <span style='color:green;font-size:12px;'>🟢 Currently Viewing</span>"
        else:
            display_label = label

        # Render clickable buttons
        if st.sidebar.button(label, key=f"resume_{i}"):
            st.session_state["idx"] = i
            st.rerun()

        # Show badge below current active item
        if i == current_idx:
            st.sidebar.markdown(display_label, unsafe_allow_html=True)


    if st.sidebar.button("⟳ Reset"):
        for k in ["results", "idx"]:
            st.session_state.pop(k, None)
        st.rerun()

# ─── All resumes tab ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    st.markdown("##  All Parsed Resumes")

    table_data = []
    for r in st.session_state["results"]:
        table_data.append({
            "Name": r.get("name", ""),
            "Email": r.get("email", ""),
            "Phone": r.get("phone", ""),
            "LinkedIn": r.get("linkedin", ""),
            "GitHub": r.get("github", ""),
            "Skills": " ".join([f"`{s}`" for s in r.get("skills", [])]),
            "Companies–Positions": " | ".join(r.get("companies_positions", [])),
            "Experience": r.get("experience_section",""),
            "Education": r.get("education_section","")
        })

    df = pd.DataFrame(table_data)

    # Show with markdown-styled skill badges
    st.dataframe(df, use_container_width=True, height=300)

    # Excel download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Parsed Resumes")
    st.download_button(
        " Download Excel",
        data=output.getvalue(),
        file_name="parsed_resumes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ─── Main Display: One Resume + Details ────────────────────────────────────────
if "results" in st.session_state:
    idx = st.session_state["idx"]
    res = st.session_state["results"][idx]

    # ─── Auto‑Animating ATS Gauge ───────────────────────────────────────────────
    if res.get("ats_score") is not None:
        st.markdown("##  ATS Score")
        placeholder = st.empty()
        target = int(res["ats_score"])
        # Animate from 0 → target
        for val in range(0, target + 1):
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=val,
                    title={'text': "ATS Score", 'font': {'size': 18}},
                    gauge={
                        'shape': 'angular',
                        'axis': {'range': [0, 100]},
                        'bar': {'color': '#1f77b4'},
                        'bgcolor': 'lightgray',
                        'borderwidth': 0,
                        'steps': [
                            {'range': [0, 50], 'color': '#d62728'},
                            {'range': [50, 75], 'color': '#ff7f0e'},
                            {'range': [75, 100], 'color': '#2ca02c'},
                        ],
                    },
                    number={'suffix': "%", 'font': {'size': 24}},
                )
            )
            fig.update_layout(margin={'t':0,'b':0,'l':0,'r':0}, height=250)
            placeholder.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            time.sleep(0.01)

    # ─── PDF Viewer ─────────────────────────────────────────────
    st.markdown("##  View Resume")
    b64 = base64.b64encode(res["_pdf_buffer"]).decode("utf-8")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" '
        'width="100%" height="1100px"></iframe>',
        unsafe_allow_html=True,
    )

    details = {
        "Name": res.get("name", "—"),
        "Email": res.get("email", "—"),
        "Phone": res.get("phone", "—"),
        "LinkedIn": res.get("linkedin", "—"),
        "GitHub": res.get("github", "—"),
        "Skills": ", ".join(res.get("skills", [])) or "—",
        "Companies–Positions": "\n".join(res.get("companies_positions", [])) or "—",
        "Education": res.get("education_section", "—"),
        "Experience": res.get("experience_section", "—"),
        "Required Skills": ", ".join(res.get("required_skills", [])) or "—",
        "Matched Skills" : ", ".join(res.get("matched_skills", [])) or "—",
        "ATS Score" : f"{res['ats_score']}%"  if res.get("ats_score") else "—"

    }
    
    # ─── Tabs UI ────────────────────────────────────────────────────────
if "results" in st.session_state:
    idx     = st.session_state["idx"]
    results = st.session_state["results"]
    res      = results[idx]


    tab = st.tabs([" CSV Output"])[0]
    with tab:
        st.markdown("###  CSV Output")
        table_data = {
            "Field": list(details.keys()),
            "Value": list(details.values())
        }
        df_single = pd.DataFrame(table_data)
        st.dataframe(df_single, use_container_width=True)  

            # ─── Pagination ────────────────────────────────────────────────────────────
    prev_col, _, next_col = st.columns([1, 1, 1])
    if prev_col.button("⬅️ Previous") and idx > 0:
                    st.session_state["idx"] = idx - 1
                    st.rerun()
    if next_col.button("Next ➡️") and idx < len(results) - 1:
                    st.session_state["idx"] = idx + 1
                    st.rerun()

