import streamlit as st
import pdfplumber
from openai import OpenAI
import json
import os
import re
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
    return (
        str(text)
        .replace("•", "-")
        .replace("–", "-")
        .replace("—", "-")
        .encode("latin-1", "ignore")
        .decode("latin-1")
    )

def score_color(score):
    return {"Low": "green", "Medium": "orange", "High": "red"}.get(score, "gray")

def parse_json_safely(raw_output):
    try:
        return json.loads(raw_output)
    except Exception:
        try:
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                return json.loads(match.group())
            return None
        except Exception:
            return None

def build_pdf_report(
    file_name,
    risk_score,
    study_complexity,
    retention_risk,
    protocol_deviation_risk,
    complexity_rationale,
    retention_rationale,
    deviation_rationale,
    key_risks,
    inclusion,
    exclusion,
    cra_priorities,
    operational_challenges,
    deviation_hotspots,
    deviation_analysis,
    monitoring_strategy,
    visit_schedule,
    checklist,
    question,
    answer,
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def add_section(title, items):
        pdf.set_font("Arial", "B", 13)
        pdf.multi_cell(0, 8, clean_pdf_text(title))
        pdf.set_font("Arial", "", 11)

        if isinstance(items, list):
            if items:
                for item in items:
                    pdf.multi_cell(0, 7, f"- {clean_pdf_text(item)}")
            else:
                pdf.multi_cell(0, 7, "No information extracted.")
        else:
            text = clean_pdf_text(items)
            if text.strip():
                pdf.multi_cell(0, 7, text)
            else:
                pdf.multi_cell(0, 7, "No information extracted.")
        pdf.ln(3)

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Clinical Trial AI Assistant Pro", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "CRA Protocol Review Report", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, clean_pdf_text(f"Generated: {report_date}"), ln=True)
    pdf.cell(0, 6, clean_pdf_text(f"Document: {file_name}"), ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "Executive Score Summary", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 7, clean_pdf_text(f"Overall Risk: {risk_score}"), ln=True)
    pdf.cell(0, 7, clean_pdf_text(f"Study Complexity: {study_complexity}"), ln=True)
    pdf.cell(0, 7, clean_pdf_text(f"Retention Risk: {retention_risk}"), ln=True)
    pdf.cell(0, 7, clean_pdf_text(f"Deviation Risk: {protocol_deviation_risk}"), ln=True)
    pdf.ln(6)

    add_section("Complexity Rationale", complexity_rationale)
    add_section("Retention Rationale", retention_rationale)
    add_section("Deviation Rationale", deviation_rationale)
    add_section("Key Risks", key_risks)
    add_section("Inclusion Criteria", inclusion)
    add_section("Exclusion Criteria", exclusion)
    add_section("CRA Monitoring Priorities", cra_priorities)
    add_section("Operational Challenges", operational_challenges)
    add_section("Deviation Hotspots", deviation_hotspots)
    add_section("SMART Deviation Analysis", deviation_analysis)
    add_section("Monitoring Strategy", monitoring_strategy)

    visit_lines = []
    for visit in visit_schedule:
        visit_name = visit.get("visit_name", "Unknown Visit")
        timing = visit.get("timing", "Unknown Timing")
        activities = visit.get("activities", [])
        activity_text = ", ".join(activities) if activities else "No activities extracted"
        visit_lines.append(f"{visit_name} - {timing}: {activity_text}")

    add_section("Visit Schedule", visit_lines)
    add_section("Monitoring Visit Checklist", checklist)

    safe_q = clean_pdf_text(question)
    safe_a = clean_pdf_text(answer)
    add_section("Q&A", [f"Question: {safe_q}", f"Answer: {safe_a}"])

    return pdf.output(dest="S").encode("latin-1")

# ---------- UI ----------
st.markdown(
    """
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.card {
    background-color: #f8f9fb;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e6e8ef;
    margin-bottom: 16px;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: #1f2937;
}
.soft-box {
    background-color: #f4f8ff;
    padding: 16px;
    border-radius: 12px;
    border: 1px solid #dbeafe;
}
.risk-card {
    padding: 15px;
    border-radius: 12px;
    background-color: #f5f5f5;
    text-align: center;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("# Clinical Trial AI Assistant Pro")
st.caption("AI-powered protocol review and CRA decision support")
st.markdown("---")

if st.session_state.reports:
    st.markdown("## 📂 Previous Analyses")
    for r in st.session_state.reports[::-1]:
        st.markdown(
            f"""
            <div class="card">
            📄 <b>{r['file']}</b><br>
            <small>
            Risk: <b>{r['risk']}</b> |
            Complexity: <b>{r['complexity']}</b> |
            Retention: <b>{r['retention']}</b> |
            Deviation: <b>{r['deviation']}</b>
            </small>
            </div>
            """,
            unsafe_allow_html=True,
        )

uploaded_file = st.file_uploader("Upload protocol document", type="pdf")
question = st.text_input("Initial protocol question (optional, used in report export)")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    analyze_button = st.button("Analyze")
with col_btn2:
    clear_button = st.button("Clear Chat")

if clear_button:
    st.session_state.chat_history = []

# ---------- ANALYZE ----------
if uploaded_file and analyze_button:
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    if not text.strip():
        st.error("Could not extract text from this PDF.")
    else:
        with st.spinner("Analyzing protocol..."):
            summary_prompt = f"""
You are an AI assistant helping a Clinical Research Associate.

Analyze this clinical trial protocol and return ONLY valid JSON.

Use this schema:

{{
  "risk_score": "Low/Medium/High",
  "study_complexity": "Low/Medium/High",
  "retention_risk": "Low/Medium/High",
  "protocol_deviation_risk": "Low/Medium/High",
  "complexity_rationale": ["..."],
  "retention_rationale": ["..."],
  "deviation_rationale": ["..."],
  "key_risks": ["..."],
  "inclusion": ["..."],
  "exclusion": ["..."],
  "cra_priorities": ["..."],
  "operational_challenges": ["..."],
  "deviation_hotspots": ["..."],
  "deviation_analysis": ["..."],
  "monitoring_strategy": ["..."],
  "visit_schedule": [
    {{
      "visit_name": "...",
      "timing": "...",
      "activities": ["...", "..."]
    }}
  ]
}}

Rules:
- No explanation
- No markdown
- Only JSON
- Keep items short and practical
- All list items should be concise and CRA-relevant
- protocol_deviation_risk should reflect likelihood of site-level deviations based on protocol complexity, visit burden, eligibility complexity, and operational demands
- deviation_hotspots should list the areas most likely to generate protocol deviations
- deviation_analysis should include visit-level and process-level deviation risks
- highlight where sites are most likely to make mistakes
- monitoring_strategy should recommend visit frequency, monitoring intensity, and risk-based approach
- suggestions should be practical and CRA-focused
- visit_schedule should extract the main protocol visits with timing and key activities
- keep visit names and timing concise
- activities should be short and CRA-relevant

Protocol:
{text}
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
            )

            raw_output = response.choices[0].message.content
            data = parse_json_safely(raw_output)

            if data is None:
                st.error("Model did not return valid JSON.")
                st.code(raw_output)
                st.stop()

            risk_score = data.get("risk_score", "Unknown")
            study_complexity = data.get("study_complexity", "Unknown")
            retention_risk = data.get("retention_risk", "Unknown")
            protocol_deviation_risk = data.get("protocol_deviation_risk", "Unknown")

            complexity_rationale = data.get("complexity_rationale", [])
            retention_rationale = data.get("retention_rationale", [])
            deviation_rationale = data.get("deviation_rationale", [])

            key_risks = data.get("key_risks", [])
            inclusion = data.get("inclusion", [])
            exclusion = data.get("exclusion", [])
            cra_priorities = data.get("cra_priorities", [])
            operational_challenges = data.get("operational_challenges", [])
            deviation_hotspots = data.get("deviation_hotspots", [])
            deviation_analysis = data.get("deviation_analysis", [])
            monitoring_strategy = data.get("monitoring_strategy", [])
            visit_schedule = data.get("visit_schedule", [])

            checklist_prompt = f"""
You are a senior Clinical Research Associate.

Based on this protocol, generate a Monitoring Visit Checklist including:
- Critical data points
- High-risk areas
- SDV priorities
- Patient safety checks
- Compliance risks

Protocol:
{text}
"""

            checklist_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": checklist_prompt}],
            )

            checklist = checklist_response.choices[0].message.content

            st.session_state.protocol_text = text
            st.session_state.analysis_result = {
                "file_name": uploaded_file.name,
                "risk_score": risk_score,
                "study_complexity": study_complexity,
                "retention_risk": retention_risk,
                "protocol_deviation_risk": protocol_deviation_risk,
                "complexity_rationale": complexity_rationale,
                "retention_rationale": retention_rationale,
                "deviation_rationale": deviation_rationale,
                "key_risks": key_risks,
                "inclusion": inclusion,
                "exclusion": exclusion,
                "cra_priorities": cra_priorities,
                "operational_challenges": operational_challenges,
                "deviation_hotspots": deviation_hotspots,
                "deviation_analysis": deviation_analysis,
                "monitoring_strategy": monitoring_strategy,
                "visit_schedule": visit_schedule,
                "checklist": checklist,
            }

            st.session_state.reports.append(
                {
                    "file": uploaded_file.name,
                    "risk": risk_score,
                    "complexity": study_complexity,
                    "retention": retention_risk,
                    "deviation": protocol_deviation_risk,
                }
            )

