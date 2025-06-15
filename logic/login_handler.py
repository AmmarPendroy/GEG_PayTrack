# logic/login_handler.py

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_controller import CookieController

# ─── COOKIE CONTROLLER SETUP ────────────────────────────────────────────────────
controller = CookieController()
# hydrate any existing cookies into controller._cookies
controller.get_all()

# If we have a saved session cookie, restore it to session_state
if "user" not in st.session_state:
    saved = controller.get("user_session")
    if saved is not None:
        st.session_state.user = saved

# ─── HELPERS ─────────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    """
    Check creds, load assigned projects, then persist a cookie that
    expires in 30 days so you stay logged in across browser restarts.
    """
    db_dsn = st.secrets["db_url"]

    try:
        # verify creds
        conn = psycopg2.connect(db_dsn, cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT id, username, role, hashed_password
            FROM users
            WHERE username = %s AND is_active = TRUE
            """,
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
    conn = psycopg2.connect(db_dsn, cursor_factory=RealDictCursor)
    cur  = conn.cursor()
    cur.execute(
        "SELECT project_id FROM user_projects WHERE user_id = %s",
        (user["id"],)
    )
    assigned = [r["project_id"] for r in cur.fetchall()]
    conn.close()

    # build our session dict
    session_user = {
        "id":                user["id"],
        "username":          user["username"],
        "role":              user["role"],
        "assigned_projects": assigned,
    }
    st.session_state.user = session_user

    # persist to cookie for 30 days (2592000 seconds)
    controller.set(
        "user_session",
        session_user,
        max_age=30 * 24 * 3600
    )
    controller.save()

    return True

# ─── LOGOUT ────────────────────────────────────────────────────────────────────────
def logout():
    st.session_state.pop("user", None)
    controller.delete("user_session")
    controller.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
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
