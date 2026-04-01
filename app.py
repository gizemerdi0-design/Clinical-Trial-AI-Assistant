import streamlit as st
import pdfplumber
from openai import OpenAI
import json
import os

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.markdown("# 🧠 Clinical Trial AI Assistant Pro")
st.caption("AI-powered protocol analysis for Clinical Research Associates")

st.markdown("""
<style>
.card {
    padding: 15px;
    border-radius: 12px;
    background-color: #f8f9fa;
    margin-bottom: 15px;
    border: 1px solid #e6e6e6;
}
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload Clinical Trial PDF", type="pdf")
question = st.text_input("💬 Ask a clinical question about the protocol")

if st.button("Clear Chat"):
    st.session_state.chat_history = []

if st.button("Analyze"):
    if not uploaded_file:
        st.warning("Please upload a PDF")
    elif not question:
        st.warning("Please enter a question")
    else:
        text = ""

        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            st.error("PDF could not be read or may be scanned.")
        else:
            with st.spinner("Analyzing protocol with AI..."):

                summary_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": f"""
You are an AI assistant helping a Clinical Research Associate review a clinical trial protocol.

Analyze the following protocol and return ONLY valid JSON.
Do not add explanations, markdown, or extra text.

Use this exact schema:

{{
  "protocol_overview": ["..."],
  "key_risks": ["..."],
  "inclusion_criteria": ["..."],
  "exclusion_criteria": ["..."],
  "critical_insights": ["..."],
  "cra_monitoring_priorities": ["..."],
  "operational_challenges": ["..."],
  "overall_risk_score": "Low/Medium/High",
  "risk_rationale": ["..."]
}}

Rules:
- Each field must be a list of short bullet-style strings except overall_risk_score
- overall_risk_score must be exactly one of: Low, Medium, High
- risk_rationale must be a short list explaining the score
- Be concise, practical, and clinically relevant
- If a section is not clear, return an empty list

Text:
{text}
"""
                        }
                    ]
                )

                summary_raw = summary_response.choices[0].message.content

                try:
                    summary_data = json.loads(summary_raw)
                except Exception:
                    st.error("JSON parse failed. Raw model output:")
                    st.code(summary_raw)
                    st.stop()

                overview = summary_data.get("protocol_overview", [])
                risks = summary_data.get("key_risks", [])
                inclusion = summary_data.get("inclusion_criteria", [])
                exclusion = summary_data.get("exclusion_criteria", [])
                insights = summary_data.get("critical_insights", [])
                cra_priorities = summary_data.get("cra_monitoring_priorities", [])
                operational_challenges = summary_data.get("operational_challenges", [])
                overall_risk_score = summary_data.get("overall_risk_score", "Unknown")
                risk_rationale = summary_data.get("risk_rationale", [])

                st.subheader("📊 AI Clinical Summary")

                if overall_risk_score == "High":
                    st.markdown("## 🔴 High Risk Protocol")
                elif overall_risk_score == "Medium":
                    st.markdown("## 🟡 Medium Risk Protocol")
                elif overall_risk_score == "Low":
                    st.markdown("## 🟢 Low Risk Protocol")
                else:
                    st.markdown("## ⚪ Risk Unknown")

                st.markdown("### 📝 Risk Rationale")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if risk_rationale:
                    for rr in risk_rationale:
                        st.write(f"- {rr}")
                else:
                    st.write("No rationale extracted.")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("## 📊 Protocol Summary Dashboard")

                st.markdown("#### 🧾 Protocol Overview")
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if overview:
                    for item in overview:
                        st.write(f"- {item}")
                else:
                    st.write("No overview extracted.")
                st.markdown("</div>", unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### ⚠️ Risks")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if risks:
                        for r in risks:
                            st.write(f"- {r}")
                    else:
                        st.write("No risks extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("#### 👥 Inclusion")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if inclusion:
                        for i in inclusion:
                            st.write(f"- {i}")
                    else:
                        st.write("No inclusion criteria extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("#### 🎯 CRA Monitoring Priorities")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if cra_priorities:
                        for c in cra_priorities:
                            st.write(f"- {c}")
                    else:
                        st.write("No CRA priorities extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                with col2:
                    st.markdown("#### 🚫 Exclusion")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if exclusion:
                        for e in exclusion:
                            st.write(f"- {e}")
                    else:
                        st.write("No exclusion criteria extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("#### 🔬 Insights")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if insights:
                        for ins in insights:
                            st.write(f"- {ins}")
                    else:
                        st.write("No critical insights extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("#### 🛠️ Operational Challenges")
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if operational_challenges:
                        for op in operational_challenges:
                            st.write(f"- {op}")
                    else:
                        st.write("No operational challenges extracted.")
                    st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")

                conversation_messages = [
                    {
                        "role": "system",
                        "content": """
You are an AI assistant helping a Clinical Research Associate understand a clinical trial protocol.
Answer using only the provided protocol text.
Be concise, clinically relevant, practical, and consistent with prior conversation context.
"""
                    },
                    {
                        "role": "user",
                        "content": f"Protocol text:\n{text}"
                    }
                ]

                for role, message in st.session_state.chat_history:
                    if role == "You":
                        conversation_messages.append({"role": "user", "content": message})
                    else:
                        conversation_messages.append({"role": "assistant", "content": message})

                conversation_messages.append({"role": "user", "content": question})

                qa_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=conversation_messages
                )

                answer = qa_response.choices[0].message.content

                st.session_state.chat_history.append(("You", question))
                st.session_state.chat_history.append(("Assistant", answer))

                st.subheader("💬 Answer")
                st.write(answer)

                st.subheader("🗂️ Chat History")
                for role, message in st.session_state.chat_history:
                    if role == "You":
                        st.markdown(f"🧑‍💼 **You:** {message}")
                    else:
                        st.markdown(f"🤖 **Assistant:** {message}")
