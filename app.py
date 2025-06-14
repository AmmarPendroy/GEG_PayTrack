import streamlit as st
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# === Streamlit Page Configuration ===
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️"
)

# (Optional) helper you can use elsewhere
def get_timestamp() -> str:
    return datetime.utcnow().isoformat()

# === Remember which page we’re on ===
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# === Authentication ===
# This will either hydrate `st.session_state.user` from your cookie,
# or render the login form and then STOP here.
login_form()
user = st.session_state.get("user")
if not user:
    st.stop()

# === Main App ===
# Now that we know we have a `user`, render the sidebar and page.
render_sidebar(user)

page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
