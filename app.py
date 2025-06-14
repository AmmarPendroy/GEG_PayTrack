import streamlit as st

# ─── STREAMLIT CONFIG (MUST BE FIRST) ────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── STANDARD IMPORTS ─────────────────────────────────────────────────────────────
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# ─── NAVIGATION STATE ────────────────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ─── AUTHENTICATION ──────────────────────────────────────────────────────────────
# This will hydrate `st.session_state.user` from the cookie (if any),
# or render the login form and then stop here.
login_form()
user = st.session_state.get("user")
if not user:
    st.stop()

# ─── MAIN APP LAYOUT ──────────────────────────────────────────────────────────────
# Only runs once we have a valid `user`.
render_sidebar(user)

page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
