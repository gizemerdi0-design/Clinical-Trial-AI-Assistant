import streamlit as st
import pdfplumber
from openai import OpenAI
import json
import os
from fpdf import FPDF

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


def clean_pdf_text(text: str) -> str:
    return str(text).replace("•", "-").replace("–", "-").replace("—", "-").encode("latin-1", "ignore").decode("latin-1")


def build_pdf_report(
    risk_score,
    key_risks,
    inclusion,
    exclusion,
    cra_priorities,
    operational_challenges,
    checklist,
    question,
    answer,
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Clinical Trial AI Assistant Pro", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, "CRA Protocol Review Report", ln=True)
    pdf.ln(5)

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

    add_section("Overall Risk Score", risk_score)
    add_section("Key Risks", key_risks)
    add_section("Inclusion Criteria", inclusion)
    add_section("Exclusion Criteria", exclusion)
    add_section("CRA Monitoring Priorities", cra_priorities)
    add_section("Operational Challenges", operational_challenges)
    add_section("Monitoring Visit Checklist", checklist)

    safe_q = clean_pdf_text(question)
    safe_a = clean_pdf_text(answer)
    add_section("Q&A", [f"Question: {safe_q}", f"Answer: {safe_a}"])

    return pdf.output(dest="S").encode("latin-1")


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("🧪 Clinical Trial AI Assistant Pro")
st.caption("AI-powered protocol analysis for Clinical Research Associates")

uploaded_file = st.file_uploader("Upload Clinical Trial Protocol (PDF)", type="pdf")
question = st.text_input("Ask a clinical question about the protocol")

if st.button("Clear Chat"):
    st.session_state.chat_history = []

if uploaded_file and st.button("Analyze"):
    text = ""

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    if not text.strip():
        st.error("Could not extract text from this PDF.")
    else:
        with st.spinner("Analyzing protocol..."):
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

            summary_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": summary_prompt}],
            )

            summary_raw = summary_response.choices[0].message.content

            try:
                summary_data = json.loads(summary_raw)
            except Exception:
                st.error("Model did not return valid JSON.")
                st.code(summary_raw)
                st.stop()

            risk_score = summary_data.get("risk_score", "Unknown")
            key_risks = summary_data.get("key_risks", [])
            inclusion = summary_data.get("inclusion", [])
            exclusion = summary_data.get("exclusion", [])
            cra_priorities = summary_data.get("cra_priorities", [])
            operational_challenges = summary_data.get("operational_challenges", [])

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

            st.subheader("🧪 Monitoring Visit Checklist")
            st.write(checklist)

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
                    messages=[{"role": "user", "content": qa_prompt}],
                )

                answer = qa_response.choices[0].message.content

                st.session_state.chat_history.append(("You", question))
                st.session_state.chat_history.append(("Assistant", answer))

                st.subheader("💬 Answer")
                st.write(answer)

            pdf_data = build_pdf_report(
                risk_score=risk_score,
                key_risks=key_risks,
                inclusion=inclusion,
                exclusion=exclusion,
                cra_priorities=cra_priorities,
                operational_challenges=operational_challenges,
                checklist=checklist,
                question=question,
                answer=answer,
            )

            st.download_button(
                label="📥 Download CRA Report (PDF)",
                data=pdf_data,
                file_name="cra_protocol_report.pdf",
                mime="application/pdf",
            )

            if st.session_state.chat_history:
                st.subheader("🗂️ Chat History")
                for role, message in st.session_state.chat_history:
                    if role == "You":
                        st.markdown(f"**You:** {message}")
                    else:
                        st.markdown(f"**Assistant:** {message}")
