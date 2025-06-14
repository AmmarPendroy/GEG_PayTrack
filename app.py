import streamlit as st
import uuid
from datetime import datetime
from logic.login_handler import login_form
from logic.login_handler import login_form
login_form()
from components.sidebar import render_sidebar

# === Streamlit Page Configuration ===
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# === Helpers ===
def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

# === Initialize Session State ===
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

user = st.session_state.user

# === Login or Main App View ===
if not user:
    login_form()
else:
    # Render sidebar and get selected page
    render_sidebar(user)
    page = st.session_state.current_page

    # === Page Content (Temporary Placeholder) ===
    st.title(f"📄 {page}")
    st.info("This page is under construction.")
