import streamlit as st

# ─── 1) Page Config MUST BE FIRST ───────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) Imports ─────────────────────────────────────────────────────────────────
from logic.login_handler import login_form

# ─── 3) Login Gate ──────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── 4) Logout Button ───────────────────────────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.pop("user", None)
    st.rerun()

# ─── 5) Info Placeholder ────────────────────────────────────────────────────────
st.success("✅ Logged in! Use the sidebar to navigate.")
