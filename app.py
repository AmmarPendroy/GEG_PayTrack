import streamlit as st

from components.header import render_header

# ...
render_header()


# ─── 1) page_config must be first ────────────────────────────────────────────────
st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# ─── 2) standard imports ─────────────────────────────────────────────────────────
from datetime import datetime
from logic.login_handler import login_form
from components.sidebar import render_sidebar

# ─── 3) navigation state ─────────────────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"

# ─── 4) auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("user"):
    # show login form and then stop everything else
    login_form()
    st.stop()

# ─── 5) main app ─────────────────────────────────────────────────────────────────
# at this point we have st.session_state.user populated
render_sidebar(st.session_state.user)

page = st.session_state.current_page
st.title(f"📄 {page}")
st.info("This page is under construction.")
