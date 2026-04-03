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

            Analyze this clinical trial protocol and return ONLY valid JSON.

            Use this schema:

            {{
              "risk_score": "Low/Medium/High",
              "study_complexity": "Low/Medium/High",
              "retention_risk": "Low/Medium/High",
              "complexity_rationale": ["..."],
              "retention_rationale": ["..."],
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
            - All list items should be concise and CRA-relevant

            Protocol:
            {text}
            """
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
            study_complexity = summary_data.get("study_complexity", "Unknown")
            retention_risk = summary_data.get("retention_risk", "Unknown")

            complexity_rationale = summary_data.get("complexity_rationale", [])
            retention_rationale = summary_data.get("retention_rationale", [])

            key_risks = summary_data.get("key_risks", [])
            inclusion = summary_data.get("inclusion", [])
            exclusion = summary_data.get("exclusion", [])
            cra_priorities = summary_data.get("cra_priorities", [])
            operational_challenges = summary_data.get("operational_challenges", [])

            # Score colors
            def score_color(score):
                return {
                    "Low": "green",
                    "Medium": "orange",
                    "High": "red"
                }.get(score, "gray")

            st.markdown("## 📊 Protocol Risk Dashboard")

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.markdown(f"""
                <div style="
                    padding:15px;
                    border-radius:12px;
                    background-color:#f5f5f5;
                    text-align:center;
                 ">
                    <h4 style="margin:0;">Overall Risk</h4>
                    <h2 style="color:{score_color(risk_score)};">{risk_score}</h2>
                </div>
                """,
                unsafe_allow_html=True)

           with col_b:
               st.markdown(f"""
               <div style="
                   padding:15px;
                   border-radius:12px;
                   background-color:#f5f5f5;
                   text-align:center;
                ">
                   <h4 style="margin:0;">Study Complexity</h4>
                   <h2 style="color:{score_color(study_complexity)};">{study_complexity}</h2>
               </div>
               """,
               unsafe_allow_html=True)

           with col_c:
               st.markdown(f"""
               <div style="
                   padding:15px;
                   border-radius:12px;
                   background-color:#f5f5f5;
                   text-align:center;
                ">
                   <h4 style="margin:0;">Retention Risk</h4>
                   <h2 style="color:{score_color(retention_risk)};">{retention_risk}</h2>
                </div>
                """, unsafe_allow_html=True)

            # 🎨 Risk color logic
            risk_color = {
                "Low": "green",
                "Medium": "orange",
                "High": "red"
            }.get(risk_score, "gray")

            st.markdown("## 📊 Overall Risk Assessment")

            st.markdown(f"""
            <div style="
            padding:20px;
            border-radius:12px;
            background-color:#f5f5f5;
            text-align:center;
            margin-bottom:20px;
            ">
            <h2 style="color:{risk_color}; margin:0;">
                {risk_score}
            </h2>
        </div>
        """, unsafe_allow_html=True)


            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### ⚠️ Key Risks")
                for r in key_risks:
                    st.markdown(f"• {r}")

                st.markdown("### 👥 Inclusion Criteria")
                for i in inclusion:
                    st.markdown(f"• {i}")

                st.markdown("### 🚫 Exclusion Criteria")
                for e in exclusion:
                    st.markdown(f"• {e}")

                st.markdown("### 🛠️ Operational Challenges")
                for c in operational_challenges:
                    st.markdown(f"• {c}")

            st.markdown("### 🎯 CRA Monitoring Priorities")
            for p in cra_priorities:
                st.markdown(f"• {p}")

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

            st.markdown("## 🧪 Monitoring Visit Checklist")
            st.markdown(checklist) 

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

                st.markdown("## 💬 Clinical Insight")

                st.markdown(f"""
                <div style="
                    padding:15px;
                    border-radius:10px;
                    background-color:#f0f8ff;
                 ">
                 {answer}
                 </div>
                 """, unsafe_allow_html=True)

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
