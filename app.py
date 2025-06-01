import streamlit as st
import uuid
from datetime import datetime
from logic.login_handler import login_form
from logic.contractors import render_contractor_module

# === Page Configuration ===
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# === Utilities ===
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

# === Session Initialization ===
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

    # === Page Routing ===
    if page == "Dashboard":
        st.title("📊 Dashboard")
        st.info("This page is under construction.")
    elif page == "Projects":
        st.title("🏗️ Projects")
        st.info("This page is under construction.")
    elif page == "Contractors":
        render_contractor_module(user)
    elif page == "Contracts":
        st.title("📄 Contracts")
        st.info("This page is under construction.")
    elif page == "Payment Requests":
        st.title("💰 Payment Requests")
        st.info("This page is under construction.")
    elif page == "User Management":
        st.title("👥 User Management")
        st.info("This page is under construction.")
    elif page == "Activity Log":
        st.title("📜 Activity Log")
        st.info("This page is under construction.")
    elif page == "Settings":
        st.title("⚙️ Settings")
        st.info("This page is under construction.")
