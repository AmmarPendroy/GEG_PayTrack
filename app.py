import streamlit as st
from utils.core import get_current_user, logout
from components.layout_components import sidebar_navigation


st.set_page_config(page_title="GEG PayTrack", layout="wide", page_icon="🏗️")

if "user" not in st.session_state:
    st.session_state.user = None

user = get_current_user()

if not user:
    st.switch_page("pages/01_login.py")
else:
    sidebar_navigation(user)
    st.switch_page("pages/02_dashboard.py")
