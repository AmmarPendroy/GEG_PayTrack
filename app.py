import streamlit as st
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# === Streamlit Page Configuration ===
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# === Helpers ===
def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

# === Track current page across navigations ===
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# === Authentication (login_form handles both login & logout) ===
login_form()

# If you're not logged in, stop here (login_form will have shown the form)
user = st.session_state.get("user")
if not user:
    st.stop()

# === Main app ===
# Render your sidebar (this will set st.session_state.current_page)
render_sidebar(user)

# Then render content for the selected page
page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
