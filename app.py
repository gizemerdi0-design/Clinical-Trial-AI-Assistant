import streamlit as st
import pdfplumber
from openai import OpenAI
import json
import os
from fpdf import FPDF
from datetime import datetime

# ---------- API KEY ----------
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# ---------- SESSION ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

if "protocol_text" not in st.session_state:
    st.session_state.protocol_text = ""

if "reports" not in st.session_state:
    st.session_state.reports = []

# ---------- HELPERS ----------
def clean_pdf_text(text):
    return str(text).replace("•", "-").encode("latin-1", "ignore").decode("latin-1")

def score_color(score):
    return {"Low":"green","Medium":"orange","High":"red"}.get(score,"gray")

# ---------- UI ----------
st.title("Clinical Trial AI Assistant Pro")

uploaded_file = st.file_uploader("Upload protocol", type="pdf")
question = st.text_input("Ask a question")

ask_button = st.button("Ask")
analyze_button = st.button("Analyze")

# ---------- ANALYZE ----------
if uploaded_file and analyze_button:

    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    prompt = f"""
Return ONLY JSON:

{{
 "risk_score":"Low/Medium/High",
 "study_complexity":"Low/Medium/High",
 "retention_risk":"Low/Medium/High",
 "protocol_deviation_risk":"Low/Medium/High",
 "key_risks":["..."],
 "cra_priorities":["..."]
}}

Protocol:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    data = json.loads(response.choices[0].message.content)

    st.session_state.protocol_text = text

    st.session_state.analysis_result = data

# ---------- DISPLAY ----------
if st.session_state.analysis_result:

    data = st.session_state.analysis_result

    risk = data.get("risk_score")
    complexity = data.get("study_complexity")
    retention = data.get("retention_risk")
    deviation = data.get("protocol_deviation_risk")

    key_risks = data.get("key_risks",[])
    cra_priorities = data.get("cra_priorities",[])

    st.markdown("## Dashboard")

    col1,col2,col3,col4 = st.columns(4)

    col1.markdown(f"<h3 style='color:{score_color(risk)}'>{risk}</h3>",unsafe_allow_html=True)
    col2.markdown(f"<h3 style='color:{score_color(complexity)}'>{complexity}</h3>",unsafe_allow_html=True)
    col3.markdown(f"<h3 style='color:{score_color(retention)}'>{retention}</h3>",unsafe_allow_html=True)
    col4.markdown(f"<h3 style='color:{score_color(deviation)}'>{deviation}</h3>",unsafe_allow_html=True)

    # heatmap
    st.markdown("### Risk Distribution")
    st.progress(0.7)

    st.markdown("## Key Risks")
    for r in key_risks:
        st.markdown(f"⚠️ {r}")

    st.markdown("## CRA Priorities")
    for p in cra_priorities:
        st.markdown(f"• {p}")

# ---------- Q&A ----------
answer = ""

if question and ask_button and st.session_state.analysis_result:

    messages = [
        {"role":"system","content":"Answer based on protocol"},
        {"role":"user","content":st.session_state.protocol_text}
    ]

    for role,msg in st.session_state.chat_history:
        messages.append({"role":"user" if role=="You" else "assistant","content":msg})

    messages.append({"role":"user","content":question})

    qa = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    answer = qa.choices[0].message.content

    st.session_state.chat_history.append(("You",question))
    st.session_state.chat_history.append(("Assistant",answer))

if answer:
    st.markdown("## Answer")
    st.write(answer)

if st.session_state.chat_history:
    st.markdown("## History")
    for role,msg in st.session_state.chat_history:
        st.write(f"{role}: {msg}")
