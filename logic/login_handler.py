import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import hashlib
from streamlit_cookies_manager import EncryptedCookieManager

# ─── COOKIE SETUP (PERSISTENT) ────────────────────────────────────────────────────
# max_age_days=30 makes this cookie live for 30 days
cookies = EncryptedCookieManager(
    prefix="paytrack/",
    password=st.secrets["cookie_password"],
    max_age_days=30
)
# must wait until the cookie manager hydrates
if not cookies.ready():
    st.stop()

# if we already have a saved session, restore it
saved = cookies.get("user_session")
if saved:
    st.session_state.user = saved

# ─── UTILITY ──────────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """SHA-256 hash."""
    return hashlib.sha256(password.encode()).hexdigest()

# ─── AUTHENTICATE ─────────────────────────────────────────────────────────────────
def authenticate_user(username: str, password: str) -> bool:
    """Check credentials, then persist user in a 30-day cookie."""
    db_url = st.secrets["db_url"]  # your single‐line DSN

    try:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur  = conn.cursor()
        cur.execute(
            "SELECT id, username, role, hashed_password "
            "FROM users WHERE username = %s AND is_active = TRUE",
            (username,)
        )
        user = cur.fetchone()
        conn.close()

        if user and hash_password(password) == user["hashed_password"]:
            # load assigned project IDs
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            cur  = conn.cursor()
            cur.execute(
                "SELECT project_id FROM user_projects WHERE user_id = %s",
                (user["id"],)
            )
            assigned = [r["project_id"] for r in cur.fetchall()]
            conn.close()

            # save into session_state
            st.session_state.user = {
                "id":                user["id"],
                "username":          user["username"],
                "role":              user["role"],
                "assigned_projects": assigned
            }

            # persist as a 30-day encrypted cookie
            cookies["user_session"] = st.session_state.user
            cookies.save()

            return True
    except Exception as e:
        st.error(f"Database error: {e}")

    return False

# ─── LOGOUT ────────────────────────────────────────────────────────────────────────
def logout():
    """Clear session and cookie, then rerun to show login again."""
    st.session_state.pop("user", None)
    cookies["user_session"] = None
    cookies.save()
    st.experimental_rerun()

# ─── LOGIN FORM ────────────────────────────────────────────────────────────────────
def login_form():
    """
    If user is in session_state, show Logout button;
    otherwise render the login form.
    """
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
