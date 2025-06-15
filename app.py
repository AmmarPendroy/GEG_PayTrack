import streamlit as st
from logic.login_handler import login_form

# Page config
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# Auth check
if not st.session_state.get("user"):
    login_form()
    st.stop()

# App is protected by login, Streamlit handles the page routing from here
st.switch_page("pages/02_dashboard.py")  # optional, redirect to default after login
