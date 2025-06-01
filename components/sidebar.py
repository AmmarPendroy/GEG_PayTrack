import streamlit as st

def render_sidebar(user: dict):
    st.sidebar.title("🏗️ GEG PayTrack")
    
    # User identity
    st.sidebar.markdown(
        f"👤 **{user.get('username', 'User')}**\n\n"
        f"🛡️ Role: `{user.get('role', 'N/A')}`"
    )

    st.sidebar.markdown("---")

    # Role-based dynamic menu (expandable in future)
    available_pages = [
        "Dashboard", 
        "Projects", 
        "Contractors", 
        "Contracts", 
        "Payment Requests", 
        "User Management", 
        "Activity Log", 
        "Settings"
    ]

    page_icons = {
        "Dashboard": "📊",
        "Projects": "🏗️",
        "Contractors": "👷",
        "Contracts": "📄",
        "Payment Requests": "💸",
        "User Management": "🔐",
        "Activity Log": "🕒",
        "Settings": "⚙️",
    }

    # Render page selector with icons
    choice = st.sidebar.radio("📂 Navigate", [
        f"{page_icons.get(p, '')} {p}" for p in available_pages
    ])

    # Clean page name from icon text
    st.session_state.current_page = choice.split(" ", 1)[-1]

    # Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
