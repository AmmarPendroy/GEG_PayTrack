import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager

# ─── COOKIE MANAGER (persistent, 30 days) ────────────────────────────────────────
cookies = EncryptedCookieManager(
    prefix="paytrack/",
    password=st.secrets["cookie_password"],
    max_age_days=30,                # keeps cookie alive for 30 days
)
if not cookies.ready():
    # wait for the cookie component to initialize
    st.stop()

# If there’s already a session saved, restore it
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── HELPER ───────────────────────────────────────────────────────────────────────
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── AUTHENTICATION ───────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    dsn = st.secrets["db_url"]  # your single‐line DSN
    try:
        conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, username, role, hashed_password "
            "FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        user = cur.fetchone()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

    if not user or hash_password(password) != user["hashed_password"]:
        return False

    # load assigned_projects
    conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
    cur  = conn.cursor()
    cur.execute("SELECT project_id FROM user_projects WHERE user_id = %s", (user["id"],))
    assigned = [r["project_id"] for r in cur.fetchall()]
    conn.close()

    # build session dict
    session_user = {
        "id":                user["id"],
        "username":          user["username"],
        "role":              user["role"],
        "assigned_projects": assigned,
    }
    st.session_state.user = session_user

    # persist into a 30-day encrypted cookie
    cookies["user_session"] = session_user
    cookies.save()

    return True

# ─── LOGOUT ───────────────────────────────────────────────────────────────────────
def logout():
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
def login_form():
    # If already logged in, show logout button
    if st.session_state.get("user"):
        st.write(f"👋 Logged in as **{st.session_state.user['username']}**")
        if st.button("🔒 Logout"):
            logout()
        return

    # Otherwise render login UI
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
