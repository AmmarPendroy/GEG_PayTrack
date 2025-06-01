import streamlit as st
import os, sys

# Ensure the root path is available for imports
sys.path.append(os.path.abspath("."))

from utils.core import get_current_user, logout
from components.layout_components import sidebar_navigation

# --- Page Configuration ---
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# --- Initialize Session State ---
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# --- Authenticated User Routing ---
user = get_current_user()

if not user:
    # Redirect to login page (Streamlit will auto-load from /pages)
    st.switch_page("pages/01_login.py")
else:
    # Sidebar Navigation
    sidebar_navigation(user)

    # Trigger proper page by role (simplified initial routing)
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

    # Logout Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        logout()
        st.experimental_rerun()
