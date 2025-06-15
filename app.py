import streamlit as st

# ─── 1) page_config must be first ─────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) imports ───────────────────────────────────────────────────────────
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# ─── 3) auth ───────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── 4) logout with animation ──────────────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.success("👋 Logging out... See you soon!")
    st.markdown("<meta http-equiv='refresh' content='2'>", unsafe_allow_html=True)
    st.session_state.pop("user", None)
    st.stop()

# ─── 5) sidebar and routing ────────────────────────────────────────────────
render_sidebar(st.session_state.user)

# ─── 6) placeholder content ────────────────────────────────────────────────
page = st.session_state.get("current_page", "Dashboard")
st.title(f"📄 {page}")
st.info("This page is under construction.")
