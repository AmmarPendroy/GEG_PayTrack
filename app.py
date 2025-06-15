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
    # Show login form
    login_form()

    # Show animated welcome container (below the login form)
    st.markdown("""
        <style>
        .login-box {
            animation: fadeIn 1s ease-in-out;
            margin-top: 30px;
            text-align: center;
            background-color: #f0f2f6;
            padding: 1.5rem;
            border-radius: 1.5rem;
            border: 1px solid #ccc;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        <div class="login-box">
            <h3>👋 Welcome to <strong>GEG PayTrack</strong></h3>
            <p>Please log in to continue.</p>
        </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── Logged In View ────────────────────────────────────────
user = st.session_state["user"]
st.success(f"✅ Logged in as **{user['username']}** ({user['role']})")

# ─── Logout Button with Animation ──────────────────────────
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

# ─── Landing Message ───────────────────────────────────────
st.markdown("👉 Use the left sidebar to navigate between modules.")
