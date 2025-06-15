# logic/login_handler.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager

# ─── 1) COOKIE SETUP ────────────────────────────────────────────────────────────────
# This manager will read/write an encrypted cookie under the hood.
cookies = EncryptedCookieManager(
    prefix="paytrack/",                     # avoid collisions
    password=st.secrets["cookie_password"], # your 32+ char secret
)
# must block until the component loads existing cookies
if not cookies.ready():
    st.stop()

# If we already have a saved session in the cookie, restore it now
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── 2) PASSWORD HASHING ────────────────────────────────────────────────────────────
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

# ─── 3) AUTHENTICATION ─────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    dsn = st.secrets["db_url"]  # your single-line URI

    try:
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, username, role, hashed_password "
            "FROM users WHERE username=%s AND is_active=TRUE",
            (username,)
        )
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

    if not user or hash_password(password) != user["hashed_password"]:
        return False

    # load assigned projects
    conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
    cur  = conn.cursor()
    cur.execute(
        "SELECT project_id FROM user_projects WHERE user_id=%s",
        (user["id"],)
    )
    assigned = [r["project_id"] for r in cur.fetchall()]
    conn.close()

    # build the session dict
    session_user = {
        "id":                user["id"],
        "username":          user["username"],
        "role":              user["role"],
        "assigned_projects": assigned,
    }
    st.session_state.user = session_user

    # ─── 4) PERSIST TO COOKIE ────────────────────────────────────────────────────────
    # This writes a browser cookie that lives until the cookie expires (defaults to persistent).
    cookies["user_session"] = session_user
    cookies.save()

    return True

# ─── 5) LOGOUT ───────────────────────────────────────────────────────────────────────
def logout():
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── 6) LOGIN FORM ───────────────────────────────────────────────────────────────────
def login_form():
    # if we already have `user` in session_state, show a logout button
    if st.session_state.get("user"):
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    # otherwise, render the login form
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
