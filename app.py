import streamlit as st
import hashlib
import uuid
from datetime import datetime

# --- Streamlit Page Config ---
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# === 🔐 Auth Functions (was in core.py) ===

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

# === 🧠 Temporary Sidebar Navigation (Replace later with layout_components.py) ===
def sidebar_navigation(user):
    st.sidebar.title("🏗️ GEG PayTrack")
    st.sidebar.write(f"👤 **{user.get('username')}**")
    options = ["Dashboard", "Projects", "Contractors", "Contracts", "Payment Requests", "User Management", "Activity Log", "Settings"]
    choice = st.sidebar.radio("📂 Navigate to:", options)
    st.session_state.current_page = choice

# === Initialize Session ===
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# === Routing Logic ===
user = get_current_user()

if not user:
    st.switch_page("pages/01_login.py")
else:
    sidebar_navigation(user)

    if st.session_state.current_page == "Dashboard":
        st.switch_page("pages/02_dashboard.py")
    elif st.session_state.current_page == "Projects":
        st.switch_page("pages/03_projects.py")
    elif st.session_state.current_page == "Contractors":
        st.switch_page("pages/04_contractors.py")
    elif st.session_state.current_page == "Contracts":
        st.switch_page("pages/05_contracts.py")
    elif st.session_state.current_page == "Payment Requests":
        st.switch_page("pages/06_payment_requests.py")
    elif st.session_state.current_page == "User Management":
        st.switch_page("pages/07_user_management.py")
    elif st.session_state.current_page == "Activity Log":
        st.switch_page("pages/08_activity_log.py")
    elif st.session_state.current_page == "Settings":
        st.switch_page("pages/09_settings.py")

    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        logout()
        st.experimental_rerun()
