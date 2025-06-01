import streamlit as st

# Define role-based page access
ROLE_PAGE_MAP = {
    "Superadmin": [
        "Dashboard", "Projects", "Contractors", "Contracts",
        "Payment Requests", "User Management", "Activity Log", "Settings"
    ],
    "HQ Admin": [
        "Dashboard", "Projects", "Contractors", "Contracts",
        "Payment Requests", "Activity Log"
    ],
    "HQ Accountant": [
        "Dashboard", "Projects", "Contracts",
        "Payment Requests", "Activity Log"
    ],
    "Site PM": [
        "Dashboard", "Projects", "Contractors", "Contracts",
        "Payment Requests"
    ],
    "Site Accountant": [
        "Dashboard", "Projects", "Contracts", "Payment Requests"
    ]
}

# Page icons
PAGE_ICONS = {
    "Dashboard": "📊",
    "Projects": "🏗️",
    "Contractors": "👷",
    "Contracts": "📄",
    "Payment Requests": "💸",
    "User Management": "🔐",
    "Activity Log": "🕒",
    "Settings": "⚙️",
}

def render_sidebar(user: dict):
    st.sidebar.title("🏗️ GEG PayTrack")
    
    # Display user info
    st.sidebar.markdown(
        f"👤 **{user.get('username', 'User')}**\n\n"
        f"🛡️ Role: `{user.get('role', 'N/A')}`"
    )

    st.sidebar.markdown("---")

    # Determine pages for role
    role = user.get("role", "Site Accountant")
    allowed_pages = ROLE_PAGE_MAP.get(role, [])

    # Sidebar navigation
    choice = st.sidebar.radio("📂 Navigate", [
        f"{PAGE_ICONS.get(p, '')} {p}" for p in allowed_pages
    ])

    st.session_state.current_page = choice.split(" ", 1)[-1]

    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔓 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
