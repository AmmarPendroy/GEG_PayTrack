import streamlit as st
from logic.login_handler import login_form

st.set_page_config(
    page_title="🏗️ GEG PayTrack",
    layout="wide",
    page_icon="🏗️",
)

# Auth only
if not st.session_state.get("user"):
    login_form()
    st.stop()

# That’s it — routing happens through Streamlit sidebar
st.success("✅ Logged in! Use the sidebar to navigate.")

st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.rerun()
