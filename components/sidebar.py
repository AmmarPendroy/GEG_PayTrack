import streamlit as st

def render_sidebar(user: dict):
    role = user.get("role", "")
    current = st.session_state.get("current_page", "Dashboard")

    st.sidebar.markdown("### 🏗️ GEG PayTrack")
    st.sidebar.markdown(f"**👤 {user.get('username', 'Guest')}**")
    st.sidebar.markdown(f"`Role: {role}`")

    # ─── NAVIGATION ───────────────────────────────────────────
    def nav_button(label: str, page: str, icon: str):
        if st.sidebar.button(f"{icon} {label}", key=page):
            st.session_state.current_page = page
            st.rerun()

    st.sidebar.markdown("---")

    with st.sidebar.expander("📊 Core Modules", expanded=True):
        nav_button("Dashboard", "Dashboard", "🏠")
        nav_button("Projects", "Projects", "🏗️")
        nav_button("Contractors", "Contractors", "👷")
        nav_button("Contracts", "Contracts", "📄")
        nav_button("Payment Requests", "Payment Requests", "💰")

    with st.sidebar.expander("🛠️ Admin Tools", expanded=(role in ["Superadmin", "HQ Admin"])):
        if role in ["Superadmin", "HQ Admin"]:
            nav_button("User Management", "User Management", "🔐")
            nav_button("Activity Log", "Activity Log", "🕓")

    with st.sidebar.expander("⚙️ Settings", expanded=False):
        nav_button("Settings", "Settings", "⚙️")

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.rerun()
