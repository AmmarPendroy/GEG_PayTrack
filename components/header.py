import streamlit as st

def render_header():
    user = st.session_state.get("user", {})
    page = st.session_state.get("current_page", "Dashboard")

    # === Top Bar Layout ===
    col1, col2, col3 = st.columns([3, 6, 1])

    with col1:
        st.markdown(
            f"""
            <div style='padding: 0.4rem 0; font-size: 0.85rem; color: gray;'>
                📍 <strong>{page}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div style="text-align: right; padding: 0.2rem 1rem 0 0;">
                <span style="margin-right: 1rem; cursor: pointer;">🔔</span>
                <span style="margin-right: 1rem; cursor: pointer;" onclick="window.location.reload();">
                    {theme_toggle}
                </span>
            </div>
            """.replace("{theme_toggle}", "🌞" if st.session_state.get("theme", "light") == "light" else "🌙"),
            unsafe_allow_html=True
        )

    with col3:
        with st.expander(f"👤 {user.get('username', '')}", expanded=False):
            st.markdown(f"**Role**: `{user.get('role', 'Unknown')}`", unsafe_allow_html=True)
            if st.button("🔒 Logout"):
                st.session_state.pop("user", None)
                st.rerun()

    # === Theme toggle logic (optional) ===
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"
