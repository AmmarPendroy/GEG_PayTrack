import streamlit as st

# ─── 1) Page Config (must be first) ──────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) Imports ──────────────────────────────────────────────────────────────────
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar
from components.header import render_header

# ─── 3) Initialize Session State ─────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ─── 4) Auth Guard ───────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── 5) Main UI Layout ───────────────────────────────────────────────────────────
# Render layout blocks
render_header()
render_sidebar(st.session_state.user)

# Load selected page (this is a placeholder)
page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
