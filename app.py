import streamlit as st

from router import route_user

# Streamlit page configuration
st.set_page_config(
    page_title="GEG PayTrack",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for user if not present
if "user" not in st.session_state:
    login_page()
else:
    route_user()
