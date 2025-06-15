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
from streamlit_lottie import st_lottie
import json

def load_lottie(file_path):
    with open(file_path, "r") as f:
        return json.load(f)

if st.button("🚪 Logout"):
    lottie = load_lottie("animations/logout.json")  # Put a Lottie file in your repo
    st_lottie(lottie, speed=1, height=200)
    st.markdown("### Logging out...")
    st.session_state.pop("user", None)
    st.stop()



# (optional) Add a custom landing screen or instructions
st.markdown("👉 Use the left sidebar to navigate between modules.")
