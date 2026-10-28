"""Streamlit chat UI.  Run: streamlit run src/ui/app.py"""

import requests
import streamlit as st

from src.config import get_settings

settings = get_settings()
REQUEST_TIMEOUT_S = 120
DISCLAIMER = "*⚠️ AI generated summary. Do not use for diagnostic purposes.*"

st.set_page_config(page_title="Zero-Trust Clinical EHR", layout="centered")
st.title("🏥 Enterprise EHR Chat")
st.caption("Protected by Presidio Zero-Trust & NeMo Guardrails")
st.warning("Demo only: not a medical device. Do not use for clinical decisions.")


@st.cache_data(ttl=300)  # cache the patient list for 5 minutes to reduce database load
def fetch_patient_list() -> list[str]:
    try:
        response = requests.get(settings.api_patients_url, timeout=30)
        response.raise_for_status()
        return response.json().get("patients") or ["No patients found"]
    except requests.exceptions.RequestException:
        return ["Database Connection Error"]


patient_id = st.sidebar.selectbox("Select Patient File (type to search)", fetch_patient_list())
st.sidebar.info(f"🔒 Database explicitly locked to Patient: {patient_id}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input(f"Ask about patient {patient_id}'s history..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    payload = {"patient_id": patient_id, "messages": st.session_state.messages}

    with st.spinner("Analyzing securely..."):
        try:
            response = requests.post(settings.api_chat_url, json=payload, timeout=REQUEST_TIMEOUT_S)
            response.raise_for_status()
            body = response.json()
            bot_reply = body.get("llm_response", "")
            for warning in body.get("warnings", []):
                bot_reply += f"\n\n⚠️ {warning}"
            bot_reply += f"\n\n{DISCLAIMER}"
        except requests.exceptions.RequestException as e:
            bot_reply = f"❌ API Error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.chat_message("assistant").write(bot_reply)
