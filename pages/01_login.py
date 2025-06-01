import streamlit as st
from utils.data_handler import authenticate_user

# ---------------------------------------
# Login Page
# ---------------------------------------
def login_page():
    st.title("🔐 GEG PayTrack Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Welcome, {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")
