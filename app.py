import streamlit as st
from logic.login_handler import login_form

# ─── 1) Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) Login Gate ──────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── 3) Logout Button ───────────────────────────────────────────────────────────
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state.pop("user", None)
    st.rerun()

# ─── 4) Info Placeholder ────────────────────────────────────────────────────────
st.success("✅ Logged in! Use the sidebar to navigate.")
