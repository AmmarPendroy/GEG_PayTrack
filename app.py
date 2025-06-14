import streamlit as st

# ─── STREAMLIT CONFIG (MUST BE FIRST) ────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── STANDARD IMPORTS ─────────────────────────────────────────────────────────────
import uuid
from datetime import datetime

# Pull in your login handler (with cookies) *after* page_config
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# ─── HELPERS ─────────────────────────────────────────────────────────────────────
def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

# ─── NAVIGATION STATE ────────────────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ─── AUTHENTICATION ──────────────────────────────────────────────────────────────
# This call hydrates from cookie or shows the login form and stops.
login_form()
user = st.session_state.get("user")
if not user:
    st.stop()

# ─── MAIN APP LAYOUT ──────────────────────────────────────────────────────────────
# Sidebar will update `st.session_state.current_page`
render_sidebar(user)

page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
