import streamlit as st

# ─── 1) Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) Imports ──────────────────────────────────────────────────────────────────
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar
from components.header import render_header

# ─── 3) Init State ───────────────────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ─── 4) Auth ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    login_form()
    st.stop()

# ─── 5) UI Layout ────────────────────────────────────────────────────────────────
render_header()
render_sidebar(st.session_state.user)

# ─── 6) Page Loader ──────────────────────────────────────────────────────────────
def page_loader(page: str):
    try:
        if page == "Dashboard":
            from pages.02_dashboard import render
        elif page == "Projects":
            from pages.03_projects import render
        elif page == "Contractors":
            from pages.04_contractors import render
        elif page == "Contracts":
            from pages.05_contracts import render
        elif page == "Payment Requests":
            from pages.06_payment_requests import render
        elif page == "User Management":
            from pages.07_user_management import render
        elif page == "Activity Log":
            from pages.08_activity_log import render
        elif page == "Settings":
            from pages.09_settings import render
        else:
            st.error("🚧 Page not found.")
            return
        render()  # Call the page render function
    except Exception as e:
        st.error(f"❌ Failed to load page: {e}")

# ─── 7) Load the Selected Page ───────────────────────────────────────────────────
page_loader(st.session_state.current_page)
