import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager
import json


# ─── COOKIE MANAGER (persistent across sessions) ───────────────────────────────
cookies = EncryptedCookieManager(
    prefix="paytrack/",
    password=st.secrets["cookie_password"]
)
if not cookies.ready():
    st.stop()

# Restore session from cookie if available
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── PASSWORD HASH ─────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── AUTHENTICATION ────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    try:
        conn = psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, username, role, hashed_password FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

    if not user or hash_password(password) != user["hashed_password"]:
        return False

    # Load assigned projects
    conn = psycopg2.connect(st.secrets["db_url"], cursor_factory=RealDictCursor)
    cur  = conn.cursor()
    cur.execute("SELECT project_id FROM user_projects WHERE user_id = %s", (user["id"],))
    assigned = [r["project_id"] for r in cur.fetchall()]
    conn.close()

    session_user = {
        "id":                user["id"],
        "username":          user["username"],
        "role":              user["role"],
        "assigned_projects": assigned,
    }
    st.session_state.user = session_user

    # Save to cookie
    cookies["user_session"] = session_user
    cookies.save()

    return True

# ─── LOGOUT ────────────────────────────────────────────────────────────────────
def logout():
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────
def login_form():
    if st.session_state.get("user"):
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    st.subheader("🔐 Login to GEG PayTrack")
    with st.form("login_form"):
        uname  = st.text_input("Username")
        pwd    = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            if authenticate_user(uname, pwd):
                st.success("✅ Login successful")
                st.experimental_rerun()
            else:
                st.error("❌ Invalid username or password")
