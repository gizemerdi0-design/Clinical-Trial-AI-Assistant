import os
import json
import re
from io import BytesIO

import pdfplumber
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem


# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="Clinical Trial AI Assistant Pro", layout="wide")


# =========================
# CUSTOM CSS
# =========================
st.markdown(
    """
    <style>
    .main-title {
        font-size: 34px;
        font-weight: 700;
        color: #1f3c88;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #5b6475;
        margin-bottom: 1.2rem;
    }
    .card {
        background-color: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
    }
    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #22304a;
        margin-bottom: 10px;
    }
    .soft-box {
        background-color: #f6f8fc;
        border-radius: 12px;
        padding: 12px 14px;
        border: 1px solid #e7ebf3;
        margin-bottom: 8px;
    }
    .mini-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 8px;
    }
    .risk-low {
        background-color: #d9f7e8;
        color: #117a43;
    }
    .risk-medium {
        background-color: #fff4d6;
        color: #9a6700;
    }
    .risk-high {
        background-color: #fde1e1;
        color: #b42318;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# SESSION STATE
# =========================
def init_session_state():
    defaults = {
        "protocol_text": "",
        "analysis_result": None,
        "chat_history": [],
        "last_question": "",
        "last_answer": "",
        "uploaded_file_name": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


# =========================
# HELPERS
# =========================
def get_client():
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    if not api_key:
        st.error("OPENAI_API_KEY not found. Add it to Streamlit secrets or environment variables.")
        st.stop()
    return OpenAI(api_key=api_key)


client = get_client()


def extract_pdf_text(uploaded_file) -> str:
    text_chunks = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n\n".join(text_chunks).strip()


def safe_json_loads(text: str):
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"^```", "", text)
    text = re.sub(r"```$", "", text)
    text = text.strip()
    return json.loads(text)


def ensure_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def ensure_visit_schedule(value):
    if not isinstance(value, list):
        return []

    clean_visits = []
    for item in value:
        if not isinstance(item, dict):
            continue
        clean_visits.append(
            {
                "visit_name": str(item.get("visit_name", "Unknown Visit")),
                "timing": str(item.get("timing", "Unknown Timing")),
                "activities": ensure_list(item.get("activities", [])),
            }
        )
    return clean_visits


def ensure_visit_risk_flags(value):
    if not isinstance(value, list):
        return []

    clean_flags = []
    for item in value:
        if not isinstance(item, dict):
            continue
        clean_flags.append(
            {
                "visit_name": str(item.get("visit_name", "Unknown Visit")),
                "risk_level": str(item.get("risk_level", "Low")),
                "reason": str(item.get("reason", "")),
            }
        )
    return clean_flags


def clean_pdf_text(text: str) -> str:
    if text is None:
        return ""
    return str(text).replace("•", "-").replace("–", "-").replace("—", "-")


def risk_icon(risk_level: str) -> str:
    value = str(risk_level).strip().lower()
    if value == "high":
        return "🔴"
    if value == "medium":
        return "🟠"
    return "🟢"


def risk_badge_html(risk_level: str) -> str:
    value = str(risk_level).strip().lower()
    cls = "risk-low"
    label = "Low"
    if value == "high":
        cls = "risk-high"
        label = "High"
    elif value == "medium":
        cls = "risk-medium"
        label = "Medium"
    return f'<span class="mini-badge {cls}">{label}</span>'


def build_analysis_prompt(protocol_text: str, user_question: str) -> str:
    question_block = user_question.strip() if user_question.strip() else "No initial question provided."
    return f"""
You are an expert Clinical Research Associate assistant.

Analyze the following clinical trial protocol and return ONLY valid JSON.
No markdown. No explanations. No code block fences.

Required JSON schema:
{{
  "file_name": "string",
  "risk_score": "Low/Medium/High",
  "study_complexity": "Low/Medium/High",
  "retention_risk": "Low/Medium/High",
  "protocol_deviation_risk": "Low/Medium/High",
  "complexity_rationale": ["string", "string"],
  "retention_rationale": ["string", "string"],
  "deviation_rationale": ["string", "string"],
  "key_risks": ["string"],
  "inclusion": ["string"],
  "exclusion": ["string"],
  "cra_priorities": ["string"],
  "operational_challenges": ["string"],
  "site_action_items": ["string"],
  "deviation_hotspots": ["string"],
  "deviation_analysis": ["string"],
  "monitoring_strategy": ["string"],
  "visit_risk_flags": [
    {{
      "visit_name": "string",
      "risk_level": "Low/Medium/High",
      "reason": "string"
    }}
  ],
  "visit_schedule": [
    {{
      "visit_name": "string",
      "timing": "string",
      "activities": ["string"]
    }}
  ],
  "checklist": ["string"]
}}

Guidance:
- Keep outputs practical and CRA-focused.
- Extract visit schedule only if present or strongly inferable from the protocol.
- Site action items should be actionable for site staff or site-facing monitoring follow-up.
- Deviation hotspots should focus on likely noncompliance or protocol deviation areas.
- Keep each bullet concise.
- If something is not available, return an empty list.

Initial user question:
{question_block}

Protocol:
{protocol_text}
""".strip()


def parse_analysis_result(raw_json_text: str, uploaded_file_name: str):
    data = safe_json_loads(raw_json_text)

    return {
        "file_name": uploaded_file_name,
        "risk_score": str(data.get("risk_score", "Low")),
        "study_complexity": str(data.get("study_complexity", "Low")),
        "retention_risk": str(data.get("retention_risk", "Low")),
        "protocol_deviation_risk": str(data.get("protocol_deviation_risk", "Low")),
        "complexity_rationale": ensure_list(data.get("complexity_rationale", [])),
        "retention_rationale": ensure_list(data.get("retention_rationale", [])),
        "deviation_rationale": ensure_list(data.get("deviation_rationale", [])),
        "key_risks": ensure_list(data.get("key_risks", [])),
        "inclusion": ensure_list(data.get("inclusion", [])),
        "exclusion": ensure_list(data.get("exclusion", [])),
        "cra_priorities": ensure_list(data.get("cra_priorities", [])),
        "operational_challenges": ensure_list(data.get("operational_challenges", [])),
        "site_action_items": ensure_list(data.get("site_action_items", [])),
        "deviation_hotspots": ensure_list(data.get("deviation_hotspots", [])),
        "deviation_analysis": ensure_list(data.get("deviation_analysis", [])),
        "monitoring_strategy": ensure_list(data.get("monitoring_strategy", [])),
        "visit_risk_flags": ensure_visit_risk_flags(data.get("visit_risk_flags", [])),
        "visit_schedule": ensure_visit_schedule(data.get("visit_schedule", [])),
        "checklist": ensure_list(data.get("checklist", [])),
    }


def ask_protocol_question(protocol_text: str, analysis_result: dict, question: str, chat_history: list):
    summary_context = json.dumps(analysis_result, ensure_ascii=False)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Clinical Trial AI Assistant for Clinical Research Associates. "
                "Answer only based on the uploaded protocol text and the extracted analysis summary. "
                "If the answer is not supported, say so clearly."
            ),
        },
        {
            "role": "user",
            "content": f"Protocol text:\n{protocol_text}\n\nExtracted analysis summary:\n{summary_context}",
        },
    ]

    for item in chat_history[-6:]:
        messages.append({"role": "user", "content": item.get("question", "")})
        messages.append({"role": "assistant", "content": item.get("answer", "")})

    messages.append({"role": "user", "content": question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def add_section(story, styles, title, content):
    story.append(Paragraph(f"<b>{clean_pdf_text(title)}</b>", styles["section_header"]))
    story.append(Spacer(1, 0.15 * cm))

    if isinstance(content, list):
        items = [clean_pdf_text(x) for x in content if str(x).strip()]
        if items:
            bullet_items = [
                ListItem(Paragraph(item, styles["body"]), leftIndent=10) for item in items
            ]
            story.append(ListFlowable(bullet_items, bulletType="bullet"))
        else:
            story.append(Paragraph("No data available.", styles["body"]))
    else:
        value = clean_pdf_text(content)
        story.append(Paragraph(value if value else "No data available.", styles["body"]))

    story.append(Spacer(1, 0.25 * cm))


def build_pdf_report(file_name, analysis_result, question, answer):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base_styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1f3c88"),
            spaceAfter=12,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            parent=base_styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#22304a"),
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base_styles["BodyText"],
            fontSize=10,
            leading=14,
            spaceAfter=4,
        ),
    }

    story = []
    story.append(Paragraph("Clinical Trial AI Assistant Report", styles["title"]))
    story.append(Paragraph(f"<b>Protocol File:</b> {clean_pdf_text(file_name)}", styles["body"]))
    story.append(Spacer(1, 0.2 * cm))

    dashboard_lines = [
        f"Overall Risk Score: {analysis_result.get('risk_score', 'Low')}",
        f"Study Complexity: {analysis_result.get('study_complexity', 'Low')}",
        f"Retention Risk: {analysis_result.get('retention_risk', 'Low')}",
        f"Protocol Deviation Risk: {analysis_result.get('protocol_deviation_risk', 'Low')}",
    ]
    add_section(story, styles, "Executive Risk Dashboard", dashboard_lines)
    add_section(story, styles, "Protocol Overview", analysis_result.get("complexity_rationale", []))
    add_section(story, styles, "Retention Rationale", analysis_result.get("retention_rationale", []))
    add_section(story, styles, "Protocol Deviation Rationale", analysis_result.get("deviation_rationale", []))
    add_section(story, styles, "Key Risks", analysis_result.get("key_risks", []))
    add_section(story, styles, "Inclusion Criteria", analysis_result.get("inclusion", []))
    add_section(story, styles, "Exclusion Criteria", analysis_result.get("exclusion", []))
    add_section(story, styles, "CRA Monitoring Priorities", analysis_result.get("cra_priorities", []))
    add_section(story, styles, "Operational Challenges", analysis_result.get("operational_challenges", []))
    add_section(story, styles, "Site-Facing Action Items", analysis_result.get("site_action_items", []))
    add_section(story, styles, "Deviation Hotspots", analysis_result.get("deviation_hotspots", []))
    add_section(story, styles, "SMART Deviation Analysis", analysis_result.get("deviation_analysis", []))
    add_section(story, styles, "Monitoring Strategy", analysis_result.get("monitoring_strategy", []))

    visit_lines = []
    for visit in analysis_result.get("visit_schedule", []):
        visit_name = visit.get("visit_name", "Unknown Visit")
        timing = visit.get("timing", "Unknown Timing")
        activities = visit.get("activities", [])
        activity_text = ", ".join([clean_pdf_text(a) for a in activities]) if activities else "No activities extracted"
        visit_lines.append(f"{visit_name} - {timing}: {activity_text}")
    add_section(story, styles, "Visit Schedule", visit_lines)

    risk_flag_lines = []
    for item in analysis_result.get("visit_risk_flags", []):
        risk_flag_lines.append(
            f"{item.get('visit_name', 'Unknown Visit')} - {item.get('risk_level', 'Low')}: {item.get('reason', '')}"
        )
    add_section(story, styles, "Visit Risk Flags", risk_flag_lines)
    add_section(story, styles, "Monitoring Visit Checklist", analysis_result.get("checklist", []))

    safe_q = clean_pdf_text(question if question else "No initial protocol question provided.")
    safe_a = clean_pdf_text(answer if answer else "No follow-up answer generated.")
    add_section(story, styles, "Q&A", [f"Question: {safe_q}", f"Answer: {safe_a}"])

    doc.build(story)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data


def render_list_card(title, items):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if items:
        for item in items:
            st.markdown(f'<div class="soft-box">- {item}</div>', unsafe_allow_html=True)
    else:
        st.write("No data extracted.")
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# UI HEADER
# =========================
st.markdown('<div class="main-title">🧠 Clinical Trial AI Assistant Pro</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">AI-powered protocol analysis for Clinical Research Associates</div>',
    unsafe_allow_html=True,
)


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("Settings")
    st.caption("Upload a protocol PDF, analyze it, ask follow-up questions, and export a report.")

    if st.button("Clear Chat / Reset Session"):
        for key in [
            "protocol_text",
            "analysis_result",
            "chat_history",
            "last_question",
            "last_answer",
            "uploaded_file_name",
        ]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


# =========================
# MAIN INPUTS
# =========================
uploaded_file = st.file_uploader("Upload Clinical Trial PDF", type=["pdf"])
initial_question = st.text_input("Initial protocol question (optional, used in report export)")

col_a, col_b = st.columns([1, 1])
with col_a:
    analyze_clicked = st.button("Analyze")
with col_b:
    clear_chat_clicked = st.button("Clear Chat")

if clear_chat_clicked:
    st.session_state.chat_history = []
    st.session_state.last_question = ""
    st.session_state.last_answer = ""
    st.rerun()


# =========================
# ANALYZE
# =========================
if analyze_clicked:
    if not uploaded_file:
        st.warning("Please upload a protocol PDF first.")
    else:
        with st.spinner("Extracting protocol text and generating CRA analysis..."):
            try:
                protocol_text = extract_pdf_text(uploaded_file)
                if not protocol_text:
                    st.error("No readable text found in the PDF.")
                else:
                    prompt = build_analysis_prompt(protocol_text, initial_question)
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "system",
                                "content": "Return only valid JSON matching the requested schema.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                    )
                    raw_text = response.choices[0].message.content
                    analysis_result = parse_analysis_result(raw_text, uploaded_file.name)

                    st.session_state.protocol_text = protocol_text
                    st.session_state.analysis_result = analysis_result
                    st.session_state.uploaded_file_name = uploaded_file.name
                    st.session_state.last_question = initial_question.strip()
                    st.session_state.last_answer = ""
            except Exception as e:
                st.error(f"Analysis failed: {e}")


# =========================
# RENDER RESULTS
# =========================
analysis_result = st.session_state.analysis_result
protocol_text = st.session_state.protocol_text

if analysis_result:
    file_name = analysis_result.get("file_name", st.session_state.uploaded_file_name)
    risk_score = analysis_result.get("risk_score", "Low")
    study_complexity = analysis_result.get("study_complexity", "Low")
    retention_risk = analysis_result.get("retention_risk", "Low")
    protocol_deviation_risk = analysis_result.get("protocol_deviation_risk", "Low")

    complexity_rationale = analysis_result.get("complexity_rationale", [])
    retention_rationale = analysis_result.get("retention_rationale", [])
    deviation_rationale = analysis_result.get("deviation_rationale", [])
    key_risks = analysis_result.get("key_risks", [])
    inclusion = analysis_result.get("inclusion", [])
    exclusion = analysis_result.get("exclusion", [])
    cra_priorities = analysis_result.get("cra_priorities", [])
    operational_challenges = analysis_result.get("operational_challenges", [])
    site_action_items = analysis_result.get("site_action_items", [])
    deviation_hotspots = analysis_result.get("deviation_hotspots", [])
    deviation_analysis = analysis_result.get("deviation_analysis", [])
    monitoring_strategy = analysis_result.get("monitoring_strategy", [])
    visit_schedule = analysis_result.get("visit_schedule", [])
    visit_risk_flags = analysis_result.get("visit_risk_flags", [])
    checklist = analysis_result.get("checklist", [])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">## Executive Risk Dashboard</div>', unsafe_allow_html=True)
    st.markdown(f"**Protocol File:** {file_name}")
    st.markdown(risk_badge_html(risk_score) + risk_badge_html(study_complexity) + risk_badge_html(retention_risk) + risk_badge_html(protocol_deviation_risk), unsafe_allow_html=True)
    st.markdown(f"**📊 Risk Level:** {risk_score}")
    st.markdown(f"**Study Complexity:** {study_complexity}")
    st.markdown(f"**Retention Risk:** {retention_risk}")
    st.markdown(f"**Protocol Deviation Risk:** {protocol_deviation_risk}")
    st.markdown("</div>", unsafe_allow_html=True)

    render_list_card("📊 AI Clinical Summary", complexity_rationale)
    render_list_card("### 🧾 Protocol Overview", complexity_rationale)
    render_list_card("### ⚠️ Risks", key_risks)
    render_list_card("### 👥 Inclusion", inclusion)
    render_list_card("### 🚫 Exclusion", exclusion)
    render_list_card("### 🎯 CRA Monitoring Priorities", cra_priorities)
    render_list_card("### 🛠️ Operational Challenges", operational_challenges)
    render_list_card("### ✅ Site-Facing Action Items", site_action_items)
    render_list_card("### 🔬 Retention Rationale", retention_rationale)
    render_list_card("### 📍 Deviation Rationale", deviation_rationale)
    render_list_card("### 🔥 Deviation Hotspots", deviation_hotspots)
    render_list_card("SMART Deviation Analysis", deviation_analysis)
    render_list_card("Monitoring Strategy", monitoring_strategy)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Visit Schedule Timeline</div>', unsafe_allow_html=True)
    if visit_schedule:
        for visit in visit_schedule:
            visit_name = visit.get("visit_name", "Unknown Visit")
            timing = visit.get("timing", "Unknown Timing")
            activities = visit.get("activities", [])

            risk_level = "Low"
            risk_reason = ""
            for flag in visit_risk_flags:
                if flag.get("visit_name", "").strip().lower() == visit_name.strip().lower():
                    risk_level = flag.get("risk_level", "Low")
                    risk_reason = flag.get("reason", "")
                    break

            with st.expander(f"{risk_icon(risk_level)} {visit_name} - {timing}"):
                st.markdown(f"**Risk Level:** {risk_level}")
                if risk_reason:
                    st.markdown(f"_Reason:_ {risk_reason}")
                if activities:
                    for act in activities:
                        st.markdown(f'<div class="soft-box">- {act}</div>', unsafe_allow_html=True)
                else:
                    st.markdown("- No activities extracted")
    else:
        st.write("No visit schedule extracted.")
    st.markdown("</div>", unsafe_allow_html=True)

    render_list_card("Monitoring Visit Checklist", checklist)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💬 Ask Follow-up Questions</div>', unsafe_allow_html=True)
    with st.form("ask_form", clear_on_submit=True):
        ask_question = st.text_input("Ask follow-up questions about the analyzed protocol")
        ask_button = st.form_submit_button("Ask")

    if ask_button:
        if not ask_question.strip():
            st.warning("Please type a question first.")
        else:
            with st.spinner("Generating answer..."):
                try:
                    answer = ask_protocol_question(
                        protocol_text=protocol_text,
                        analysis_result=analysis_result,
                        question=ask_question,
                        chat_history=st.session_state.chat_history,
                    )
                    st.session_state.chat_history.append(
                        {"question": ask_question.strip(), "answer": answer}
                    )
                    st.session_state.last_question = ask_question.strip()
                    st.session_state.last_answer = answer
                    st.rerun()
                except Exception as e:
                    st.error(f"Q&A failed: {e}")

    if st.session_state.last_answer:
        st.markdown("**💬 Answer**")
        st.write(st.session_state.last_answer)

    if st.session_state.chat_history:
        st.markdown("**🗂️ Chat History**")
        for item in reversed(st.session_state.chat_history):
            st.markdown(f"🧑‍💼 **You:** {item['question']}")
            st.markdown(f"🤖 **Assistant:** {item['answer']}")
            st.markdown("---")
    st.markdown("</div>", unsafe_allow_html=True)

    pdf_question = st.session_state.last_question or initial_question.strip() or "No initial protocol question provided."
    pdf_answer = st.session_state.last_answer or "No follow-up answer generated."

    try:
        pdf_data = build_pdf_report(
            file_name=file_name,
            analysis_result=analysis_result,
            question=pdf_question,
            answer=pdf_answer,
        )
        st.download_button(
            label="📥 Download CRA Report",
            data=pdf_data,
            file_name="cra_protocol_review_report.pdf",
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
else:
    st.info("Upload a protocol PDF and click Analyze to generate your CRA summary.")

