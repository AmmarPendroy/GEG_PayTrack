import streamlit as st

# ---------------------------------------
# Sidebar with role-based navigation
# ---------------------------------------
def show_sidebar(user):
    role = user.get("role")
    st.sidebar.title("🧭 Navigation")

    # Public to all authenticated users
    st.sidebar.page_link("pages/02_dashboard.py", label="📊 Dashboard")

    if role in ["Superadmin", "HQ Admin", "Site PM"]:
        st.sidebar.page_link("pages/03_projects.py", label="🏗️ Projects")
        st.sidebar.page_link("pages/04_contractors.py", label="👷 Contractors")
        st.sidebar.page_link("pages/05_contracts.py", label="📄 Contracts")

    if role in ["Site PM", "Site Accountant", "HQ Accountant"]:
        st.sidebar.page_link("pages/06_payment_requests.py", label="💸 Payment Requests")

    if role in ["Superadmin", "HQ Admin"]:
        st.sidebar.page_link("pages/07_user_management.py", label="👥 User Management")
        st.sidebar.page_link("pages/08_activity_log.py", label="📝 Activity Log")

    st.sidebar.page_link("pages/09_settings.py", label="⚙️ Settings")
