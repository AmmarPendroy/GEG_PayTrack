import streamlit as st
from components.layout_components import show_sidebar
from utils.auth import get_current_user

# ---------------------------------------
# Main App Entry Point
# ---------------------------------------
def main():
    st.set_page_config(page_title="GEG PayTrack", page_icon="🏗️", layout="wide")

    user = get_current_user()

    if not user:
        st.switch_page("pages/01_login.py")
    else:
        st.session_state.user = user
        show_sidebar(user)
        st.sidebar.success(f"Logged in as: {user['username']} ({user['role']})")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # Page rendering handled by Streamlit multi-page routing

if __name__ == "__main__":
    main()
