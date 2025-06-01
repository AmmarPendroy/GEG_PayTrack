import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user by checking hashed password from the database."""
    db_url = st.secrets["db_url"]

    try:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and hash_password(password) == user["hashed_password"]:
            st.session_state.user = {
                "username": user["username"],
                "role": user["role"],
                "assigned_projects": user.get("assigned_projects", [])
            }
            return True
    except Exception as e:
        st.error(f"Database error: {e}")
    return False

def login_form():
    """Render the login form."""
    st.subheader("🔐 Login to GEG PayTrack")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if authenticate_user(username, password):
                st.success("✅ Login successful")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
