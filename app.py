import streamlit as st
import hashlib
import uuid
from datetime import datetime
import os, sys

# Set Streamlit config
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# === 🔧 DEV MODE ===
DEV_MODE = True  # Set to False in production

# === 🔐 Auth Functions ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password: str, stored_hash: str) -> bool:
    return hash_password(input_password) == stored_hash

def get_current_user():
    return st.session_state.get("user", None)

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

# === 📋 Sidebar Navigation ===
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


# === Initialize Session State ===
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# === Auth Routing ===
user = get_current_user()

if not user:
    if DEV_MODE:
        # 🧪 Fake user for development
        st.session_state.user = {
            "username": "dev_admin",
            "role": "Superadmin"
        }
        st.rerun()
    else:
        st.switch_page("pages/01_login.py")
else:
    sidebar_navigation(user)

    page = st.session_state.current_page

    # 🔁 Page Routing Logic
    if page == "Dashboard":
        st.switch_page("pages/02_dashboard.py")
    elif page == "Projects":
        st.switch_page("pages/03_projects.py")
    elif page == "Contractors":
        st.switch_page("pages/04_contractors.py")
    elif page == "Contracts":
        st.switch_page("pages/05_contracts.py")
    elif page == "Payment Requests":
        st.switch_page("pages/06_payment_requests.py")
    elif page == "User Management":
        st.switch_page("pages/07_user_management.py")
    elif page == "Activity Log":
        st.switch_page("pages/08_activity_log.py")
    elif page == "Settings":
        st.switch_page("pages/09_settings.py")