# ---------- DISPLAY ANALYSIS ----------
if st.session_state.analysis_result:
    data = st.session_state.analysis_result

    file_name = data["file_name"]
    risk_score = data["risk_score"]
    study_complexity = data["study_complexity"]
    retention_risk = data["retention_risk"]
    protocol_deviation_risk = data["protocol_deviation_risk"]

    complexity_rationale = data["complexity_rationale"]
    retention_rationale = data["retention_rationale"]
    deviation_rationale = data["deviation_rationale"]

    key_risks = data["key_risks"]
    inclusion = data["inclusion"]
    exclusion = data["exclusion"]
    cra_priorities = data["cra_priorities"]
    operational_challenges = data["operational_challenges"]
    deviation_hotspots = data["deviation_hotspots"]
    deviation_analysis = data.get("deviation_analysis", [])
    monitoring_strategy = data.get("monitoring_strategy", [])
    visit_schedule = data.get("visit_schedule", [])
    checklist = data["checklist"]

    st.markdown("## Executive Risk Dashboard")

    st.markdown("### Risk Distribution")

    risk_levels = {"Low": 0, "Medium": 0, "High": 0}
    for r in key_risks:
        r_lower = r.lower()
        if "high" in r_lower:
            risk_levels["High"] += 1
        elif "medium" in r_lower:
            risk_levels["Medium"] += 1
        else:
            risk_levels["Low"] += 1

    total = sum(risk_levels.values()) or 1
    low_pct = int((risk_levels["Low"] / total) * 100)
    med_pct = int((risk_levels["Medium"] / total) * 100)
    high_pct = int((risk_levels["High"] / total) * 100)

    st.markdown(
        f"""
<div style="display:flex; height:20px; border-radius:10px; overflow:hidden; margin-bottom:10px;">
  <div style="width:{low_pct}%; background-color:green;"></div>
  <div style="width:{med_pct}%; background-color:orange;"></div>
  <div style="width:{high_pct}%; background-color:red;"></div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.caption(f"Low: {low_pct}% | Medium: {med_pct}% | High: {high_pct}%")

    col1, col2, col3, col4 = st.columns(4)

    col1.markdown(f"""<div class="risk-card"><h4>Overall Risk</h4><h2 style="color:{score_color(risk_score)};">{risk_score}</h2></div>""", unsafe_allow_html=True)
    col2.markdown(f"""<div class="risk-card"><h4>Study Complexity</h4><h2 style="color:{score_color(study_complexity)};">{study_complexity}</h2></div>""", unsafe_allow_html=True)
    col3.markdown(f"""<div class="risk-card"><h4>Retention Risk</h4><h2 style="color:{score_color(retention_risk)};">{retention_risk}</h2></div>""", unsafe_allow_html=True)
    col4.markdown(f"""<div class="risk-card"><h4>Deviation Risk</h4><h2 style="color:{score_color(protocol_deviation_risk)};">{protocol_deviation_risk}</h2></div>""", unsafe_allow_html=True)

    col_r1, col_r2, col_r3 = st.columns(3)

    with col_r1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Complexity Rationale</div>', unsafe_allow_html=True)
        for item in complexity_rationale:
            st.markdown(f"• {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Retention Rationale</div>', unsafe_allow_html=True)
        for item in retention_rationale:
            st.markdown(f"• {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Deviation Rationale</div>', unsafe_allow_html=True)
        for item in deviation_rationale:
            st.markdown(f"• {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Key Risks</div>', unsafe_allow_html=True)
        for r in key_risks:
            st.markdown(f"⚠️ {r}")

        st.markdown('<div class="section-title">Inclusion Criteria</div>', unsafe_allow_html=True)
        for i in inclusion:
            st.markdown(f"• {i}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Exclusion Criteria</div>', unsafe_allow_html=True)
        for e in exclusion:
            st.markdown(f"• {e}")

        st.markdown('<div class="section-title">Operational Challenges</div>', unsafe_allow_html=True)
        for c in operational_challenges:
            st.markdown(f"• {c}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">CRA Monitoring Priorities</div>', unsafe_allow_html=True)
    for p in cra_priorities:
        st.markdown(f"• {p}")

    st.markdown('<div class="section-title">Monitoring Strategy (AI Recommended)</div>', unsafe_allow_html=True)
    if monitoring_strategy:
        for item in monitoring_strategy:
            st.markdown(f"🧠 {item}")
    else:
        st.write("No monitoring strategy generated.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Deviation Hotspots</div>', unsafe_allow_html=True)
    if deviation_hotspots:
        for item in deviation_hotspots:
            st.markdown(f"• {item}")
    else:
        st.write("No deviation hotspots extracted.")

    st.markdown('<div class="section-title">SMART Deviation Analysis</div>', unsafe_allow_html=True)
    if deviation_analysis:
        for item in deviation_analysis:
            st.markdown(f"⚠️ {item}")
    else:
        st.write("No detailed deviation analysis extracted.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Visit Timeline</div>', unsafe_allow_html=True)

    if visit_schedule:
        for idx, visit in enumerate(visit_schedule, start=1):
            visit_name = visit.get("visit_name", f"Visit {idx}")
            timing = visit.get("timing", "Unknown Timing")
            activities = visit.get("activities", [])

                                with st.expander(f"{visit_name} — {timing}"):
                                                 if activities:
                                                     for act in activities:
                                                         st.markdown(f"""
    <div style="
        background-color:#eef2ff;
        padding:8px 10px;
        border-radius:8px;
        margin-bottom:6px;
    ">
        • {act}
    </div>
    """, unsafe_allow_html=True)
                else:
                    st.markdown("• No activities extracted")
    else:
        st.write("No visit schedule extracted.")

    st.markdown("</div>", unsafe_allow_html=True)





    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("## Monitoring Visit Checklist")
    st.markdown(f'<div class="soft-box">{checklist}</div>', unsafe_allow_html=True)

    answer = ""

    with st.form("ask_form", clear_on_submit=True):
        ask_question = st.text_input("Ask follow-up questions about the analyzed protocol")
        ask_button = st.form_submit_button("Ask")

    if ask_button and ask_question:
        messages = [
            {
                "role": "system",
                "content": """
You are an AI assistant helping a Clinical Research Associate understand a clinical trial protocol.
Answer using only the provided protocol text.
Be concise, clinically relevant, practical, and consistent with prior conversation context.
""",
            },
            {"role": "user", "content": f"Protocol text:\n{st.session_state.protocol_text}"},
        ]

        for role, msg in st.session_state.chat_history:
            messages.append(
                {"role": "user" if role == "You" else "assistant", "content": msg}
            )

        messages.append({"role": "user", "content": ask_question})

        qa = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

        answer = qa.choices[0].message.content
        st.session_state.chat_history.append(("You", ask_question))
        st.session_state.chat_history.append(("Assistant", answer))

    latest_answer = ""
    if st.session_state.chat_history and st.session_state.chat_history[-1][0] == "Assistant":
        latest_answer = st.session_state.chat_history[-1][1]

    if latest_answer:
        st.markdown("## Clinical Insight")
        st.markdown(f'<div class="soft-box">{latest_answer}</div>', unsafe_allow_html=True)

    pdf_question = question if question else "No initial question provided."
    pdf_answer = latest_answer if latest_answer else "No Q&A response generated yet."

    pdf_data = build_pdf_report(
        file_name=file_name,
        risk_score=risk_score,
        study_complexity=study_complexity,
        retention_risk=retention_risk,
        protocol_deviation_risk=protocol_deviation_risk,
        complexity_rationale=complexity_rationale,
        retention_rationale=retention_rationale,
        deviation_rationale=deviation_rationale,
        key_risks=key_risks,
        inclusion=inclusion,
        exclusion=exclusion,
        cra_priorities=cra_priorities,
        operational_challenges=operational_challenges,
        deviation_hotspots=deviation_hotspots,
        deviation_analysis=deviation_analysis,
        monitoring_strategy=monitoring_strategy,
        visit_schedule=visit_schedule,
        checklist=checklist,
        question=pdf_question,
        answer=pdf_answer,
    )

    st.markdown("## Export")
    st.download_button(
        label="📥 Download CRA Report (PDF)",
        data=pdf_data,
        file_name=f"{file_name.rsplit('.', 1)[0]}_CRA_Report.pdf",
        mime="application/pdf",
    )

    if st.session_state.chat_history:
        st.subheader("Conversation History")
        for role, msg in st.session_state.chat_history:
            st.write(f"{role}: {msg}")
