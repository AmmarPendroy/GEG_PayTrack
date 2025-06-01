import streamlit as st

# ---------------------------------------
# Sidebar Navigation
# ---------------------------------------
def show_sidebar(user):
    st.sidebar.title("📂 Navigation")

    pages = {
        "Dashboard": "02_dashboard",
        "Projects": "03_projects",
        "Contractors": "04_contractors",
        "Contracts": "05_contracts",
        "Payment Requests": "06_payment_requests",
        "User Management": "07_user_management",
        "Activity Log": "08_activity_log",
        "Settings": "09_settings"
    }

    for label, path in pages.items():
        if st.sidebar.button(f"➡️ {label}"):
            st.switch_page(f"pages/{path}.py")

# ---------------------------------------
# Section Header
# ---------------------------------------
def section_header(title: str, icon: str = \"📘\"):
    st.markdown(f\"## {icon} {title}\")
