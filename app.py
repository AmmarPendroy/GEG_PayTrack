import streamlit as st
from components.layout_components import show_sidebar
from utils.auth import get_current_user

# ---------------------------------------
# Main App Entry Point
# ---------------------------------------
def main():
    st.set_page_config(page_title="GEG PayTrack", page_icon="🏗️", layout="wide")

    # Check if user is already authenticated
    user = get_current_user()

    # Redirect unauthenticated users to the login page
    if not user:
        st.switch_page("pages/01_login.py")
    else:
        st.session_state.user = user

        # Show navigation
        show_sidebar(user)

        # Show user info
        st.sidebar.success(f"Logged in as: {user['username']} ({user['role']})")

        # Logout button
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        # Page rendering is handled by Streamlit's multipage feature via /pages folder

if __name__ == "__main__":
    main()
