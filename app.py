import streamlit as st
from utils.data_handler import authenticate_user
from components.layout_components import show_sidebar

# ---------------------------------------
# Main App Entry Point
# ---------------------------------------
def main():
    st.set_page_config(page_title="GEG PayTrack", page_icon="🏗️", layout="wide")

    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        from pages import 01_login as login_page
        login_page.login_page()
    else:
        user = st.session_state.user
        show_sidebar(user)
        st.sidebar.success(f"Logged in as: {user['username']} ({user['role']})")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()

        # Actual page rendering handled by pages/* structure

if __name__ == "__main__":
    main()
