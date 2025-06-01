import streamlit as st
import uuid
from datetime import datetime
from logic.login_handler import login_form

# === Page Configuration ===
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# === Utils (inline for now) ===
def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# === Sidebar Navigation ===
def sidebar_navigation(user):
    st.sidebar.title("🏗️ GEG PayTrack")
    st.sidebar.write(f"👤 **{user.get('username')}** ({user.get('role')})")

    pages = [
        "Dashboard", "Projects", "Contractors", "Contracts",
        "Payment Requests", "User Management", "Activity Log", "Settings"
    ]
    choice = st.sidebar.radio("📂 Navigate to:", pages)
    st.session_state.current_page = choice

    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        logout()
        st.rerun()

# === Initialize Session ===
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

user = st.session_state.user

# === Auth Gate ===
if not user:
    login_form()
else:
    sidebar_navigation(user)
    page = st.session_state.current_page

    st.title(f"📄 {page}")
    st.info("This page is under construction.")
