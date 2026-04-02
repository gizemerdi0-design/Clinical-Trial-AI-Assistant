import streamlit as st
import pdfplumber
from openai import OpenAI
import os
from fpdf import FPDF

# 🔐 API KEY
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# 🧠 PDF REPORT FUNCTION
def build_pdf_report(
    overall_risk_score,
    risk_rationale,
    overview,
    risks,
    inclusion,
    exclusion,
    insights,
    cra_priorities,
    operational_challenges,
    question,
    answer,
    checklist
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def clean(text):
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Clinical Trial AI Assistant Pro", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "CRA Protocol Review Report", ln=True)
    pdf.ln(5)

    def add_section(title, content):
        pdf.set_font("Arial", "B", 13)
        pdf.multi_cell(0, 8, clean(title))
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, clean(content))
        pdf.ln(3)

    add_section("Overall Risk Score", overall_risk_score)
    add_section("Risk Rationale", risk_rationale)
    add_section("Protocol Overview", overview)
    add_section("Key Risks", risks)
    add_section("Inclusion Criteria", inclusion)
    add_section("Exclusion Criteria", exclusion)
    add_section("Critical Insights", insights)
    add_section("CRA Monitoring Priorities", cra_priorities)
    add_section("Operational Challenges", operational_challenges)

    add_section("Q&A", f"Question: {question}\nAnswer: {answer}")
    add_section("Monitoring Visit Checklist", checklist)

    return pdf.output(dest="S").encode("latin-1")

# 🖥️ UI
st.title("🧪 Clinical Trial AI Assistant Pro")
st.caption("AI-powered protocol analysis for Clinical Research Associates")

uploaded_file = st.file_uploader("Upload Clinical Trial Protocol (PDF)", type="pdf")
question = st.text_input("Ask a clinical question about the protocol")

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""

    # 🧠 SUMMARY PROMPT
    summary_prompt = f"""
    You are an AI assistant helping a Clinical Research Associate.

    Analyze the clinical trial protocol and return ONLY valid JSON.

    Use this schema:

    {{
      "risk_score": "Low/Medium/High",
      "key_risks": ["..."],
      "inclusion": ["..."],
      "exclusion": ["..."],
      "cra_priorities": ["..."],
      "operational_challenges": ["..."]
     }}

     Rules:
     - No explanation
     - No markdown
     - Only JSON
     - Keep items short and practical

    Protocol:
    {text}
    """
    Analyze this clinical trial protocol and provide:

    1. Overall Risk Score (Low/Medium/High)
    2. Risk Rationale
    3. Protocol Overview
    4. Key Risks
    5. Inclusion Criteria
    6. Exclusion Criteria
    7. Critical Insights
    8. CRA Monitoring Priorities
    9. Operational Challenges

    Protocol:
    {text}
    """

    summary_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": summary_prompt}]
    )

    summary = summary_response.choices[0].message.content
    import json

    summary_data = json.loads(summary_response.choices[0].message.content)

    risk_score = summary_data.get("risk_score", "Unknown")
    key_risks = summary_data.get("key_risks", [])
    inclusion = summary_data.get("inclusion", [])
    exclusion = summary_data.get("exclusion", [])
    cra_priorities = summary_data.get("cra_priorities", [])
    operational_challenges = summary_data.get("operational_challenges", []

    st.subheader("📊 Protocol Analysis")
    st.subheader("📊 Risk Level")
    st.write(risk_score)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("⚠️ Key Risks")
        for r in key_risks:
            st.write(f"- {r}")

        st.subheader("👥 Inclusion")
        for i in inclusion:
            st.write(f"- {i}")

    with col2:
        st.subheader("🚫 Exclusion")
        for e in exclusion:
            st.write(f"- {e}")

    st.subheader("🛠️ Challenges")
    for c in operational_challenges:
        st.write(f"- {c}")

    st.subheader("🎯 CRA Priorities")
    for p in cra_priorities:
        st.write(f"- {p}")

    # 🧪 CHECKLIST PROMPT
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
        messages=[{"role": "user", "content": checklist_prompt}]
    )

    checklist = checklist_response.choices[0].message.content

    st.subheader("🧪 Monitoring Visit Checklist")
    st.write(checklist)

    # 💬 Q&A
    answer = ""
    if question:
        qa_prompt = f"""
        Based on this protocol, answer the question:

        {question}

        Protocol:
        {text}
        """

        qa_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": qa_prompt}]
        )

        answer = qa_response.choices[0].message.content

        st.subheader("💬 Answer")
        st.write(answer)

    # 📥 PDF DOWNLOAD
    pdf_data = build_pdf_report(
        overall_risk_score=summary[:50],
        risk_rationale=summary,
        overview=summary,
        risks=summary,
        inclusion=summary,
        exclusion=summary,
        insights=summary,
        cra_priorities=summary,
        operational_challenges=summary,
        question=question,
        answer=answer,
        checklist=checklist
    )

    st.download_button(
        label="📥 Download CRA Report (PDF)",
        data=pdf_data,
        file_name="cra_protocol_report.pdf",
        mime="application/pdf"
    )
