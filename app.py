import streamlit as st

# ─── Page Config (MUST BE FIRST) ─────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── Imports AFTER config ────────────────────────────────────
from logic.login_handler import login_form

# ─── Login Guard ─────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── Logged In View ──────────────────────────────────────────
user = st.session_state["user"]
st.success(f"✅ Logged in as **{user['username']}** ({user['role']})")

# ─── Logout Button with Animation ────────────────────────────
if st.button("🚪 Logout"):
    st.markdown("""
        <style>
        .fade-out {
            animation: fadeOut 1s forwards;
        }
        @keyframes fadeOut {
            to { opacity: 0; transform: scale(0.95); }
        }
        </style>
        <div class="fade-out">
            <h3>👋 Logging you out...</h3>
        </div>
        <meta http-equiv="refresh" content="1">
    """, unsafe_allow_html=True)
    st.session_state.pop("user", None)
    st.stop()

# ─── Landing Message ─────────────────────────────────────────
st.markdown("👉 Use the left sidebar to navigate between modules.")
