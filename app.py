import streamlit as st
from logic.login_handler import login_form

# ─── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── Login Guard ───────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── Logged In View ────────────────────────────────────────
user = st.session_state["user"]
st.success(f"✅ Logged in as **{user['username']}** ({user['role']})")

# ─── Logout Button ─────────────────────────────────────────
if st.button("🚪 Logout"):
    st.session_state.pop("user", None)
    st.rerun()

# (optional) Add a custom landing screen or instructions
st.markdown("👉 Use the left sidebar to navigate between modules.")
