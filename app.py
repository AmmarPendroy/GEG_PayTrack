import streamlit as st
from pages import (
    _01_login,
    _02_dashboard,
    _03_projects,
    _04_contractors,
    _05_contracts,
    _06_payment_requests,
    _07_user_management,
    _08_activity_log,
    _09_settings,
)
from utils.core import get_current_user, logout
from components.layout_components import sidebar_navigation

st.set_page_config(page_title="GEG PayTrack", layout="wide", page_icon="🏗️")

# Authenticated session
if "user" not in st.session_state:
    st.session_state.user = None

user = get_current_user()

if not user:
    _01_login.show()
else:
    sidebar_navigation(user)

    page = st.session_state.get("current_page", "Dashboard")

    if page == "Dashboard":
        _02_dashboard.show(user)
    elif page == "Projects":
        _03_projects.show(user)
    elif page == "Contractors":
        _04_contractors.show(user)
    elif page == "Contracts":
        _05_contracts.show(user)
    elif page == "Payment Requests":
        _06_payment_requests.show(user)
    elif page == "User Management":
        _07_user_management.show(user)
    elif page == "Activity Log":
        _08_activity_log.show(user)
    elif page == "Settings":
        _09_settings.show(user)

    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        logout()
        st.experimental_rerun()
