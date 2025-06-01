import streamlit as st
from logic.login_handler import login_form

# --- App Config ---
st.set_page_config(page_title="🏗️ GEG PayTrack", layout="wide", page_icon="🏗️")

# --- Session Initialization ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- Main ---
user = st.session_state.user

if not user:
    login_form()
else:
    st.success(f"✅ Logged in as **{user['username']}** ({user['role']})")
    st.info("📂 Use the sidebar to access different modules.")
